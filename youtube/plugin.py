"""
Universal YouTube Plugin - Works across all bot platforms

This plugin provides YouTube video processing, summarization, and Q&A functionality
that works across different bot platforms using the universal plugin architecture.
"""

import yt_dlp
import os
import tempfile
import logging
import urllib.parse
import subprocess
import re
import aiohttp
import asyncio
import yaml
from datetime import datetime, timedelta
from collections import OrderedDict
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform


class UniversalYouTubePlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("youtube", logger=logger)
        self.version = "2.0.4"  # Testing hot reload with cleanup
        self.description = "Universal YouTube video processing, summarization, and Q&A functionality"
        
        # This plugin supports all platforms
        self.supported_platforms = [BotPlatform.MATRIX, BotPlatform.SIMPLEX]
        
        # Use provided logger or fallback to default
        if not self.logger:
            self.logger = logging.getLogger(f"plugin.{self.name}")
        
        # Load configuration
        self.config = self._load_config()
        
        # Plugin state
        self.transcript_cache = {}  # chat_id -> OrderedDict of URL -> (title, transcript, timestamp)
        self.last_processed_video = {}  # chat_id -> most recent video URL
    
    @classmethod
    def get_youtube_patterns(cls) -> List[str]:
        """Get all supported YouTube URL patterns"""
        return [
            r'((?:https?://)?(?:www\.)?youtube\.com/watch\?v=[a-zA-Z0-9_-]+(?:[&?][^\s]*)?)',
            r'((?:https?://)?(?:www\.)?youtu\.be/[a-zA-Z0-9_-]+(?:[&?][^\s]*)?)',
            r'((?:https?://)?(?:www\.)?youtube\.com/embed/[a-zA-Z0-9_-]+(?:[&?][^\s]*)?)',
            r'((?:https?://)?(?:www\.)?youtube\.com/v/[a-zA-Z0-9_-]+(?:[&?][^\s]*)?)',
            r'((?:https?://)?(?:www\.)?m\.youtube\.com/watch\?v=[a-zA-Z0-9_-]+(?:[&?][^\s]*)?)',
            r'((?:https?://)?(?:www\.)?youtube\.com/shorts/[a-zA-Z0-9_-]+(?:[&?][^\s]*)?)'
        ]
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml"""
        try:
            config_path = Path(__file__).parent / "config.yaml"
            self.logger.info(f"🔍 Looking for config at: {config_path}")
            self.logger.info(f"🔍 Config file exists: {config_path.exists()}")
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    self.logger.info("✅ YouTube configuration loaded successfully from config.yaml")
                    
                    # Log the actual config values being used
                    ai_config = config.get("ai", {})
                    self.logger.info(f"🤖 AI CONFIG - chunk_model: {ai_config.get('chunk_model')}")
                    self.logger.info(f"🤖 AI CONFIG - final_model: {ai_config.get('final_model')}")
                    self.logger.info(f"🤖 AI CONFIG - qa_model: {ai_config.get('qa_model')}")
                    
                    max_tokens = ai_config.get("max_tokens", {})
                    self.logger.info(f"🎯 MAX_TOKENS - chunk_summary: {max_tokens.get('chunk_summary')}")
                    self.logger.info(f"🎯 MAX_TOKENS - final_summary: {max_tokens.get('final_summary')}")
                    self.logger.info(f"🎯 MAX_TOKENS - qa_response: {max_tokens.get('qa_response')}")
                    
                    processing = config.get("processing", {})
                    self.logger.info(f"⚙️ PROCESSING - chunk_size: {processing.get('chunk_size')}")
                    self.logger.info(f"⚙️ PROCESSING - max_chunks: {processing.get('max_chunks')}")
                    
                    return config
            else:
                self.logger.warning("❌ config.yaml not found, using default settings")
                return self._get_default_config()
        except Exception as e:
            self.logger.error(f"❌ Error loading config: {e}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if config.yaml is missing"""
        return {
            "ai": {
                "chunk_model": "mistralai/mistral-small-3.2-24b-instruct:free",
                "final_model": "mistralai/mistral-small-3.2-24b-instruct:free",
                "qa_model": "mistralai/mistral-small-3.2-24b-instruct:free",
                "max_tokens": {"chunk_summary": 800, "final_summary": 5000, "qa_response": 5000},
                "temperature": {"summarization": 0.7, "qa": 0.7}
            },
            "processing": {
                "chunk_size": 8000, "chunk_overlap": 800, "max_chunks": 50,
                "max_qa_transcript_length": 6000
            },
            "cache": {"max_cached_per_room": 5, "expiry_hours": 24},
            "features": {
                "subtitle_extraction": True, "ai_summarization": True,
                "qa_enabled": True, "show_progress": True, "caching_enabled": True
            },
            "advanced": {
                "subtitle_languages": ["en", "en-US", "en-GB"],
                "extraction_timeout": 30, "ai_timeout": 60, "retry_attempts": 3
            }
        }
    
    async def initialize(self, adapter) -> bool:
        """Initialize the plugin with bot adapter"""
        try:
            # Call parent initialization
            if not await super().initialize(adapter):
                return False
            
            self.logger.info(f"Initializing YouTube plugin for {adapter.platform.value} platform")
            
            # Check for required API key
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                self.logger.warning("OPENROUTER_API_KEY not found - summarization features will be disabled")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize YouTube plugin: {e}")
            return False
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return ["youtube", "yt", "video", "summary", "ytconfig"]
    
    async def handle_command(self, context: CommandContext) -> Optional[str]:
        """Handle commands for this plugin"""
        self.logger.info(f"Handling {context.command} command from {context.user_display_name} on {context.platform.value}")
        
        try:
            if context.command in ["youtube", "yt", "video"]:
                return await self._handle_youtube_command(context)
            elif context.command == "summary":
                return await self._handle_summary_command(context)
            elif context.command == "ytconfig":
                return await self._handle_config_command(context)
                
        except Exception as e:
            self.logger.error(f"Error handling {context.command} command: {str(e)}", exc_info=True)
            return f"❌ Error processing {context.command} command"
        
        return None
    
    async def _handle_youtube_command(self, context: CommandContext) -> str:
        """Handle YouTube URL processing and summarization"""
        if not context.has_args:
            return self._get_youtube_help()
        
        args = context.args_raw.strip()
        
        # Check if this contains a YouTube URL + question
        url_match = None
        question = None
        
        # Extract URL and question if both are present
        for pattern in self.get_youtube_patterns():
            match = re.search(pattern, args)
            if match:
                url_match = match.group(1)
                # Check if there's text after the URL (potential question)
                url_end = match.end()
                remaining_text = args[url_end:].strip()
                if remaining_text:
                    question = remaining_text
                self.logger.info(f"🔍 URL found: {url_match}, Question: {question}")
                break
        
        # Check if this is a question about the last video (no URL found)
        if not url_match:
            if self.config["features"]["qa_enabled"]:
                return await self._handle_video_question(context, args)
            else:
                return "❌ Q&A functionality is disabled in configuration"
        
        # Process YouTube URL
        url = url_match
        
        # Check for required API key
        if not os.getenv("OPENROUTER_API_KEY"):
            return "❌ YouTube summary feature requires OPENROUTER_API_KEY in environment variables"
        
        # Check if AI summarization is enabled
        if not self.config["features"]["ai_summarization"]:
            return "❌ AI summarization is disabled in configuration"
        
        try:
            # Send processing message if enabled
            if self.config["features"]["show_progress"]:
                await self.adapter.send_message("🔄 Extracting subtitles from YouTube video...", context)
            
            # Extract subtitles
            subtitles = await self._extract_youtube_subtitles(url)
            
            if not subtitles:
                return "❌ No subtitles found for this video. The video might not have subtitles or be unavailable."
            
            # Get video title
            title = await self._get_youtube_title(url)
            
            # Cache the transcript for Q&A functionality
            self._cache_transcript(url, title, subtitles, context.chat_id)
            
            # If a question was provided with the URL, answer it directly
            if question:
                self.logger.info(f"🤖 Processing Q&A for question: {question}")
                if self.config["features"]["qa_enabled"]:
                    # Send AI processing message if enabled
                    if self.config["features"]["show_progress"]:
                        await self.adapter.send_message("🤖 Generating answer using AI...", context)
                    
                    answer = await self._answer_question_about_video(subtitles, title, question)
                    return f"""📺 **{title}**

**Q:** {question}

**A:** {answer}

💡 Ask more questions with: `!youtube <your question>`"""
                else:
                    return "❌ Q&A functionality is disabled in configuration"
            else:
                self.logger.info("📄 No question provided, generating summary")
            
            # Send AI processing message if enabled (for summary)
            if self.config["features"]["show_progress"]:
                await self.adapter.send_message("🤖 Generating summary using AI...", context)
            
            # Otherwise, provide summary
            summary = await self._summarize_with_ai(subtitles, title)
            
            if summary:
                response = f"""📺 **{title}**

**Summary:**
{summary}

💡 Ask questions about this video using: `!youtube <your question>`"""
                return response
            else:
                return "❌ Failed to generate summary. Please try again later."
                
        except Exception as e:
            self.logger.error(f"Error processing YouTube URL: {e}")
            return f"❌ Error processing YouTube video: {str(e)}"
    
    async def _handle_summary_command(self, context: CommandContext) -> str:
        """Handle summary command for last processed video"""
        chat_id = context.chat_id
        
        if chat_id not in self.last_processed_video:
            return "❌ No recent YouTube video found. Please process a video first with `!youtube <url>`"
        
        last_url = self.last_processed_video[chat_id]
        
        if chat_id in self.transcript_cache and last_url in self.transcript_cache[chat_id]:
            title, transcript, _ = self.transcript_cache[chat_id][last_url]
            
            if context.has_args:
                # Answer question about the video
                question = context.args_raw
                answer = await self._answer_question_about_video(transcript, title, question)
                return f"**Q:** {question}\n\n**A:** {answer}"
            else:
                # Return basic info about last video
                return f"📺 **Last processed video:** {title}\n\n💡 Ask questions with: `!summary <your question>`"
        else:
            return "❌ Transcript not found for the last video. Please process a video again."
    
    async def _handle_video_question(self, context: CommandContext, question: str) -> str:
        """Handle questions about the last processed video"""
        chat_id = context.chat_id
        
        if chat_id not in self.last_processed_video:
            return "❌ No recent YouTube video found. Please process a video first with `!youtube <url>`"
        
        last_url = self.last_processed_video[chat_id]
        
        if chat_id in self.transcript_cache and last_url in self.transcript_cache[chat_id]:
            title, transcript, _ = self.transcript_cache[chat_id][last_url]
            answer = await self._answer_question_about_video(transcript, title, question)
            return f"**Q:** {question}\n\n**A:** {answer}"
        else:
            return "❌ Transcript not found for the last video. Please process a video again."
    
    async def _handle_config_command(self, context: CommandContext) -> str:
        """Handle YouTube configuration commands"""
        if not context.has_args:
            return self._get_config_help()
        
        args = context.args
        action = args[0].lower()
        
        if action == "show":
            return self._show_config()
        elif action == "set" and len(args) >= 3:
            return await self._set_config(args[1], args[2:], context)
        elif action == "get" and len(args) >= 2:
            return self._get_config(args[1])
        elif action == "reload":
            return self._reload_config()
        elif action == "models":
            return self._show_available_models()
        else:
            return self._get_config_help()
    
    def _get_youtube_help(self) -> str:
        """Get YouTube plugin help text"""
        return """📺 **YouTube Plugin Help**

**Commands:**
• `!youtube <url>` - Summarize a YouTube video
• `!youtube <url> <question>` - Process video and answer question directly
• `!yt <url>` - Alias for youtube command  
• `!yt <url> <question>` - Process video and ask question in one command
• `!youtube <question>` - Ask a question about the last processed video
• `!summary` - Show info about last processed video
• `!summary <question>` - Ask a question about the last video
• `!ytconfig` - Configure YouTube plugin settings

**Examples:**
• `!youtube https://youtube.com/watch?v=...` - Get video summary
• `!yt https://youtu.be/abc123 What are the main points?` - Get answer directly
• `!youtube What did they say about X?` - Ask about last video
• `!summary How long is the video?` - Ask specific question

**Supported URLs:**
• youtube.com/watch?v=...
• youtu.be/...
• m.youtube.com/watch?v=...
• youtube.com/shorts/...

**Features:**
• Automatic subtitle extraction
• AI-powered summarization
• Q&A about processed videos
• One-command URL + question processing
• Per-chat video history

**Requirements:** OPENROUTER_API_KEY environment variable required for AI features."""
    
    def _get_config_help(self) -> str:
        """Get configuration help text"""
        return """⚙️ **YouTube Configuration**

**Commands:**
• `!ytconfig show` - Show current configuration
• `!ytconfig get <setting>` - Get specific setting value
• `!ytconfig set <setting> <value>` - Update a setting
• `!ytconfig reload` - Reload configuration from file
• `!ytconfig models` - Show available AI models

**Examples:**
• `!ytconfig show` - Display all settings
• `!ytconfig get ai.chunk_model` - Show chunk model
• `!ytconfig set ai.max_tokens.final_summary 1200` - Set final summary tokens
• `!ytconfig set features.show_progress false` - Disable progress messages

**Configurable Settings:**
• AI models (chunk_model, final_model, qa_model)
• Token limits (chunk_summary, final_summary, qa_response)
• Processing settings (chunk_size, max_chunks)
• Feature toggles (qa_enabled, show_progress)
• Cache settings (max_cached_per_room, expiry_hours)"""
    
    def _show_config(self) -> str:
        """Show current configuration"""
        config_str = "⚙️ **YouTube Plugin Configuration**\n\n"
        
        # AI Settings
        ai = self.config["ai"]
        config_str += f"**🤖 AI Models:**\n"
        config_str += f"• Chunk: `{ai['chunk_model']}`\n"
        config_str += f"• Final: `{ai['final_model']}`\n"
        config_str += f"• Q&A: `{ai['qa_model']}`\n\n"
        
        config_str += f"**📊 Token Limits:**\n"
        tokens = ai["max_tokens"]
        config_str += f"• Chunk Summary: {tokens['chunk_summary']}\n"
        config_str += f"• Final Summary: {tokens['final_summary']}\n"
        config_str += f"• Q&A Response: {tokens['qa_response']}\n\n"
        
        # Processing Settings
        proc = self.config["processing"]
        config_str += f"**🔧 Processing:**\n"
        config_str += f"• Chunk Size: {proc['chunk_size']}\n"
        config_str += f"• Max Chunks: {proc['max_chunks']}\n"
        config_str += f"• Chunk Overlap: {proc['chunk_overlap']}\n\n"
        
        # Features
        feat = self.config["features"]
        config_str += f"**✨ Features:**\n"
        config_str += f"• AI Summarization: {'✅' if feat['ai_summarization'] else '❌'}\n"
        config_str += f"• Q&A: {'✅' if feat['qa_enabled'] else '❌'}\n"
        config_str += f"• Progress Messages: {'✅' if feat['show_progress'] else '❌'}\n"
        config_str += f"• Caching: {'✅' if feat['caching_enabled'] else '❌'}\n"
        
        return config_str
    
    def _get_config(self, setting_path: str) -> str:
        """Get a specific configuration value"""
        try:
            keys = setting_path.split('.')
            value = self.config
            for key in keys:
                value = value[key]
            return f"⚙️ `{setting_path}` = `{value}`"
        except KeyError:
            return f"❌ Setting `{setting_path}` not found"
    
    async def _set_config(self, setting_path: str, value_parts: List[str], context: CommandContext) -> str:
        """Set a configuration value"""
        try:
            # Join value parts back together
            value_str = " ".join(value_parts)
            
            # Parse the value
            if value_str.lower() in ['true', 'false']:
                value = value_str.lower() == 'true'
            elif value_str.isdigit():
                value = int(value_str)
            elif '.' in value_str and value_str.replace('.', '').isdigit():
                value = float(value_str)
            else:
                value = value_str
            
            # Navigate to the setting and update it
            keys = setting_path.split('.')
            config_ref = self.config
            for key in keys[:-1]:
                if key not in config_ref:
                    return f"❌ Invalid setting path: `{setting_path}`"
                config_ref = config_ref[key]
            
            last_key = keys[-1]
            if last_key not in config_ref:
                return f"❌ Invalid setting: `{last_key}`"
            
            old_value = config_ref[last_key]
            config_ref[last_key] = value
            
            # Save configuration to file
            try:
                config_path = Path(__file__).parent / "config.yaml"
                with open(config_path, 'w') as f:
                    yaml.dump(self.config, f, default_flow_style=False, indent=2)
                
                return f"✅ Updated `{setting_path}`: `{old_value}` → `{value}`\n💾 Configuration saved to file"
            except Exception as e:
                # Rollback the change
                config_ref[last_key] = old_value
                return f"❌ Failed to save configuration: {e}"
                
        except Exception as e:
            return f"❌ Error updating setting: {e}"
    
    def _reload_config(self) -> str:
        """Reload configuration from file"""
        try:
            old_config = self.config.copy()
            self.config = self._load_config()
            return "✅ Configuration reloaded successfully from config.yaml"
        except Exception as e:
            return f"❌ Error reloading configuration: {e}"
    
    def _show_available_models(self) -> str:
        """Show available free models"""
        return """🤖 **Available Free Models on OpenRouter**

**Recommended for YouTube:**
• `mistralai/mistral-small-3.2-24b-instruct:free` ⭐ **Best**
• `mistralai/mistral-small-3.1-24b-instruct:free`
• `meta-llama/llama-4-maverick:free`
• `cognitivecomputations/dolphin3.0-mistral-24b:free`

**Rate Limits:** 20 requests/minute, 50-1000 requests/day

**To change model:**
`!ytconfig set ai.chunk_model mistralai/mistral-small-3.2-24b-instruct:free`

**Model Features:**
• Mistral 3.2: Latest, optimized for instructions
• Llama 4: High-capacity MoE architecture  
• Dolphin 3.0: General purpose, good for Q&A"""
    
    def _is_youtube_url(self, text: str) -> bool:
        """Check if text contains a YouTube URL"""
        for pattern in self.get_youtube_patterns():
            if re.search(pattern, text):
                return True
        return False
    
    async def _extract_youtube_subtitles(self, url: str) -> Optional[str]:
        """Extract subtitles from YouTube video using yt-dlp"""
        try:
            # Configure yt-dlp options for subtitle extraction
            ydl_opts = {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en', 'en-US', 'en-GB'],
                'skip_download': True,
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info
                info = ydl.extract_info(url, download=False)
                
                # Try to get subtitles
                subtitles = info.get('subtitles', {})
                automatic_captions = info.get('automatic_captions', {})
                
                # Prefer manual subtitles, fall back to automatic
                sub_data = None
                for lang in ['en', 'en-US', 'en-GB']:
                    if lang in subtitles:
                        sub_data = subtitles[lang]
                        break
                    elif lang in automatic_captions:
                        sub_data = automatic_captions[lang]
                        break
                
                if not sub_data:
                    return None
                
                # Find the best subtitle format
                subtitle_url = None
                for sub_format in sub_data:
                    if sub_format['ext'] in ['vtt', 'srv3', 'srv2', 'srv1']:
                        subtitle_url = sub_format['url']
                        break
                
                if not subtitle_url:
                    return None
                
                # Download and parse subtitles
                async with aiohttp.ClientSession() as session:
                    async with session.get(subtitle_url) as response:
                        if response.status == 200:
                            subtitle_content = await response.text()
                            return self._parse_subtitles(subtitle_content)
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting subtitles: {e}")
            return None
    
    def _parse_subtitles(self, subtitle_content: str) -> str:
        """Parse subtitle content and return clean text"""
        try:
            lines = subtitle_content.split('\n')
            text_lines = []
            
            for line in lines:
                line = line.strip()
                # Skip timestamp lines and empty lines
                if '-->' in line or not line or line.startswith('WEBVTT') or line.isdigit():
                    continue
                
                # Remove HTML tags
                line = re.sub(r'<[^>]+>', '', line)
                
                # Remove timestamps from within text
                line = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3}', '', line)
                
                if line:
                    text_lines.append(line)
            
            return ' '.join(text_lines)
            
        except Exception as e:
            self.logger.error(f"Error parsing subtitles: {e}")
            return ""
    
    async def _get_youtube_title(self, url: str) -> str:
        """Get YouTube video title"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('title', 'Unknown Video')
                
        except Exception as e:
            self.logger.error(f"Error getting video title: {e}")
            return "Unknown Video"
    
    def _cache_transcript(self, url: str, title: str, transcript: str, chat_id: str):
        """Cache transcript for Q&A functionality"""
        if not self.config["features"]["caching_enabled"]:
            return
            
        if chat_id not in self.transcript_cache:
            self.transcript_cache[chat_id] = OrderedDict()
        
        # Add to cache
        self.transcript_cache[chat_id][url] = (title, transcript, datetime.now())
        
        # Update last processed video
        self.last_processed_video[chat_id] = url
        
        # Limit cache size per room
        max_cached = self.config["cache"]["max_cached_per_room"]
        while len(self.transcript_cache[chat_id]) > max_cached:
            self.transcript_cache[chat_id].popitem(last=False)
    
    async def _summarize_with_ai(self, transcript: str, title: str) -> Optional[str]:
        """Summarize transcript using OpenRouter AI with smart approach selection"""
        try:
            self.logger.info(f"🤖 Starting AI summarization for: {title}")
            self.logger.info(f"🤖 Transcript length: {len(transcript)} characters")
            
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                self.logger.error("❌ No OPENROUTER_API_KEY found")
                return None
            
            self.logger.info("✅ API key found, proceeding with summarization")
            
            # Smart approach selection based on transcript length
            max_single_pass_length = 25000  # Characters that can fit in single API call
            
            if len(transcript) <= max_single_pass_length:
                self.logger.info("🚀 Using single-pass summarization (more efficient)")
                return await self._single_pass_summarize(transcript, title, api_key)
            else:
                self.logger.info("📦 Using chunked summarization (transcript too long)")
                return await self._chunked_summarize(transcript, title, api_key)
                
        except Exception as e:
            self.logger.error(f"❌ Error summarizing with AI: {e}")
            import traceback
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return None
    
    async def _single_pass_summarize(self, transcript: str, title: str, api_key: str) -> Optional[str]:
        """Summarize entire transcript in single API call with fallback models"""
        fallback_models = self.config.get("ai", {}).get("fallback_models", {}).get("final", [self.config["ai"]["final_model"]])
        
        for attempt, model in enumerate(fallback_models):
            try:
                self.logger.info(f"🎯 SINGLE-PASS - Attempt {attempt + 1} with model: {model}")
                
                async with aiohttp.ClientSession() as session:
                    result = await self._make_api_call(session, api_key, model, transcript, title, call_type="single_pass")
                    if result:
                        if attempt > 0:
                            self.logger.info(f"✅ Single-pass succeeded with fallback model {model}")
                        return result
                        
            except Exception as e:
                self.logger.error(f"❌ Single-pass failed with {model}: {e}")
                continue
        
        self.logger.error(f"❌ All fallback models failed for single-pass summarization")
        return None
    
    async def _chunked_summarize(self, transcript: str, title: str, api_key: str) -> Optional[str]:
        """Fallback to chunked summarization for very long transcripts"""
        # Original chunked approach but with better parameters
        chunk_size = self.config["processing"]["chunk_size"]
        chunk_overlap = self.config["processing"]["chunk_overlap"]
        max_chunks = self.config["processing"]["max_chunks"]
        
        self.logger.info(f"📊 Chunking parameters: size={chunk_size}, overlap={chunk_overlap}, max={max_chunks}")
        
        chunks = self._chunk_text(transcript, chunk_size, chunk_overlap)
        self.logger.info(f"📦 Created {len(chunks)} chunks from transcript")
        
        if len(chunks) > max_chunks:
            self.logger.info(f"⚠️ Limiting to {max_chunks} chunks (was {len(chunks)})")
            chunks = chunks[:max_chunks]
        
        chunk_summaries = []
        
        self.logger.info(f"🔄 Starting chunk processing with {len(chunks)} chunks...")
        
        async with aiohttp.ClientSession() as session:
            for i, chunk in enumerate(chunks):
                self.logger.info(f"🔥 Processing chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)...")
                
                chunk_summary = await self._summarize_chunk(session, api_key, chunk, title, i + 1, len(chunks))
                if chunk_summary:
                    chunk_summaries.append(chunk_summary)
                    self.logger.info(f"✅ Chunk {i + 1}/{len(chunks)} completed ({len(chunk_summary)} chars)")
                else:
                    self.logger.error(f"❌ Chunk {i + 1}/{len(chunks)} failed")
        
        if not chunk_summaries:
            self.logger.error("❌ No chunk summaries were created")
            return None
        
        self.logger.info(f"📝 Successfully processed {len(chunk_summaries)} chunks")
        
        # If we have multiple chunks, create a final summary
        if len(chunk_summaries) > 1:
            combined_text = "\n\n".join(chunk_summaries)
            self.logger.info(f"🎯 Creating final summary from {len(chunk_summaries)} chunk summaries ({len(combined_text)} chars)")
            
            final_summary = await self._create_final_summary(combined_text, title)
            if final_summary:
                self.logger.info(f"✅ Final summary completed ({len(final_summary)} chars)")
                return final_summary
            else:
                self.logger.error("❌ Final summary creation failed")
                return None
        else:
            self.logger.info("📄 Single chunk, returning chunk summary directly")
            return chunk_summaries[0]
    
    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            
            if end >= len(text):
                break
            
            start = end - overlap
        
        return chunks
    
    async def _summarize_chunk(self, session: aiohttp.ClientSession, api_key: str, chunk: str, title: str, chunk_num: int, total_chunks: int) -> Optional[str]:
        """Summarize a single chunk using OpenRouter with fallback models"""
        fallback_models = self.config.get("ai", {}).get("fallback_models", {}).get("chunk", [self.config["ai"]["chunk_model"]])
        
        for attempt, model in enumerate(fallback_models):
            try:
                self.logger.info(f"🔥 CHUNK {chunk_num}/{total_chunks} - Attempt {attempt + 1} with model: {model}")
                
                result = await self._make_api_call(session, api_key, model, chunk, title, chunk_num, total_chunks, "chunk")
                if result:
                    if attempt > 0:
                        self.logger.info(f"✅ Chunk {chunk_num}/{total_chunks} succeeded with fallback model {model}")
                    return result
                    
            except Exception as e:
                self.logger.error(f"❌ Chunk {chunk_num}/{total_chunks} failed with {model}: {e}")
                continue
        
        self.logger.error(f"❌ All fallback models failed for chunk {chunk_num}/{total_chunks}")
        return None
    
    async def _make_api_call(self, session: aiohttp.ClientSession, api_key: str, model: str, text: str, title: str, chunk_num: int = None, total_chunks: int = None, call_type: str = "summary") -> Optional[str]:
        """Generic API call with error handling"""
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "YouTube Bot Plugin"
            }
            
            # Create appropriate prompt based on call type
            if call_type == "chunk":
                prompt = f"""Summarize this part ({chunk_num}/{total_chunks}) of the YouTube video "{title}".

