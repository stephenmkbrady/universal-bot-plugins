"""
Loupe Plugin - Comprehensive Web Scraper & Monitor

Advanced web scraping plugin with intelligent change detection, monitoring,
and flexible notification system. Supports any website type with generic
diff system for tracking changes.

Quick Commands:
- !loupe - Show help and configured sites
- !loupe <site_name> - Scrape a specific site
- !loupe list - List all available sites
- !loupe monitor - Show monitoring status
- !loupe notifications - Show recent change notifications

Site Management:
- !loupe add-site <id> <url> <name> - Add new site (auto-configures notifications)
- !loupe remove-site <id> - Remove site completely
- !loupe edit-site <id> <field> <value> - Edit site properties

Selector Management:
- !loupe selectors <site> - Show all selectors for a site
- !loupe add-selector <site> <name> <css> - Add CSS selector
- !loupe test-selector <site> <name> - Test existing selector
- !loupe try-selector <site> <css> - Try selector without saving

Monitoring & Notifications:
- !loupe enable <site> [interval] - Enable monitoring
- !loupe disable <site> - Disable monitoring
- !loupe add-group <site> <group> - Add notification group
- !loupe add-user <site> <user> - Add notification user

Diff System:
- !loupe diff-mode <site> <mode> - Set diff mode (lines/full/disabled)
- !loupe diff-config <site> - Show diff configuration

Run '!loupe' for complete help and examples.
"""

from typing import List, Optional, Dict, Any
import logging
import asyncio
import aiohttp
import yaml
import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import html2text
from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform

# Optional import for Cloudflare challenge handling
try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False


class LoupePlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("loupe", logger=logger)
        self.version = "1.0.0"
        self.description = "Configurable web scraper with HTML to text conversion"
        
        # Supports all platforms
        self.supported_platforms = [BotPlatform.MATRIX, BotPlatform.SIMPLEX]
        
        if not self.logger:
            self.logger = logging.getLogger(f"plugin.{self.name}")
        
        # Configuration
        self.config_file = Path(__file__).parent / "config.yml"
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.sites = {}
        self.load_config()
        
        # HTML to text converter
        self.html2text = html2text.HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.body_width = 0
        self.html2text.unicode_snob = True
        self.html2text.ignore_images = True
        
        # Monitoring
        self.monitoring_tasks = {}
        self.last_content = {}
        self.adapter = None  # Will be set when the plugin is initialized
    
    def load_config(self):
        """Load sites configuration from config.yml"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
                    self.sites = config.get('sites', {})
                    self.logger.info(f"Loaded {len(self.sites)} sites from config")
            else:
                self.logger.warning("No config.yml found, creating example")
                self.create_example_config()
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            self.sites = {}
    
    def create_example_config(self):
        """Create an example config.yml file"""
        example_config = {
            'sites': {
                'hacker_news': {
                    'url': 'https://news.ycombinator.com/',
                    'name': 'Hacker News',
                    'selectors': {
                        'stories': '.athing .title > a',  # Story titles
                        'scores': '.score',              # Story scores
                        'comments': '.subtext a[href*="item"]'  # Comment counts
                    },
                    'description': 'Latest tech news and discussions'
                },
                'github_trending': {
                    'url': 'https://github.com/trending',
                    'name': 'GitHub Trending',
                    'selectors': {
                        'repositories': 'article h1 a',
                        'descriptions': 'article p',
                        'languages': 'article [itemprop="programmingLanguage"]'
                    },
                    'description': 'Trending repositories on GitHub'
                }
            }
        }
        
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(example_config, f, default_flow_style=False, indent=2)
            self.sites = example_config['sites']
            self.logger.info("Created example config.yml")
        except Exception as e:
            self.logger.error(f"Error creating example config: {e}")
    
    async def _save_config(self):
        """Save current configuration to config.yml"""
        try:
            config = {'sites': self.sites}
            
            # Read existing file to preserve comments and structure
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    lines = f.readlines()
                
                # Find where sites section starts
                sites_line_idx = None
                for i, line in enumerate(lines):
                    if line.strip().startswith('sites:'):
                        sites_line_idx = i
                        break
                
                if sites_line_idx is not None:
                    # Keep header comments and add updated sites
                    header_lines = lines[:sites_line_idx]
                else:
                    header_lines = []
            else:
                header_lines = []
            
            # Write updated configuration
            with open(self.config_file, 'w') as f:
                # Write header comments if they exist
                f.writelines(header_lines)
                
                # Write updated sites configuration
                import yaml
                yaml.dump(config, f, default_flow_style=False, indent=2, sort_keys=False)
            
            self.logger.info("Configuration saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            raise
    
    async def initialize(self, adapter) -> bool:
        """Initialize plugin with bot adapter"""
        try:
            if not await super().initialize(adapter):
                return False
            
            self.adapter = adapter
            self.logger.info(f"Initializing loupe plugin for {adapter.platform.value} platform")
            self.logger.info(f"Configured sites: {list(self.sites.keys())}")
            
            # Start monitoring tasks
            self.start_monitoring()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize loupe plugin: {e}")
            return False
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return ["loupe"]
    
    async def handle_command(self, context: CommandContext) -> Optional[str]:
        """Handle loupe commands"""
        self.logger.info(f"Handling loupe command from {context.user_display_name}")
        
        try:
            if not context.has_args:
                # Show help information and configured sites
                return self._show_help_and_sites()
            
            arg = context.get_arg(0).lower()
            
            if arg == "list":
                return self._list_sites()
            elif arg == "reload":
                return self._reload_config()
            elif arg == "monitor":
                return self._show_monitoring_status()
            elif arg == "status":
                return self._show_monitoring_status()
            elif arg == "notifications":
                return self._show_recent_notifications()
            elif arg == "test" and context.has_args and context.arg_count > 1:
                # Test command: !loupe test <site_id>
                test_site_id = context.get_arg(1)
                return await self._test_monitoring(test_site_id)
            elif arg == "enable" and context.has_args and context.arg_count > 1:
                # Enable monitoring: !loupe enable <site_name> [interval]
                site_id = context.get_arg(1)
                interval = int(context.get_arg(2)) if context.arg_count > 2 else 3600
                return await self._enable_monitoring(site_id, interval, context)
            elif arg == "disable" and context.has_args and context.arg_count > 1:
                # Disable monitoring: !loupe disable <site_name>
                site_id = context.get_arg(1)
                return await self._disable_monitoring(site_id)
            elif arg == "interval" and context.has_args and context.arg_count > 2:
                # Set interval: !loupe interval <site_name> <seconds>
                site_id = context.get_arg(1)
                interval = int(context.get_arg(2))
                return await self._set_interval(site_id, interval)
            elif arg == "add-group" and context.has_args and context.arg_count > 2:
                # Add group: !loupe add-group <site_name> <group_name>
                site_id = context.get_arg(1)
                group_name = " ".join(context.args[2:])  # Allow group names with spaces
                return await self._add_notification_target(site_id, group_name, "group")
            elif arg == "remove-group" and context.has_args and context.arg_count > 2:
                # Remove group: !loupe remove-group <site_name> <group_name>
                site_id = context.get_arg(1)
                group_name = " ".join(context.args[2:])
                return await self._remove_notification_target(site_id, group_name, "group")
            elif arg == "add-user" and context.has_args and context.arg_count > 2:
                # Add user: !loupe add-user <site_name> <user_name>
                site_id = context.get_arg(1)
                user_name = context.get_arg(2)
                return await self._add_notification_target(site_id, user_name, "user")
            elif arg == "remove-user" and context.has_args and context.arg_count > 2:
                # Remove user: !loupe remove-user <site_name> <user_name>
                site_id = context.get_arg(1)
                user_name = context.get_arg(2)
                return await self._remove_notification_target(site_id, user_name, "user")
            # Diff configuration commands
            elif arg == "diff-mode" and context.has_args and context.arg_count > 2:
                # Set diff mode: !loupe diff-mode <site_name> <mode>
                site_id = context.get_arg(1)
                mode = context.get_arg(2).lower()
                return await self._set_diff_mode(site_id, mode)
            elif arg == "diff-config" and context.has_args and context.arg_count > 1:
                # Show diff configuration: !loupe diff-config <site_name>
                site_id = context.get_arg(1)
                return self._show_diff_config(site_id)
            # Site management commands
            elif arg == "add-site" and context.has_args and context.arg_count > 3:
                # Add site: !loupe add-site <site_id> <url> <display_name>
                site_id = context.get_arg(1)
                url = context.get_arg(2)
                display_name = " ".join(context.args[3:])
                return await self._add_site(site_id, url, display_name, context)
            elif arg == "remove-site" and context.has_args and context.arg_count > 1:
                # Remove site: !loupe remove-site <site_id>
                site_id = context.get_arg(1)
                return await self._remove_site(site_id)
            elif arg == "edit-site" and context.has_args and context.arg_count > 3:
                # Edit site: !loupe edit-site <site_id> <field> <value>
                site_id = context.get_arg(1)
                field = context.get_arg(2)
                value = " ".join(context.args[3:])
                return await self._edit_site(site_id, field, value)
            # Selector management commands
            elif arg == "selectors" and context.has_args and context.arg_count > 1:
                # Show selectors: !loupe selectors <site_name>
                site_id = context.get_arg(1)
                return self._show_selectors(site_id)
            elif arg == "add-selector" and context.has_args and context.arg_count > 3:
                # Add selector: !loupe add-selector <site_name> <selector_name> <css_selector>
                site_id = context.get_arg(1)
                selector_name = context.get_arg(2)
                css_selector = " ".join(context.args[3:])
                return await self._add_selector(site_id, selector_name, css_selector)
            elif arg == "edit-selector" and context.has_args and context.arg_count > 3:
                # Edit selector: !loupe edit-selector <site_name> <selector_name> <new_css_selector>
                site_id = context.get_arg(1)
                selector_name = context.get_arg(2)
                new_css_selector = " ".join(context.args[3:])
                return await self._edit_selector(site_id, selector_name, new_css_selector)
            elif arg == "remove-selector" and context.has_args and context.arg_count > 2:
                # Remove selector: !loupe remove-selector <site_name> <selector_name>
                site_id = context.get_arg(1)
                selector_name = context.get_arg(2)
                return await self._remove_selector(site_id, selector_name)
            elif arg == "test-selector" and context.has_args and context.arg_count > 2:
                # Test selector: !loupe test-selector <site_name> <selector_name>
                site_id = context.get_arg(1)
                selector_name = context.get_arg(2)
                return await self._test_selector(site_id, selector_name)
            elif arg == "try-selector" and context.has_args and context.arg_count > 2:
                # Try selector: !loupe try-selector <site_name> <css_selector>
                site_id = context.get_arg(1)
                css_selector = " ".join(context.args[2:])
                return await self._try_selector(site_id, css_selector)
            elif arg in self.sites:
                # Scrape specific site
                return await self._scrape_site(arg)
            else:
                return f"❌ Unknown site '{arg}'. Use `!loupe list` to see available sites."
                
        except Exception as e:
            self.logger.error(f"Error handling loupe command: {str(e)}", exc_info=True)
            return f"❌ Error processing loupe command"
    
    def _show_help_and_sites(self) -> str:
        """Show comprehensive help information and configured sites"""
        help_text = """🔍 **Loupe - Web Scraper Plugin**
