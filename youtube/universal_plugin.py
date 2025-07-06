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
from datetime import datetime
from collections import OrderedDict
from typing import Optional, Tuple, List
from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform


class UniversalYouTubePlugin(UniversalBotPlugin):
    def __init__(self):
        super().__init__("youtube")
        self.version = "2.0.0"  # Updated for universal support
        self.description = "Universal YouTube video processing, summarization, and Q&A functionality"
        
        # This plugin supports all platforms
        self.supported_platforms = [BotPlatform.MATRIX, BotPlatform.SIMPLEX]
        
        self.logger = logging.getLogger(f"plugin.{self.name}")
        
        # Plugin configuration
        self.chunk_size = 8000
        self.chunk_overlap = 800
        self.max_chunks = 10
        self.max_cached_transcripts_per_room = 5
        self.transcript_cache = {}  # chat_id -> OrderedDict of URL -> (title, transcript, timestamp)
        self.last_processed_video = {}  # chat_id -> most recent video URL
    
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
        return ["youtube", "yt", "video", "summary"]
    
    async def handle_command(self, context: CommandContext) -> Optional[str]:
        """Handle commands for this plugin"""
        self.logger.info(f"Handling {context.command} command from {context.user_display_name} on {context.platform.value}")
        
        try:
            if context.command in ["youtube", "yt", "video"]:
                return await self._handle_youtube_command(context)
            elif context.command == "summary":
                return await self._handle_summary_command(context)
                
        except Exception as e:
            self.logger.error(f"Error handling {context.command} command: {str(e)}", exc_info=True)
            return f"❌ Error processing {context.command} command"
        
        return None
    
    async def _handle_youtube_command(self, context: CommandContext) -> str:
        """Handle YouTube URL processing and summarization"""
        if not context.has_args:
            return self._get_youtube_help()
        
        args = context.args_raw.strip()
        
        # Check if this is a question about the last video
        if not self._is_youtube_url(args):
            return await self._handle_video_question(context, args)
        
        # Process YouTube URL
        url = args
        
        # Check for required API key
        if not os.getenv("OPENROUTER_API_KEY"):
            return "❌ YouTube summary feature requires OPENROUTER_API_KEY in environment variables"
        
        try:
            # Send processing message
            await self.adapter.send_message("🔄 Extracting subtitles from YouTube video...", context)
            
            # Extract subtitles
            subtitles = await self._extract_youtube_subtitles(url)
            
            if not subtitles:
                return "❌ No subtitles found for this video. The video might not have subtitles or be unavailable."
            
            # Send AI processing message
            await self.adapter.send_message("🤖 Generating summary using AI...", context)
            
            # Get video title
            title = await self._get_youtube_title(url)
            
            # Cache the transcript for Q&A functionality
            self._cache_transcript(url, title, subtitles, context.chat_id)
            
            # Summarize using AI
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
    
    def _get_youtube_help(self) -> str:
        """Get YouTube plugin help text"""
        return """📺 **YouTube Plugin Help**

**Commands:**
• `!youtube <url>` - Summarize a YouTube video
• `!yt <url>` - Alias for youtube command
• `!youtube <question>` - Ask a question about the last processed video
• `!summary` - Show info about last processed video
• `!summary <question>` - Ask a question about the last video

**Examples:**
• `!youtube https://youtube.com/watch?v=...` - Get video summary
• `!youtube What are the main points?` - Ask about last video
• `!summary How long is the video?` - Ask specific question

**Features:**
• Automatic subtitle extraction
• AI-powered summarization
• Q&A about processed videos
• Per-chat video history

**Requirements:** OPENROUTER_API_KEY environment variable required for AI features."""
    
    def _is_youtube_url(self, text: str) -> bool:
        """Check if text contains a YouTube URL"""
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in youtube_patterns:
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
        if chat_id not in self.transcript_cache:
            self.transcript_cache[chat_id] = OrderedDict()
        
        # Add to cache
        self.transcript_cache[chat_id][url] = (title, transcript, datetime.now())
        
        # Update last processed video
        self.last_processed_video[chat_id] = url
        
        # Limit cache size per room
        while len(self.transcript_cache[chat_id]) > self.max_cached_transcripts_per_room:
            self.transcript_cache[chat_id].popitem(last=False)
    
    async def _summarize_with_ai(self, transcript: str, title: str) -> Optional[str]:
        """Summarize transcript using OpenRouter AI"""
        try:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                return None
            
            # Chunk the transcript if it's too long
            chunks = self._chunk_text(transcript, self.chunk_size, self.chunk_overlap)
            
            if len(chunks) > self.max_chunks:
                chunks = chunks[:self.max_chunks]
            
            chunk_summaries = []
            
            async with aiohttp.ClientSession() as session:
                for i, chunk in enumerate(chunks):
                    chunk_summary = await self._summarize_chunk(session, api_key, chunk, title, i + 1, len(chunks))
                    if chunk_summary:
                        chunk_summaries.append(chunk_summary)
            
            if not chunk_summaries:
                return None
            
            # If we have multiple chunks, create a final summary
            if len(chunk_summaries) > 1:
                combined_text = "\n\n".join(chunk_summaries)
                final_summary = await self._create_final_summary(combined_text, title)
                return final_summary
            else:
                return chunk_summaries[0]
                
        except Exception as e:
            self.logger.error(f"Error summarizing with AI: {e}")
            return None
    
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
        """Summarize a single chunk using OpenRouter"""
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "YouTube Bot Plugin"
            }
            
            prompt = f"""Summarize this part ({chunk_num}/{total_chunks}) of the YouTube video "{title}".

Focus on:
- Key points and main ideas
- Important details and facts
- Actionable insights
- Notable quotes or examples

Keep it concise but informative:

{chunk}"""
            
            data = {
                "model": "mistralai/mistral-small-3.2-24b-instruct:free",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.7
            }
            
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content'].strip()
                else:
                    self.logger.error(f"OpenRouter API error: {response.status}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error summarizing chunk: {e}")
            return None
    
    async def _create_final_summary(self, combined_summaries: str, title: str) -> Optional[str]:
        """Create final summary from chunk summaries"""
        try:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                return combined_summaries
            
            url = "https://openrouter.ai/api/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "YouTube Bot Plugin"
            }
            
            prompt = f"""Create a comprehensive summary of the YouTube video "{title}" based on these section summaries:

{combined_summaries}

Create a well-structured summary that:
- Captures the main theme and purpose
- Highlights key points and insights
- Maintains logical flow
- Is engaging and informative

Format with clear sections if appropriate."""
            
            data = {
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 800,
                "temperature": 0.7
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content'].strip()
                    else:
                        return combined_summaries
                        
        except Exception as e:
            self.logger.error(f"Error creating final summary: {e}")
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
            if len(transcript) > 6000:
                transcript = transcript[:6000] + "..."
            
            prompt = f"""Answer the following question about the YouTube video "{title}" based on its transcript:

Question: {question}

Video transcript:
{transcript}

Provide a helpful, accurate answer based on the content. If the information isn't in the transcript, say so."""
            
            data = {
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 400,
                "temperature": 0.7
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content'].strip()
                    else:
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