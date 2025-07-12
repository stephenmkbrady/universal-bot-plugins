"""
Universal AI Plugin - Works across all bot platforms

This plugin provides AI-powered features including magic 8-ball, advice, and other
AI-generated content that works across different bot platforms using the universal plugin architecture.
"""

import logging
import os
import aiohttp
import time
from typing import List, Optional
from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform


class UniversalAIPlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("ai", logger=logger)
        self.version = "2.0.0"  # Updated for universal support
        self.description = "Universal AI-powered features including magic 8-ball, advice, and content generation"
        
        # This plugin supports all platforms
        self.supported_platforms = [BotPlatform.MATRIX, BotPlatform.SIMPLEX]
        
        if not self.logger:
            self.logger = logging.getLogger(f"plugin.{self.name}")
        
        # AI configuration
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.nist_beacon_url = os.getenv("NIST_BEACON_URL", "https://beacon.nist.gov/beacon/2.0/pulse/last")
        self.openrouter_url = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
        self.model = "cognitivecomputations/dolphin3.0-mistral-24b:free"
    
    async def initialize(self, adapter) -> bool:
        """Initialize the plugin with bot adapter"""
        try:
            # Call parent initialization
            if not await super().initialize(adapter):
                return False
            
            self.logger.info(f"Initializing AI plugin for {adapter.platform.value} platform")
            
            # Check for required API key
            if not self.openrouter_api_key:
                self.logger.warning("OPENROUTER_API_KEY not found - AI features will be disabled")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI plugin: {e}")
            return False
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return ["8ball", "advice", "advise", "bible", "song", "nist", "ai", "ask"]
    
    async def handle_command(self, context: CommandContext) -> Optional[str]:
        """Handle commands for this plugin"""
        self.logger.info(f"Handling {context.command} command from {context.user_display_name} on {context.platform.value}")
        
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
                
        except Exception as e:
            self.logger.error(f"Error handling {context.command} command: {str(e)}", exc_info=True)
            return f"❌ Error processing {context.command} command"
        
        return None
    
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
        
        topic = context.args_raw if context.has_args else "hope and encouragement"
        
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
            beacon_int = await self._get_nist_beacon_random_number()
            is_positive = (beacon_int % 2) == 0
            
            response = f"""🔢 **NIST Randomness Beacon**

**Current Value:** {beacon_int}
**Polarity:** {'POSITIVE' if is_positive else 'NEGATIVE'}
**Source:** US National Institute of Standards and Technology

The NIST Randomness Beacon provides publicly verifiable randomness.
This value changes every 60 seconds and is cryptographically signed."""
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error getting NIST beacon: {e}")
            return "❌ Unable to access NIST Randomness Beacon at the moment."
    
    async def _handle_ai_question(self, context: CommandContext) -> str:
        """Handle general AI question"""
        if not context.has_args:
            return "🤖 **AI Assistant**\n\nAsk me anything!\nExample: `!ai What is the meaning of life?`"
        
        if not self.openrouter_api_key:
            return "❌ AI features require OPENROUTER_API_KEY environment variable"
        
        question = context.args_raw
        
        try:
            answer = await self._generate_ai_response(question)
            return f"🤖 **AI Assistant**\n\n**Question:** {question}\n\n**Answer:** {answer}"
            
        except Exception as e:
            self.logger.error(f"Error generating AI response: {e}")
            return "❌ Unable to process your question at the moment."
    
    async def _get_nist_beacon_random_number(self) -> int:
        """Get current NIST Randomness Beacon value and return as integer"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.nist_beacon_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        output_value = data['pulse']['outputValue']
                        beacon_int = int(output_value, 16)
                        return beacon_int
                    else:
                        # Fallback to timestamp
                        return int(time.time())
        except Exception as e:
            self.logger.error(f"Error getting NIST beacon: {e}")
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
        
        return await self._call_openrouter_api(prompt, max_tokens=100)
    
    async def _generate_advice(self, topic: str) -> str:
        """Generate helpful advice on a topic"""
        prompt = f"""Provide thoughtful, practical advice about {topic}. 

Make it:
- Actionable and specific
- Encouraging yet realistic  
- Based on wisdom and common sense
- Suitable for someone seeking guidance

Keep it concise but meaningful (2-3 sentences max)."""
        
        return await self._call_openrouter_api(prompt, max_tokens=200)
    
    async def _generate_bible_verse(self, topic: str) -> str:
        """Generate or recall a relevant Bible verse"""
        prompt = f"""Provide an encouraging Bible verse related to {topic}.

Include:
- The actual verse text (accurate)
- The Bible reference (book, chapter:verse)
- A brief application to the topic

Format like: "Verse text" - Reference

Then add a short explanation of how it relates to {topic}."""
        
        return await self._call_openrouter_api(prompt, max_tokens=300)
    
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
        
        return await self._call_openrouter_api(prompt, max_tokens=400)
    
    async def _generate_ai_response(self, question: str) -> str:
        """Generate a general AI response"""
        prompt = f"""Answer this question helpfully and accurately: {question}

Provide:
- Clear, informative response
- Practical insights where applicable
- Honest acknowledgment if uncertain
- Conversational but professional tone

Keep response concise but comprehensive."""
        
        return await self._call_openrouter_api(prompt, max_tokens=500)
    
    async def _call_openrouter_api(self, prompt: str, max_tokens: int = 300) -> str:
        """Make API call to OpenRouter"""
        try:
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "AI Bot Plugin"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.8
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.openrouter_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content'].strip()
                    else:
                        self.logger.error(f"OpenRouter API error: {response.status}")
                        return "❌ AI service temporarily unavailable"
                        
        except Exception as e:
            self.logger.error(f"Error calling OpenRouter API: {e}")
            return "❌ Error communicating with AI service"
    
    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        self.logger.info("Universal AI plugin cleanup completed")


# Export the plugin class for the plugin manager to discover