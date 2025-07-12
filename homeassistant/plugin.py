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
"""

from typing import List, Optional, Dict, Any
import logging
import asyncio
import yaml
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
        """Load plugin configuration from config.yaml"""
        try:
            config_path = Path(__file__).parent / "config.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    full_config = yaml.safe_load(f)
                    self.config = full_config.get('homeassistant', {})
                    self.logger.info(f"Loaded Home Assistant config from {config_path}")
            else:
                self.logger.warning(f"Config file not found: {config_path}")
                self.config = {}
        except Exception as e:
            self.logger.error(f"Failed to load Home Assistant config: {e}")
            self.config = {}
    
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
            port = self.config.get('port', 8123)
            token = self.config.get('token', '')
            ssl = self.config.get('ssl', False)
            
            if not token:
                self.logger.error("Home Assistant token not configured")
                return False
            
            # Build URL
            protocol = 'https' if ssl else 'http'
            url = f"{protocol}://{host}:{port}"
            
            # Initialize client
            self.ha_client = HomeAssistantClient(url, token)
            
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
        service_data = kwargs
        if entity_id:
            service_data['entity_id'] = entity_id
        return await loop.run_in_executor(None, 
                                          self.ha_client.call_service, 
                                          domain, service, service_data)
    
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
        else:
            return f"❌ Unknown subcommand: {subcmd}\n\n{self._get_help_text()}"
    
    async def _get_status(self) -> str:
        """Get Home Assistant status"""
        try:
            states = await self._async_get_states()
            
            # Count entities by domain
            domains = {}
            for state in states:
                domain = state['entity_id'].split('.')[0]
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
            lights = [s for s in states if s['entity_id'].startswith('light.')]
            
            if len(context.args) <= 1:  # Just list lights
                if not lights:
                    return "💡 No lights found"
                
                response = "💡 **Lights:**\n\n"
                for light in lights[:self.config.get('max_entities_per_response', 20)]:
                    entity_id = light['entity_id']
                    name = light['attributes'].get('friendly_name', entity_id)
                    state = light['state']
                    icon = "🟡" if state == "on" else "⚫"
                    response += f"{icon} {name} ({state})\n"
                
                if len(lights) > self.config.get('max_entities_per_response', 20):
                    response += f"\n... and {len(lights) - 20} more lights"
                
                response += "\n\n**Usage:** `!ha light <name> on/off`"
                return response
            
            # Control specific light
            light_name = context.get_arg(1).lower()
            action = context.get_arg(2, "").lower()
            
            if not action:
                return "❌ Please specify 'on' or 'off'"
            
            if action not in ["on", "off"]:
                return "❌ Action must be 'on' or 'off'"
            
            # Find matching light
            matching_light = None
            for light in lights:
                entity_id = light['entity_id']
                friendly_name = light['attributes'].get('friendly_name', '').lower()
                
                if (light_name in entity_id.lower() or 
                    light_name in friendly_name):
                    matching_light = light
                    break
            
            if not matching_light:
                return f"❌ Light '{light_name}' not found"
            
            # Control the light
            service = "turn_on" if action == "on" else "turn_off"
            await self._async_call_service("light", service, matching_light['entity_id'])
            
            name = matching_light['attributes'].get('friendly_name', matching_light['entity_id'])
            icon = "🟡" if action == "on" else "⚫"
            return f"{icon} {name} turned {action}"
            
        except Exception as e:
            return f"❌ Error controlling lights: {str(e)}"
    
    async def _handle_switches_command(self, context: CommandContext) -> str:
        """Handle switches command"""
        return await self._handle_switches_subcommand(context)
    
    async def _handle_switches_subcommand(self, context: CommandContext) -> str:
        """Handle switches subcommand"""
        try:
            states = await self._async_get_states()
            switches = [s for s in states if s['entity_id'].startswith('switch.')]
            
            if len(context.args) <= 1:  # Just list switches
                if not switches:
                    return "🔌 No switches found"
                
                response = "🔌 **Switches:**\n\n"
                for switch in switches[:self.config.get('max_entities_per_response', 20)]:
                    entity_id = switch['entity_id']
                    name = switch['attributes'].get('friendly_name', entity_id)
                    state = switch['state']
                    icon = "🟢" if state == "on" else "🔴"
                    response += f"{icon} {name} ({state})\n"
                
                if len(switches) > self.config.get('max_entities_per_response', 20):
                    response += f"\n... and {len(switches) - 20} more switches"
                
                response += "\n\n**Usage:** `!ha switch <name> on/off`"
                return response
            
            # Control specific switch (similar logic to lights)
            switch_name = context.get_arg(1).lower()
            action = context.get_arg(2, "").lower()
            
            if not action:
                return "❌ Please specify 'on' or 'off'"
            
            if action not in ["on", "off"]:
                return "❌ Action must be 'on' or 'off'"
            
            # Find matching switch
            matching_switch = None
            for switch in switches:
                entity_id = switch['entity_id']
                friendly_name = switch['attributes'].get('friendly_name', '').lower()
                
                if (switch_name in entity_id.lower() or 
                    switch_name in friendly_name):
                    matching_switch = switch
                    break
            
            if not matching_switch:
                return f"❌ Switch '{switch_name}' not found"
            
            # Control the switch
            service = "turn_on" if action == "on" else "turn_off"
            await self._async_call_service("switch", service, matching_switch['entity_id'])
            
            name = matching_switch['attributes'].get('friendly_name', matching_switch['entity_id'])
            icon = "🟢" if action == "on" else "🔴"
            return f"{icon} {name} turned {action}"
            
        except Exception as e:
            return f"❌ Error controlling switches: {str(e)}"
    
    async def _handle_sensors_command(self, context: CommandContext) -> str:
        """Handle sensors command"""
        try:
            states = await self._async_get_states()
            sensors = [s for s in states if s['entity_id'].startswith('sensor.')]
            
            if not sensors:
                return "📊 No sensors found"
            
            response = "📊 **Sensors:**\n\n"
            
            for sensor in sensors[:self.config.get('max_entities_per_response', 20)]:
                entity_id = sensor['entity_id']
                name = sensor['attributes'].get('friendly_name', entity_id)
                state = sensor['state']
                unit = sensor['attributes'].get('unit_of_measurement', '')
                
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
            climate_devices = [s for s in states if s['entity_id'].startswith('climate.')]
            
            if len(context.args) <= 1:  # Just list climate devices
                if not climate_devices:
                    return "🌡️ No climate devices found"
                
                response = "🌡️ **Climate Devices:**\n\n"
                for device in climate_devices:
                    entity_id = device['entity_id']
                    name = device['attributes'].get('friendly_name', entity_id)
                    current_temp = device['attributes'].get('current_temperature', 'Unknown')
                    target_temp = device['attributes'].get('temperature', 'Unknown')
                    state = device['state']
                    
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
                entity_id = device['entity_id']
                friendly_name = device['attributes'].get('friendly_name', '').lower()
                
                if (device_name in entity_id.lower() or 
                    device_name in friendly_name):
                    matching_device = device
                    break
            
            if not matching_device:
                return f"❌ Climate device '{device_name}' not found"
            
            # Set temperature
            await self._async_call_service("climate", "set_temperature", 
                                         matching_device['entity_id'], 
                                         temperature=temp_value)
            
            name = matching_device['attributes'].get('friendly_name', matching_device['entity_id'])
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
            automations = [s for s in states if s['entity_id'].startswith('automation.')]
            
            if len(context.args) <= 1:  # Just list automations
                if not automations:
                    return "🤖 No automations found"
                
                response = "🤖 **Automations:**\n\n"
                for automation in automations[:self.config.get('max_entities_per_response', 20)]:
                    entity_id = automation['entity_id']
                    name = automation['attributes'].get('friendly_name', entity_id)
                    state = automation['state']
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
                entity_id = automation['entity_id']
                friendly_name = automation['attributes'].get('friendly_name', '').lower()
                
                if (automation_name in entity_id.lower() or 
                    automation_name in friendly_name):
                    matching_automation = automation
                    break
            
            if not matching_automation:
                return f"❌ Automation '{automation_name}' not found"
            
            # Trigger automation
            await self._async_call_service("automation", "trigger", matching_automation['entity_id'])
            
            name = matching_automation['attributes'].get('friendly_name', matching_automation['entity_id'])
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
                domain = state['entity_id'].split('.')[0]
                if domain not in domains:
                    domains[domain] = []
                domains[domain].append(state)
            
            response = "🏠 **All Entities by Domain:**\n\n"
            
            # Show top domains
            sorted_domains = sorted(domains.items(), key=lambda x: len(x[1]), reverse=True)
            
            for domain, entities in sorted_domains[:10]:
                response += f"**{domain.title()}** ({len(entities)}):\n"
                for entity in entities[:5]:  # Show first 5 entities
                    name = entity['attributes'].get('friendly_name', entity['entity_id'])
                    state = entity['state']
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

**Direct Commands:**
• `!lights`, `!switches`, `!sensors` - Quick access
• `!climate`, `!automation`, `!entities` - Quick access

Configure your Home Assistant connection in the plugin config file."""

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