Focus on:
- Key points and main ideas
- Important details and facts
- Actionable insights
- Notable quotes or examples

Keep it concise but informative:

{text}"""
                max_tokens = self.config["ai"]["max_tokens"]["chunk_summary"]
            elif call_type == "final":
                prompt = f"""Create a comprehensive summary of the YouTube video "{title}" based on these section summaries:

{text}

Create a well-structured summary that:
- Captures the main theme and purpose
- Highlights key points and insights in detail
- Maintains logical flow and structure
- Includes important examples, quotes, and actionable insights
- Is thorough but well-organized

Format with clear sections and bullet points where appropriate."""
                max_tokens = self.config["ai"]["max_tokens"]["final_summary"]
            elif call_type == "single_pass":
                prompt = f"""Create a comprehensive summary of the YouTube video "{title}" based on its complete transcript:

{text}

Create a well-structured summary that:
- Captures the main theme and purpose
- Highlights all key points and insights in detail
- Maintains logical flow and structure
- Includes important examples, quotes, and actionable insights
- Is thorough but well-organized

Format with clear sections and bullet points where appropriate. Be comprehensive since this is the only chance to capture all important information."""
                max_tokens = self.config["ai"]["max_tokens"]["final_summary"]
            else:
                prompt = text
                max_tokens = self.config["ai"]["max_tokens"]["qa_response"]
            
            temperature = self.config["ai"]["temperature"]["summarization"]
            
            data = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            import time
            start_time = time.time()
            
            async with session.post(url, headers=headers, json=data) as response:
                elapsed = time.time() - start_time
                
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content'].strip()
                    self.logger.info(f"✅ {call_type.upper()} API success with {model} ({elapsed:.2f}s, {len(content)} chars)")
                    return content
                else:
                    error_text = await response.text()
                    self.logger.error(f"❌ {call_type.upper()} API error {response.status} with {model} ({elapsed:.2f}s): {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"❌ {call_type.upper()} API exception with {model}: {e}")
            return None
    
    async def _create_final_summary(self, combined_summaries: str, title: str) -> Optional[str]:
        """Create final summary from chunk summaries with fallback models"""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return combined_summaries
        
        fallback_models = self.config.get("ai", {}).get("fallback_models", {}).get("final", [self.config["ai"]["final_model"]])
        
        for attempt, model in enumerate(fallback_models):
            try:
                self.logger.info(f"🎯 FINAL SUMMARY - Attempt {attempt + 1} with model: {model}")
                
                async with aiohttp.ClientSession() as session:
                    result = await self._make_api_call(session, api_key, model, combined_summaries, title, call_type="final")
                    if result:
                        if attempt > 0:
                            self.logger.info(f"✅ Final summary succeeded with fallback model {model}")
                        return result
                        
            except Exception as e:
                self.logger.error(f"❌ Final summary failed with {model}: {e}")
                continue
        
        self.logger.warning("❌ All fallback models failed for final summary, returning combined chunks")
        return combined_summaries
    
    async def _answer_question_about_video(self, transcript: str, title: str, question: str) -> str:
        """Answer a question about the video using AI"""
        try:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                return "❌ AI features require OPENROUTER_API_KEY"
            
            url = "https://openrouter.ai/api/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "YouTube Bot Plugin"
            }
            
            # Limit transcript length for Q&A
            max_qa_length = self.config["processing"]["max_qa_transcript_length"]
            if len(transcript) > max_qa_length:
                transcript = transcript[:max_qa_length] + "..."
            
            prompt = f"""Answer the following question about the YouTube video "{title}" based on its transcript:

