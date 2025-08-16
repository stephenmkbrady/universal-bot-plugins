"""
Universal AI Plugin - Works across all bot platforms

This plugin provides AI-powered features including magic 8-ball, advice, and other
AI-generated content that works across different bot platforms using the universal plugin architecture.
"""

import logging
import os
import aiohttp
import time
import re
import yaml
import random
from typing import List, Optional, Set, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform

@dataclass
class ChatMessage:
    """Represents a stored chat message"""
    content: str
    sender: str
    timestamp: datetime
    message_id: str
    chat_id: str

class MessageIndexParser:
    """Parses message index selections like '1', '1-3', '1,4,6', '2-5,8,10-12'"""
    
    @staticmethod
    def parse_message_indices(index_str: str) -> Set[int]:
        """
        Parse message index string into set of indices
        Examples:
        - '1' → {1}
        - '1-3' → {1, 2, 3}  
        - '1,4,6' → {1, 4, 6}
        - '2-5,8,10-12' → {2, 3, 4, 5, 8, 10, 11, 12}
        """
        indices = set()
        
        # Split by commas first
        parts = index_str.strip().split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part and not part.startswith('-'):
                # Range like '1-3' or '10-12'
                try:
                    start, end = map(int, part.split('-', 1))
                    if start <= end:
                        indices.update(range(start, end + 1))
                except ValueError:
                    continue  # Skip invalid ranges
            else:
                # Single number
                try:
                    indices.add(int(part))
                except ValueError:
                    continue  # Skip invalid numbers
        
        return indices

class MessageHistory:
    """Manages message history per chat with rolling buffer"""
    
    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self.chat_histories: Dict[str, List[ChatMessage]] = {}
    
    def add_message(self, chat_id: str, message: ChatMessage):
        """Add a message to the chat history"""
        if chat_id not in self.chat_histories:
            self.chat_histories[chat_id] = []
        
        history = self.chat_histories[chat_id]
        history.append(message)
        
        # Maintain rolling buffer - remove oldest if over limit
        if len(history) > self.max_messages:
            history.pop(0)
    
    def get_messages_by_indices(self, chat_id: str, indices: Set[int]) -> List[ChatMessage]:
        """Get messages by their indices (1-based, 1 = most recent)"""
        if chat_id not in self.chat_histories:
            return []
        
        history = self.chat_histories[chat_id]
        if not history:
            return []
        
        selected_messages = []
        for index in sorted(indices):
            # Convert 1-based index to 0-based from end of list
            # index 1 = last message, index 2 = second-to-last, etc.
            array_index = len(history) - index
            if 0 <= array_index < len(history):
                selected_messages.append(history[array_index])
        
        # Return in chronological order (oldest first)
        return sorted(selected_messages, key=lambda m: m.timestamp)
    
    def get_chat_message_count(self, chat_id: str) -> int:
        """Get number of available messages for a chat"""
        return len(self.chat_histories.get(chat_id, []))


class UniversalAIPlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("ai", logger=logger)
        self.version = "2.1.0"  # Updated with message context support
        self.description = "Universal AI-powered features including magic 8-ball, advice, and content generation with message context"
        
        # Universal plugin - supports all platforms with message history service
        self.supported_platforms = []  # Empty means supports all platforms
        
        if not self.logger:
            self.logger = logging.getLogger(f"plugin.{self.name}")
        
        # Load configuration from YAML file
        self.config = self._load_config()
        
        # AI configuration with fallback to environment variables
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.nist_beacon_url = self.config.get('nist', {}).get('beacon_url', os.getenv("NIST_BEACON_URL", "https://beacon.nist.gov/beacon/2.0/pulse/last"))
        self.openrouter_url = self.config.get('api', {}).get('url', os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions"))
        self.model = self.config.get('primary_model', os.getenv("AI_MODEL", "cognitivecomputations/dolphin3.0-mistral-24b:free"))
        
        # Message history management
        message_history_config = self.config.get('message_history', {})
        self.max_messages = message_history_config.get('max_messages', int(os.getenv("AI_MAX_MESSAGES", "50")))
        self.message_history = MessageHistory(max_messages=self.max_messages)
        
        # Configurable limits from config or environment
        self.max_recent_display = message_history_config.get('max_recent_display', int(os.getenv("AI_MAX_RECENT_DISPLAY", "10")))
        self.max_preview_length = message_history_config.get('max_preview_length', int(os.getenv("AI_MAX_PREVIEW_LENGTH", "100")))
        self.nist_update_interval = self.config.get('nist', {}).get('update_interval', int(os.getenv("AI_NIST_UPDATE_INTERVAL", "60")))
        self.api_timeout = self.config.get('api', {}).get('timeout', int(os.getenv("AI_API_TIMEOUT", "10")))
        
        # Token limits for different commands from config
        tokens_config = self.config.get('tokens', {})
        self.tokens_8ball = tokens_config.get('8ball', int(os.getenv("AI_TOKENS_8BALL", "100")))
        self.tokens_advice = tokens_config.get('advice', int(os.getenv("AI_TOKENS_ADVICE", "200")))
        self.tokens_bible = tokens_config.get('bible', int(os.getenv("AI_TOKENS_BIBLE", "300")))
        self.tokens_song = tokens_config.get('song', int(os.getenv("AI_TOKENS_SONG", "400")))
        self.tokens_ai = tokens_config.get('ai', int(os.getenv("AI_TOKENS_AI", "500")))
        self.tokens_ask = tokens_config.get('ask', int(os.getenv("AI_TOKENS_ASK", "600")))
        self.parser = MessageIndexParser()
        
        # Public commands management - will read from admin_config.yml
        self.admin_config_path = '/home/user/Documents/DEV/SIMPLEX_BOT_V2/admin_config.yml'
    
    async def _on_initialize(self) -> bool:
        """Initialize the plugin with bot adapter"""
        try:
            self.logger.info(f"Initializing AI plugin for {self.adapter.platform.value} platform")
            
            # Check for required API key
            if not self.openrouter_api_key:
                self.logger.warning("OPENROUTER_API_KEY not found - AI features will be disabled")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI plugin: {e}")
            return False
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return ["8ball", "advice", "advise", "bible", "song", "nist", "ai", "ask", "msghistory", "publiccmds", "publiccmd"]
    
    async def handle_command(self, context: CommandContext) -> Optional[str]:
        """Handle commands for this plugin"""
        self.logger.info(f"Handling {context.command} command from {context.user_display_name} on {context.platform.value}")
        
        # First, get conversation context using platform service (platform-agnostic)
        await self._get_conversation_context(context)
        
        try:
            if context.command == "8ball":
                return await self._handle_8ball(context)
            elif context.command in ["advice", "advise"]:
                return await self._handle_advice(context)
            elif context.command == "bible":
                return await self._handle_bible(context)
            elif context.command == "song":
                return await self._handle_song(context)
            elif context.command == "nist":
                return await self._handle_nist(context)
            elif context.command in ["ai", "ask"]:
                return await self._handle_ai_question(context)
            elif context.command == "msghistory":
                return await self._handle_msghistory_debug(context)
            elif context.command == "publiccmds":
                return await self._handle_publiccmds_list(context)
            elif context.command == "publiccmd":
                return await self._handle_publiccmd_manage(context)
                
        except Exception as e:
            self.logger.error(f"Error handling {context.command} command: {str(e)}", exc_info=True)
            return f"❌ Error processing {context.command} command"
        
        return None
    
    async def handle_message(self, context: CommandContext) -> Optional[str]:
        """Store non-command messages in history for context"""
        try:
            self.logger.info(f"📥 AI PLUGIN: handle_message called for: '{context.args_raw}' from {context.user_display_name} in {context.chat_id}")
            
            # Only store non-command messages
            if not context.args_raw.startswith('!'):
                self.logger.info(f"📥 AI PLUGIN: Storing non-command message")
                message = ChatMessage(
                    content=context.args_raw,
                    sender=context.user_display_name,
                    timestamp=datetime.now(),
                    message_id=f"{context.chat_id}_{context.user_id}_{datetime.now().timestamp()}",
                    chat_id=context.chat_id
                )
                
                self.message_history.add_message(context.chat_id, message)
                total_messages = self.message_history.get_chat_message_count(context.chat_id)
                self.logger.info(f"✅ AI PLUGIN: Stored message from {context.user_display_name} in {context.chat_id} (total: {total_messages})")
            else:
                self.logger.info(f"📥 AI PLUGIN: Skipping command message (starts with !)")
                
        except Exception as e:
            self.logger.error(f"❌ AI PLUGIN: Error storing message: {e}")
        
        return None  # Don't respond to regular messages
    
    async def _handle_msghistory_debug(self, context: CommandContext) -> str:
        """Debug command to show message history state"""
        try:
            chat_id = context.chat_id
            total_messages = self.message_history.get_chat_message_count(chat_id)
            
            debug_info = f"🔍 **Message History Debug for {chat_id}**\n\n"
            debug_info += f"**Total Messages:** {total_messages}\n\n"
            
            if chat_id in self.message_history.chat_histories:
                all_messages = self.message_history.chat_histories[chat_id]
                debug_info += f"**Recent Messages (last {self.max_recent_display}):**\n"
                
                recent_messages = all_messages[-self.max_recent_display:] if all_messages else []
                for i, msg in enumerate(recent_messages):
                    debug_info += f"{i+1}. [{msg.sender}] {msg.timestamp.strftime('%H:%M:%S')}: {msg.content[:self.max_preview_length]}...\n"
                    
                if not recent_messages:
                    debug_info += "No messages stored yet.\n"
            else:
                debug_info += f"**No chat history found for chat_id:** `{chat_id}`\n"
            
            debug_info += f"\n**Chat histories tracked:** {list(self.message_history.chat_histories.keys())}"
            
            return debug_info
            
        except Exception as e:
            return f"❌ Error getting message history debug: {e}"
    
    async def _handle_publiccmds_list(self, context: CommandContext) -> str:
        """List all public commands"""
        try:
            public_commands = self._load_admin_config().get('public_commands', [])
            
            if not public_commands:
                return "📋 **Public Commands**\n\nNo public commands are currently enabled."
            
            public_list = sorted(list(public_commands))
            commands_text = "\n".join([f"• `!{cmd}`" for cmd in public_list])
            
            return f"📋 **Public Commands** ({len(public_list)} enabled)\n\n{commands_text}\n\n💡 Use `!publiccmd add/remove <command>` to manage"
            
        except Exception as e:
            return f"❌ Error listing public commands: {e}"
    
    async def _handle_publiccmd_manage(self, context: CommandContext) -> str:
        """Manage public commands (add/remove)"""
        try:
            if not context.has_args:
                return """📋 **Public Command Management**

**Usage:**
• `!publiccmd add <command>` - Add command to public list
• `!publiccmd remove <command>` - Remove command from public list  
• `!publiccmd list` - Show current public commands

**Available commands:** 8ball, advice, advise, bible, song, nist, ai, ask, msghistory

**Examples:**
• `!publiccmd add 8ball`
• `!publiccmd remove bible`"""

            args = context.args
            if len(args) < 2:
                return "❌ **Usage:** `!publiccmd <add/remove> <command>`"
            
            action = args[0].lower()
            command = args[1].lower()
            
            # Available commands from this plugin
            available_commands = ["8ball", "advice", "advise", "bible", "song", "nist", "ai", "ask", "msghistory"]
            
            if action == "list":
                return await self._handle_publiccmds_list(context)
            
            if command not in available_commands:
                return f"❌ **Invalid command:** `{command}`\n💡 Available: {', '.join(available_commands)}"
            
            # Load current admin config
            admin_config = self._load_admin_config()
            public_commands = set(admin_config.get('public_commands', []))
            
            if action == "add":
                if command in public_commands:
                    return f"ℹ️ Command `!{command}` is already public"
                
                public_commands.add(command)
                admin_config['public_commands'] = sorted(list(public_commands))
                self._save_admin_config(admin_config)
                return f"✅ Added `!{command}` to public commands\n📋 Public commands: {len(public_commands)} total"
                
            elif action == "remove":
                if command not in public_commands:
                    return f"ℹ️ Command `!{command}` is not in public commands"
                
                public_commands.remove(command)
                admin_config['public_commands'] = sorted(list(public_commands))
                self._save_admin_config(admin_config)
                return f"✅ Removed `!{command}` from public commands\n📋 Public commands: {len(public_commands)} total"
                
            else:
                return f"❌ **Invalid action:** `{action}`\n💡 Use: add, remove, or list"
                
        except Exception as e:
            return f"❌ Error managing public commands: {e}"
    
    async def _handle_8ball(self, context: CommandContext) -> str:
        """Handle magic 8-ball command"""
        if not context.has_args:
            return "🎱 **Magic 8-Ball**\n\nAsk me a yes/no question!\nExample: `!8ball Will it rain today?`"
        
        if not self.openrouter_api_key:
            return "❌ AI features require OPENROUTER_API_KEY environment variable"
        
        question = context.args_raw
        
        try:
            # Get NIST beacon randomness
            is_positive = await self._get_nist_beacon_value()
            
            # Generate AI response
            response = await self._generate_ai_fortune(question, is_positive)
            
            return f"🎱 **Magic 8-Ball**\n\n**Question:** {question}\n\n**Answer:** {response}"
            
        except Exception as e:
            self.logger.error(f"Error in 8ball command: {e}")
            return "❌ The magic 8-ball is currently unavailable. Try again later!"
    
    async def _handle_advice(self, context: CommandContext) -> str:
        """Handle advice command"""
        if not self.openrouter_api_key:
            return "❌ AI features require OPENROUTER_API_KEY environment variable"
        
        topic = context.args_raw if context.has_args else "general life"
        
        try:
            advice = await self._generate_advice(topic)
            return f"💡 **AI Advice**\n\n**Topic:** {topic}\n\n{advice}"
            
        except Exception as e:
            self.logger.error(f"Error generating advice: {e}")
            return "❌ Unable to generate advice at the moment. Please try again later."
    
    async def _handle_bible(self, context: CommandContext) -> str:
        """Handle bible verse command"""
        if not self.openrouter_api_key:
            return "❌ AI features require OPENROUTER_API_KEY environment variable"
        
        if context.has_args:
            topic = context.args_raw
        else:
            # Use NIST beacon to randomly select a topic
            random_topics = [
                "hope", "strength", "peace", "love", "faith", "wisdom", "courage", 
                "forgiveness", "joy", "patience", "kindness", "perseverance", 
                "comfort", "guidance", "trust", "protection", "healing", "gratitude",
                "humility", "mercy", "grace", "salvation", "redemption", "renewal"
            ]
            beacon_int = await self._get_nist_beacon_random_number()
            current_second = int(time.time())
            combined_randomness = beacon_int + current_second
            topic_index = combined_randomness % len(random_topics)
            topic = random_topics[topic_index]
        
        try:
            verse = await self._generate_bible_verse(topic)
            return f"📖 **Bible Verse**\n\n**Topic:** {topic}\n\n{verse}"
            
        except Exception as e:
            self.logger.error(f"Error generating bible verse: {e}")
            return "❌ Unable to retrieve a bible verse at the moment."
    
    async def _handle_song(self, context: CommandContext) -> str:
        """Handle song generation command"""
        if not self.openrouter_api_key:
            return "❌ AI features require OPENROUTER_API_KEY environment variable"
        
        topic = context.args_raw if context.has_args else "happiness"
        
        try:
            song = await self._generate_song(topic)
            return f"🎵 **AI-Generated Song**\n\n**Theme:** {topic}\n\n{song}"
            
        except Exception as e:
            self.logger.error(f"Error generating song: {e}")
            return "❌ Unable to compose a song at the moment."
    
    async def _handle_nist(self, context: CommandContext) -> str:
        """Handle NIST beacon randomness command"""
        try:
            beacon_data = await self._get_nist_beacon_full_data()
            if not beacon_data:
                return "❌ Unable to access NIST Randomness Beacon at the moment."
            
            beacon_int = int(beacon_data['outputValue'], 16)
            is_positive = (beacon_int % 2) == 0
            timestamp = beacon_data.get('timeStamp', 'Unknown')
            pulse_index = beacon_data.get('pulseIndex', 'Unknown')
            
            response = f"""🔢 **NIST Randomness Beacon**

**Current Value:** {beacon_int}
**Polarity:** {'POSITIVE' if is_positive else 'NEGATIVE'}
**Pulse Index:** {pulse_index}
**Timestamp:** {timestamp}
**Source:** US National Institute of Standards and Technology

The NIST Randomness Beacon provides publicly verifiable randomness.
This value changes every {self.nist_update_interval} seconds and is cryptographically signed."""
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error getting NIST beacon: {e}")
            return "❌ Unable to access NIST Randomness Beacon at the moment."
    
    async def _handle_ai_question(self, context: CommandContext) -> str:
        """Handle general AI question with optional message context"""
        if not context.has_args:
            return self._show_ai_help()
        
        if not self.openrouter_api_key:
            return "❌ AI features require OPENROUTER_API_KEY environment variable"
        
        # Parse command for message index flags
        args = context.args.copy()
        selected_messages = []
        
        # Debug logging
        self.logger.info(f"AI command debug - args: {args}, args_raw: '{context.args_raw}'")
        
        # Check for message context flag (support both -m and m formats)
        if args and (args[0].startswith('-m') or args[0].startswith('m')):
            message_flag = args.pop(0)
            
            # Extract index part (support multiple formats)
            if message_flag == '-m' and args:
                # Format: -m 1,4,6 (old format)
                index_str = args.pop(0)
            elif message_flag == 'm' and args:
                # Format: m 1,4,6 (new format with space)
                index_str = args.pop(0)
            elif message_flag.startswith('-m') and len(message_flag) > 2:
                # Format: -m1,4,6 (old format)
                index_str = message_flag[2:]
            elif message_flag.startswith('m') and len(message_flag) > 1:
                # Format: m1,4,6 (new format without space)
                index_str = message_flag[1:]
            else:
                return "❌ **Invalid message context usage**\n💡 Use: `!ask m1,4,6 your question`"
            
            # Parse the indices
            try:
                indices = self.parser.parse_message_indices(index_str)
                if not indices:
                    return f"❌ **No valid message indices found**\n🔍 Parsed from: `{index_str}`"
                
                # Get selected messages
                selected_messages = self.message_history.get_messages_by_indices(
                    context.chat_id, indices
                )
                
                available_count = self.message_history.get_chat_message_count(context.chat_id)
                
                # Add detailed debugging
                self.logger.info(f"🔍 MESSAGE HISTORY DEBUG:")
                self.logger.info(f"  - Chat ID: {context.chat_id}")
                self.logger.info(f"  - Requested indices: {sorted(indices)}")
                self.logger.info(f"  - Available message count: {available_count}")
                self.logger.info(f"  - Selected messages: {len(selected_messages)}")
                
                # Log recent messages for debugging
                if context.chat_id in self.message_history.chat_histories:
                    all_messages = self.message_history.chat_histories[context.chat_id]
                    recent_messages = all_messages[-5:] if all_messages else []
                    self.logger.info(f"  - Recent messages (last 5):")
                    for i, msg in enumerate(recent_messages):
                        self.logger.info(f"    {i+1}. [{msg.sender}]: {msg.content[:self.max_preview_length]}...")
                else:
                    self.logger.info(f"  - No chat history found for chat_id: {context.chat_id}")
                
                if not selected_messages:
                    return f"❌ **No messages found for indices: {sorted(indices)}**\n💡 Only {available_count} messages available in this chat..."
                
                self.logger.info(f"Using {len(selected_messages)} context messages for AI query from {context.user_display_name}")
                
            except Exception as e:
                return f"❌ **Error parsing message indices**: {str(e)}\n💡 Use format: `1`, `1-3`, `1,4,6`"
        
        # Remaining args are the AI query
        if not args:
            return "❌ **No question provided**\n💡 Use: `!ask your question here`"
        
        question = " ".join(args)
        
        try:
            # Process the AI request with context
            answer = await self._generate_ai_response_with_context(question, selected_messages)
            
            # Format response
            response = f"🤖 *AI Assistant*\n"
            
            if selected_messages:
                response += f"📝 Context: Used {len(selected_messages)} previous message(s)\n"
            
            response += f"{answer}"
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating AI response: {e}")
            return "❌ Unable to process your question at the moment."
    
    async def _get_nist_beacon_full_data(self) -> Optional[dict]:
        """Get full NIST Randomness Beacon data"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.nist_beacon_url,
                    timeout=aiohttp.ClientTimeout(total=self.api_timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['pulse']
                    else:
                        self.logger.warning(f"NIST beacon returned HTTP {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"Error getting NIST beacon: {e}")
            return None

    async def _get_nist_beacon_random_number(self) -> int:
        """Get current NIST Randomness Beacon value and return as integer"""
        try:
            beacon_data = await self._get_nist_beacon_full_data()
            if beacon_data:
                output_value = beacon_data['outputValue']
                beacon_int = int(output_value, 16)
                return beacon_int
            else:
                # Fallback to timestamp
                return int(time.time())
        except Exception as e:
            self.logger.error(f"Error processing NIST beacon data: {e}")
            return int(time.time())
    
    async def _get_nist_beacon_value(self) -> bool:
        """Get current NIST Randomness Beacon value and determine positive/negative"""
        beacon_int = await self._get_nist_beacon_random_number()
        return (beacon_int % 2) == 0
    
    async def _generate_ai_fortune(self, question: str, is_positive: bool) -> str:
        """Generate a magic 8-ball style response"""
        polarity = "positive and encouraging" if is_positive else "negative or cautionary"
        
        prompt = f"""You are a mystical magic 8-ball. The user asked: "{question}"

Based on cosmic randomness from NIST, your response should be {polarity}.

Respond like a classic magic 8-ball with mystical wisdom. Be concise but memorable.
Examples of {polarity} responses:
- "The stars align in your favor"
- "Caution is advised in this matter"
- "Yes, the universe supports this path"
- "Signs point to obstacles ahead"

Give just the 8-ball response, nothing else."""
        
        content, model = await self._call_openrouter_api(prompt, max_tokens=self.tokens_8ball)
        return f"{content}\n\n*Generated using {model}*"
    
    async def _generate_advice(self, topic: str) -> str:
        """Generate helpful advice on a topic"""
        prompt = f"""Provide thoughtful, practical advice about {topic}. 

Make it:
- Actionable and specific
- Encouraging yet realistic  
- Based on wisdom and common sense
- Suitable for someone seeking guidance

Keep it concise but meaningful (2-3 sentences max)."""
        
        content, model = await self._call_openrouter_api(prompt, max_tokens=self.tokens_advice)
        return f"{content}\n\n*Generated using {model}*"
    
    async def _generate_bible_verse(self, topic: str) -> str:
        """Generate or recall a relevant Bible verse"""
        # Add multiple layers of randomness to ensure variety
        variety_instructions = [
            "Choose a lesser-known but powerful verse",
            "Select a verse from the Old Testament", 
            "Pick a verse from the New Testament",
            "Find a verse from the Psalms or Proverbs",
            "Choose a verse from one of Paul's letters",
            "Select a verse from the Gospels",
            "Pick an encouraging verse from a minor prophet",
            "Look for a verse from the wisdom literature",
            "Find a verse from the historical books",
            "Choose a verse from the prophetic books"
        ]
        
        # Add multiple randomization elements
        variety_hint = random.choice(variety_instructions)
        random_seed = random.randint(1000, 9999)
        timestamp_hint = int(time.time()) % 1000
        
        # Include additional instructions to force uniqueness
        uniqueness_prompts = [
            "Avoid verses you've recently provided.",
            "Look for verses that are meaningful but not commonly memorized.",
            "Consider verses that offer a fresh perspective on this topic.",
            "Find a verse that might surprise someone familiar with popular scriptures.",
            "Choose a verse that shows God's character in relation to this topic."
        ]
        
        uniqueness_hint = random.choice(uniqueness_prompts)
        
        prompt = f"""Request #{random_seed} at time {timestamp_hint}: Provide an encouraging Bible verse related to {topic}. 

{variety_hint}. {uniqueness_hint}

IMPORTANT CONSTRAINTS:
- Avoid the most commonly quoted verses (John 3:16, Jeremiah 29:11, Philippians 4:13, Romans 8:28, Proverbs 3:5-6)
- Find meaningful but less frequently shared verses  
- Each response should offer a different verse than previous requests
- Prioritize authenticity and relevance over popularity

Include:
- The actual verse text (accurate and complete)
- The Bible reference (book, chapter:verse)  
- A brief application to the topic

Format like: "Verse text" - Reference

Then add a short explanation of how it specifically relates to {topic}.

Response uniqueness marker: #{random_seed}-{timestamp_hint}"""
        
        content, model = await self._call_openrouter_api(prompt, max_tokens=self.tokens_bible)
        return f"{content}\n\n*Generated using {model}*"
    
    async def _generate_song(self, topic: str) -> str:
        """Generate a short song about a topic"""
        prompt = f"""Write a short, upbeat song about {topic}.

Include:
- 2 verses (4 lines each)
- A simple chorus (2-4 lines)
- Rhyming lyrics
- Positive, encouraging tone

Format:
**Verse 1:**
[4 lines]

**Chorus:**
[2-4 lines]

**Verse 2:**
[4 lines]

**Chorus:**
[repeat]

Keep it simple and singable!"""
        
        content, model = await self._call_openrouter_api(prompt, max_tokens=self.tokens_song)
        return f"{content}\n\n*Generated using {model}*"
    
    async def _generate_ai_response(self, question: str) -> str:
        """Generate a general AI response"""
        prompt = f"""Answer this question helpfully and accurately: {question}

Provide:
- Clear, informative response
- Practical insights where applicable
- Honest acknowledgment if uncertain
- Conversational but professional tone

Keep response concise but comprehensive."""
        
        content, model = await self._call_openrouter_api(prompt, max_tokens=self.tokens_ai)
        return f"{content}\n\n*Generated using {model}*"
    
    async def _generate_ai_response_with_context(self, question: str, selected_messages: List[ChatMessage]) -> str:
        """Generate AI response with optional message context"""
        # Build context from selected messages
        context_text = ""
        if selected_messages:
            context_text = "CONTEXT:\n"
            for i, msg in enumerate(selected_messages, 1):
                context_text += f"[{i}] {msg.sender}: {msg.content}\n"
            context_text += "\n"
        
        # Combine context and query
        prompt = f"""{context_text}USER QUERY: {question}

Answer the user's question helpfully and accurately. If context was provided, use it to inform your response.

Provide:
- Clear, informative response
- Reference context when relevant
- Practical insights where applicable
- Honest acknowledgment if uncertain
- Conversational but professional tone

Keep response concise but comprehensive."""
        
        content, model = await self._call_openrouter_api(prompt, max_tokens=self.tokens_ask)
        return f"{content}\n\n*Generated using {model}*"
    
    def _show_ai_help(self) -> str:
        """Show AI assistant help information"""
        return """🤖 *AI Assistant Plugin*

**AI Commands Available:**
• `!8ball <question>` - Magic 8-ball with NIST randomness
• `!advice [topic]` - Get helpful advice on any topic
• `!bible [topic]` - Get random Bible verse (NIST randomized if no topic)
• `!song [topic]` - Generate a song about any topic
• `!nist` - Show current NIST Randomness Beacon value
• `!msghistory` - Debug message history for this chat

**Public Command Management:**
• `!publiccmds` - List all public commands
• `!publiccmd add/remove <command>` - Manage public command list

**AI Chat Commands:**
• `!ask your question here` - Ask AI without context
• `!ai your question here` - Same as !ask

**With Message Context:**
• `!ask m1 your question` - Include previous message
• `!ask m1-3 your question` - Include last 3 messages  
• `!ask m1,4,6 your question` - Include messages 1, 4, and 6
• `!ask m2-5,8 your question` - Include messages 2-5 and 8

**Message Index System:**
• `1` = Most recent message (immediate previous)
• `2` = Second most recent message
• `3` = Third most recent message
• etc.

**Examples:**
• `!8ball Will it rain today?`
• `!advice relationships`
• `!bible strength`
• `!ask m1 what is the main topic discussed?`
• `!ask m1-3 how many calories in total?`

**Note**: Only the last {self.max_messages} messages per chat are remembered."""
    
    async def _get_conversation_context(self, context: CommandContext) -> List[Dict]:
        """Get conversation context using platform service (platform-agnostic)"""
        try:
            # Try to get conversation context from platform service
            message_service = self.require_service('message_history')
            if message_service:
                self.logger.info("📜 AI: Using message history service for conversation context")
                messages = await message_service.get_recent_messages(context.chat_id, self.max_recent_display)
                
                # Convert service messages to our format
                for msg_data in messages:
                    if isinstance(msg_data, dict) and 'content' in msg_data:
                        # Don't store commands as context
                        content = msg_data.get('content', '')
                        if not content.startswith('!'):
                            message = ChatMessage(
                                content=content,
                                sender=msg_data.get('sender', context.user_display_name),
                                timestamp=datetime.now(),
                                message_id=f"service_{context.chat_id}_{len(messages)}",
                                chat_id=context.chat_id
                            )
                            self.message_history.add_message(context.chat_id, message)
                
                self.logger.info(f"📜 AI: Retrieved {len(messages)} messages via service")
                return messages
            else:
                self.logger.info("📜 AI: No message history service available, using local history only")
                return []
                
        except Exception as e:
            self.logger.error(f"📜 AI: Error getting conversation context: {e}")
            return []
    
# SimpleX-specific helper methods removed - now using platform service for message history
    
    async def _call_openrouter_api(self, prompt: str, max_tokens: int = None) -> tuple[str, str]:
        """Make API call to OpenRouter with fallback models"""
        # Use default token limit if none provided
        if max_tokens is None:
            max_tokens = self.tokens_ai
            
        # Define fallback models from config
        fallback_models = [self.model]  # Primary model first
        config_fallbacks = self.config.get('fallback_models', [
            "google/gemini-2.0-flash-exp:free",
            "deepseek/deepseek-chat-v3-0324:free", 
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-3-27b-it:free",
            "mistralai/mistral-7b-instruct:free"
        ])
        fallback_models.extend(config_fallbacks)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_models = []
        for model in fallback_models:
            if model not in seen:
                seen.add(model)
                unique_models.append(model)
        
        fallback_models = unique_models
            
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",
            "X-Title": "AI Bot Plugin"
        }
        
        # Try each model in sequence
        for attempt, model in enumerate(fallback_models):
            try:
                self.logger.info(f"🎯 AI API - Attempt {attempt + 1} with model: {model}")
                
                data = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": self.config.get('api', {}).get('temperature', 0.8)
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.openrouter_url, 
                        headers=headers, 
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=self.api_timeout)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            content = result['choices'][0]['message']['content'].strip()
                            if attempt > 0:
                                self.logger.info(f"✅ AI API succeeded with fallback model {model}")
                            return content, model
                        else:
                            error_text = await response.text()
                            self.logger.error(f"❌ SINGLE_PASS API error {response.status} with {model}: {error_text}")
                            continue
                            
            except Exception as e:
                self.logger.error(f"❌ AI API failed with {model}: {e}")
                continue
        
        # If all models failed
        self.logger.error(f"❌ All fallback models failed for AI request")
        return "❌ AI service temporarily unavailable. All fallback models failed.", "unknown"
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.yml')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    self.logger.info(f"✅ AI CONFIG: Loaded configuration from {config_path}")
                    return config or {}
            else:
                self.logger.warning(f"⚠️ AI CONFIG: Configuration file not found at {config_path}, using defaults")
                return {}
        except Exception as e:
            self.logger.error(f"❌ AI CONFIG: Error loading configuration from {config_path}: {e}")
            return {}
    
    def _load_admin_config(self) -> Dict[str, Any]:
        """Load admin configuration from admin_config.yml"""
        try:
            if os.path.exists(self.admin_config_path):
                with open(self.admin_config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    return config or {}
            else:
                self.logger.warning(f"⚠️ Admin config not found at {self.admin_config_path}")
                return {}
        except Exception as e:
            self.logger.error(f"❌ Error loading admin config from {self.admin_config_path}: {e}")
            return {}
    
    def _save_admin_config(self, config: Dict[str, Any]):
        """Save admin configuration to admin_config.yml"""
        try:
            with open(self.admin_config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"✅ Saved admin config to {self.admin_config_path}")
            
        except Exception as e:
            self.logger.error(f"❌ Error saving admin config to {self.admin_config_path}: {e}")
    
    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        self.logger.info("Universal AI plugin cleanup completed")


# Export the plugin class for the plugin manager to discover