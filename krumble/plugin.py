"""
Krumble Plugin - Kick & Rumble Content Monitor

This plugin monitors content across two streaming platforms:
- Rumble (rumble.com) - livestreams and videos
- Kick (kick.com) - livestreams and videos  

Uses containerized web scraping with platform-specific parsers.
"""

import os
import asyncio
import subprocess
import json
import yaml
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from plugins.universal_plugin_base import ContainerizedBotPlugin, CommandContext, BotPlatform


class UniversalKrumblePlugin(ContainerizedBotPlugin):
    def __init__(self, logger=None):
        super().__init__(
            name="krumble", 
            logger=logger,
            service_host="krumble-scraper",
            service_port=8001
        )
        self.version = "1.0.0"
        self.description = "Monitor Kick and Rumble platforms for new content"
        
        # This plugin supports all platforms
        self.supported_platforms = [BotPlatform.MATRIX, BotPlatform.SIMPLEX]
        
        # Plugin paths (using parent class plugin_dir)
        self.plugin_dir = Path(__file__).parent
        self.config_file = self.plugin_dir / "config.yml"
        self.data_dir = self.plugin_dir / "data"
        self.screenshots_dir = self.plugin_dir / "screenshots"
        
        # Ensure directories exist with proper permissions
        self.data_dir.mkdir(exist_ok=True, mode=0o755)
        self.screenshots_dir.mkdir(exist_ok=True, mode=0o755)
        
        # Fix permissions if directory already exists
        try:
            import os
            import stat
            os.chmod(str(self.data_dir), 0o755)
            os.chmod(str(self.screenshots_dir), 0o755)
        except Exception as e:
            if logger:
                logger.warning(f"Could not set directory permissions: {e}")
        
        # Load configuration and strings
        self.config = self._load_config()
        self.strings = self._load_strings()
        
        # Monitoring state
        self.monitoring_task = None
        self.is_monitoring = False

    async def initialize(self, adapter=None) -> bool:
        """Initialize the plugin with containerized services"""
        try:
            # Call parent initialization (starts containers automatically)
            if not await super().initialize(adapter):
                return False
            
            self.logger.info(f"Initializing Krumble plugin v{self.version}")
            
            # Start monitoring task
            await self._start_monitoring()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Krumble plugin: {e}")
            return False

    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return ["krumble", "kmonitor", "klist", "kadd", "kremove", "kstatus", "khelp", "kcheck"]

    async def handle_command(self, context: CommandContext) -> Optional[str]:
        """Handle commands for this plugin"""
        command = context.command
        args = context.args
        self.logger.info(f"Handling {command} command from {context.user_display_name}")
        
        try:
            if command == "krumble":
                return await self._handle_krumble_command(args, context)
            elif command == "kmonitor":
                return await self._handle_monitor_command(args, context)
            elif command == "klist":
                return await self._handle_list_command(args, context)
            elif command == "kadd":
                return await self._handle_add_command(args, context)
            elif command == "kremove":
                return await self._handle_remove_command(args, context)
            elif command == "kstatus":
                return await self._handle_status_command(args, context)
            elif command == "khelp":
                return await self._handle_help_command(args, context)
            elif command == "kcheck":
                return await self._handle_manual_check(args, context)
        except Exception as e:
            self.logger.error(f"Error handling {command} command: {e}")
            return self._get_string("errors.command_error", command=command)
        
        return None

    def get_help(self) -> str:
        """Return help text for this plugin"""
        help_data = self.strings.get('help', {})
        return f"🎯 {help_data.get('description', 'Monitor Kick and Rumble channels for new content')} - Use !krumble help for detailed commands"

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yml"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    self.logger.info("✅ Krumble configuration loaded successfully")
                    return config
            else:
                self.logger.warning("❌ config.yml not found, creating default configuration")
                default_config = self._get_default_config()
                self._save_config(default_config)
                return default_config
        except Exception as e:
            self.logger.error(f"❌ Error loading config: {e}, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "monitoring": {
                "check_interval_minutes": 5,
                "enabled": True,
                "max_retries": 3,
                "timeout_seconds": 30
            },
            "detection": {
                "detect_removed": True,
                "detect_live_status_changes": True,
                "screenshot_on_block": True
            },
            "messages": {
                "new_stream": "🔴 **New Stream:** {title}\n🔗 {url}\n📅 {time}",
                "new_video": "📺 **New Video:** {title}\n🔗 {url}\n📅 {time}",
                "stream_ended": "⚫ **Stream Ended:** {title}",
                "blocked": "🚫 **Krumble Monitor Blocked:** Channel {channel} may have anti-bot protection",
                "error": "❌ **Krumble Monitor Error:** {error}",
                "added": "✅ **Added Channel:** {channel}\n📺 Monitoring for: {context_type}",
                "removed": "🗑️ **Removed Channel:** {channel}",
                "not_found": "❌ **Channel not found:** {channel}"
            }
        }

    def _load_strings(self) -> Dict[str, Any]:
        """Load localized strings"""
        return {
            "help": {
                "description": "Monitor Rumble channels for new livestreams and videos",
                "commands": {
                    "rumble": "Main command and help",
                    "radd": "Add channel to monitor",
                    "rremove": "Remove channel from monitoring",
                    "rlist": "List monitored channels",
                    "rstatus": "Show monitoring status",
                    "rmonitor": "Control monitoring"
                }
            },
            "errors": {
                "command_error": "❌ Error processing {command} command",
                "invalid_url": "❌ Invalid Rumble URL. Expected format: https://rumble.com/c/channelname",
                "permission_denied": "❌ You don't have permission to manage Rumble monitoring",
                "monitoring_disabled": "❌ Rumble monitoring is disabled in configuration"
            }
        }

    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            self.logger.info("✅ Configuration saved successfully")
        except Exception as e:
            self.logger.error(f"❌ Error saving configuration: {e}")

    async def _handle_krumble_command(self, args: List[str], context: CommandContext) -> str:
        """Handle main krumble command"""
        if not args or args[0] == "help":
            return self._get_krumble_help()
        
        subcommand = args[0].lower()
        
        if subcommand == "check":
            return await self._handle_manual_check(args[1:], context)
        else:
            return self._get_krumble_help()

    async def _handle_add_command(self, args: List[str], context: CommandContext, content_type: str = "both") -> str:
        """Handle add channel command"""
        if not args:
            return "❌ Usage: !kadd <channel_url_or_name>"
        
        channel_input = args[0]
        
        # Parse channel info from URL or direct input
        channel_info = self._parse_channel_info(channel_input)
        if not channel_info:
            return "❌ Invalid URL or channel name. Supported platforms: Rumble, Kick"
        
        platform = channel_info["platform"]
        channel_name = channel_info["channel"]
        base_url = channel_info["base_url"]
        
        # Determine context (user or group)
        context_type = "group" if context.chat_id.startswith("group_") else "user"
        context_id = context.chat_id
        
        # Load existing channels for this context
        channels = self._load_context_channels(context_id)
        
        # Generate URLs based on platform
        if platform == "rumble":
            if content_type == "both":
                urls_and_types = [
                    (f"{base_url}/livestreams", "livestreams"),
                    (f"{base_url}/videos", "videos")
                ]
            else:
                urls_and_types = [(f"{base_url}/{content_type}", content_type)]
        elif platform == "kick":
            if content_type == "both":
                urls_and_types = [
                    (f"{base_url}", "livestreams"),  # Kick main page shows streams
                    (f"{base_url}/videos", "videos")
                ]
            else:
                if content_type == "livestreams":
                    urls_and_types = [(f"{base_url}", "livestreams")]
                else:
                    urls_and_types = [(f"{base_url}/videos", "videos")]
        else:
            return f"❌ Unsupported platform: {platform}"
        
        results = []
        for url, ctype in urls_and_types:
            # Create unique key for this channel + content type combination
            channel_key = f"{channel_name}_{ctype}" if content_type == "both" else channel_name
            
            channel_data = {
                "name": channel_name,
                "platform": platform,
                "content_type": ctype,
                "url": url,
                "added_by": context.user_display_name,
                "added_at": datetime.now().isoformat(),
                "context_type": context_type,
                "original_context_id": context_id,
                "last_check": None,
                "status": "active"
            }
            
            channels[channel_key] = channel_data
            
            # Perform immediate check for this URL
            try:
                result = await self._check_channel(url)
                if result.get("success"):
                    # Update last check time
                    channels[channel_key]["last_check"] = datetime.now().isoformat()
                    
                    new_count = len(result.get("new_streams", []))
                    total_count = result.get("total_streams", 0)
                    content_desc = "livestreams" if ctype == "livestreams" else "videos"
                    
                    results.append(f"✅ **{channel_name} ({content_desc}):** {total_count} items found, {new_count} are new")
                else:
                    results.append(f"⚠️ **{channel_name} ({ctype}):** Initial check failed - {result.get('error', 'Unknown error')}")
            except Exception as e:
                self.logger.error(f"Error during initial check for {channel_name} ({ctype}): {e}")
                results.append(f"⚠️ **{channel_name} ({ctype}):** Initial check failed - {str(e)}")
        
        # Save all channel entries
        self._save_context_channels(context_id, channels)
        
        # Return combined results
        if len(results) == 1:
            return f"📺 **Added Rumble Channel:** {channel_name}\n{results[0]}"
        else:
            return f"📺 **Added Rumble Channel:** {channel_name}\n" + "\n".join(results)

    async def _handle_remove_command(self, args: List[str], context: CommandContext) -> str:
        """Handle remove channel command"""
        if not args:
            return "❌ Usage: !kremove <channel_name>"
        
        channel_input = args[0]
        context_id = context.chat_id
        
        # Load existing channels
        channels = self._load_context_channels(context_id)
        
        # Handle URL input - extract channel name
        if channel_input.startswith('http'):
            channel_info = self._parse_channel_info(channel_input)
            if channel_info:
                channel_name = channel_info["channel"]
            else:
                return "❌ Invalid URL format"
        else:
            channel_name = channel_input
        
        # Find all entries for this channel (including _livestreams and _videos suffixes)
        keys_to_remove = []
        for key in channels.keys():
            # Check exact match or channel name match (for entries with suffixes)
            if key == channel_name or key.startswith(f"{channel_name}_"):
                keys_to_remove.append(key)
        
        if keys_to_remove:
            for key in keys_to_remove:
                del channels[key]
            self._save_context_channels(context_id, channels)
            
            if len(keys_to_remove) == 1:
                return self.config["messages"]["removed"].format(channel=channel_name)
            else:
                return f"✅ **Removed Channel:** {channel_name} ({len(keys_to_remove)} entries removed: {', '.join(keys_to_remove)})"
        else:
            return self.config["messages"]["not_found"].format(channel=channel_name)

    async def _handle_list_command(self, args: List[str], context: CommandContext) -> str:
        """Handle list channels command"""
        context_id = context.chat_id
        channels = self._load_context_channels(context_id)
        
        if not channels:
            return "📺 No channels being monitored for this context"
        
        result = "📺 **Monitored Channels:**\n\n"
        for name, data in channels.items():
            status_emoji = "✅" if data.get("status") == "active" else "⚠️"
            last_check = data.get("last_check", "Never")
            if last_check != "Never":
                try:
                    # Parse UTC timestamp and convert to local timezone
                    from datetime import timezone
                    if last_check.endswith('Z'):
                        # ISO format with Z suffix (UTC)
                        utc_dt = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                    else:
                        # Assume UTC if no timezone info
                        utc_dt = datetime.fromisoformat(last_check).replace(tzinfo=timezone.utc)
                    
                    # Convert to local time
                    local_dt = utc_dt.astimezone()
                    last_check = local_dt.strftime("%Y-%m-%d %H:%M")
                except:
                    # Fallback: try to parse as naive datetime (older format)
                    try:
                        last_check = datetime.fromisoformat(last_check).strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
            
            platform = data.get('platform', 'rumble')
            content_type = data.get('content_type', 'livestreams')
            
            # Platform emojis
            platform_emoji = {
                "rumble": "🟡",
                "kick": "🟢"
            }.get(platform, "⚪")
            
            # Content type emojis
            content_emoji = "📺" if content_type == "videos" else "🔴"
            
            result += f"{status_emoji} **{name}** {platform_emoji} {platform} {content_emoji} {content_type}\n"
            result += f"   🔗 {data.get('url', 'N/A')}\n"
            result += f"   👤 Added by: {data.get('added_by', 'Unknown')}\n"
            result += f"   🕐 Last check: {last_check}\n\n"
        
        return result

    async def _handle_status_command(self, args: List[str], context: CommandContext) -> str:
        """Handle monitoring status command"""
        status = "🟢 Running" if self.is_monitoring else "🔴 Stopped"
        interval = self.config["monitoring"]["check_interval_minutes"]
        
        # Count total monitored channels
        total_channels = 0
        for context_file in self.data_dir.glob("*.yml"):
            try:
                filename = context_file.stem
                channels = self._load_context_channels(filename)
                total_channels += len(channels)
            except:
                pass
        
        return f"""📺 **Krumble Monitor Status**

🔄 **Status:** {status}
⏱️ **Check Interval:** {interval} minutes
📺 **Total Channels:** {total_channels}
📂 **Plugin Version:** {self.version}

Use `!kmonitor start/stop` to control monitoring"""

    async def _handle_monitor_command(self, args: List[str], context: CommandContext) -> str:
        """Handle monitor control commands"""
        if not args:
            return "❌ Usage: !kmonitor <start|stop|restart|status>"
        
        action = args[0].lower()
        
        if action == "start":
            if self.is_monitoring:
                return "✅ Krumble monitoring is already running"
            await self._start_monitoring()
            return "✅ Krumble monitoring started"
        elif action == "stop":
            if not self.is_monitoring:
                return "⚠️ Krumble monitoring is not running"
            await self._stop_monitoring()
            return "⚠️ Krumble monitoring stopped"
        elif action == "restart":
            await self._stop_monitoring()
            await self._start_monitoring()
            return "🔄 Krumble monitoring restarted"
        elif action == "status":
            return await self._handle_status_command([], context)
        else:
            return "❌ Usage: !kmonitor <start|stop|restart|status>"

    async def _handle_help_command(self, args: List[str], context: CommandContext) -> str:
        """Handle dedicated help command with troubleshooting"""
        return self._get_comprehensive_help()

    async def _handle_manual_check(self, args: List[str], context: CommandContext) -> str:
        """Handle manual check command"""
        if not args:
            return "❌ Usage: !kcheck <channel_name> or !krumble check <channel_name>"
        
        channel_name = args[0]
        context_id = context.chat_id
        
        channels = self._load_context_channels(context_id)
        if channel_name not in channels:
            return f"❌ Channel '{channel_name}' is not being monitored. Use `!klist` to see monitored channels or `!kadd {channel_name}` to add it."
        
        channel_data = channels[channel_name]
        url = channel_data.get("url")
        
        try:
            result = await self._check_channel(url)
            if result.get("success"):
                new_count = len(result.get("new_streams", []))
                total_count = result.get("total_streams", 0)
                return f"✅ **Manual check completed for {channel_name}**\n📺 Total streams: {total_count}\n🆕 New streams: {new_count}"
            else:
                return f"❌ Check failed for {channel_name}: {result.get('error', 'Unknown error')}"
        except Exception as e:
            return f"❌ Error checking {channel_name}: {str(e)}"

    def _detect_platform(self, url: str) -> str:
        """Detect which platform a URL belongs to"""
        if "rumble.com" in url:
            return "rumble"
        elif "kick.com" in url:
            return "kick"
        else:
            return "unknown"
    
    def _parse_channel_info(self, input_str: str) -> Optional[Dict[str, str]]:
        """Parse channel info from URL or direct input"""
        platform = self._detect_platform(input_str)
        
        if platform == "rumble":
            if "rumble.com/c/" in input_str:
                parts = input_str.split("/")
                if len(parts) >= 5:
                    channel_name = parts[4]
                    return {
                        "platform": "rumble",
                        "channel": channel_name,
                        "base_url": f"https://rumble.com/c/{channel_name}"
                    }
        elif platform == "kick":
            if "kick.com/" in input_str:
                # kick.com/channelname or kick.com/channelname/videos
                parts = input_str.split("/")
                if len(parts) >= 4:
                    channel_name = parts[3]
                    return {
                        "platform": "kick", 
                        "channel": channel_name,
                        "base_url": f"https://kick.com/{channel_name}"
                    }
        
        # Fallback: assume it's a direct channel name for Rumble
        if "/" not in input_str and input_str.replace("_", "").replace("-", "").isalnum():
            return {
                "platform": "rumble",
                "channel": input_str,
                "base_url": f"https://rumble.com/c/{input_str}"
            }
        
        return None

    def _sanitize_filename(self, context_id: str) -> str:
        """Sanitize context ID for use as filename"""
        import re
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r'[^\w\-_.]', '_', context_id)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized

    def _load_context_channels(self, context_id: str) -> Dict[str, Any]:
        """Load channels for a specific context (user or group)"""
        filename = self._sanitize_filename(context_id)
        context_file = self.data_dir / f"{filename}.yml"
        try:
            if context_file.exists():
                with open(context_file, 'r') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"Error loading channels for {context_id}: {e}")
        return {}

    def _save_context_channels(self, context_id: str, channels: Dict[str, Any]):
        """Save channels for a specific context"""
        filename = self._sanitize_filename(context_id)
        context_file = self.data_dir / f"{filename}.yml"
        try:
            # Ensure parent directory exists and is writable
            self.data_dir.mkdir(exist_ok=True, mode=0o755)
            
            with open(context_file, 'w') as f:
                yaml.dump(channels, f, default_flow_style=False, indent=2)
            
            # Set file permissions
            import os
            os.chmod(str(context_file), 0o644)
            
        except Exception as e:
            self.logger.error(f"Error saving channels for {context_id}: {e}")

    async def _start_monitoring(self):
        """Start the monitoring task"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("✅ Krumble monitoring started")

    async def _stop_monitoring(self):
        """Stop the monitoring task"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        self.logger.info("⚠️ Krumble monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                await self._check_all_channels()
                
                # Wait for next check
                interval = self.config["monitoring"]["check_interval_minutes"] * 60
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _check_all_channels(self):
        """Check all monitored channels for updates"""
        # Get all context files
        for context_file in self.data_dir.glob("*.yml"):
            filename = context_file.stem
            # For now, use filename as context_id since we don't store reverse mapping
            # This will work for sanitized names, original context_id is stored in channel data
            channels = self._load_context_channels(filename)
            
            for channel_name, channel_data in channels.items():
                try:
                    # Use the original context_id if stored in channel data, otherwise use filename
                    context_id = channel_data.get('original_context_id', filename)
                    await self._check_and_notify_channel(context_id, channel_name, channel_data)
                except Exception as e:
                    self.logger.error(f"Error checking channel {channel_name} for {filename}: {e}")

    async def _check_and_notify_channel(self, context_id: str, channel_name: str, channel_data: Dict[str, Any]):
        """Check a single channel and send notifications if needed"""
        url = channel_data.get("url")
        if not url:
            return
        
        # Run the scraper
        result = await self._check_channel(url)
        
        # Update last check time
        channels = self._load_context_channels(context_id)
        if channel_name in channels:
            channels[channel_name]["last_check"] = datetime.now().isoformat()
            self._save_context_channels(context_id, channels)
        
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            if "blocked" in error.lower() or "security" in error.lower():
                # Send blocking notification
                message = self.config["messages"]["blocked"].format(channel=channel_name)
                await self._send_notification(context_id, message)
            return
        
        # Check for new streams
        new_streams = result.get("new_streams", [])
        for stream in new_streams:
            if stream.get("isLive"):
                message = self.config["messages"]["new_stream"].format(
                    title=stream.get("title", "Unknown"),
                    url=stream.get("url", ""),
                    time=stream.get("publishTime", "Unknown")
                )
            else:
                message = self.config["messages"]["new_video"].format(
                    title=stream.get("title", "Unknown"),
                    url=stream.get("url", ""),
                    time=stream.get("publishTime", "Unknown")
                )
            
            await self._send_notification(context_id, message)

    async def _check_channel(self, url: str) -> Dict[str, Any]:
        """Check channel via HTTP API to containerized scraper"""
        try:
            # Send request to containerized scraper service
            result = await self.send_http_request("/scrape", {
                "channel_url": url,
                "options": {
                    "detect_changes": True,
                    "screenshot": True
                }
            }, method="POST")
            
            if result.get("success"):
                return {
                    "success": True,
                    "new_streams": result.get("newStreams", []),
                    "total_streams": result.get("totalStreams", 0),
                    "has_changes": result.get("hasChanges", False)
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown scraper error")
                }
                
        except Exception as e:
            self.logger.error(f"Error checking channel {url}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _send_notification(self, context_id: str, message: str):
        """Send notification to the appropriate context"""
        try:
            if self.adapter:
                # Create a minimal context for sending
                from plugins.universal_plugin_base import CommandContext
                notification_context = CommandContext(
                    command="",
                    args=[],
                    args_raw="",
                    user_id="system",
                    chat_id=context_id,
                    user_display_name="Krumble Monitor",
                    platform=self.adapter.platform,
                    raw_message={}
                )
                
                await self.adapter.send_message(message, notification_context)
            else:
                self.logger.warning(f"No adapter available to send notification to {context_id}")
        except Exception as e:
            self.logger.error(f"Error sending notification to {context_id}: {e}")

    def _get_krumble_help(self) -> str:
        """Get basic Krumble plugin help text"""
        return """🎯 **Krumble Plugin Help**

**Multi-Platform Content Monitor**
Supports: 🟡 Rumble, 🟢 Kick

**Commands:**
• `!krumble help` - Show this help
• `!khelp` - Show comprehensive help with troubleshooting
• `!krumble check <channel>` - Manually check a channel
• `!kcheck <channel>` - Same as above (shortcut)
• `!kadd <channel_url_or_name>` - Add channel (monitors both livestreams and videos)
• `!kremove <channel_name>` - Remove channel from monitoring
• `!klist` - List monitored channels for this context
• `!kstatus` - Show monitoring status
• `!kmonitor <start|stop|restart>` - Control monitoring

**Quick Start:**
1. `!kadd madattheinternet` - Add Rumble channel
2. `!kadd https://kick.com/kinocasinogaming` - Add Kick channel
3. `!klist` - Verify channels were added
4. Bot will automatically notify on new content!

Use `!khelp` for detailed help and troubleshooting."""

    def _get_comprehensive_help(self) -> str:
        """Get comprehensive help with troubleshooting"""
        return """🎯 **Krumble Plugin - Complete Guide**

**Multi-Platform Content Monitor**
Supports: 🟡 Rumble, 🟢 Kick

**📋 All Commands:**
• `!kadd <channel>` - Add channel (monitors both livestreams and videos)
• `!kremove <channel>` - Remove channel from monitoring
• `!klist` - List monitored channels for this context
• `!kcheck <channel>` - Manually check a channel
• `!kstatus` - Show monitoring status and stats
• `!kmonitor <start|stop|restart>` - Control monitoring
• `!khelp` - Show this comprehensive help

**🚀 Getting Started:**

**Step 1 - Add Channels:**
```
!kadd madattheinternet                          # Rumble channel
!kadd https://kick.com/kinocasinogaming         # Kick channel  
!kadd https://rumble.com/c/madattheinternet     # Full Rumble URL
```
Bot automatically detects the platform and monitors both livestreams and videos.

**Step 2 - Verify It's Added:**
```
!klist
```
You should see your channel listed. If not, see troubleshooting below.

**Step 3 - Test Manual Check:**
```
!kcheck madattheinternet
```
This tests if the bot can access the channel properly.

**🔧 Troubleshooting:**

**Problem: Channel not in !klist after adding**
• Check you're in the same context (group/DM) where you added it
• Channels added in groups only show in that group
• Channels added in DMs only show in DMs with that user
• Try: `!kadd channelname` again to re-add

**Problem: !kcheck says channel not monitored**
• First run `!klist` to see what channels are actually monitored
• If missing, re-add with `!kadd channelname`
• Make sure you're spelling the channel name exactly as shown in `!klist`

**Problem: No notifications for new content**
• Check monitoring is running: `!kstatus`
• If stopped, start it: `!kmonitor start`
• Test manual check: `!kcheck channelname`
• Check channel is active in `!klist` (should show ✅)

**Problem: Bot says channel is blocked**
• Platform has anti-bot protection that sometimes triggers
• Bot will automatically retry later
• Use `!kcheck channelname` to test current status
• Bot takes screenshots when blocked for debugging

**💡 How It Works:**

**Context Separation:**
• Each group and each user has separate channel lists
• Adding a channel in Group A won't notify Group B
• This allows different contexts to monitor different channels

**Monitoring Process:**
• Bot checks all channels every 5 minutes (configurable)
• Detects new livestreams and videos automatically
• Sends notifications to the context where channel was added
• Handles rate limiting and anti-bot measures gracefully

**Channel Storage:**
• Each context gets its own data file: `data/contextid.yml`
• Files contain channel names, URLs, and metadata
• Deleting a data file stops monitoring for that context

**🎯 Best Practices:**

1. **Test First:** Always use `!kcheck` after adding a channel
2. **Monitor Status:** Regularly check `!kstatus` to ensure monitoring is active
3. **Context Awareness:** Remember channels are per-group/per-user
4. **Be Patient:** Initial detection can take up to 5 minutes
5. **Check Logs:** Bot will notify if a channel gets blocked

**📊 Advanced Features:**

• **Screenshots:** Bot takes screenshots when sites block it
• **Docker Isolation:** Uses containerized scraping for reliability
• **Anti-Bot Detection:** Gracefully handles security measures
• **Configurable Intervals:** Admins can adjust check frequency
• **Retry Logic:** Automatically retries failed checks
• **Health Monitoring:** Built-in container health checks

**🔄 Monitoring Control:**
```
!kmonitor status   # Check if monitoring is running
!kmonitor start    # Start automatic monitoring
!kmonitor stop     # Stop automatic monitoring  
!kmonitor restart  # Restart monitoring service
```

**Need more help?** Check the bot logs or contact an admin."""

    def _get_string(self, key: str, **kwargs) -> str:
        """Get localized string with formatting"""
        keys = key.split('.')
        value = self.strings
        for k in keys:
            value = value.get(k, key)
        
        if isinstance(value, str) and kwargs:
            return value.format(**kwargs)
        return str(value)

    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        await self._stop_monitoring()
        self.logger.info("Krumble plugin cleanup completed")


# Export the plugin class
__all__ = ['UniversalKrumblePlugin']