*Configurable web scraper with monitoring and notifications*
*🛡️ Includes advanced DDoS/bot challenge bypass support*

**📚 Quick Commands:**
• `!loupe` - Show this help and configured sites
• `!loupe <site>` - Scrape a specific site
• `!loupe list` - List all sites
• `!loupe monitor` - Show monitoring status

**⚙️ Site Management:**
• `!loupe add-site <id> <url> <name>` - Add new site
• `!loupe remove-site <id>` - Remove site
• `!loupe edit-site <id> <field> <value>` - Edit site

**🎯 Selector Management:**
• `!loupe selectors <site>` - Show selectors
• `!loupe add-selector <site> <name> <css>` - Add selector
• `!loupe test-selector <site> <name>` - Test selector
• `!loupe try-selector <site> <css>` - Try selector

**📊 Monitoring:**
• `!loupe enable <site> [interval]` - Enable monitoring
• `!loupe disable <site>` - Disable monitoring
• `!loupe interval <site> <seconds>` - Set interval
• `!loupe add-group <site> <group>` - Add notification group
• `!loupe add-user <site> <user>` - Add notification user

**🔄 Diff System:**
• `!loupe diff-mode <site> <mode>` - Set diff mode (lines/full/disabled)
• `!loupe diff-config <site>` - Show diff configuration

**💡 Examples:**
• `!loupe add-site hn https://news.ycombinator.com "Hacker News"`
• `!loupe add-selector hn titles "a.storylink"`
• `!loupe enable hn 1800` (30 min monitoring)
• `!loupe add-group hn "Tech Team"`
• `!loupe diff-mode hn lines` (enable line-based diff notifications)

For complete documentation, see COMPLETE_COMMANDS.md in the plugin directory.

