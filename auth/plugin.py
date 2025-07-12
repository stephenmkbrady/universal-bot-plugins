"""
Universal Auth Plugin - Works across all bot platforms

This plugin provides PIN-based authentication for database access
that works across different bot platforms using the universal plugin architecture.
"""

import logging
import asyncio
import aiohttp
import json
import os
from datetime import datetime
from typing import List, Optional
from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform


class UniversalAuthPlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("auth", logger=logger)
        self.version = "2.0.0"  # Updated for universal support
        self.description = "Universal PIN authentication for database access - Request PINs for rooms"
        
        # This plugin supports all platforms
        self.supported_platforms = [BotPlatform.MATRIX, BotPlatform.SIMPLEX]
        
        if not self.logger:
            self.logger = logging.getLogger(f"plugin.{self.name}")
        
        # API configuration
        self.api_base_url = None
        self.api_key = None
    
    async def initialize(self, adapter) -> bool:
        """Initialize the plugin with bot adapter"""
        try:
            # Call parent initialization
            if not await super().initialize(adapter):
                return False
            
            self.logger.info(f"Initializing Auth plugin for {adapter.platform.value} platform")
            
            # Get API configuration from environment
            self.api_base_url = os.getenv("DATABASE_API_URL", os.getenv("DATABASE_URL", "http://localhost:8000")).rstrip('/')
            self.api_key = os.getenv("DATABASE_API_KEY", os.getenv("API_KEY"))
            
            if not self.api_base_url or not self.api_key:
                self.logger.warning("DATABASE_API_URL and DATABASE_API_KEY not configured - auth features will be limited")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Auth plugin: {e}")
            return False
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return ["pin", "auth", "request", "verify"]
    
    async def handle_command(self, context: CommandContext) -> Optional[str]:
        """Handle commands for this plugin"""
        self.logger.info(f"Handling {context.command} command from {context.user_display_name} on {context.platform.value}")
        
        try:
            if context.command in ["pin", "request"]:
                return await self._handle_pin_request(context)
            elif context.command in ["auth", "verify"]:
                return await self._handle_auth_verify(context)
                
        except Exception as e:
            self.logger.error(f"Error handling {context.command} command: {str(e)}", exc_info=True)
            return f"❌ Error processing {context.command} command"
        
        return None
    
    async def _handle_pin_request(self, context: CommandContext) -> str:
        """Handle PIN request command"""
        if not self.api_base_url or not self.api_key:
            return "❌ Authentication service not configured. Contact the bot administrator."
        
        try:
            # Request PIN for the current chat/room
            pin_data = await self._request_pin_for_room(context.chat_id, context.user_display_name)
            
            if pin_data:
                return f"""🔐 **PIN Request Successful**

A new PIN has been generated for this room.
**PIN:** `{pin_data['pin']}`
**Valid for:** {pin_data.get('validity', '24 hours')}

Use this PIN to access database features.
Keep this PIN secure and don't share it publicly."""
            else:
                return "❌ Failed to generate PIN. Please try again later."
                
        except Exception as e:
            self.logger.error(f"Error requesting PIN: {e}")
            return "❌ Error communicating with authentication service."
    
    async def _handle_auth_verify(self, context: CommandContext) -> str:
        """Handle authentication verification"""
        if not context.has_args:
            return """🔐 **PIN Verification**

Usage: `!auth <pin>` or `!verify <pin>`

Enter the PIN provided by the pin request command to verify access."""
        
        pin = context.get_arg(0)
        
        if not self.api_base_url or not self.api_key:
            return "❌ Authentication service not configured."
        
        try:
            is_valid = await self._verify_pin(context.chat_id, pin, context.user_display_name)
            
            if is_valid:
                return f"""✅ **Authentication Successful**

PIN verified for this room.
You now have access to authenticated database features.
**User:** {context.user_display_name}
**Room:** {context.chat_id}"""
            else:
                return "❌ Invalid PIN. Please check the PIN and try again."
                
        except Exception as e:
            self.logger.error(f"Error verifying PIN: {e}")
            return "❌ Error verifying authentication."
    
    async def _request_pin_for_room(self, room_id: str, user_name: str) -> Optional[dict]:
        """Request a new PIN for a room from the API"""
        try:
            url = f"{self.api_base_url}/auth/request-pin"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "room_id": room_id,
                "user_name": user_name,
                "platform": self.adapter.platform.value,
                "timestamp": datetime.now().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.error(f"PIN request failed: {response.status}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"Error requesting PIN: {e}")
            return None
    
    async def _verify_pin(self, room_id: str, pin: str, user_name: str) -> bool:
        """Verify a PIN with the API"""
        try:
            url = f"{self.api_base_url}/auth/verify-pin"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "room_id": room_id,
                "pin": pin,
                "user_name": user_name,
                "platform": self.adapter.platform.value,
                "timestamp": datetime.now().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("valid", False)
                    else:
                        self.logger.error(f"PIN verification failed: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error verifying PIN: {e}")
            return False
    
    async def is_user_authenticated(self, room_id: str, user_name: str) -> bool:
        """Check if user is authenticated in a room"""
        try:
            url = f"{self.api_base_url}/auth/check-auth"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "room_id": room_id,
                "user_name": user_name,
                "platform": self.adapter.platform.value
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("authenticated", False)
                    else:
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error checking authentication: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        self.logger.info("Universal Auth plugin cleanup completed")


# Export the plugin class for the plugin manager to discover