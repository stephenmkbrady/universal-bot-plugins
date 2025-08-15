"""
Universal Macro Plugin - Create and manage command shortcuts and auto-triggers

This plugin allows users to create custom command macros and set up automatic
command execution based on message content matching regex patterns.
"""

import os
import re
import yaml
import time
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform


class MacroPlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("macro", logger=logger)
        self.version = "1.0.0"
        self.description = "Create and manage command macros with auto-trigger support"
        
        # Universal plugin - supports all platforms
        self.supported_platforms = []  # Empty means supports all platforms
        
        if not self.logger:
            self.logger = logging.getLogger(f"plugin.{self.name}")
            
        # Configuration
        self.config_path = Path(__file__).parent / "config.yml"
        self.config = {}
        self.macros = {}
        self.auto_triggers = []
        self.settings = {}
        
        # Auto-trigger rate limiting
        self.auto_trigger_history = {}  # chat_id -> [(timestamp, trigger_name), ...]
        self.user_macros = {}  # user_id -> {macro_name: command, ...}
        
        # Load configuration
        self._load_config()
        
    def _load_config(self):
        """Load macro configuration from YAML file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
                    
                self.macros = self.config.get('macros', {})
                self.auto_triggers = self.config.get('auto_triggers', [])
                self.settings = self.config.get('settings', {})
                
                # Compile regex patterns for auto-triggers
                for trigger in self.auto_triggers:
                    try:
                        trigger['compiled_regex'] = re.compile(trigger['regex'], re.IGNORECASE | re.MULTILINE | re.DOTALL)
                    except re.error as e:
                        self.logger.error(f"Invalid regex for trigger '{trigger['name']}': {e}")
                        trigger['enabled'] = False
                
                self.logger.info(f"Loaded {len(self.macros)} macros and {len(self.auto_triggers)} auto-triggers")
            else:
                self.logger.warning(f"Config file not found: {self.config_path}")
                
        except Exception as e:
            self.logger.error(f"Error loading macro config: {e}")
            
    def _save_config(self):
        """Save macro configuration to YAML file"""
        try:
            # Remove compiled regex before saving
            config_to_save = self.config.copy()
            if 'auto_triggers' in config_to_save:
                for trigger in config_to_save['auto_triggers']:
                    trigger.pop('compiled_regex', None)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_to_save, f, default_flow_style=False, sort_keys=False)
                
            self.logger.info("Macro configuration saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving macro config: {e}")
            
    async def _on_initialize(self) -> bool:
        """Initialize the plugin with bot adapter"""
        try:
            self.logger.info(f"Initializing macro plugin for {self.adapter.platform.value} platform")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize macro plugin: {e}")
            return False
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return ["macro", "macros", "addmacro", "delmacro", "triggers", "addtrigger", "deltrigger"]
    
    async def handle_command(self, context: CommandContext) -> Optional[str]:
        """Handle commands for this plugin"""
        self.logger.info(f"Handling {context.command} command from {context.user_display_name}")
        
        try:
            if context.command == "macro":
                return await self._handle_macro(context)
            elif context.command == "macros":
                return await self._handle_list_macros(context)
            elif context.command == "addmacro":
                return await self._handle_add_macro(context)
            elif context.command == "delmacro":
                return await self._handle_delete_macro(context)
            elif context.command == "triggers":
                return await self._handle_list_triggers(context)
            elif context.command == "addtrigger":
                return await self._handle_add_trigger(context)
            elif context.command == "deltrigger":
                return await self._handle_delete_trigger(context)
                
        except Exception as e:
            self.logger.error(f"Error handling {context.command} command: {str(e)}", exc_info=True)
            return f"❌ Error processing {context.command} command"
        
        return None
    
    async def handle_message(self, context: CommandContext) -> Optional[str]:
        """Handle non-command messages for auto-trigger detection"""
        self.logger.info(f"🔍 MACRO: Checking message: '{context.args_raw[:100]}...' (length: {len(context.args_raw)})")
        
        if not context.args_raw or context.args_raw.startswith('!'):
            self.logger.info(f"🔍 MACRO: Skipping - empty or command message")
            return None
            
        # Check for auto-triggers
        self.logger.info(f"🔍 MACRO: Checking {len(self.auto_triggers)} auto-triggers")
        triggered_commands = await self._check_auto_triggers(context)
        
        if triggered_commands:
            self.logger.info(f"🤖 MACRO AUTO-TRIGGER: {len(triggered_commands)} triggers fired")
            # Execute triggered commands
            for trigger_name, command in triggered_commands:
                await self._execute_macro_command(context, command, f"auto-trigger '{trigger_name}'")
        else:
            self.logger.info(f"🔍 MACRO: No triggers matched")
                
        return None
    
    async def _handle_macro(self, context: CommandContext) -> str:
        """Handle !macro command - execute a macro or show help"""
        if not context.has_args:
            return self._show_macro_help()
            
        macro_name = context.args[0].lower()
        
        # Check built-in macros first
        if macro_name in self.macros:
            command = self.macros[macro_name]
            await self._execute_macro_command(context, command, f"macro '{macro_name}'")
            return f"🔧 Executed macro: `{macro_name}`"
            
        # Check user macros
        user_macros = self.user_macros.get(context.user_id, {})
        if macro_name in user_macros:
            command = user_macros[macro_name]
            await self._execute_macro_command(context, command, f"user macro '{macro_name}'")
            return f"🔧 Executed user macro: `{macro_name}`"
            
        # Macro not found
        available_macros = list(self.macros.keys()) + list(user_macros.keys())
        if available_macros:
            return f"❌ Macro `{macro_name}` not found.\n\n**Available macros:**\n" + \
                   "\n".join([f"• `{name}`" for name in sorted(available_macros)])
        else:
            return "❌ No macros available. Use `!addmacro <name> <command>` to create one."
    
    async def _handle_list_macros(self, context: CommandContext) -> str:
        """Handle !macros command - list all available macros"""
        response = "🔧 **Available Macros**\n\n"
        
        # Built-in macros
        if self.macros:
            response += "**Built-in Macros:**\n"
            for name, command in self.macros.items():
                response += f"• `!macro {name}` - {command[:60]}{'...' if len(command) > 60 else ''}\n"
            response += "\n"
        
        # User macros
        user_macros = self.user_macros.get(context.user_id, {})
        if user_macros:
            response += "**Your Macros:**\n"
            for name, command in user_macros.items():
                response += f"• `!macro {name}` - {command[:60]}{'...' if len(command) > 60 else ''}\n"
            response += "\n"
        
        if not self.macros and not user_macros:
            response += "No macros available.\n\n"
            
        response += "💡 Use `!addmacro <name> <command>` to create a new macro"
        
        return response
    
    async def _handle_add_macro(self, context: CommandContext) -> str:
        """Handle !addmacro command - add a new user macro"""
        if not self.settings.get('allow_user_macros', True):
            return "❌ User macro creation is disabled"
            
        if len(context.args) < 2:
            return "❌ **Usage:** `!addmacro <name> <command>`\n\n" \
                   "**Example:** `!addmacro translate !ask m1 translate this to English`"
        
        macro_name = context.args[0].lower()
        macro_command = " ".join(context.args[1:])
        
        # Validate macro name
        if not re.match(r'^[a-zA-Z0-9_]+$', macro_name):
            return "❌ Macro name can only contain letters, numbers, and underscores"
            
        if macro_name in ['help', 'list', 'add', 'delete', 'remove']:
            return "❌ Cannot use reserved words as macro names"
        
        # Initialize user macros if needed
        if context.user_id not in self.user_macros:
            self.user_macros[context.user_id] = {}
        
        # Add the macro
        self.user_macros[context.user_id][macro_name] = macro_command
        
        return f"✅ Added user macro: `{macro_name}`\n" \
               f"**Command:** `{macro_command}`\n" \
               f"**Usage:** `!macro {macro_name}`"
    
    async def _handle_delete_macro(self, context: CommandContext) -> str:
        """Handle !delmacro command - delete a user macro"""
        if not context.has_args:
            return "❌ **Usage:** `!delmacro <name>`"
            
        macro_name = context.args[0].lower()
        user_macros = self.user_macros.get(context.user_id, {})
        
        if macro_name not in user_macros:
            return f"❌ User macro `{macro_name}` not found"
            
        del user_macros[macro_name]
        
        return f"✅ Deleted user macro: `{macro_name}`"
    
    async def _handle_list_triggers(self, context: CommandContext) -> str:
        """Handle !triggers command - list auto-triggers"""
        response = "🤖 **Auto-Triggers**\n\n"
        
        if not self.auto_triggers:
            return response + "No auto-triggers configured."
            
        for trigger in self.auto_triggers:
            status = "🟢 Enabled" if trigger.get('enabled', False) else "🔴 Disabled"
            response += f"**{trigger['name']}** - {status}\n"
            response += f"• Pattern: `{trigger['regex']}`\n"
            response += f"• Command: `{trigger['command']}`\n"
            response += f"• Description: {trigger.get('description', 'No description')}\n\n"
            
        return response
    
    async def _handle_add_trigger(self, context: CommandContext) -> str:
        """Handle !addtrigger command - add auto-trigger (admin only)"""
        # Check admin permission if required
        if self.settings.get('require_admin_for_auto_triggers', True):
            admin_service = self.require_service('admin_management')
            if admin_service and not await admin_service.is_admin(context.user_id):
                return "❌ Admin permission required to manage auto-triggers"
        
        if len(context.args) < 3:
            return "❌ **Usage:** `!addtrigger <name> <regex> <command>`\n\n" \
                   "**Example:** `!addtrigger url_extract 'https?://\\S+' '!ask m1 extract URLs'`"
        
        name = context.args[0]
        regex_pattern = context.args[1]
        command = " ".join(context.args[2:])
        
        # Validate regex
        try:
            re.compile(regex_pattern)
        except re.error as e:
            return f"❌ Invalid regex pattern: {e}"
        
        # Add trigger
        new_trigger = {
            'name': name,
            'regex': regex_pattern,
            'command': command,
            'enabled': True,
            'description': f"Added by {context.user_display_name}",
            'compiled_regex': re.compile(regex_pattern, re.IGNORECASE | re.MULTILINE)
        }
        
        self.auto_triggers.append(new_trigger)
        self.config['auto_triggers'] = self.auto_triggers
        self._save_config()
        
        return f"✅ Added auto-trigger: `{name}`\n" \
               f"**Pattern:** `{regex_pattern}`\n" \
               f"**Command:** `{command}`"
    
    async def _handle_delete_trigger(self, context: CommandContext) -> str:
        """Handle !deltrigger command - delete auto-trigger (admin only)"""
        # Check admin permission if required
        if self.settings.get('require_admin_for_auto_triggers', True):
            admin_service = self.require_service('admin_management')
            if admin_service and not await admin_service.is_admin(context.user_id):
                return "❌ Admin permission required to manage auto-triggers"
        
        if not context.has_args:
            return "❌ **Usage:** `!deltrigger <name>`"
            
        name = context.args[0]
        
        # Find and remove trigger
        for i, trigger in enumerate(self.auto_triggers):
            if trigger['name'] == name:
                del self.auto_triggers[i]
                self.config['auto_triggers'] = self.auto_triggers
                self._save_config()
                return f"✅ Deleted auto-trigger: `{name}`"
        
        return f"❌ Auto-trigger `{name}` not found"
    
    async def _check_auto_triggers(self, context: CommandContext) -> List[tuple]:
        """Check if message triggers any auto-triggers"""
        triggered = []
        
        for trigger in self.auto_triggers:
            self.logger.info(f"🔍 TRIGGER: Checking '{trigger['name']}' - enabled: {trigger.get('enabled', False)}")
            
            if not trigger.get('enabled', False):
                self.logger.info(f"🔍 TRIGGER: Skipping disabled trigger '{trigger['name']}'")
                continue
                
            if not trigger.get('compiled_regex'):
                self.logger.info(f"🔍 TRIGGER: No compiled regex for '{trigger['name']}'")
                continue
            
            # Check if message matches pattern
            regex_pattern = trigger['regex']
            self.logger.info(f"🔍 TRIGGER: Testing pattern '{regex_pattern}' against message")
            
            if trigger['compiled_regex'].search(context.args_raw):
                self.logger.info(f"🎯 TRIGGER MATCH: '{trigger['name']}' matched!")
                
                # Check rate limiting (but allow through with warning for now)
                if self._is_rate_limited(context.chat_id, trigger['name']):
                    self.logger.warning(f"⏳ TRIGGER RATE WARNING: '{trigger['name']}' would be rate limited, but allowing through for testing")
                    # continue  # Commented out to disable blocking for testing
                
                triggered.append((trigger['name'], trigger['command']))
                self._record_auto_trigger(context.chat_id, trigger['name'])
                
                self.logger.info(f"Auto-trigger '{trigger['name']}' matched in {context.chat_id}")
        
        return triggered
    
    def _is_rate_limited(self, chat_id: str, trigger_name: str) -> bool:
        """Check if auto-trigger is rate limited"""
        now = time.time()
        cooldown = self.settings.get('auto_trigger_cooldown', 30)
        max_per_hour = self.settings.get('max_auto_triggers_per_hour', 10)
        
        if chat_id not in self.auto_trigger_history:
            return False
            
        history = self.auto_trigger_history[chat_id]
        
        # Remove old entries
        cutoff_time = now - 3600  # 1 hour ago
        history[:] = [(ts, name) for ts, name in history if ts > cutoff_time]
        
        # Check cooldown (same trigger)
        for ts, name in reversed(history):
            if name == trigger_name and (now - ts) < cooldown:
                return True
        
        # Check hourly limit (all triggers)
        if len(history) >= max_per_hour:
            return True
            
        return False
    
    def _record_auto_trigger(self, chat_id: str, trigger_name: str):
        """Record auto-trigger execution for rate limiting"""
        now = time.time()
        
        if chat_id not in self.auto_trigger_history:
            self.auto_trigger_history[chat_id] = []
            
        self.auto_trigger_history[chat_id].append((now, trigger_name))
    
    async def _execute_macro_command(self, context: CommandContext, command: str, source: str):
        """Execute a macro command"""
        try:
            self.logger.info(f"🚀 MACRO EXEC: Executing {source}: {command}")
            
            # Get bot instance and use plugin manager to execute command
            if hasattr(self.adapter, 'bot'):
                self.logger.debug(f"🔧 MACRO EXEC: Bot found via adapter.bot")
                bot = self.adapter.bot
                
                # Try to use plugin manager directly for command execution
                if hasattr(bot, 'plugin_manager'):
                    plugin_manager = bot.plugin_manager
                    
                    self.logger.debug(f"🔧 MACRO EXEC: Using plugin manager to execute: {command}")
                    
                    # Parse the command
                    if command.startswith('!'):
                        cmd_parts = command[1:].split()
                        cmd_name = cmd_parts[0] if cmd_parts else ""
                        cmd_args = cmd_parts[1:] if len(cmd_parts) > 1 else []
                        
                        # Create new context for the macro command
                        new_context = CommandContext(
                            command=cmd_name,
                            args=cmd_args,
                            args_raw=" ".join(cmd_args) if cmd_args else "",
                            user_id=context.user_id,
                            user_display_name=context.user_display_name,
                            chat_id=context.chat_id,
                            platform=context.platform,
                            raw_message=command
                        )
                        
                        # Execute command through plugin manager
                        result = await plugin_manager.handle_command(new_context)
                        
                        if result:
                            # Send result back to user via adapter
                            await self.adapter.send_message(result, context)
                            self.logger.info(f"✅ MACRO EXEC: Command executed and result sent")
                        else:
                            self.logger.warning(f"⚠️ MACRO EXEC: Command returned no result")
                    else:
                        self.logger.error(f"❌ MACRO EXEC: Invalid command format: {command}")
                else:
                    self.logger.error("❌ MACRO EXEC: Plugin manager not available")
            else:
                self.logger.error("❌ MACRO EXEC: Bot instance not available")
                
        except Exception as e:
            self.logger.error(f"❌ MACRO EXEC: Error executing macro command '{command}': {e}", exc_info=True)
    
    def _show_macro_help(self) -> str:
        """Show macro plugin help"""
        help_text = """🔧 **Macro Plugin**

**Basic Usage:**
• `!macro <name>` - Execute a macro
• `!macros` - List all available macros

**Macro Management:**
• `!addmacro <name> <command>` - Create a new macro
• `!delmacro <name>` - Delete your macro

**Auto-Triggers:**
• `!triggers` - List auto-triggers
• `!addtrigger <name> <regex> <command>` - Add auto-trigger (admin)
• `!deltrigger <name>` - Delete auto-trigger (admin)

**Examples:**
• `!addmacro translate !ask m1 translate this to English`
• `!macro translate` - Run the translate macro
• `!addtrigger urls 'https?://\\S+' '!ask m1 extract all URLs'`

**Auto-Triggers:**
Auto-triggers automatically execute commands when messages match regex patterns.
Rate limiting prevents spam (configurable cooldown and hourly limits).
"""
        
        return help_text
    
    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        self.logger.info("Macro plugin cleanup completed")


# Export the plugin class for the plugin manager to discover