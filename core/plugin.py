"""
Universal Core Plugin - Essential bot commands for any platform

This plugin provides core bot functionality like help, status, plugin management, etc.
that works across different bot platforms using the universal plugin architecture.
"""

from typing import List, Optional
import logging
import asyncio
from datetime import datetime
from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform


class UniversalCorePlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("core", logger=logger)
        self.version = "2.0.0"  # Updated for universal support
        self.description = "Universal core bot commands (help, status, ping, plugin management)"
        
        # Core plugin should always be enabled
        self.enabled = True
        
        # Supports all platforms
        self.supported_platforms = [BotPlatform.MATRIX, BotPlatform.SIMPLEX]
        
        if not self.logger:
            self.logger = logging.getLogger(f"plugin.{self.name}")
        self.start_time = datetime.now()
    
    async def initialize(self, adapter) -> bool:
        """Initialize plugin with bot adapter"""
        try:
            # Call parent initialization
            if not await super().initialize(adapter):
                return False
            
            self.logger.info(f"Initializing core plugin for {adapter.platform.value} platform")
            self.start_time = datetime.now()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize core plugin: {e}")
            return False
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return [
            "ping", "uptime",
            "plugins", "reload", "enable", "disable",
            "platform", "commands"
        ]
    
    async def handle_command(self, context: CommandContext) -> Optional[str]:
        """Handle commands for this plugin"""
        self.logger.info(f"Handling {context.command} command from {context.user_display_name} on {context.platform.value}")
        
        try:
            if context.command == "ping":
                return await self._handle_ping(context)
            elif context.command == "uptime":
                return await self._handle_uptime(context)
            elif context.command == "plugins":
                return await self._handle_plugins(context)
            elif context.command == "reload":
                return await self._handle_reload(context)
            elif context.command == "enable":
                return await self._handle_enable(context)
            elif context.command == "disable":
                return await self._handle_disable(context)
            elif context.command == "platform":
                return await self._handle_platform_info(context)
            elif context.command == "commands":
                return await self._handle_commands(context)
                
        except Exception as e:
            self.logger.error(f"Error handling {context.command} command: {str(e)}", exc_info=True)
            return f"❌ Error processing {context.command} command"
        
        return None
    
    
    async def _handle_ping(self, context: CommandContext) -> str:
        """Handle ping command"""
        return f"🏓 Pong! Bot is responsive on {context.platform.value}."
    
    
    async def _handle_uptime(self, context: CommandContext) -> str:
        """Show bot uptime"""
        uptime = datetime.now() - self.start_time
        return f"⏰ **Bot Uptime:** {str(uptime).split('.')[0]}\n*Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}*"
    
    async def _handle_plugins(self, context: CommandContext) -> str:
        """List all plugins and their status"""
        try:
            plugin_manager = getattr(self.adapter.bot, 'plugin_manager', None)
            if not plugin_manager:
                return "❌ Plugin manager not available"
            
            status = plugin_manager.get_plugin_status()
            
            plugins_text = f"""🔌 **Plugin Status - {context.platform.value.title()}**

**Summary:**
• Loaded: {status['total_loaded']}
• Failed: {status['total_failed']}
• Hot Reloading: {'🔥 Active' if status['hot_reloading'] else '❄️ Inactive'}

**Loaded Plugins:**"""
            
            for name, info in status['loaded'].items():
                enabled_icon = "🟢" if info['enabled'] else "🔴"
                plugins_text += f"\n{enabled_icon} **{name}** v{info['version']}"
                plugins_text += f"\n   *{info['description']}*"
                plugins_text += f"\n   Commands: {', '.join([f'`!{cmd}`' for cmd in info['commands']])}"
                plugins_text += f"\n   Platform: {info.get('current_platform', 'unknown')}\n"
            
            if status['failed']:
                plugins_text += "\n**Failed Plugins:**"
                for name, error in status['failed'].items():
                    plugins_text += f"\n❌ **{name}**: {error[:100]}..."
            
            return plugins_text
            
        except Exception as e:
            self.logger.error(f"Error listing plugins: {e}")
            return "❌ Error retrieving plugin information"
    
    async def _handle_reload(self, context: CommandContext) -> str:
        """Reload a specific plugin"""
        if not context.has_args:
            return "❓ **Reload Plugin**\n\nUsage: `!reload <plugin_name>`\nExample: `!reload example`"
        
        plugin_name = context.get_arg(0)
        plugin_manager = getattr(self.adapter.bot, 'plugin_manager', None)
        
        if not plugin_manager:
            return "❌ Plugin manager not available"
        
        if plugin_name not in plugin_manager.plugins and plugin_name not in plugin_manager.failed_plugins:
            return f"❌ Plugin '{plugin_name}' not found"
        
        try:
            success = await plugin_manager.reload_plugin(plugin_name)
            if success:
                return f"✅ Plugin '{plugin_name}' reloaded successfully"
            else:
                return f"❌ Failed to reload plugin '{plugin_name}'"
        except Exception as e:
            return f"❌ Error reloading plugin '{plugin_name}': {str(e)}"
    
    async def _handle_enable(self, context: CommandContext) -> str:
        """Enable a plugin"""
        if not context.has_args:
            return "❓ **Enable Plugin**\n\nUsage: `!enable <plugin_name>`\nExample: `!enable example`"
        
        plugin_name = context.get_arg(0)
        plugin_manager = getattr(self.adapter.bot, 'plugin_manager', None)
        
        if not plugin_manager:
            return "❌ Plugin manager not available"
        
        success = plugin_manager.enable_plugin(plugin_name)
        if success:
            return f"✅ Plugin '{plugin_name}' enabled"
        else:
            return f"❌ Plugin '{plugin_name}' not found"
    
    async def _handle_disable(self, context: CommandContext) -> str:
        """Disable a plugin"""
        if not context.has_args:
            return "❓ **Disable Plugin**\n\nUsage: `!disable <plugin_name>`\nExample: `!disable example`"
        
        plugin_name = context.get_arg(0)
        
        # Prevent disabling core plugin
        if plugin_name == "core":
            return "❌ Cannot disable core plugin"
        
        plugin_manager = getattr(self.adapter.bot, 'plugin_manager', None)
        
        if not plugin_manager:
            return "❌ Plugin manager not available"
        
        success = plugin_manager.disable_plugin(plugin_name)
        if success:
            return f"⏸️ Plugin '{plugin_name}' disabled"
        else:
            return f"❌ Plugin '{plugin_name}' not found"
    
    async def _handle_platform_info(self, context: CommandContext) -> str:
        """Show platform-specific information"""
        platform_info = f"""🌐 **Platform Information**

**Current Platform:** {context.platform.value.title()}
**User ID:** {context.user_id}
**Chat ID:** {context.chat_id}
**Display Name:** {context.user_display_name}
"""
        
        # Add platform-specific details
        if context.platform == BotPlatform.SIMPLEX:
            bot = self.adapter.bot
            platform_info += f"""
**SimpleX Features:**
• End-to-end encrypted messaging
• No central servers or user databases
• XFTP for file transfers
• Contact-based communication

**Bot Configuration:**
• WebSocket URL: {getattr(bot.websocket_manager, 'websocket_url', 'N/A') if hasattr(bot, 'websocket_manager') else 'N/A'}
• Media Downloads: {'✅ Enabled' if hasattr(bot, 'file_download_manager') and bot.file_download_manager.media_enabled else '❌ Disabled'}
• XFTP Client: {'✅ Available' if hasattr(bot, 'xftp_client') else '❌ Not Available'}"""
            
        elif context.platform == BotPlatform.MATRIX:
            platform_info += f"""
**Matrix Features:**
• Federated network
• Room-based communication  
• Rich media and formatting support
• End-to-end encryption support"""
        
        return platform_info
    
    async def _handle_commands(self, context: CommandContext) -> str:
        """List all available commands"""
        try:
            plugin_manager = getattr(self.adapter.bot, 'plugin_manager', None)
            if not plugin_manager:
                return "❌ Plugin manager not available"
            
            commands = plugin_manager.get_all_commands()
            
            commands_text = f"📝 **Available Commands - {context.platform.value.title()}**\n\n"
            
            # Group by plugin
            plugins_commands = {}
            for cmd, plugin_name in commands.items():
                if plugin_name not in plugins_commands:
                    plugins_commands[plugin_name] = []
                plugins_commands[plugin_name].append(cmd)
            
            for plugin_name, cmds in plugins_commands.items():
                commands_text += f"**{plugin_name.title()} Plugin:**\n"
                commands_text += f"{', '.join([f'`!{cmd}`' for cmd in sorted(cmds)])}\n\n"
            
            commands_text += f"💡 Use `!help` for detailed command descriptions."
            
            return commands_text
            
        except Exception as e:
            self.logger.error(f"Error listing commands: {e}")
            return "❌ Error retrieving command list"
    
    
    
    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        self.logger.info("Universal core plugin cleanup completed")


# Export the plugin class for the plugin manager to discover