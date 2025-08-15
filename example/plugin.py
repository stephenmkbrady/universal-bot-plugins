"""
Universal Example Plugin - Works with any bot platform

This plugin demonstrates the universal plugin architecture that works across
different bot platforms (Matrix, SimpleX, Discord, etc.) using bot adapters.

It's been updated from the original Matrix-specific version to be platform-agnostic.
"""

from typing import List, Optional
import logging
import os
from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform


class UniversalExamplePlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("example", logger=logger)
        self.version = "2.0.0"  # Updated for universal support
        self.description = "Universal example plugin that works across bot platforms"
        
        # IMPORTANT: This plugin is disabled by default for safety
        # Set to True to enable this plugin
        self.enabled = True
        
        # Universal plugin - supports all platforms
        self.supported_platforms = []  # Empty means supports all platforms
        
        if not self.logger:
            self.logger = logging.getLogger(f"plugin.{self.name}")
        
        # Plugin-specific configuration (can be overridden by environment variables)
        self.demo_mode = os.getenv('EXAMPLE_DEMO_MODE', 'true').lower() == 'true'
        self.max_echo_length = int(os.getenv('EXAMPLE_MAX_ECHO_LENGTH', '1000'))
        self.repeat_count = int(os.getenv('EXAMPLE_REPEAT_COUNT', '3'))
    
    async def _on_initialize(self) -> bool:
        """Initialize the plugin with bot adapter"""
        try:
            self.logger.info(f"Initializing {self.name} plugin for {self.adapter.platform.value} platform")
            
            # Platform-specific initialization could go here
            if self.adapter.platform == BotPlatform.SIMPLEX:
                self.logger.info("SimpleX-specific initialization")
                # Could access SimpleX-specific features here
            elif self.adapter.platform == BotPlatform.MATRIX:
                self.logger.info("Matrix-specific initialization")
                # Could access Matrix-specific features here
            
            if not self.enabled:
                self.logger.info("Example plugin is disabled (set enabled=True in plugin code)")
                return True
            
            self.logger.info("Universal example plugin initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize example plugin: {e}")
            return False
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return ["echo", "repeat", "example", "platform"]
    
    async def handle_command(self, context: CommandContext) -> Optional[str]:
        """Handle commands for this plugin"""
        self.logger.info(f"Handling {context.command} command from {context.user_display_name} on {context.platform.value}")
        
        if not self.enabled:
            return "❌ Example plugin is disabled. Enable it in the plugin code."
        
        try:
            if context.command == "echo":
                return await self._handle_echo(context)
            elif context.command == "repeat":
                return await self._handle_repeat(context)
            elif context.command == "example":
                return await self._handle_example(context)
            elif context.command == "platform":
                return await self._handle_platform(context)
                
        except Exception as e:
            self.logger.error(f"Error handling {context.command} command: {str(e)}", exc_info=True)
            return f"❌ Error processing {context.command} command"
        
        return None
    
    async def _handle_echo(self, context: CommandContext) -> str:
        """Echo back the user's message"""
        if not context.has_args:
            return "🔊 **Echo Command**\n\nUsage: `!echo <message>`\nI'll repeat whatever you type!"
        
        # Respect max_echo_length configuration
        message = context.args_raw
        if len(message) > self.max_echo_length:
            message = message[:self.max_echo_length] + "... (truncated)"
        
        # Add demo mode information if enabled
        demo_info = f"\n🎯 *Demo mode active on {context.platform.value}!*" if self.demo_mode else ""
        
        return f"🔊 **Echo from {context.user_display_name}:**\n{message}{demo_info}"
    
    async def _handle_repeat(self, context: CommandContext) -> str:
        """Repeat the user's message multiple times"""
        if not context.has_args:
            return f"🔁 **Repeat Command**\n\nUsage: `!repeat <message>`\nI'll repeat your message {self.repeat_count} times!"
        
        # Repeat the message using configured count
        message = context.args_raw
        repeated = "\n".join([f"{i+1}. {message}" for i in range(self.repeat_count)])
        return f"🔁 **Repeating message from {context.user_display_name}:**\n{repeated}"
    
    async def _handle_platform(self, context: CommandContext) -> str:
        """Show platform-specific information"""
        platform_info = f"""🤖 **Platform Information**
        
**Current Platform:** {context.platform.value.title()}
**User ID:** {context.user_id}
**Chat ID:** {context.chat_id}
**Display Name:** {context.user_display_name}

**Supported Platforms:** {'All platforms (universal)' if not self.supported_platforms else ', '.join([p.value for p in self.supported_platforms])}
**Plugin Version:** {self.version}
"""
        
        # Add platform-specific information
        if context.platform == BotPlatform.SIMPLEX:
            platform_info += """
**SimpleX Features:**
• End-to-end encrypted messaging
• No user identifiers or metadata
• XFTP file transfers
• Contact-based communication"""
            
        elif context.platform == BotPlatform.MATRIX:
            platform_info += f"""
**Matrix Features:**
• Federated network
• Room-based communication
• Room ID: {context.chat_id}
• Rich media support"""
        
        return platform_info
    
    async def _handle_example(self, context: CommandContext) -> str:
        """Show example of plugin capabilities"""
        return f"""🎯 **Universal Example Plugin Demo**

**Available Commands:**
• `!echo <message>` - Echo back your message
• `!repeat <message>` - Repeat your message {self.repeat_count} times  
• `!example` - Show this demo
• `!platform` - Show platform information

**Plugin Info:**
• Name: {self.name}
• Version: {self.version}
• Enabled: {self.enabled}
• Platform: {context.platform.value}

**User Info:**
• Display Name: {context.user_display_name}
• User ID: {context.user_id}
• Chat ID: {context.chat_id}

**Command Info:**
• Arguments: {context.args_raw if context.has_args else "(none)"}
• Arg Count: {context.arg_count}

**Configuration:**
• Demo Mode: {self.demo_mode}
• Max Echo Length: {self.max_echo_length}
• Repeat Count: {self.repeat_count}

This is a universal plugin that works across bot platforms! 🚀"""
    
    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        self.logger.info("Universal example plugin cleanup completed")


# Export the plugin class for the plugin manager to discover
# The plugin manager looks for classes that inherit from UniversalBotPlugin