Question: {question}

Video transcript:
{transcript}

Provide a helpful, accurate answer based on the content. If the information isn't in the transcript, say so."""
            
            # Log what values are actually being used
            qa_model = self.config["ai"]["qa_model"]
            max_tokens = self.config["ai"]["max_tokens"]["qa_response"]
            temperature = self.config["ai"]["temperature"]["qa"]
            
            self.logger.info(f"💬 Q&A API CALL - model: {qa_model}")
            self.logger.info(f"💬 Q&A API CALL - max_tokens: {max_tokens}")
            self.logger.info(f"💬 Q&A API CALL - temperature: {temperature}")
            self.logger.info(f"💬 Q&A API CALL - transcript length: {len(transcript)} chars")
            
            data = {
                "model": qa_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content'].strip()
                        self.logger.info(f"✅ Q&A API success with {qa_model} ({len(content)} chars)")
                        return content
                    else:
                        error_text = await response.text()
                        self.logger.error(f"❌ Q&A API error {response.status} with {qa_model}: {error_text}")
                        return "❌ Failed to process question with AI"
                        
        except Exception as e:
            self.logger.error(f"Error answering question: {e}")
            return f"❌ Error processing question: {str(e)}"
    
    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        self.transcript_cache.clear()
        self.last_processed_video.clear()
        self.logger.info("Universal YouTube plugin cleanup completed")


# Export the plugin class for the plugin manager to discover