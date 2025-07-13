"""
Universal Home Assistant Plugin

This plugin provides Home Assistant integration for any bot platform,
allowing users to control and monitor their Home Assistant instance via chat commands.

Features:
- Turn lights/switches on/off
- Get entity states  
- Control climate devices
- Run automations
- Get sensor readings
- Control media players, locks, covers, etc.

Commands:
- !ha status - Get Home Assistant status
- !ha lights - List all lights
- !ha light <name> on/off - Control specific light
- !ha switches - List all switches  
- !ha switch <name> on/off - Control specific switch
- !ha sensors - List sensor readings
- !ha climate - List climate devices
- !ha climate <name> <temperature> - Set temperature
- !ha automation <name> - Run automation
- !ha entities - List all entities
- !ha todos - List all todo lists
- !ha todo <list> - Show items in a specific todo list
- !ha todo <list> add <item> - Add item to todo list
- !ha todo <list> done <item> - Mark item as complete
- !ha todo <list> undo <item> - Mark completed item as todo
- !ha connections - Show Ping(ICMP) sensor status
- !ha wake - List Wake on LAN buttons
- !ha wake list - List Wake on LAN buttons
- !ha wake <button> - Send Wake on LAN signal
"""

from typing import List, Optional, Dict, Any
import logging
import asyncio
import yaml
import os
import re
from pathlib import Path
from homeassistant_api import Client as HomeAssistantClient

from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform


class UniversalHomeAssistantPlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("homeassistant", logger=logger)
        self.version = "1.0.0"
        self.description = "Home Assistant integration for controlling smart home devices"
        
        # Plugin settings
        self.enabled = True
        self.supported_platforms = [BotPlatform.SIMPLEX, BotPlatform.MATRIX]
        
        if not self.logger:
            self.logger = logging.getLogger(f"plugin.{self.name}")
        
        # Home Assistant connection
        self.ha_client = None
        self.config = {}
        
        # Load configuration
        self._load_config()
    
    def _load_config(self):
        """Load plugin configuration from config.yaml with environment variable substitution"""
        try:
            config_path = Path(__file__).parent / "config.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    content = f.read()
                    # Simple environment variable substitution
                    content = self._substitute_env_vars(content)
                    full_config = yaml.safe_load(content)
                    self.config = full_config.get('homeassistant', {})
                    self.logger.info(f"Loaded Home Assistant config from {config_path}")
            else:
                self.logger.warning(f"Config file not found: {config_path}")
                self.config = {}
        except Exception as e:
            self.logger.error(f"Failed to load Home Assistant config: {e}")
            self.config = {}
    
    def _substitute_env_vars(self, content: str) -> str:
        """Substitute environment variables in config content"""
        # Pattern: ${VAR_NAME:default_value} or ${VAR_NAME}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            return os.getenv(var_name, default_value)
        
        return re.sub(pattern, replace_var, content)
    
    def _extract_aliases_from_name(self, name: str) -> List[str]:
        """Extract potential aliases from entity names (lights, switches, wake buttons, etc.)"""
        if not name:
            return []
        
        # Common words to filter out
        stop_words = {
            'light', 'lamp', 'bulb', 'switch', 'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for',
            'wake', 'wol', 'lan', 'button', 'sensor', 'ping', 'icmp', 'binary', 'todo', 'list'
        }
        
        # Split name into words and clean them
        words = []
        for word in name.lower().split():
            # Remove common punctuation
            word = word.strip('()[]{}.,!?":;')
            # Skip empty words, numbers, and stop words
            if word and not word.isdigit() and word not in stop_words:
                # Filter out words with special characters (umlauts, etc.)
                if word.isascii() and word.isalpha():
                    words.append(word)
        
        return words
    
    def _find_entities_by_alias(self, entities, search_term: str):
        """Find all entities (lights/switches/etc) matching an alias or search term"""
        search_term = search_term.lower().strip()
        matching_entities = []
        
        # First pass: exact alias match
        for entity in entities:
            entity_id = entity.entity_id.lower()
            friendly_name = entity.attributes.get('friendly_name', '')
            
            # Check entity ID parts (e.g., "light.office_desk_lamp" -> ["office", "desk", "lamp"])
            entity_parts = entity_id.split('.')[1].replace('_', ' ').split() if '.' in entity_id else []
            
            # Check friendly name aliases
            name_aliases = self._extract_aliases_from_name(friendly_name)
            
            # Combine all possible aliases
            all_aliases = entity_parts + name_aliases
            
            # Exact match on any alias
            if search_term in all_aliases:
                matching_entities.append(entity)
        
        # If no exact alias matches, try partial match in friendly name or entity ID
        if not matching_entities:
            for entity in entities:
                entity_id = entity.entity_id.lower()
                friendly_name = entity.attributes.get('friendly_name', '').lower()
                
                if (search_term in entity_id or search_term in friendly_name):
                    matching_entities.append(entity)
        
        return matching_entities
    
    async def initialize(self, adapter) -> bool:
        """Initialize plugin with bot adapter"""
        try:
            if not await super().initialize(adapter):
                return False
            
            self.logger.info(f"Initializing Home Assistant plugin for {adapter.platform.value}")
            
            # Initialize Home Assistant client
            if not await self._initialize_ha_client():
                self.logger.error("Failed to initialize Home Assistant client")
                return False
            
            self.logger.info("Home Assistant plugin initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Home Assistant plugin: {e}")
            return False
    
    async def _initialize_ha_client(self) -> bool:
        """Initialize Home Assistant API client"""
        try:
            host = self.config.get('host', 'localhost')
            port = int(self.config.get('port', 8123))
            token = self.config.get('token', '')
            ssl_config = self.config.get('ssl', False)
            # Convert string 'false'/'true' to boolean
            if isinstance(ssl_config, str):
                ssl = ssl_config.lower() in ('true', '1', 'yes', 'on')
            else:
                ssl = bool(ssl_config)
            
            if not token:
                self.logger.error("Home Assistant token not configured")
                return False
            
            # Build URL - HomeAssistant API client expects the full API URL
            protocol = 'https' if ssl else 'http'
            url = f"{protocol}://{host}:{port}/api"
            
            # Configure caching based on user preference
            cache_enabled = self.config.get('enable_cache', False)
            # Convert string 'false'/'true' to boolean if needed
            if isinstance(cache_enabled, str):
                cache_enabled = cache_enabled.lower() in ('true', '1', 'yes', 'on')
            else:
                cache_enabled = bool(cache_enabled)
            
            self.logger.info(f"Home Assistant API caching: {'enabled' if cache_enabled else 'disabled'}")
            
            # Initialize client with configurable caching
            # When enabled: Better performance, 30-second cache, less bandwidth
            # When disabled: Real-time updates, new/deleted entities appear immediately
            self.ha_client = HomeAssistantClient(
                url, 
                token, 
                cache_session=cache_enabled  # Use configured caching preference
            )
            
            # Test connection
            try:
                states = await self._async_get_states()
                self.logger.info(f"Connected to Home Assistant: {len(states)} entities found")
                return True
            except Exception as e:
                self.logger.error(f"Failed to connect to Home Assistant: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Home Assistant client: {e}")
            return False
    
    async def _async_get_states(self):
        """Get all states from Home Assistant (async wrapper)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.ha_client.get_states)
    
    async def _async_get_state(self, entity_id):
        """Get state of specific entity (async wrapper)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.ha_client.get_state, entity_id)
    
    async def _async_call_service(self, domain, service, entity_id=None, **kwargs):
        """Call Home Assistant service (async wrapper)"""
        loop = asyncio.get_event_loop()
        service_data = kwargs.copy()
        if entity_id:
            service_data['entity_id'] = entity_id
        
        # Call trigger_service with keyword arguments
        return await loop.run_in_executor(None, 
                                          lambda: self.ha_client.trigger_service(domain, service, **service_data))
    
    async def _async_call_service_with_response(self, domain, service, entity_id=None, **kwargs):
        """Call Home Assistant service and get response (async wrapper)"""
        loop = asyncio.get_event_loop()
        service_data = kwargs.copy()
        if entity_id:
            service_data['entity_id'] = entity_id
        
        # Call trigger_service_with_response with keyword arguments
        return await loop.run_in_executor(None, 
                                          lambda: self.ha_client.trigger_service_with_response(domain, service, **service_data))
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return [
            "ha", "homeassistant",
            "lights", "switches", "sensors", "climate", 
            "automation", "entities"
        ]
    
    async def handle_command(self, context: CommandContext) -> Optional[str]:
        """Handle incoming commands"""
        try:
            if not self.ha_client:
                return "❌ Home Assistant not connected"
            
            cmd = context.command.lower()
            
            # Main HA command dispatcher
            if cmd in ["ha", "homeassistant"]:
                return await self._handle_ha_command(context)
            
            # Direct entity commands
            elif cmd == "lights":
                return await self._handle_lights_command(context)
            elif cmd == "switches":
                return await self._handle_switches_command(context)
            elif cmd == "sensors":
                return await self._handle_sensors_command(context)
            elif cmd == "climate":
                return await self._handle_climate_command(context)
            elif cmd == "automation":
                return await self._handle_automation_command(context)
            elif cmd == "entities":
                return await self._handle_entities_command(context)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error handling Home Assistant command: {e}")
            return f"❌ Error: {str(e)}"
    
    async def _handle_ha_command(self, context: CommandContext) -> str:
        """Handle main !ha command with subcommands"""
        if not context.has_args:
            return self._get_help_text()
        
        subcmd = context.get_arg(0).lower()
        
        if subcmd == "status":
            return await self._get_status()
        elif subcmd == "help":
            return self._get_help_text()
        elif subcmd in ["lights", "light"]:
            return await self._handle_lights_subcommand(context)
        elif subcmd in ["switches", "switch"]:
            return await self._handle_switches_subcommand(context)
        elif subcmd == "sensors":
            return await self._handle_sensors_command(context)
        elif subcmd == "climate":
            return await self._handle_climate_subcommand(context)
        elif subcmd == "automation":
            return await self._handle_automation_subcommand(context)
        elif subcmd == "entities":
            return await self._handle_entities_command(context)
        elif subcmd in ["todos", "todo"]:
            return await self._handle_todo_subcommand(context)
        elif subcmd == "connections":
            return await self._handle_connections_command(context)
        elif subcmd == "wake":
            return await self._handle_wake_command(context)
        else:
            return f"❌ Unknown subcommand: {subcmd}\n\n{self._get_help_text()}"
    
    async def _get_status(self) -> str:
        """Get Home Assistant status"""
        try:
            states = await self._async_get_states()
            
            # Count entities by domain
            domains = {}
            for state in states:
                domain = state.entity_id.split('.')[0]
                domains[domain] = domains.get(domain, 0) + 1
            
            # Sort by count
            sorted_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)
            
            status_text = "🏠 **Home Assistant Status**\n\n"
            status_text += f"**Total Entities:** {len(states)}\n\n"
            status_text += "**Entity Breakdown:**\n"
            
            for domain, count in sorted_domains[:10]:  # Top 10 domains
                status_text += f"• {domain}: {count}\n"
            
            if len(sorted_domains) > 10:
                status_text += f"• ... and {len(sorted_domains) - 10} more domains\n"
            
            return status_text
            
        except Exception as e:
            return f"❌ Failed to get status: {str(e)}"
    
    async def _handle_lights_command(self, context: CommandContext) -> str:
        """Handle lights command"""
        return await self._handle_lights_subcommand(context)
    
    async def _handle_lights_subcommand(self, context: CommandContext) -> str:
        """Handle lights subcommand"""
        try:
            states = await self._async_get_states()
            lights = [s for s in states if s.entity_id.startswith('light.')]
            
            if len(context.args) <= 1 or (len(context.args) == 2 and context.get_arg(1).lower() == "all"):  # List lights
                if not lights:
                    return "💡 No lights found"
                
                # Check if user wants to see all lights
                show_all = len(context.args) == 2 and context.get_arg(1).lower() == "all"
                max_to_show = len(lights) if show_all else self.config.get('max_entities_per_response', 50)
                
                response = "💡 **Lights:**\n\n"
                for light in lights[:max_to_show]:
                    entity_id = light.entity_id
                    name = light.attributes.get('friendly_name', entity_id)
                    state = light.state
                    icon = "🟡" if state == "on" else "⚫"
                    
                    # Show available aliases
                    aliases = self._extract_aliases_from_name(name)
                    if aliases:
                        alias_text = f" [{', '.join(aliases[:3])}]"  # Show first 3 aliases
                    else:
                        alias_text = ""
                    
                    response += f"{icon} {name} ({state}){alias_text}\n"
                
                if not show_all and len(lights) > max_to_show:
                    remaining = len(lights) - max_to_show
                    response += f"\n... and {remaining} more lights\n"
                    response += f"**Use `!ha lights all` to see all {len(lights)} lights**\n"
                
                response += "\n**Usage:** `!ha light <name|alias> on/off`\n**Tip:** Use aliases in brackets for easier control"
                return response
            
            # Control specific light
            light_name = context.get_arg(1).lower()
            action = context.get_arg(2, "").lower()
            
            
            if not action:
                return "❌ Please specify 'on' or 'off'"
            
            if action not in ["on", "off"]:
                return "❌ Action must be 'on' or 'off'"
            
            # Find matching lights using auto-generated aliases
            matching_lights = self._find_entities_by_alias(lights, light_name)
            
            if not matching_lights:
                return f"❌ Light '{light_name}' not found"
            
            # Control all matching lights
            service = "turn_on" if action == "on" else "turn_off"
            icon = "🟡" if action == "on" else "⚫"
            
            controlled_lights = []
            errors = []
            
            for light in matching_lights:
                try:
                    await self._async_call_service("light", service, light.entity_id)
                    name = light.attributes.get('friendly_name', light.entity_id)
                    controlled_lights.append(name)
                except Exception as e:
                    name = light.attributes.get('friendly_name', light.entity_id)
                    errors.append(f"{name}: {str(e)}")
            
            # Build response
            if controlled_lights:
                if len(controlled_lights) == 1:
                    return f"{icon} {controlled_lights[0]} turned {action}"
                else:
                    lights_list = '\n'.join([f"{icon} {name}" for name in controlled_lights])
                    response = f"Turned {action} {len(controlled_lights)} lights:\n{lights_list}"
                    if errors:
                        response += f"\n\n❌ Errors:\n" + '\n'.join(errors)
                    return response
            else:
                return f"❌ Failed to control lights:\n" + '\n'.join(errors)
            
        except Exception as e:
            return f"❌ Error controlling lights: {str(e)}"
    
    async def _handle_switches_command(self, context: CommandContext) -> str:
        """Handle switches command"""
        return await self._handle_switches_subcommand(context)
    
    async def _handle_switches_subcommand(self, context: CommandContext) -> str:
        """Handle switches subcommand"""
        try:
            states = await self._async_get_states()
            switches = [s for s in states if s.entity_id.startswith('switch.')]
            
            if len(context.args) <= 1 or (len(context.args) == 2 and context.get_arg(1).lower() == "all"):  # List switches
                if not switches:
                    return "🔌 No switches found"
                
                # Check if user wants to see all switches
                show_all = len(context.args) == 2 and context.get_arg(1).lower() == "all"
                max_to_show = len(switches) if show_all else self.config.get('max_entities_per_response', 50)
                
                response = "🔌 **Switches:**\n\n"
                for switch in switches[:max_to_show]:
                    entity_id = switch.entity_id
                    name = switch.attributes.get('friendly_name', entity_id)
                    state = switch.state
                    icon = "🟢" if state == "on" else "🔴"
                    
                    # Show available aliases
                    aliases = self._extract_aliases_from_name(name)
                    if aliases:
                        alias_text = f" [{', '.join(aliases[:3])}]"  # Show first 3 aliases
                    else:
                        alias_text = ""
                    
                    response += f"{icon} {name} ({state}){alias_text}\n"
                
                if not show_all and len(switches) > max_to_show:
                    remaining = len(switches) - max_to_show
                    response += f"\n... and {remaining} more switches\n"
                    response += f"**Use `!ha switches all` to see all {len(switches)} switches**\n"
                
                response += "\n**Usage:** `!ha switch <name|alias> on/off`\n**Tip:** Use aliases in brackets for easier control"
                return response
            
            # Control specific switch using alias system
            switch_name = context.get_arg(1).lower()
            action = context.get_arg(2, "").lower()
            
            if not action:
                return "❌ Please specify 'on' or 'off'"
            
            if action not in ["on", "off"]:
                return "❌ Action must be 'on' or 'off'"
            
            # Find matching switches using auto-generated aliases
            matching_switches = self._find_entities_by_alias(switches, switch_name)
            
            if not matching_switches:
                return f"❌ Switch '{switch_name}' not found"
            
            # Control all matching switches
            service = "turn_on" if action == "on" else "turn_off"
            icon = "🟢" if action == "on" else "🔴"
            
            controlled_switches = []
            errors = []
            
            for switch in matching_switches:
                try:
                    await self._async_call_service("switch", service, switch.entity_id)
                    name = switch.attributes.get('friendly_name', switch.entity_id)
                    controlled_switches.append(name)
                except Exception as e:
                    name = switch.attributes.get('friendly_name', switch.entity_id)
                    errors.append(f"{name}: {str(e)}")
            
            # Build response
            if controlled_switches:
                if len(controlled_switches) == 1:
                    return f"{icon} {controlled_switches[0]} turned {action}"
                else:
                    switches_list = '\n'.join([f"{icon} {name}" for name in controlled_switches])
                    response = f"Turned {action} {len(controlled_switches)} switches:\n{switches_list}"
                    if errors:
                        response += f"\n\n❌ Errors:\n" + '\n'.join(errors)
                    return response
            else:
                return f"❌ Failed to control switches:\n" + '\n'.join(errors)
            
        except Exception as e:
            return f"❌ Error controlling switches: {str(e)}"
    
    async def _handle_sensors_command(self, context: CommandContext) -> str:
        """Handle sensors command"""
        try:
            states = await self._async_get_states()
            sensors = [s for s in states if s.entity_id.startswith('sensor.')]
            
            if not sensors:
                return "📊 No sensors found"
            
            response = "📊 **Sensors:**\n\n"
            
            for sensor in sensors[:self.config.get('max_entities_per_response', 20)]:
                entity_id = sensor.entity_id
                name = sensor.attributes.get('friendly_name', entity_id)
                state = sensor.state
                unit = sensor.attributes.get('unit_of_measurement', '')
                
                if unit:
                    state_text = f"{state} {unit}"
                else:
                    state_text = state
                
                response += f"📈 {name}: {state_text}\n"
            
            if len(sensors) > self.config.get('max_entities_per_response', 20):
                response += f"\n... and {len(sensors) - 20} more sensors"
            
            return response
            
        except Exception as e:
            return f"❌ Error getting sensors: {str(e)}"
    
    async def _handle_climate_command(self, context: CommandContext) -> str:
        """Handle climate command"""
        return await self._handle_climate_subcommand(context)
    
    async def _handle_climate_subcommand(self, context: CommandContext) -> str:
        """Handle climate subcommand"""
        try:
            states = await self._async_get_states()
            climate_devices = [s for s in states if s.entity_id.startswith('climate.')]
            
            if len(context.args) <= 1:  # Just list climate devices
                if not climate_devices:
                    return "🌡️ No climate devices found"
                
                response = "🌡️ **Climate Devices:**\n\n"
                for device in climate_devices:
                    entity_id = device.entity_id
                    name = device.attributes.get('friendly_name', entity_id)
                    current_temp = device.attributes.get('current_temperature', 'Unknown')
                    target_temp = device.attributes.get('temperature', 'Unknown')
                    state = device.state
                    
                    response += f"🌡️ {name}:\n"
                    response += f"   Current: {current_temp}°\n"
                    response += f"   Target: {target_temp}°\n"
                    response += f"   Mode: {state}\n\n"
                
                response += "**Usage:** `!ha climate <name> <temperature>`"
                return response
            
            # Set temperature for specific device
            device_name = context.get_arg(1).lower()
            temperature = context.get_arg(2, "")
            
            if not temperature:
                return "❌ Please specify temperature"
            
            try:
                temp_value = float(temperature)
            except ValueError:
                return "❌ Invalid temperature value"
            
            # Find matching climate device
            matching_device = None
            for device in climate_devices:
                entity_id = device.entity_id
                friendly_name = device.attributes.get('friendly_name', '').lower()
                
                if (device_name in entity_id.lower() or 
                    device_name in friendly_name):
                    matching_device = device
                    break
            
            if not matching_device:
                return f"❌ Climate device '{device_name}' not found"
            
            # Set temperature
            await self._async_call_service("climate", "set_temperature", 
                                         matching_device.entity_id, 
                                         temperature=temp_value)
            
            name = matching_device.attributes.get('friendly_name', matching_device.entity_id)
            return f"🌡️ {name} temperature set to {temp_value}°"
            
        except Exception as e:
            return f"❌ Error controlling climate: {str(e)}"
    
    async def _handle_automation_command(self, context: CommandContext) -> str:
        """Handle automation command"""
        return await self._handle_automation_subcommand(context)
    
    async def _handle_automation_subcommand(self, context: CommandContext) -> str:
        """Handle automation subcommand"""
        try:
            states = await self._async_get_states()
            automations = [s for s in states if s.entity_id.startswith('automation.')]
            
            if len(context.args) <= 1:  # Just list automations
                if not automations:
                    return "🤖 No automations found"
                
                response = "🤖 **Automations:**\n\n"
                for automation in automations[:self.config.get('max_entities_per_response', 20)]:
                    entity_id = automation.entity_id
                    name = automation.attributes.get('friendly_name', entity_id)
                    state = automation.state
                    icon = "✅" if state == "on" else "❌"
                    response += f"{icon} {name}\n"
                
                if len(automations) > self.config.get('max_entities_per_response', 20):
                    response += f"\n... and {len(automations) - 20} more automations"
                
                response += "\n\n**Usage:** `!ha automation <name>`"
                return response
            
            # Trigger specific automation
            automation_name = " ".join(context.args[1:]).lower()
            
            # Find matching automation
            matching_automation = None
            for automation in automations:
                entity_id = automation.entity_id
                friendly_name = automation.attributes.get('friendly_name', '').lower()
                
                if (automation_name in entity_id.lower() or 
                    automation_name in friendly_name):
                    matching_automation = automation
                    break
            
            if not matching_automation:
                return f"❌ Automation '{automation_name}' not found"
            
            # Trigger automation
            await self._async_call_service("automation", "trigger", matching_automation.entity_id)
            
            name = matching_automation.attributes.get('friendly_name', matching_automation.entity_id)
            return f"🤖 Triggered automation: {name}"
            
        except Exception as e:
            return f"❌ Error with automation: {str(e)}"
    
    async def _handle_entities_command(self, context: CommandContext) -> str:
        """Handle entities command - list all entities"""
        try:
            states = await self._async_get_states()
            
            if not states:
                return "❌ No entities found"
            
            # Group by domain
            domains = {}
            for state in states:
                domain = state.entity_id.split('.')[0]
                if domain not in domains:
                    domains[domain] = []
                domains[domain].append(state)
            
            response = "🏠 **All Entities by Domain:**\n\n"
            
            # Show top domains
            sorted_domains = sorted(domains.items(), key=lambda x: len(x[1]), reverse=True)
            
            for domain, entities in sorted_domains[:10]:
                response += f"**{domain.title()}** ({len(entities)}):\n"
                for entity in entities[:5]:  # Show first 5 entities
                    name = entity.attributes.get('friendly_name', entity.entity_id)
                    state = entity.state
                    response += f"  • {name}: {state}\n"
                
                if len(entities) > 5:
                    response += f"  ... and {len(entities) - 5} more\n"
                response += "\n"
            
            if len(sorted_domains) > 10:
                response += f"... and {len(sorted_domains) - 10} more domains\n"
            
            response += f"\n**Total:** {len(states)} entities across {len(domains)} domains"
            
            return response
            
        except Exception as e:
            return f"❌ Error listing entities: {str(e)}"
    
    async def _handle_todo_subcommand(self, context: CommandContext) -> str:
        """Handle todo subcommand"""
        try:
            states = await self._async_get_states()
            todo_lists = [s for s in states if s.entity_id.startswith('todo.')]
            
            if len(context.args) <= 1:  # List all todo lists
                if not todo_lists:
                    return "📋 No todo lists found"
                
                response = "📋 **Todo Lists:**\n\n"
                for todo_list in todo_lists:
                    entity_id = todo_list.entity_id
                    name = todo_list.attributes.get('friendly_name', entity_id)
                    # Use the state as item count (this is the actual count from HA)
                    item_count = int(todo_list.state) if todo_list.state.isdigit() else 0
                    
                    # Show available aliases
                    aliases = self._extract_aliases_from_name(name)
                    if aliases:
                        alias_text = f" [{', '.join(aliases[:3])}]"  # Show first 3 aliases
                    else:
                        alias_text = ""
                    
                    response += f"📝 {name}: {item_count} items{alias_text}\n"
                
                response += "\n**Usage:**\n"
                response += "• `!ha todo <list|alias>` - Show items in list\n"
                response += "• `!ha todo <list|alias> add <item>` - Add item\n"
                response += "• `!ha todo <list|alias> done <item|alias>` - Mark complete\n"
                response += "• `!ha todo <list|alias> undo <item|alias>` - Mark as pending\n"
                response += "**Tip:** Use aliases in brackets for easier access to lists and items"
                return response
            
            # Handle specific todo list operations
            list_name = context.get_arg(1).lower()
            operation = context.get_arg(2, "").lower()
            
            # Find matching todo list using alias system
            matching_lists = self._find_entities_by_alias(todo_lists, list_name)
            
            if not matching_lists:
                return f"❌ Todo list '{list_name}' not found"
            
            if len(matching_lists) > 1:
                # Show both matching lists instead of error
                response = f"📋 **Multiple todo lists match '{list_name}':**\n\n"
                
                for todo_list in matching_lists:
                    list_friendly_name = todo_list.attributes.get('friendly_name', todo_list.entity_id)
                    try:
                        # Get actual items for each matching list
                        items_response = await self._async_call_service_with_response('todo', 'get_items', todo_list.entity_id)
                        if isinstance(items_response, tuple) and len(items_response) > 1:
                            response_data = items_response[1]
                            items = response_data.get(todo_list.entity_id, {}).get('items', [])
                        else:
                            items = items_response.get('items', []) if items_response else []
                        
                        # Count not-done items
                        not_done_count = sum(1 for item in items if item.get('status', 'needs_action') != 'completed')
                        total_count = len(items)
                        
                        # Extract aliases for the list name
                        aliases = self._extract_aliases_from_name(list_friendly_name)
                        alias_text = f" [{', '.join(aliases[:2])}]" if aliases else ""
                        
                        response += f"📝 **{list_friendly_name}**: {not_done_count}/{total_count} pending{alias_text}\n"
                        
                    except Exception as e:
                        # Fallback to state count if service call fails
                        item_count = int(todo_list.state) if todo_list.state.isdigit() else 0
                        aliases = self._extract_aliases_from_name(list_friendly_name)
                        alias_text = f" [{', '.join(aliases[:2])}]" if aliases else ""
                        response += f"📝 **{list_friendly_name}**: {item_count} items{alias_text}\n"
                
                response += f"\n**Usage:** `!ha todo <list> [add|done|undo] [item]`"
                return response
            
            todo_list = matching_lists[0]
            list_friendly_name = todo_list.attributes.get('friendly_name', todo_list.entity_id)
            
            # Just show list contents
            if not operation:
                try:
                    # Get actual items using the service call
                    items_response = await self._async_call_service_with_response('todo', 'get_items', todo_list.entity_id)
                    # Response is a tuple: ((), {entity_id: {items: [...]}})
                    if isinstance(items_response, tuple) and len(items_response) > 1:
                        response_data = items_response[1]
                        items = response_data.get(todo_list.entity_id, {}).get('items', [])
                    else:
                        items = items_response.get('items', []) if items_response else []
                except Exception as e:
                    # Fallback to state count if service call fails
                    item_count = int(todo_list.state) if todo_list.state.isdigit() else 0
                    if item_count == 0:
                        return f"📋 **{list_friendly_name}** is empty"
                    else:
                        return f"📋 **{list_friendly_name}** has {item_count} items (details unavailable: {e})"
                
                if not items:
                    return f"📋 **{list_friendly_name}** is empty"
                
                # Sort items: not-done items first, then completed items
                not_done_items = [item for item in items if item.get('status', 'needs_action') != 'completed']
                completed_items = [item for item in items if item.get('status', 'needs_action') == 'completed']
                sorted_items = not_done_items + completed_items
                
                not_done_count = len(not_done_items)
                total_count = len(items)
                
                response = f"📋 **{list_friendly_name}** ({not_done_count}/{total_count} pending):\n\n"
                
                for i, item in enumerate(sorted_items, 1):
                    status = item.get('status', 'needs_action')
                    summary = item.get('summary', 'No description')
                    icon = "✅" if status == 'completed' else "⭕"
                    
                    # Show available aliases for each item
                    aliases = self._extract_aliases_from_name(summary)
                    if aliases:
                        alias_text = f" [{', '.join(aliases[:2])}]"  # Show first 2 aliases to keep it compact
                    else:
                        alias_text = ""
                    
                    response += f"{i}. {icon} {summary}{alias_text}\n"
                
                return response
            
            # Add item to list
            elif operation == "add":
                item_text = " ".join(context.args[3:]) if len(context.args) > 3 else ""
                if not item_text:
                    return "❌ Please specify item text to add"
                
                await self._async_call_service("todo", "add_item", todo_list.entity_id, item=item_text)
                return f"✅ Added '{item_text}' to {list_friendly_name}"
            
            # Mark item as complete
            elif operation in ["done", "complete", "finish"]:
                item_text = " ".join(context.args[3:]) if len(context.args) > 3 else ""
                if not item_text:
                    return "❌ Please specify item text to mark as done"
                
                # Get current items from the todo list
                try:
                    items_response = await self._async_call_service_with_response('todo', 'get_items', todo_list.entity_id)
                    # Response is a tuple: ((), {entity_id: {items: [...]}})
                    if isinstance(items_response, tuple) and len(items_response) > 1:
                        response_data = items_response[1]
                        items = response_data.get(todo_list.entity_id, {}).get('items', [])
                    else:
                        items = items_response.get('items', []) if items_response else []
                except Exception as e:
                    return f"❌ Failed to get todo items: {e}"
                
                matching_item = None
                
                # Try alias-based matching first (like lights/switches)
                for item in items:
                    summary = item.get('summary', '')
                    aliases = self._extract_aliases_from_name(summary)
                    
                    # Check if search term matches any alias exactly
                    if item_text.lower() in [alias.lower() for alias in aliases]:
                        matching_item = item
                        break
                    
                    # Check exact match on full summary
                    if summary.lower() == item_text.lower():
                        matching_item = item
                        break
                
                if not matching_item:
                    # Try partial match in summary as fallback
                    for item in items:
                        summary = item.get('summary', '')
                        if item_text.lower() in summary.lower():
                            matching_item = item
                            break
                
                if not matching_item:
                    return f"❌ Item '{item_text}' not found in {list_friendly_name}"
                
                # Check if already completed
                if matching_item.get('status') == 'completed':
                    return f"✅ '{matching_item.get('summary')}' is already completed"
                
                # Mark as complete
                item_uid = matching_item.get('uid')
                if item_uid:
                    await self._async_call_service("todo", "update_item", todo_list.entity_id, 
                                                 item=item_uid, status="completed")
                    return f"✅ Marked '{matching_item.get('summary')}' as complete in {list_friendly_name}"
                else:
                    return f"❌ Could not update item (missing UID)"
            
            # Mark item as pending (undo)
            elif operation in ["undo", "pending", "reopen"]:
                item_text = " ".join(context.args[3:]) if len(context.args) > 3 else ""
                if not item_text:
                    return "❌ Please specify item text to mark as pending"
                
                # Get current items from the todo list
                try:
                    items_response = await self._async_call_service_with_response('todo', 'get_items', todo_list.entity_id)
                    # Response is a tuple: ((), {entity_id: {items: [...]}})
                    if isinstance(items_response, tuple) and len(items_response) > 1:
                        response_data = items_response[1]
                        items = response_data.get(todo_list.entity_id, {}).get('items', [])
                    else:
                        items = items_response.get('items', []) if items_response else []
                except Exception as e:
                    return f"❌ Failed to get todo items: {e}"
                
                matching_item = None
                
                # Try alias-based matching first (like lights/switches)
                for item in items:
                    summary = item.get('summary', '')
                    aliases = self._extract_aliases_from_name(summary)
                    
                    # Check if search term matches any alias exactly
                    if item_text.lower() in [alias.lower() for alias in aliases]:
                        matching_item = item
                        break
                    
                    # Check exact match on full summary
                    if summary.lower() == item_text.lower():
                        matching_item = item
                        break
                
                if not matching_item:
                    # Try partial match in summary as fallback
                    for item in items:
                        summary = item.get('summary', '')
                        if item_text.lower() in summary.lower():
                            matching_item = item
                            break
                
                if not matching_item:
                    return f"❌ Item '{item_text}' not found in {list_friendly_name}"
                
                # Check if already pending
                if matching_item.get('status') == 'needs_action':
                    return f"⭕ '{matching_item.get('summary')}' is already pending"
                
                # Mark as pending
                item_uid = matching_item.get('uid')
                if item_uid:
                    await self._async_call_service("todo", "update_item", todo_list.entity_id, 
                                                 item=item_uid, status="needs_action")
                    return f"⭕ Marked '{matching_item.get('summary')}' as pending in {list_friendly_name}"
                else:
                    return f"❌ Could not update item (missing UID)"
            
            else:
                return f"❌ Unknown operation '{operation}'. Use: add, done, undo"
            
        except Exception as e:
            return f"❌ Error with todo lists: {str(e)}"
    
    async def _handle_connections_command(self, context: CommandContext) -> str:
        """Handle connections command - show Ping(ICMP) sensor status"""
        try:
            states = await self._async_get_states()
            
            # Find binary sensors related to Ping(ICMP) integration
            # These typically have entity IDs like binary_sensor.ping_<hostname>
            # or contain "ping" in their integration/device info
            ping_sensors = []
            
            for state in states:
                entity_id = state.entity_id
                
                # Filter for binary sensors first
                if not entity_id.startswith('binary_sensor.'):
                    continue
                
                # Check if it's a ping sensor by entity ID pattern
                if 'ping' in entity_id.lower():
                    ping_sensors.append(state)
                    continue
                
                # Check device/integration info for Ping(ICMP) integration
                device_class = state.attributes.get('device_class')
                source_type = state.attributes.get('source_type')
                integration = state.attributes.get('integration', '')
                platform = state.attributes.get('platform', '')
                
                # Common patterns for ping sensors
                if (device_class == 'connectivity' or 
                    source_type == 'ping' or
                    integration.lower() == 'ping' or
                    platform.lower() == 'ping' or
                    'ping' in str(state.attributes.get('attribution', '')).lower()):
                    ping_sensors.append(state)
            
            if not ping_sensors:
                return "🌐 No Ping(ICMP) connection sensors found"
            
            response = "🌐 **Network Connections (Ping/ICMP Status):**\n\n"
            
            # Sort by status (online first) then by name
            ping_sensors.sort(key=lambda x: (x.state != 'on', x.attributes.get('friendly_name', x.entity_id).lower()))
            
            for sensor in ping_sensors:
                entity_id = sensor.entity_id
                name = sensor.attributes.get('friendly_name', entity_id)
                state = sensor.state
                
                # Status icons
                if state == 'on':
                    icon = "🟢"
                    status_text = "Online"
                elif state == 'off':
                    icon = "🔴"
                    status_text = "Offline"
                else:
                    icon = "❓"
                    status_text = f"Unknown ({state})"
                
                # Try to get additional info like IP address from attributes
                ip_address = sensor.attributes.get('ip_address', '')
                last_changed = sensor.last_changed if hasattr(sensor, 'last_changed') else None
                
                response += f"{icon} **{name}**: {status_text}"
                
                if ip_address:
                    response += f" ({ip_address})"
                
                response += "\n"
            
            response += f"\n**Total:** {len(ping_sensors)} monitored connections"
            return response
            
        except Exception as e:
            return f"❌ Error getting connection status: {str(e)}"
    
    async def _handle_wake_command(self, context: CommandContext) -> str:
        """Handle wake command - list or trigger Wake on LAN buttons"""
        try:
            states = await self._async_get_states()
            
            # Find Wake on LAN buttons - these are typically button entities
            # with names containing "wake" or from wake_on_lan integration
            wake_buttons = []
            
            for state in states:
                entity_id = state.entity_id
                
                # Filter for button entities first
                if not entity_id.startswith('button.'):
                    continue
                
                # Check if it's a wake on lan button
                entity_lower = entity_id.lower()
                name_lower = state.attributes.get('friendly_name', '').lower()
                integration = state.attributes.get('integration', '').lower()
                device_class = state.attributes.get('device_class', '').lower()
                
                if ('wake' in entity_lower or 
                    'wol' in entity_lower or
                    'wake' in name_lower or
                    'wol' in name_lower or
                    integration == 'wake_on_lan' or
                    device_class == 'restart'):  # Some WoL buttons use restart device class
                    wake_buttons.append(state)
            
            # Handle subcommands
            if len(context.args) <= 1:  # Just "!ha wake" - list all wake buttons
                if not wake_buttons:
                    return "💤 No Wake on LAN buttons found"
                
                response = "💤 **Wake on LAN Buttons:**\n\n"
                
                for i, button in enumerate(wake_buttons, 1):
                    entity_id = button.entity_id
                    name = button.attributes.get('friendly_name', entity_id)
                    
                    # Try to get MAC address or target info from attributes
                    mac_address = button.attributes.get('mac_address', '')
                    target_host = button.attributes.get('host', button.attributes.get('target', ''))
                    
                    response += f"{i}. **{name}**"
                    
                    if mac_address:
                        response += f"\n   MAC: {mac_address}"
                    if target_host:
                        response += f"\n   Target: {target_host}"
                    
                    response += "\n\n"
                
                response += f"**Usage:** `!ha wake <number>` or `!ha wake <button_name>`\n"
                response += f"**Examples:** `!ha wake 1`, `!ha wake 2`, `!ha wake FRITZ!Box`"
                return response
            
            elif context.get_arg(1).lower() == "list":  # "!ha wake list" - same as above
                return await self._handle_wake_command(CommandContext(
                    command=context.command,
                    args=["wake"],  # Remove "list" argument
                    args_raw=context.args_raw,
                    user_id=context.user_id,
                    chat_id=context.chat_id,
                    user_display_name=context.user_display_name,
                    platform=context.platform,
                    raw_message=context.raw_message
                ))
            
            else:  # "!ha wake <button_name_or_number>" - trigger specific wake button
                button_input = context.get_arg(1)
                
                # Check if input is a number
                try:
                    button_number = int(button_input)
                    if 1 <= button_number <= len(wake_buttons):
                        # Use the button at the specified index (1-based)
                        wake_button = wake_buttons[button_number - 1]
                        button_friendly_name = wake_button.attributes.get('friendly_name', wake_button.entity_id)
                        
                        # Press the button (button entities use the "press" service)
                        await self._async_call_service("button", "press", wake_button.entity_id)
                        
                        # Get additional info for response
                        mac_address = wake_button.attributes.get('mac_address', '')
                        target_host = wake_button.attributes.get('host', wake_button.attributes.get('target', ''))
                        
                        response = f"💤 **Wake on LAN signal sent!**\n\n"
                        response += f"🖥️ **Target:** {button_friendly_name}\n"
                        
                        if mac_address:
                            response += f"📱 **MAC:** {mac_address}\n"
                        if target_host:
                            response += f"🌐 **Host:** {target_host}\n"
                        
                        response += f"\n✅ Wake signal has been transmitted"
                        
                        return response
                    else:
                        return f"❌ Invalid button number. Please use 1-{len(wake_buttons)} or button name."
                        
                except ValueError:
                    # Not a number, try name matching
                    button_name = button_input.lower()
                    
                    # Find matching wake button using alias system
                    matching_buttons = self._find_entities_by_alias(wake_buttons, button_name)
                    
                    if not matching_buttons:
                        return f"❌ Wake on LAN button '{button_name}' not found"
                    
                    if len(matching_buttons) > 1:
                        response = f"❌ Multiple Wake on LAN buttons match '{button_name}':\n\n"
                        for i, button in enumerate(matching_buttons, 1):
                            name = button.attributes.get('friendly_name', button.entity_id)
                            response += f"{i}. {name}\n"
                        response += f"\nPlease be more specific with the button name or use a number from the list above."
                        return response
                    
                    # Trigger the wake button
                    wake_button = matching_buttons[0]
                    button_friendly_name = wake_button.attributes.get('friendly_name', wake_button.entity_id)
                    
                    # Press the button (button entities use the "press" service)
                    await self._async_call_service("button", "press", wake_button.entity_id)
                    
                    # Get additional info for response
                    mac_address = wake_button.attributes.get('mac_address', '')
                    target_host = wake_button.attributes.get('host', wake_button.attributes.get('target', ''))
                    
                    response = f"💤 **Wake on LAN signal sent!**\n\n"
                    response += f"🖥️ **Target:** {button_friendly_name}\n"
                    
                    if mac_address:
                        response += f"📱 **MAC:** {mac_address}\n"
                    if target_host:
                        response += f"🌐 **Host:** {target_host}\n"
                    
                    response += f"\n✅ Wake signal has been transmitted"
                    
                    return response
                
        except Exception as e:
            return f"❌ Error with Wake on LAN: {str(e)}"
    
    def _get_help_text(self) -> str:
        """Get help text for Home Assistant commands"""
        return """🏠 **Home Assistant Commands:**

**Status & Info:**
• `!ha status` - Get HA status and entity counts
• `!ha entities` - List all entities by domain

**Lights:**
• `!ha lights` - List all lights
• `!ha light <name> on/off` - Control specific light

**Switches:**
• `!ha switches` - List all switches  
• `!ha switch <name> on/off` - Control specific switch

**Sensors:**
• `!ha sensors` - Show sensor readings

**Climate:**
• `!ha climate` - List climate devices
• `!ha climate <name> <temp>` - Set temperature

**Automations:**
• `!ha automation` - List automations
• `!ha automation <name>` - Trigger automation

**Todo Lists:**
• `!ha todos` - List all todo lists
• `!ha todo <list>` - Show items in specific list
• `!ha todo <list> add <item>` - Add item to list
• `!ha todo <list> done <item>` - Mark item complete
• `!ha todo <list> undo <item>` - Mark item as pending

**Network & Wake on LAN:**
• `!ha connections` - Show Ping(ICMP) sensor status
• `!ha wake` - List Wake on LAN buttons
• `!ha wake list` - List Wake on LAN buttons
• `!ha wake <button>` - Send Wake on LAN signal

**Direct Commands:**
• `!lights`, `!switches`, `!sensors` - Quick access
• `!climate`, `!automation`, `!entities` - Quick access

**Configuration:**
Configure your Home Assistant connection and caching preference in the plugin config file.
• Cache enabled: Better performance, 30-second cache
• Cache disabled: Real-time updates, immediate entity changes"""

    async def cleanup(self):
        """Cleanup plugin resources"""
        try:
            if self.ha_client:
                # The homeassistant_api client doesn't require explicit cleanup
                self.ha_client = None
            self.logger.info("Home Assistant plugin cleaned up")
        except Exception as e:
            self.logger.error(f"Error during Home Assistant plugin cleanup: {e}")


# Plugin entry point
def create_plugin(logger=None):
    """Create and return plugin instance"""
    return UniversalHomeAssistantPlugin(logger=logger)