"""
        
        # Add configured sites information
        if self.sites:
            help_text += "**🔍 Currently Configured Sites:**\n"
            for site_id, site in self.sites.items():
                help_text += f"\n• **{site.get('name', site_id)}** (`!loupe {site_id}`)"
                if 'description' in site:
                    help_text += f"\n  *{site['description']}*"
                
                # Show monitoring status
                if site.get('monitor', False):
                    interval = site.get('interval', 3600)
                    help_text += f"\n  📊 Monitoring: ✅ (every {interval}s)"
                    
                    # Show notification targets
                    notify_groups = site.get('notify_groups', [])
                    notify_users = site.get('notify_users', [])
                    if notify_groups or notify_users:
                        targets = []
                        if notify_groups:
                            targets.extend([f"Groups: {', '.join(notify_groups)}"])
                        if notify_users:
                            targets.extend([f"Users: {', '.join(notify_users)}"])
                        help_text += f"\n  🔔 Notifies: {' | '.join(targets)}"
                else:
                    help_text += f"\n  📊 Monitoring: ❌ Disabled"
                
                # Show diff mode status
                diff_mode = site.get('diff_mode', 'lines')
                diff_icons = {'lines': '🔄', 'full': '📄', 'disabled': '❌'}
                help_text += f"\n  {diff_icons.get(diff_mode, '🔄')} Diff Mode: {diff_mode}"
                
                help_text += f"\n  🌐 URL: {site.get('url', 'N/A')}\n"
        else:
            help_text += "**🔍 Currently Configured Sites:**\nNo sites configured yet. Use `!loupe add-site` to get started!\n"
        
        return help_text
    
    def _validate_site_exists(self, site_id: str) -> Optional[str]:
        """Validate that a site exists, return error message if not"""
        if site_id not in self.sites:
            return f"❌ Site '{site_id}' not found in configuration"
        return None
    
    def _show_all_sites(self) -> str:
        """Show all configured sites"""
        if not self.sites:
            return "📋 **Loupe - Web Scraper**\n\nNo sites configured. Check config.yml file."
        
        result = "📋 **Loupe - Web Scraper**\n\nConfigured sites:\n"
        for site_id, site in self.sites.items():
            result += f"\n🔍 **{site.get('name', site_id)}**"
            result += f"\n   Command: `!loupe {site_id}`"
            if 'description' in site:
                result += f"\n   {site['description']}"
            result += f"\n   URL: {site.get('url', 'N/A')}\n"
        
        result += f"\n💡 Use `!loupe <site_name>` to scrape a site"
        return result
    
    def _list_sites(self) -> str:
        """List available sites"""
        if not self.sites:
            return "📋 No sites configured."
        
        result = "📋 **Available Sites:**\n"
        for site_id, site in self.sites.items():
            result += f"\n• `{site_id}` - {site.get('name', site_id)}"
        
        return result
    
    def _reload_config(self) -> str:
        """Reload configuration"""
        try:
            self.load_config()
            return f"✅ Configuration reloaded. {len(self.sites)} sites available."
        except Exception as e:
            return f"❌ Error reloading config: {str(e)}"
    
    def _show_monitoring_status(self) -> str:
        """Show monitoring status for all sites"""
        if not self.sites:
            return "📋 No sites configured."
        
        result = "🔍 **Monitoring Status:**\n"
        monitored_count = 0
        
        for site_id, site_config in self.sites.items():
            name = site_config.get('name', site_id)
            is_monitored = site_config.get('monitor', False)
            interval = site_config.get('interval', 3600)
            
            if is_monitored:
                monitored_count += 1
                task_status = "Running" if site_id in self.monitoring_tasks and not self.monitoring_tasks[site_id].done() else "Stopped"
                result += f"\n🟢 **{name}** (`{site_id}`)"
                result += f"\n   ⏱️ Interval: {interval}s ({interval//60}m)"
                result += f"\n   📊 Status: {task_status}"
                
                # Show notification targets
                notify_groups = site_config.get('notify_groups', [])
                notify_users = site_config.get('notify_users', [])
                if notify_groups or notify_users:
                    targets = []
                    if notify_groups:
                        targets.extend([f"👥 {g}" for g in notify_groups])
                    if notify_users:
                        targets.extend([f"👤 {u}" for u in notify_users])
                    result += f"\n   🎯 Notifies: {', '.join(targets)}"
                else:
                    result += f"\n   ⚠️ No notification targets configured"
                
                # Show last check time if available
                hash_file = self.data_dir / f"{site_id}_hash.txt"
                if hash_file.exists():
                    try:
                        last_modified = datetime.fromtimestamp(hash_file.stat().st_mtime)
                        result += f"\n   🕐 Last check: {last_modified.strftime('%Y-%m-%d %H:%M:%S')}"
                    except:
                        pass
            else:
                result += f"\n🔴 **{name}** (`{site_id}`) - Monitoring disabled"
        
        if monitored_count == 0:
            result += "\n\n⚠️ No sites have monitoring enabled."
            result += "\n💡 Enable monitoring by adding `monitor: true` and `interval: <seconds>` to site configs."
        else:
            result += f"\n\n📈 Total monitored sites: {monitored_count}/{len(self.sites)}"
        
        return result
    
    def _show_recent_notifications(self) -> str:
        """Show recent change notifications"""
        notifications_file = self.data_dir / "notifications.jsonl"
        
        if not notifications_file.exists():
            return "📬 **Recent Notifications**\n\nNo notifications found yet."
        
        try:
            notifications = []
            with open(notifications_file, 'r') as f:
                lines = f.readlines()
                # Get last 10 notifications
                for line in lines[-10:]:
                    if line.strip():
                        notifications.append(json.loads(line.strip()))
            
            if not notifications:
                return "📬 **Recent Notifications**\n\nNo notifications found yet."
            
            result = "📬 **Recent Notifications** (latest 10)\n"
            
            # Show notifications in reverse order (newest first)
            for notification in reversed(notifications):
                timestamp = datetime.fromisoformat(notification['timestamp'])
                site_name = notification['site_name']
                result += f"\n🔔 **{site_name}** - {timestamp.strftime('%m/%d %H:%M')}"
                
                # Show a preview of the content
                message = notification['message']
                content_start = message.find('\n\n')
                if content_start > 0:
                    content = message[content_start+2:]
                    preview = content[:100] + "..." if len(content) > 100 else content
                    result += f"\n   📝 {preview}"
                result += "\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error reading notifications: {e}")
            return "❌ Error reading notifications file."
    
    async def _test_monitoring(self, site_id: str) -> str:
        """Test monitoring and notifications for a specific site"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        site_config = self.sites[site_id]
        site_name = site_config.get('name', site_id)
        
        if not site_config.get('monitor', False):
            return f"❌ Monitoring is not enabled for {site_name}. Enable it in config.yml with `monitor: true`"
        
        try:
            # Force a monitoring check
            self.logger.info(f"🧪 Testing monitoring for {site_name}")
            
            # Get current content
            current_content = await self._scrape_site(site_id)
            if not current_content:
                return f"❌ Failed to scrape content from {site_name}"
            
            # Force a change by modifying the stored hash (for testing)
            hash_file = self.data_dir / f"{site_id}_hash.txt"
            if hash_file.exists():
                hash_file.write_text("test_hash_to_force_change")
            
            # Trigger notification
            await self._notify_change(site_id, current_content)
            
            # Show notification targets
            notify_groups = site_config.get('notify_groups', [])
            notify_users = site_config.get('notify_users', [])
            
            result = f"✅ **Test completed for {site_name}**\n\n"
            result += f"📊 Content scraped: {len(current_content)} characters\n"
            
            if notify_groups or notify_users:
                result += f"🎯 Notifications sent to:\n"
                for group in notify_groups:
                    result += f"   👥 Group: {group}\n"
                for user in notify_users:
                    result += f"   👤 User: {user}\n"
            else:
                result += "⚠️ No notification targets configured\n"
            
            result += f"\n💡 Check logs for detailed notification delivery status"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error testing monitoring for {site_id}: {e}")
            return f"❌ Error testing {site_name}: {str(e)}"
    
    async def _enable_monitoring(self, site_id: str, interval: int, context=None) -> str:
        """Enable monitoring for a site and auto-configure notifications based on context"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        try:
            site_config = self.sites[site_id]
            site_name = site_config.get('name', site_id)
            
            # Enable monitoring
            site_config['monitor'] = True
            site_config['interval'] = interval
            
            # Initialize notification arrays if they don't exist
            if 'notify_groups' not in site_config:
                site_config['notify_groups'] = []
            if 'notify_users' not in site_config:
                site_config['notify_users'] = []
            
            # Auto-configure notifications based on context
            notification_info = []
            if context:
                # Determine if this is a group message by checking raw_message data
                is_group_message = False
                if hasattr(context, 'raw_message') and context.raw_message:
                    # Check for groupInfo in the chat_info (SimpleX-specific logic)
                    chat_info = context.raw_message.get('chatInfo', {})
                    is_group_message = "groupInfo" in chat_info
                
                if is_group_message:
                    # In a group: add both the group and the user
                    group_name = context.chat_id  # Use chat_id as group identifier
                    if group_name not in site_config['notify_groups']:
                        site_config['notify_groups'].append(group_name)
                        notification_info.append(f"📢 Added group: {group_name}")
                    
                    user_name = context.user_display_name
                    if user_name not in site_config['notify_users']:
                        site_config['notify_users'].append(user_name)
                        notification_info.append(f"👤 Added user: {user_name}")
                else:
                    # In direct message: add only the user
                    user_name = context.user_display_name
                    if user_name not in site_config['notify_users']:
                        site_config['notify_users'].append(user_name)
                        notification_info.append(f"👤 Added user: {user_name}")
            
            # Save configuration
            await self._save_config()
            
            # Start monitoring task if not running
            if site_id not in self.monitoring_tasks or self.monitoring_tasks[site_id].done():
                task = asyncio.create_task(self._monitor_site(site_id))
                self.monitoring_tasks[site_id] = task
                self.logger.info(f"Started monitoring task for {site_id}")
            
            response = f"✅ **Monitoring enabled for {site_name}**\n⏱️ Interval: {interval}s ({interval//60}m)"
            if notification_info:
                response += f"\n🔔 **Notifications configured:**\n" + "\n".join(notification_info)
            else:
                response += "\n💡 Use `!loupe add-group` or `!loupe add-user` to configure additional notifications"
            
            return response
            
        except ValueError:
            return "❌ Invalid interval value. Please provide a number in seconds."
        except Exception as e:
            self.logger.error(f"Error enabling monitoring for {site_id}: {e}")
            return f"❌ Error enabling monitoring: {str(e)}"
    
    async def _disable_monitoring(self, site_id: str) -> str:
        """Disable monitoring for a site and remove all monitoring settings"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        try:
            site_config = self.sites[site_id]
            site_name = site_config.get('name', site_id)
            
            # Stop monitoring task
            if site_id in self.monitoring_tasks and not self.monitoring_tasks[site_id].done():
                self.monitoring_tasks[site_id].cancel()
                del self.monitoring_tasks[site_id]
                self.logger.info(f"Stopped monitoring task for {site_id}")
            
            # Remove monitoring configuration
            site_config.pop('monitor', None)
            site_config.pop('interval', None)
            site_config.pop('notify_groups', None)
            site_config.pop('notify_users', None)
            
            # Remove hash file
            hash_file = self.data_dir / f"{site_id}_hash.txt"
            if hash_file.exists():
                hash_file.unlink()
            
            # Save configuration
            await self._save_config()
            
            return f"✅ **Monitoring disabled for {site_name}**\n🗑️ All monitoring settings removed"
            
        except Exception as e:
            self.logger.error(f"Error disabling monitoring for {site_id}: {e}")
            return f"❌ Error disabling monitoring: {str(e)}"
    
    async def _set_interval(self, site_id: str, interval: int) -> str:
        """Set monitoring interval for a site"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        try:
            site_config = self.sites[site_id]
            site_name = site_config.get('name', site_id)
            
            if not site_config.get('monitor', False):
                return f"❌ Monitoring is not enabled for {site_name}. Use `!loupe enable {site_id}` first."
            
            if interval < 60:
                return "❌ Interval must be at least 60 seconds"
            
            # Update interval
            old_interval = site_config.get('interval', 3600)
            site_config['interval'] = interval
            
            # Restart monitoring task with new interval
            if site_id in self.monitoring_tasks and not self.monitoring_tasks[site_id].done():
                self.monitoring_tasks[site_id].cancel()
            
            task = asyncio.create_task(self._monitor_site(site_id))
            self.monitoring_tasks[site_id] = task
            
            # Save configuration
            await self._save_config()
            
            return f"✅ **Interval updated for {site_name}**\n⏱️ Changed from {old_interval}s ({old_interval//60}m) to {interval}s ({interval//60}m)\n🔄 Monitoring task restarted"
            
        except ValueError:
            return "❌ Invalid interval value. Please provide a number in seconds."
        except Exception as e:
            self.logger.error(f"Error setting interval for {site_id}: {e}")
            return f"❌ Error setting interval: {str(e)}"
    
    async def _add_notification_target(self, site_id: str, target_name: str, target_type: str) -> str:
        """Add a notification target (group or user) to a site"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        try:
            site_config = self.sites[site_id]
            site_name = site_config.get('name', site_id)
            
            if not site_config.get('monitor', False):
                return f"❌ Monitoring is not enabled for {site_name}. Use `!loupe enable {site_id}` first."
            
            # Determine target list
            if target_type == "group":
                target_key = 'notify_groups'
                icon = "👥"
            else:
                target_key = 'notify_users'
                icon = "👤"
            
            # Initialize list if not exists
            if target_key not in site_config:
                site_config[target_key] = []
            
            # Check if already exists
            if target_name in site_config[target_key]:
                return f"⚠️ {icon} {target_name} is already in {site_name} notification list"
            
            # Add target
            site_config[target_key].append(target_name)
            
            # Save configuration
            await self._save_config()
            
            return f"✅ **Added {target_type} to {site_name}**\n{icon} {target_name} will receive notifications when content changes"
            
        except Exception as e:
            self.logger.error(f"Error adding {target_type} {target_name} to {site_id}: {e}")
            return f"❌ Error adding {target_type}: {str(e)}"
    
    async def _remove_notification_target(self, site_id: str, target_name: str, target_type: str) -> str:
        """Remove a notification target (group or user) from a site"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        try:
            site_config = self.sites[site_id]
            site_name = site_config.get('name', site_id)
            
            # Determine target list
            if target_type == "group":
                target_key = 'notify_groups'
                icon = "👥"
            else:
                target_key = 'notify_users'
                icon = "👤"
            
            # Check if target exists
            if target_key not in site_config or target_name not in site_config[target_key]:
                return f"⚠️ {icon} {target_name} is not in {site_name} notification list"
            
            # Remove target
            site_config[target_key].remove(target_name)
            
            # Save configuration
            await self._save_config()
            
            return f"✅ **Removed {target_type} from {site_name}**\n{icon} {target_name} will no longer receive notifications"
            
        except Exception as e:
            self.logger.error(f"Error removing {target_type} {target_name} from {site_id}: {e}")
            return f"❌ Error removing {target_type}: {str(e)}"
    
    async def _set_diff_mode(self, site_id: str, mode: str) -> str:
        """Set diff mode for a site (lines, full, disabled)"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        valid_modes = ['lines', 'full', 'disabled']
        if mode not in valid_modes:
            return f"❌ Invalid diff mode '{mode}'. Valid modes: {', '.join(valid_modes)}"
        
        try:
            site_config = self.sites[site_id]
            site_name = site_config.get('name', site_id)
            old_mode = site_config.get('diff_mode', 'lines')
            
            site_config['diff_mode'] = mode
            await self._save_config()
            
            # Clear previous content if switching from disabled to enabled
            if old_mode == 'disabled' and mode in ['lines', 'full']:
                content_file = self.data_dir / f"{site_id}_content.json"
                if content_file.exists():
                    content_file.unlink()
                hash_file = self.data_dir / f"{site_id}_hash.txt"
                if hash_file.exists():
                    hash_file.unlink()
                self.logger.info(f"Cleared stored content for {site_id} when enabling diff mode")
            
            return f"✅ **Diff mode set for {site_name}**\n📊 Mode: {mode}\n\n**Mode descriptions:**\n• `lines` - Show only changed lines\n• `full` - Show complete new content\n• `disabled` - No change notifications"
            
        except Exception as e:
            self.logger.error(f"Error setting diff mode for {site_id}: {e}")
            return f"❌ Error setting diff mode: {str(e)}"
    
    def _show_diff_config(self, site_id: str) -> str:
        """Show diff configuration for a site"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        site_config = self.sites[site_id]
        site_name = site_config.get('name', site_id)
        
        diff_mode = site_config.get('diff_mode', 'lines')
        max_diff_lines = site_config.get('max_diff_lines', 20)
        major_change_threshold = site_config.get('major_change_threshold', 0.5)
        ignore_patterns = site_config.get('ignore_patterns', [])
        
        config_text = f"""📊 **Diff Configuration for {site_name}**

