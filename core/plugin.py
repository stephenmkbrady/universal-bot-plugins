"""
Universal Core Plugin - Essential bot commands for any platform

This plugin provides core bot functionality like help, status, plugin management, etc.
that works across different bot platforms using the universal plugin architecture.
"""

from typing import List, Optional, Dict, Any
import logging
import asyncio
import yaml
import os
from datetime import datetime
from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform


class UniversalCorePlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("core", logger=logger)
        self.version = "2.0.0"  # Updated for universal support
        self.description = "Universal core bot commands (help, status, ping, plugin management)"
        
        # Core plugin should always be enabled
        self.enabled = True
        
        # Universal plugin - supports all platforms
        self.supported_platforms = []  # Empty means supports all platforms
        
        if not self.logger:
            self.logger = logging.getLogger(f"plugin.{self.name}")
        self.start_time = datetime.now()
    
    async def _on_initialize(self) -> bool:
        """Initialize plugin with bot adapter"""
        try:
            self.logger.info(f"Initializing core plugin for {self.adapter.platform.value} platform")
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
            "start", "stop", "status",
            "platform", "commands",
            "container", "containers"
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
            elif context.command == "start":
                return await self._handle_start(context)
            elif context.command == "stop":
                return await self._handle_stop(context)
            elif context.command == "status":
                return await self._handle_status(context)
            elif context.command == "platform":
                return await self._handle_platform_info(context)
            elif context.command == "commands":
                return await self._handle_commands(context)
            elif context.command == "container":
                return await self._handle_container(context)
            elif context.command == "containers":
                return await self._handle_containers(context)
                
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
            
            status = await plugin_manager.get_plugin_status()
            
            plugins_text = f"""🔌 **Plugin Status - {context.platform.value.title()}**

**Summary:**
• Loaded: {status['total_loaded']}
• Failed: {status['total_failed']}
• Hot Reloading: {'🔥 Active' if status['hot_reloading'] else '❄️ Inactive'}

**Loaded Plugins:**"""
            
            for name, info in status['loaded'].items():
                enabled_icon = "🟢" if info['enabled'] else "🔴"
                container_icon = "🐳" if info.get('containerized', False) else ""
                plugins_text += f"\n{enabled_icon}{container_icon} **{name}** v{info['version']}"
                plugins_text += f"\n   *{info['description']}*"
                plugins_text += f"\n   Commands: {', '.join([f'`!{cmd}`' for cmd in info['commands']])}"
                plugins_text += f"\n   Platform: {info.get('current_platform', 'unknown')}"
                
                # Add container status if available
                if 'container_status' in info:
                    container_status = info['container_status']
                    if container_status.get('healthy'):
                        plugins_text += f"\n   🐳 Containers: ✅ Healthy ({len(container_status.get('containers', []))} running)"
                    else:
                        plugins_text += f"\n   🐳 Containers: ❌ Unhealthy"
                elif info.get('containerized', False):
                    plugins_text += f"\n   🐳 Containers: ❓ Status unknown"
                
                plugins_text += "\n"
            
            if status['failed']:
                plugins_text += "\n**Failed Plugins:**"
                for name, error in status['failed'].items():
                    plugins_text += f"\n❌ **{name}**: {error[:100]}..."
            
            return plugins_text
            
        except Exception as e:
            self.logger.error(f"Error listing plugins: {e}")
            return "❌ Error retrieving plugin information"
    
    async def _handle_reload(self, context: CommandContext) -> str:
        """Reload a specific plugin (restart containers for containerized plugins)"""
        if not context.has_args:
            return "❓ **Reload Plugin**\n\nUsage: `!reload <plugin_name>`\nExample: `!reload example`\n\nFor containerized plugins, this restarts containers. For normal plugins, this reloads the plugin."
        
        plugin_name = context.get_arg(0)
        plugin_manager = getattr(self.adapter.bot, 'plugin_manager', None)
        
        if not plugin_manager:
            return "❌ Plugin manager not available"
        
        if plugin_name not in plugin_manager.plugins and plugin_name not in plugin_manager.failed_plugins:
            return f"❌ Plugin '{plugin_name}' not found"
        
        try:
            plugin = plugin_manager.plugins.get(plugin_name)
            
            # For containerized plugins, restart containers
            if plugin and hasattr(plugin, 'restart_services'):
                success = await plugin.restart_services()
                if success:
                    return f"🔄 Plugin '{plugin_name}' containers restarted successfully"
                else:
                    return f"❌ Failed to restart containers for '{plugin_name}'"
            else:
                # For regular plugins, use normal reload
                success = await plugin_manager.reload_plugin(plugin_name)
                if success:
                    return f"✅ Plugin '{plugin_name}' reloaded successfully"
                else:
                    return f"❌ Failed to reload plugin '{plugin_name}'"
        except Exception as e:
            return f"❌ Error reloading plugin '{plugin_name}': {str(e)}"
    
    async def _handle_enable(self, context: CommandContext) -> str:
        """Enable a plugin persistently in configuration"""
        if not context.has_args:
            return "❓ **Enable Plugin**\n\nUsage: `!enable <plugin_name>`\nExample: `!enable example`\n\nThis permanently enables the plugin in configuration."
        
        plugin_name = context.get_arg(0)
        
        # Prevent enabling/disabling core plugin config (it's always enabled)
        if plugin_name == "core":
            return "❌ Core plugin is always enabled"
        
        try:
            # Load current config
            config = self._load_plugin_config()
            
            # Ensure plugin exists in config
            if plugin_name not in config.get('plugins', {}):
                config.setdefault('plugins', {})[plugin_name] = {}
            
            # Set enabled to true
            config['plugins'][plugin_name]['enabled'] = True
            
            # Save config
            self._save_plugin_config(config)
            
            # Also enable in runtime if plugin is loaded
            plugin_manager = getattr(self.adapter.bot, 'plugin_manager', None)
            if plugin_manager:
                plugin_manager.enable_plugin(plugin_name)
            
            return f"✅ Plugin '{plugin_name}' enabled in configuration (persistent)"
            
        except Exception as e:
            return f"❌ Error enabling plugin '{plugin_name}': {str(e)}"
    
    async def _handle_disable(self, context: CommandContext) -> str:
        """Disable a plugin persistently in configuration"""
        if not context.has_args:
            return "❓ **Disable Plugin**\n\nUsage: `!disable <plugin_name>`\nExample: `!disable example`\n\nThis permanently disables the plugin in configuration."
        
        plugin_name = context.get_arg(0)
        
        # Prevent disabling core plugin
        if plugin_name == "core":
            return "❌ Cannot disable core plugin"
        
        try:
            # Load current config
            config = self._load_plugin_config()
            
            # Ensure plugin exists in config
            if plugin_name not in config.get('plugins', {}):
                config.setdefault('plugins', {})[plugin_name] = {}
            
            # Set enabled to false
            config['plugins'][plugin_name]['enabled'] = False
            
            # Save config
            self._save_plugin_config(config)
            
            # Also disable in runtime if plugin is loaded
            plugin_manager = getattr(self.adapter.bot, 'plugin_manager', None)
            if plugin_manager:
                plugin_manager.disable_plugin(plugin_name)
            
            return f"⏸️ Plugin '{plugin_name}' disabled in configuration (persistent)"
            
        except Exception as e:
            return f"❌ Error disabling plugin '{plugin_name}': {str(e)}"

    def _load_plugin_config(self) -> Dict[str, Any]:
        """Load plugin configuration from plugin.yml"""
        config_file = Path("plugins/plugin.yml")
        if not config_file.exists():
            return {"plugins": {}}
        
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f) or {"plugins": {}}
        except Exception as e:
            self.logger.error(f"Error loading plugin config: {e}")
            return {"plugins": {}}
    
    def _save_plugin_config(self, config: Dict[str, Any]):
        """Save plugin configuration to plugin.yml"""
        config_file = Path("plugins/plugin.yml")
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving plugin config: {e}")
            raise

    async def _handle_start(self, context: CommandContext) -> str:
        """Start a plugin (runtime only, not persistent)"""
        if not context.has_args:
            return "❓ **Start Plugin**\n\nUsage: `!start <plugin_name>`\nExample: `!start krumble`\n\nThis starts the plugin temporarily (not persistent)."
        
        plugin_name = context.get_arg(0)
        plugin_manager = getattr(self.adapter.bot, 'plugin_manager', None)
        
        if not plugin_manager:
            return "❌ Plugin manager not available"
        
        # Check if plugin exists
        if plugin_name not in plugin_manager.plugins:
            return f"❌ Plugin '{plugin_name}' not found"
        
        plugin = plugin_manager.plugins[plugin_name]
        
        # For containerized plugins, start containers
        if hasattr(plugin, 'start_services'):
            try:
                success = await plugin.start_services()
                if success:
                    # Also enable runtime flag
                    plugin.enabled = True
                    return f"🟢 Plugin '{plugin_name}' started (containers + runtime)"
                else:
                    return f"❌ Failed to start containers for '{plugin_name}'"
            except Exception as e:
                return f"❌ Error starting '{plugin_name}': {str(e)}"
        else:
            # For regular plugins, just enable runtime
            plugin.enabled = True
            return f"🟢 Plugin '{plugin_name}' started (runtime)"

    async def _handle_stop(self, context: CommandContext) -> str:
        """Stop a plugin (runtime only, not persistent)"""
        if not context.has_args:
            return "❓ **Stop Plugin**\n\nUsage: `!stop <plugin_name>`\nExample: `!stop krumble`\n\nThis stops the plugin temporarily (not persistent)."
        
        plugin_name = context.get_arg(0)
        
        # Prevent stopping core plugin
        if plugin_name == "core":
            return "❌ Cannot stop core plugin"
        
        plugin_manager = getattr(self.adapter.bot, 'plugin_manager', None)
        
        if not plugin_manager:
            return "❌ Plugin manager not available"
        
        # Check if plugin exists
        if plugin_name not in plugin_manager.plugins:
            return f"❌ Plugin '{plugin_name}' not found"
        
        plugin = plugin_manager.plugins[plugin_name]
        
        # For containerized plugins, stop containers
        if hasattr(plugin, 'stop_services'):
            try:
                success = await plugin.stop_services()
                if success:
                    # Also disable runtime flag
                    plugin.enabled = False
                    return f"🔴 Plugin '{plugin_name}' stopped (containers + runtime)"
                else:
                    return f"❌ Failed to stop containers for '{plugin_name}'"
            except Exception as e:
                return f"❌ Error stopping '{plugin_name}': {str(e)}"
        else:
            # For regular plugins, just disable runtime
            plugin.enabled = False
            return f"🔴 Plugin '{plugin_name}' stopped (runtime)"

    async def _handle_status(self, context: CommandContext) -> str:
        """Show plugin status"""
        if not context.has_args:
            return "❓ **Plugin Status**\n\nUsage: `!status <plugin_name>`\nExample: `!status krumble`"
        
        plugin_name = context.get_arg(0)
        plugin_manager = getattr(self.adapter.bot, 'plugin_manager', None)
        
        if not plugin_manager:
            return "❌ Plugin manager not available"
        
        # Check if plugin exists
        if plugin_name not in plugin_manager.plugins:
            return f"❌ Plugin '{plugin_name}' not found"
        
        plugin = plugin_manager.plugins[plugin_name]
        
        # Get config status
        try:
            config = self._load_plugin_config()
            config_enabled = config.get('plugins', {}).get(plugin_name, {}).get('enabled', True)
        except:
            config_enabled = "unknown"
        
        # Get runtime status
        runtime_enabled = getattr(plugin, 'enabled', False)
        
        # Get container status if applicable
        container_status = "N/A"
        if hasattr(plugin, 'get_service_status'):
            try:
                container_status = await plugin.get_service_status()
            except:
                container_status = "error"
        
        status_text = f"📊 **Plugin Status: {plugin_name}**\n\n"
        status_text += f"**Configuration:** {'✅ Enabled' if config_enabled else '❌ Disabled'}\n"
        status_text += f"**Runtime:** {'🟢 Running' if runtime_enabled else '🔴 Stopped'}\n"
        
        if container_status != "N/A":
            status_text += f"**Containers:** {container_status}\n"
        
        return status_text
    
    async def _handle_platform_info(self, context: CommandContext) -> str:
        """Show platform-specific information"""
        platform_info = f"""🌐 **Platform Information**

**Current Platform:** {context.platform.value.title()}
**User ID:** {context.user_id}
**Chat ID:** {context.chat_id}
**Display Name:** {context.user_display_name}
"""
        
        # Add platform-agnostic details using services
        status_service = self.require_service('platform_status')
        if status_service:
            try:
                connection_info = await status_service.get_connection_info()
                health_info = await status_service.get_platform_health()
                
                platform_name = connection_info.get('platform', 'Unknown Platform')
                
                platform_info += f"""
**Platform:** {platform_name}

**Connection Status:**
• Status: {'✅ Connected' if connection_info.get('connected', False) else '❌ Disconnected'}
• Health: {health_info.get('status', 'unknown').title()}
• Services: {'✅ Operational' if health_info.get('websocket_connected', health_info.get('connected', False)) else '⚠️ Limited'}"""

                # Add connection details if available
                if 'websocket_url' in connection_info:
                    platform_info += f"""
• Connection URL: {connection_info.get('websocket_url', 'N/A')}"""
                
                if 'server' in connection_info:
                    platform_info += f"""
• Server: {connection_info.get('server', 'N/A')}"""
                    
            except Exception as e:
                platform_info += f"""
**Platform Status:**
• Status: ⚠️ Unable to get platform details
• Error: {str(e)}"""
        else:
            platform_info += f"""
**Platform Status:**
• Status: ⚠️ Platform status service not available
• Services: Limited diagnostic information"""
        
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
            
            # Add plugin management section
            commands_text += f"**Plugin Management:**\n"
            commands_text += f"`!plugins`, `!enable <plugin>`, `!disable <plugin>`, `!start <plugin>`, `!stop <plugin>`, `!status <plugin>`, `!reload <plugin>`\n\n"
            
            commands_text += f"💡 Use `!help` for detailed descriptions and plugin management guide."
            
            return commands_text
            
        except Exception as e:
            self.logger.error(f"Error listing commands: {e}")
            return "❌ Error retrieving command list"
    
    async def _handle_container(self, context: CommandContext) -> str:
        """Handle container management for specific plugin"""
        if not context.has_args:
            return """❓ **Container Management**

Usage: `!container <action> <plugin_name>`

**Actions:**
• `start` - Start plugin containers
• `stop` - Stop plugin containers  
• `restart` - Restart plugin containers
• `cleanup` - Full cleanup (removes volumes)
• `status` - Show container status

**Examples:**
• `!container start rumble`
• `!container stop rumble`
• `!container status rumble`"""
        
        if context.arg_count < 2:
            return "❌ **Usage:** `!container <action> <plugin_name>`"
        
        action = context.get_arg(0).lower()
        plugin_name = context.get_arg(1)
        
        plugin_manager = getattr(self.adapter.bot, 'plugin_manager', None)
        if not plugin_manager:
            return "❌ Plugin manager not available"
        
        try:
            if action == "start":
                success = await plugin_manager.start_plugin_containers(plugin_name)
                return f"✅ Started containers for {plugin_name}" if success else f"❌ Failed to start containers for {plugin_name}"
            
            elif action == "stop":
                success = await plugin_manager.stop_plugin_containers(plugin_name)
                return f"⏹️ Stopped containers for {plugin_name}" if success else f"❌ Failed to stop containers for {plugin_name}"
            
            elif action == "restart":
                success = await plugin_manager.restart_plugin_containers(plugin_name)
                return f"🔄 Restarted containers for {plugin_name}" if success else f"❌ Failed to restart containers for {plugin_name}"
            
            elif action == "cleanup":
                success = await plugin_manager.cleanup_plugin_containers(plugin_name)
                return f"🧹 Cleaned up containers for {plugin_name}" if success else f"❌ Failed to cleanup containers for {plugin_name}"
            
            elif action == "status":
                status = await plugin_manager.get_container_status(plugin_name)
                
                if "error" in status:
                    return f"❌ {status['error']}"
                
                if "message" in status:
                    return f"ℹ️ {status['message']}"
                
                containers = status.get('containers', [])
                healthy = status.get('healthy', False)
                
                status_text = f"🐳 **Container Status - {plugin_name}**\n\n"
                status_text += f"**Health:** {'✅ Healthy' if healthy else '❌ Unhealthy'}\n"
                status_text += f"**Containers:** {len(containers)}\n\n"
                
                for container in containers:
                    name = container.get('Name', 'Unknown')
                    state = container.get('State', 'Unknown')
                    status_text += f"• **{name}**: {state}\n"
                
                return status_text
            
            else:
                return f"❌ Unknown action: {action}. Use: start, stop, restart, cleanup, status"
                
        except Exception as e:
            self.logger.error(f"Error handling container command: {e}")
            return f"❌ Error managing containers for {plugin_name}: {str(e)}"
    
    async def _handle_containers(self, context: CommandContext) -> str:
        """List all containerized plugins and their status"""
        try:
            plugin_manager = getattr(self.adapter.bot, 'plugin_manager', None)
            if not plugin_manager:
                return "❌ Plugin manager not available"
            
            status = await plugin_manager.get_plugin_status()
            containerized_plugins = {}
            
            # Find containerized plugins
            for name, info in status['loaded'].items():
                if info.get('containerized', False):
                    containerized_plugins[name] = info
            
            if not containerized_plugins:
                return "📋 No containerized plugins found"
            
            containers_text = f"🐳 **Containerized Plugins ({len(containerized_plugins)})**\n\n"
            
            for name, info in containerized_plugins.items():
                enabled_icon = "🟢" if info['enabled'] else "🔴"
                containers_text += f"{enabled_icon} **{name}** v{info['version']}\n"
                
                # Add container status
                if 'container_status' in info:
                    container_status = info['container_status']
                    containers = container_status.get('containers', [])
                    healthy = container_status.get('healthy', False)
                    
                    health_icon = "✅" if healthy else "❌"
                    containers_text += f"   {health_icon} {len(containers)} container(s)"
                    
                    if containers:
                        running_count = sum(1 for c in containers if c.get('State') == 'running')
                        containers_text += f" ({running_count} running)"
                    
                    containers_text += "\n"
                else:
                    containers_text += "   ❓ Status unknown\n"
                
                containers_text += "\n"
            
            containers_text += f"💡 Use `!container status <plugin_name>` for detailed container info"
            
            return containers_text
            
        except Exception as e:
            self.logger.error(f"Error listing containers: {e}")
            return "❌ Error retrieving container information"
    
    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        self.logger.info("Universal core plugin cleanup completed")


# Export the plugin class for the plugin manager to discover