**Current Settings:**
• Mode: `{diff_mode}`
• Max diff lines: {max_diff_lines}
• Major change threshold: {major_change_threshold:.1%}
• Ignore patterns: {len(ignore_patterns)} configured

**Mode Options:**
• `lines` - Show added/removed lines only
• `full` - Show complete new content on changes  
• `disabled` - No change notifications

**Advanced Settings:**
To configure advanced settings, edit the config.yml file:
```yaml
sites:
  {site_id}:
    diff_mode: "{diff_mode}"
    max_diff_lines: {max_diff_lines}
    major_change_threshold: {major_change_threshold}
    ignore_patterns: []
```

Use `!loupe diff-mode {site_id} <mode>` to change the diff mode."""
        
        return config_text
    
    # Site Management Methods
    async def _add_site(self, site_id: str, url: str, display_name: str, context) -> str:
        """Add a new site to the configuration"""
        if site_id in self.sites:
            return f"❌ Site '{site_id}' already exists. Use `!loupe edit-site` to modify it."
        
        try:
            # Validate URL format
            if not url.startswith(('http://', 'https://')):
                return "❌ URL must start with http:// or https://"
            
            # Determine notification targets based on context
            notify_users = []
            notify_groups = []
            
            # Add the user who ran the command
            if context.user_display_name:
                notify_users.append(context.user_display_name)
            
            # Check if this was run in a group chat
            is_group_chat = self._is_group_chat(context)
            if is_group_chat:
                group_name = self._get_group_name(context)
                if group_name:
                    notify_groups.append(group_name)
            
            # Create new site configuration
            new_site = {
                'url': url,
                'name': display_name,
                'description': f'Website monitoring for {display_name}',
                'monitor': False,  # Disabled by default
                'interval': 3600,  # Default 1 hour
                'notify_groups': notify_groups,
                'notify_users': notify_users,
                'selectors': {},
                'diff_mode': 'lines'  # Default diff mode
            }
            
            # Add to sites
            self.sites[site_id] = new_site
            
            # Save configuration
            await self._save_config()
            
            # Build response with notification targets info
            response = f"✅ **Added new site: {display_name}**\n🔗 URL: {url}\n📝 Site ID: `{site_id}`"
            response += f"\n📊 Monitoring: ❌ Disabled (use `!loupe enable {site_id}` to enable)"
            
            if notify_users or notify_groups:
                response += "\n🔔 **Auto-configured notifications:**"
                if notify_users:
                    response += f"\n  👤 Users: {', '.join(notify_users)}"
                if notify_groups:
                    response += f"\n  👥 Groups: {', '.join(notify_groups)}"
            
            response += f"\n\n💡 Use `!loupe add-selector {site_id}` to add CSS selectors"
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error adding site {site_id}: {e}")
            return f"❌ Error adding site: {str(e)}"
    
    def _is_group_chat(self, context) -> bool:
        """Check if the command was run in a group chat"""
        # For SimpleX, check if chat_id is different from user_id or has group indicators
        # This is a heuristic approach - you may need to adjust based on actual context structure
        if hasattr(context, 'raw_message') and context.raw_message:
            # Check if there's group information in the raw message
            chat_info = context.raw_message.get('chatInfo', {})
            if chat_info.get('chatType') == 'group':
                return True
            
            # Check for group member information
            chat_item = context.raw_message.get('chatItem', {})
            chat_dir = chat_item.get('chatDir', {})
            if 'groupMember' in chat_dir:
                return True
        
        # Fallback: if chat_id != user_id, it might be a group
        return context.chat_id != context.user_id
    
    def _get_group_name(self, context) -> str:
        """Get the group name from context"""
        if hasattr(context, 'raw_message') and context.raw_message:
            # Try to get group name from chat info
            chat_info = context.raw_message.get('chatInfo', {})
            group_profile = chat_info.get('groupProfile', {})
            if group_profile.get('displayName'):
                return group_profile['displayName']
            
            # Try local display name
            if chat_info.get('localDisplayName'):
                return chat_info['localDisplayName']
        
        # Fallback: use chat_id if it looks like a group name
        if context.chat_id != context.user_id:
            return context.chat_id
            
        return None
    
    async def _remove_site(self, site_id: str) -> str:
        """Remove a site completely from configuration"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        try:
            site_name = self.sites[site_id].get('name', site_id)
            
            # Stop monitoring if enabled
            if site_id in self.monitoring_tasks and not self.monitoring_tasks[site_id].done():
                self.monitoring_tasks[site_id].cancel()
                del self.monitoring_tasks[site_id]
            
            # Remove hash file
            hash_file = self.data_dir / f"{site_id}_hash.txt"
            if hash_file.exists():
                hash_file.unlink()
            
            # Remove from sites
            del self.sites[site_id]
            
            # Save configuration
            await self._save_config()
            
            return f"✅ **Removed site: {site_name}**\n🗑️ Site '{site_id}' and all associated data deleted"
            
        except Exception as e:
            self.logger.error(f"Error removing site {site_id}: {e}")
            return f"❌ Error removing site: {str(e)}"
    
    async def _edit_site(self, site_id: str, field: str, value: str) -> str:
        """Edit a site's configuration"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        try:
            site_config = self.sites[site_id]
            site_name = site_config.get('name', site_id)
            
            # Validate field
            valid_fields = ['url', 'name', 'description']
            if field not in valid_fields:
                return f"❌ Invalid field '{field}'. Valid fields: {', '.join(valid_fields)}"
            
            # Validate URL if changing URL
            if field == 'url' and not value.startswith(('http://', 'https://')):
                return "❌ URL must start with http:// or https://"
            
            # Store old value
            old_value = site_config.get(field, 'Not set')
            
            # Update field
            site_config[field] = value
            
            # Save configuration
            await self._save_config()
            
            return f"✅ **Updated {site_name}**\n📝 {field.title()}: `{old_value}` → `{value}`"
            
        except Exception as e:
            self.logger.error(f"Error editing site {site_id}: {e}")
            return f"❌ Error editing site: {str(e)}"
    
    # Selector Management Methods
    def _show_selectors(self, site_id: str) -> str:
        """Show all selectors for a site"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        site_config = self.sites[site_id]
        site_name = site_config.get('name', site_id)
        selectors = site_config.get('selectors', {})
        
        if not selectors:
            return f"🔍 **{site_name} Selectors**\n\n❌ No selectors configured.\n💡 Use `!loupe add-selector {site_id} <name> <css_selector>` to add selectors"
        
        result = f"🔍 **{site_name} Selectors**\n\n"
        for selector_name, css_selector in selectors.items():
            result += f"📌 **{selector_name}**\n"
            result += f"   CSS: `{css_selector}`\n\n"
        
        result += f"💡 Test selectors with `!loupe test-selector {site_id} <name>`"
        return result
    
    async def _add_selector(self, site_id: str, selector_name: str, css_selector: str) -> str:
        """Add a CSS selector to a site"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        try:
            site_config = self.sites[site_id]
            site_name = site_config.get('name', site_id)
            
            # Initialize selectors if not exists
            if 'selectors' not in site_config:
                site_config['selectors'] = {}
            
            # Check if selector name already exists
            if selector_name in site_config['selectors']:
                return f"⚠️ Selector '{selector_name}' already exists for {site_name}. Use `!loupe edit-selector` to modify it."
            
            # Add selector
            site_config['selectors'][selector_name] = css_selector
            
            # Save configuration
            await self._save_config()
            
            return f"✅ **Added selector to {site_name}**\n📌 **{selector_name}**: `{css_selector}`\n\n💡 Test it with `!loupe test-selector {site_id} {selector_name}`"
            
        except Exception as e:
            self.logger.error(f"Error adding selector to {site_id}: {e}")
            return f"❌ Error adding selector: {str(e)}"
    
    async def _edit_selector(self, site_id: str, selector_name: str, new_css_selector: str) -> str:
        """Edit an existing CSS selector"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        try:
            site_config = self.sites[site_id]
            site_name = site_config.get('name', site_id)
            selectors = site_config.get('selectors', {})
            
            if selector_name not in selectors:
                return f"❌ Selector '{selector_name}' not found for {site_name}. Use `!loupe selectors {site_id}` to see available selectors."
            
            # Store old selector
            old_selector = selectors[selector_name]
            
            # Update selector
            selectors[selector_name] = new_css_selector
            
            # Save configuration
            await self._save_config()
            
            return f"✅ **Updated selector for {site_name}**\n📌 **{selector_name}**:\n   Old: `{old_selector}`\n   New: `{new_css_selector}`\n\n💡 Test it with `!loupe test-selector {site_id} {selector_name}`"
            
        except Exception as e:
            self.logger.error(f"Error editing selector for {site_id}: {e}")
            return f"❌ Error editing selector: {str(e)}"
    
    async def _remove_selector(self, site_id: str, selector_name: str) -> str:
        """Remove a CSS selector from a site"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        try:
            site_config = self.sites[site_id]
            site_name = site_config.get('name', site_id)
            selectors = site_config.get('selectors', {})
            
            if selector_name not in selectors:
                return f"❌ Selector '{selector_name}' not found for {site_name}"
            
            # Store removed selector for confirmation
            removed_selector = selectors[selector_name]
            
            # Remove selector
            del selectors[selector_name]
            
            # Save configuration
            await self._save_config()
            
            return f"✅ **Removed selector from {site_name}**\n🗑️ **{selector_name}**: `{removed_selector}` has been deleted"
            
        except Exception as e:
            self.logger.error(f"Error removing selector from {site_id}: {e}")
            return f"❌ Error removing selector: {str(e)}"
    
    async def _test_selector(self, site_id: str, selector_name: str) -> str:
        """Test an existing CSS selector against the live site"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        try:
            site_config = self.sites[site_id]
            site_name = site_config.get('name', site_id)
            selectors = site_config.get('selectors', {})
            
            if selector_name not in selectors:
                return f"❌ Selector '{selector_name}' not found for {site_name}"
            
            css_selector = selectors[selector_name]
            return await self._try_selector(site_id, css_selector, selector_name)
            
        except Exception as e:
            self.logger.error(f"Error testing selector for {site_id}: {e}")
            return f"❌ Error testing selector: {str(e)}"
    
    async def _try_selector(self, site_id: str, css_selector: str, selector_name: str = None) -> str:
        """Test a CSS selector against a live site without saving"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        try:
            site_config = self.sites[site_id]
            site_name = site_config.get('name', site_id)
            url = site_config.get('url')
            
            if not url:
                return f"❌ No URL configured for {site_name}"
            
            self.logger.info(f"Testing selector '{css_selector}' on {site_name}")
            
            # Fetch the webpage with fallback handling
            html_content, method_used = await self._fetch_with_fallback(url, site_name)
            
            if method_used == "cloudscraper":
                self.logger.info(f"Successfully bypassed challenge for {site_name} using cloudscraper")
            
            # Parse HTML and test selector
            soup = BeautifulSoup(html_content, 'html.parser')
            elements = soup.select(css_selector)
            
            # Build result
            test_name = f"**{selector_name}**" if selector_name else "Test Selector"
            result = f"🧪 **Testing {test_name} on {site_name}**\n"
            result += f"🔍 CSS Selector: `{css_selector}`\n"
            if method_used == "cloudscraper":
                result += f"🛡️ Challenge bypassed using cloudscraper\n"
            result += "\n"
            
            if not elements:
                result += "❌ **No elements found**\n"
                result += "💡 Try adjusting the CSS selector or check if the page structure changed"
            else:
                result += f"✅ **Found {len(elements)} elements:**\n\n"
                
                # Show first few results
                for i, element in enumerate(elements[:5], 1):
                    text = self._element_to_text(element).strip()[:100]
                    if text:
                        result += f"{i}. {text}{'...' if len(text) == 100 else ''}\n"
                    else:
                        result += f"{i}. [Empty or no text content]\n"
                
                if len(elements) > 5:
                    result += f"\n... and {len(elements) - 5} more elements"
                
                if not selector_name:
                    result += f"\n\n💡 To save this selector: `!loupe add-selector {site_id} <name> {css_selector}`"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error trying selector on {site_id}: {e}")
            return f"❌ Error testing selector: {str(e)}"
    
    async def _fetch_with_fallback(self, url: str, site_name: str) -> tuple[str, str]:
        """Fetch webpage with aiohttp, fallback to cloudscraper for challenges
        Returns (html_content, method_used)
        """
        # Try aiohttp first
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                async with session.get(url, headers=headers, timeout=30) as response:
                    # Check for challenge/protection responses
                    if response.status in [200]:
                        html_content = await response.text()
                        return html_content, "aiohttp"
                    elif response.status in [203, 403, 503, 429]:  # Challenge responses
                        self.logger.warning(f"Challenge detected for {site_name}: HTTP {response.status}")
                        # Fall through to cloudscraper
                    else:
                        raise Exception(f"HTTP {response.status}")
        except asyncio.TimeoutError:
            raise Exception("Timeout with aiohttp")
        except Exception as e:
            if "Challenge detected" not in str(e):
                self.logger.warning(f"aiohttp failed for {site_name}: {e}")
        
        # Try enhanced requests-based fallback for challenge bypass
        try:
            self.logger.info(f"Attempting enhanced requests fallback for {site_name}")
            import requests
            
            # Enhanced session with better headers for challenge bypass
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            })
            
            # Multiple retry attempts with different strategies
            for attempt in range(3):
                try:
                    # Add some randomization to avoid detection patterns
                    import time
                    import random
                    time.sleep(random.uniform(1, 3))  # Random delay between attempts
                    
                    response = session.get(url, timeout=30, allow_redirects=True)
                    
                    # Check if we got a valid response
                    if response.status_code == 200:
                        # Verify content is not a challenge page
                        content = response.text.lower()
                        challenge_indicators = [
                            'checking your browser',
                            'cloudflare',
                            'ddos protection',
                            'security check',
                            'please wait',
                            'verification in progress'
                        ]
                        
                        if not any(indicator in content for indicator in challenge_indicators):
                            self.logger.info(f"Successfully bypassed challenge for {site_name} using enhanced requests")
                            return response.text, "enhanced_requests"
                        else:
                            self.logger.warning(f"Challenge page detected on attempt {attempt + 1} for {site_name}")
                    
                except requests.exceptions.RequestException as e:
                    self.logger.warning(f"Requests attempt {attempt + 1} failed for {site_name}: {e}")
                    if attempt == 2:  # Last attempt
                        raise
            
            # If we get here, all attempts failed
            raise Exception("All challenge bypass attempts failed")
            
        except Exception as e:
            self.logger.error(f"Enhanced requests fallback also failed for {site_name}: {e}")
            raise Exception(f"Both aiohttp and enhanced requests failed: {e}")

    async def _scrape_site(self, site_id: str) -> str:
        """Scrape a specific site"""
        error = self._validate_site_exists(site_id)
        if error:
            return error
        
        site_config = self.sites[site_id]
        url = site_config.get('url')
        name = site_config.get('name', site_id)
        selectors = site_config.get('selectors', {})
        
        if not url:
            return f"❌ No URL configured for site '{site_id}'"
        
        if not selectors:
            return f"❌ No selectors configured for site '{site_id}'"
        
        try:
            self.logger.info(f"Scraping {name} at {url}")
            
            # Fetch the webpage with fallback handling
            html_content, method_used = await self._fetch_with_fallback(url, name)
            
            if method_used == "cloudscraper":
                self.logger.info(f"Successfully bypassed challenge for {name} using cloudscraper")
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract content using selectors
            results = {}
            for selector_name, selector in selectors.items():
                elements = soup.select(selector)
                results[selector_name] = []
                
                for element in elements[:10]:  # Limit to first 10 elements
                    # Convert HTML to formatted text
                    if element.get_text().strip():
                        text = self._element_to_text(element)
                        if text:
                            results[selector_name].append(text)
            
            # Format output
            return self._format_results(name, url, results)
            
        except Exception as e:
            self.logger.error(f"Error scraping {name}: {e}")
            return f"❌ Failed to fetch {name}: {str(e)}"
    
    def _element_to_text(self, element) -> str:
        """Convert HTML element to formatted text"""
        try:
            # Get the HTML content
            html = str(element)
            
            # Convert to text using html2text
            text = self.html2text.handle(html).strip()
            
            # Clean up the text
            text = ' '.join(text.split())  # Normalize whitespace
            
            return text
        except Exception as e:
            self.logger.error(f"Error converting element to text: {e}")
            return element.get_text().strip()
    
    def _format_results(self, name: str, url: str, results: Dict[str, List[str]]) -> str:
        """Format scraping results for output"""
        if not any(results.values()):
            return f"🔍 **{name}**\n\nNo content found with configured selectors."
        
        output = f"🔍 **{name}**\n\n"
        
        # Show results for each selector
        for selector_name, items in results.items():
            if items:
                output += f"**{selector_name.replace('_', ' ').title()}:**\n"
                for i, item in enumerate(items, 1):
                    # Show full items without truncation
                    output += f"{i}. {item}\n"
                output += "\n"
        
        output += f"🔗 Source: {url}"
        return output
    
    
    def start_monitoring(self):
        """Start monitoring tasks for sites with monitoring enabled"""
        for site_id, site_config in self.sites.items():
            if site_config.get('monitor', False):
                interval = site_config.get('interval', 3600)  # Default 1 hour
                self.logger.info(f"Starting monitoring for {site_id} every {interval} seconds")
                task = asyncio.create_task(self._monitor_site(site_id))
                self.monitoring_tasks[site_id] = task
    
    async def _monitor_site(self, site_id: str):
        """Monitor a site for changes"""
        site_config = self.sites.get(site_id)
        if not site_config:
            return
        
        interval = site_config.get('interval', 3600)
        
        while True:
            try:
                # Get current content
                current_content = await self._scrape_site(site_id)
                if not current_content:
                    self.logger.warning(f"No content retrieved for {site_id}, skipping this check")
                    await asyncio.sleep(interval)
                    continue
                
                # Generate hash for quick change detection
                content_hash = hashlib.md5(current_content.encode()).hexdigest()
                
                # Check hash first for quick comparison
                last_hash_file = self.data_dir / f"{site_id}_hash.txt"
                last_hash = ""
                if last_hash_file.exists():
                    last_hash = last_hash_file.read_text().strip()
                
                if content_hash != last_hash:
                    # Content hash changed, analyze the diff
                    current_lines = self._clean_content_for_diff(current_content, site_config)
                    previous_lines = self._load_previous_content(site_id)
                    
                    # Save new content and hash
                    self._save_current_content(site_id, current_lines)
                    last_hash_file.write_text(content_hash)
                    
                    if previous_lines:  # Only notify on changes, not first run
                        # Generate diff
                        diff_mode = site_config.get('diff_mode', 'lines')
                        
                        if diff_mode == 'lines':
                            diff_messages = self._generate_content_diff(previous_lines, current_lines, site_config)
                            if diff_messages:
                                self.logger.info(f"Content changed for {site_id}, posting diff update ({len(diff_messages)} message(s))")
                                await self._notify_change_with_diff(site_id, diff_messages)
                            else:
                                # Hash changed but no meaningful line differences
                                self.logger.info(f"Content hash changed for {site_id} but no line differences detected")
                        elif diff_mode == 'full':
                            # Use old behavior - show full content
                            self.logger.info(f"Content changed for {site_id}, posting full update")
                            await self._notify_change(site_id, current_content)
                        else:  # diff_mode == 'disabled'
                            self.logger.info(f"Content changed for {site_id} but diff notifications disabled")
                    else:
                        self.logger.info(f"First monitoring run for {site_id}, storing baseline")
                
                # Wait for next check
                await asyncio.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Error monitoring {site_id}: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def _notify_change(self, site_id: str, content: str):
        """Notify about content changes"""
        site_config = self.sites.get(site_id, {})
        name = site_config.get('name', site_id)
        
        message = f"🔔 **{name} Updated**\n\n{content}"
        
        # Truncate if too long
        if len(message) > 4000:
            message = message[:4000] + "\n\n... (truncated)"
        
        # Store notification for later retrieval
        notifications_file = self.data_dir / "notifications.jsonl"
        notification = {
            "timestamp": datetime.now().isoformat(),
            "site_id": site_id,
            "site_name": name,
            "message": message
        }
        
        try:
            with open(notifications_file, 'a') as f:
                f.write(json.dumps(notification) + '\n')
            
            # Send notifications to configured targets
            await self._send_to_configured_targets(site_config, message)
            
            # Log the notification
            self.logger.info(f"🔔 Content changed for {name}: stored notification and sent to targets")
            self.logger.info(f"📝 Preview: {content[:200]}{'...' if len(content) > 200 else ''}")
            
        except Exception as e:
            self.logger.error(f"Error storing/sending notification: {e}")
    
    async def _notify_change_with_diff(self, site_id: str, diff_messages: List[str]):
        """Notify about content changes using diff format (potentially multiple messages)"""
        site_config = self.sites.get(site_id, {})
        name = site_config.get('name', site_id)
        
        # Process each message part
        for i, diff_content in enumerate(diff_messages):
            # Add header to first message, continuation marker to others
            if i == 0:
                message = f"🔔 **{name} Updated**\n\n{diff_content}"
            else:
                message = f"🔔 **{name} Updated (continued {i+1}/{len(diff_messages)})**\n\n{diff_content}"
            
            # Note: No truncation needed since we're already splitting messages
            
            # Store notification for later retrieval
            notifications_file = self.data_dir / "notifications.jsonl"
            notification = {
                "timestamp": datetime.now().isoformat(),
                "site_id": site_id,
                "site_name": name,
                "message": message,
                "type": "diff",
                "part": i + 1,
                "total_parts": len(diff_messages)
            }
            
            try:
                with open(notifications_file, 'a') as f:
                    f.write(json.dumps(notification) + '\n')
                
                # Send notifications to configured targets
                await self._send_to_configured_targets(site_config, message)
                
                # Small delay between messages to avoid spam
                if i < len(diff_messages) - 1:
                    await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error storing/sending diff notification part {i+1}: {e}")
        
        # Log the notification
        self.logger.info(f"🔔 Diff notification for {name}: {len(diff_messages)} message(s) stored and sent to targets")
    
    async def _send_to_configured_targets(self, site_config: Dict[str, Any], message: str):
        """Send notification to configured groups and users"""
        if not self.adapter or not hasattr(self.adapter, 'bot'):
            return
        
        notify_groups = site_config.get('notify_groups', [])
        notify_users = site_config.get('notify_users', [])
        
        # Send to groups
        for group_name in notify_groups:
            try:
                await self.adapter.bot.websocket_manager.send_message(group_name, message, is_group=True)
                self.logger.info(f"📤 Sent notification to group: {group_name}")
            except Exception as e:
                self.logger.error(f"❌ Failed to send to group '{group_name}': {e}")
        
        # Send to users
        for user_name in notify_users:
            try:
                await self.adapter.bot.websocket_manager.send_message(user_name, message, is_group=False)
                self.logger.info(f"📤 Sent notification to user: {user_name}")
            except Exception as e:
                self.logger.error(f"❌ Failed to send to user '{user_name}': {e}")
        
        # Log summary
        total_targets = len(notify_groups) + len(notify_users)
        if total_targets > 0:
            self.logger.info(f"🎯 Notification sent to {len(notify_groups)} groups and {len(notify_users)} users")
        else:
            self.logger.info("⚠️ No notification targets configured - notification stored only")
    
    def _clean_content_for_diff(self, content: str, site_config: Dict[str, Any]) -> List[str]:
        """Clean and normalize content for diff comparison"""
        import re
        
        if not content:
            return []
        
        # Split into lines and clean each line
        lines = content.strip().split('\n')
        cleaned_lines = []
        
        # Get ignore patterns from site config
        ignore_patterns = site_config.get('ignore_patterns', [])
        
        for line in lines:
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            
            # Apply ignore patterns
            skip_line = False
            for pattern in ignore_patterns:
                try:
                    if re.search(pattern, line):
                        skip_line = True
                        break
                except re.error:
                    # Invalid regex pattern, skip it
                    continue
            
            if not skip_line:
                cleaned_lines.append(line)
        
        return cleaned_lines
    
    def _generate_content_diff(self, old_lines: List[str], new_lines: List[str], 
                              site_config: Dict[str, Any]) -> Optional[str]:
        """Generate a human-readable diff between two sets of content lines"""
        if old_lines == new_lines:
            return None
        
        old_set = set(old_lines)
        new_set = set(new_lines)
        
        added_lines = [line for line in new_lines if line not in old_set]
        removed_lines = [line for line in old_lines if line not in new_set]
        
        # Check if this is a major change (configurable threshold)
        total_lines = len(old_lines) + len(new_lines)
        changed_lines = len(added_lines) + len(removed_lines)
        change_ratio = changed_lines / max(total_lines, 1)
        
        # Get configuration
        max_diff_lines = site_config.get('max_diff_lines', 20)
        major_change_threshold = site_config.get('major_change_threshold', 0.5)
        
        # If too many changes, provide summary with sample lines
        is_major_change = change_ratio > major_change_threshold
        
        # Determine how many lines to show
        # 0 = infinite, otherwise use the configured limit
        if max_diff_lines == 0:
            # Infinite - show all lines
            sample_lines = len(added_lines) + len(removed_lines)
        elif is_major_change:
            # Major changes: show fewer sample lines (5) unless infinite is set
            sample_lines = 5
        else:
            # Normal changes: use configured limit
            sample_lines = max_diff_lines
        
        # Instead of concatenating everything, we'll build message parts
        # that can be split if they get too long
        message_parts = []
        current_part = []
        
        # For major changes, add a summary header
        if is_major_change:
            current_part.append(f"📊 **Major Update Detected**")
            current_part.append(f"• {change_ratio:.1%} of content changed")
            current_part.append(f"• {len(added_lines)} items added, {len(removed_lines)} items removed")
            current_part.append("")
        
        # Helper function to check if we should start a new message
        def should_split_message(current_lines, max_lines_per_message=30):
            return len(current_lines) > max_lines_per_message
        
        # Show added content
        if added_lines:
            count = len(added_lines)
            
            # Determine how many added lines to show
            if max_diff_lines == 0:
                # Show all added lines
                display_lines = added_lines
                label = "Added"
            elif is_major_change and len(added_lines) > sample_lines:
                display_lines = added_lines[:sample_lines]  
                label = "Sample Added"
            else:
                display_lines = added_lines[:sample_lines]
                label = "Added"
            
            # Start added section
            current_part.append(f"➕ **{label} ({count})**:")
            
            for line in display_lines:
                current_part.append(f"• {line}")
                
                # Check if we should split the message
                if should_split_message(current_part):
                    message_parts.append('\n'.join(current_part))
                    current_part = ["➕ **Added (continued)**:"]
            
            # Add "more items" indicator if truncated
            if len(added_lines) > len(display_lines):
                remaining = len(added_lines) - len(display_lines)
                current_part.append(f"• ... and {remaining} more items")
        
        # Show removed content  
        if removed_lines:
            count = len(removed_lines)
            
            # Add spacing if we have content in current part
            if current_part:
                current_part.append("")
            
            # Determine how many removed lines to show
            if max_diff_lines == 0:
                # Show all removed lines
                display_lines = removed_lines
                label = "Removed"
            elif is_major_change and len(removed_lines) > sample_lines:
                display_lines = removed_lines[:sample_lines]
                label = "Sample Removed" 
            else:
                display_lines = removed_lines[:sample_lines]
                label = "Removed"
            
            current_part.append(f"➖ **{label} ({count})**:")
            
            for line in display_lines:
                current_part.append(f"• {line}")
                
                # Check if we should split the message
                if should_split_message(current_part):
                    message_parts.append('\n'.join(current_part))
                    current_part = ["➖ **Removed (continued)**:"]
            
            # Add "more items" indicator if truncated
            if len(removed_lines) > len(display_lines):
                remaining = len(removed_lines) - len(display_lines)
                current_part.append(f"• ... and {remaining} more items")
        
        # Add summary/footer
        if current_part:
            current_part.append("")
            if is_major_change:
                current_part.append("💡 **Tip**: Use `!loupe <site>` for complete current content")
            else:
                summary_parts = []
                if added_lines:
                    summary_parts.append(f"{len(added_lines)} added")
                if removed_lines:
                    summary_parts.append(f"{len(removed_lines)} removed")
                current_part.append(f"📊 **Summary**: {', '.join(summary_parts)}")
        
        # Add the final part
        if current_part:
            message_parts.append('\n'.join(current_part))
        
        # Return list of messages instead of single concatenated string
        return message_parts if message_parts else None
    
    def _load_previous_content(self, site_id: str) -> List[str]:
        """Load previous content lines from storage"""
        content_file = self.data_dir / f"{site_id}_content.json"
        
        if not content_file.exists():
            return []
        
        try:
            with open(content_file, 'r') as f:
                data = json.load(f)
                return data.get('lines', [])
        except (json.JSONDecodeError, OSError):
            return []
    
    def _save_current_content(self, site_id: str, content_lines: List[str]):
        """Save current content lines to storage"""
        content_file = self.data_dir / f"{site_id}_content.json"
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'lines': content_lines
        }
        
        try:
            with open(content_file, 'w') as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            self.logger.error(f"Failed to save content for {site_id}: {e}")
    
    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        # Cancel monitoring tasks
        for task in self.monitoring_tasks.values():
            if not task.done():
                task.cancel()
        self.monitoring_tasks.clear()
        self.logger.info("Loupe plugin cleanup completed")


# Export the plugin class
def create_plugin(logger=None):
    return LoupePlugin(logger=logger)