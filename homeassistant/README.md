# Home Assistant Plugin

This plugin provides Home Assistant integration for the Universal Bot Framework, allowing you to control and monitor your Home Assistant instance via chat commands.

## Features

- **Device Control**: Turn lights and switches on/off
- **Sensor Monitoring**: Get real-time sensor readings
- **Climate Control**: Set temperatures for thermostats and HVAC systems
- **Automation Triggers**: Run Home Assistant automations
- **Status Monitoring**: Get overview of your entire HA setup
- **Entity Management**: List and inspect all entities
- **Network Monitoring**: Monitor Ping(ICMP) sensor status for device connectivity
- **Wake on LAN**: Send Wake on LAN signals to computers and devices
- **Todo List Management**: Manage Home Assistant todo lists and items
- **Configurable Caching**: Choose between real-time updates or performance optimization

## Setup

### 1. Install Dependencies

The plugin requires the `homeassistant-api` Python library:

```bash
pip install homeassistant-api
```

### 2. Configure Home Assistant

You need a **Long-Lived Access Token** from Home Assistant:

1. Go to your Home Assistant web interface
2. Click on your profile (bottom left)
3. Scroll down to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Give it a name (e.g., "Bot Access")
6. Copy the generated token

### 3. Configure the Plugin

Edit `plugins/external/homeassistant/config.yaml`:

```yaml
homeassistant:
  host: "your-ha-host"          # IP or hostname of your HA instance
  port: 8123                    # Port (usually 8123)
  token: "your-token-here"      # Long-lived access token
  ssl: false                    # Set to true if using HTTPS
  enable_cache: false           # Enable/disable API caching (see Cache Settings below)
```

Or use environment variables:

```bash
export HA_HOST="192.168.1.100"
export HA_PORT="8123" 
export HA_TOKEN="your-long-lived-token"
export HA_SSL="false"
export HA_ENABLE_CACHE="false"
```

## Commands

### Status & Information

- `!ha status` - Get Home Assistant status and entity counts
- `!ha entities` - List all entities grouped by domain
- `!ha help` - Show help information

### Lights

- `!ha lights` - List all lights with current states
- `!ha light <name> on` - Turn on a specific light
- `!ha light <name> off` - Turn off a specific light
- `!lights` - Quick access to list lights

Examples:
```
!ha light kitchen on
!ha light bedroom off
!ha lights
```

### Switches

- `!ha switches` - List all switches with current states
- `!ha switch <name> on` - Turn on a specific switch
- `!ha switch <name> off` - Turn off a specific switch
- `!switches` - Quick access to list switches

Examples:
```
!ha switch fan on
!ha switch outlet off
!switches
```

### Sensors

- `!ha sensors` - Show all sensor readings
- `!sensors` - Quick access to sensor data

Examples:
```
!ha sensors
!sensors
```

### Climate

- `!ha climate` - List all climate devices with current/target temps
- `!ha climate <name> <temperature>` - Set temperature for device
- `!climate` - Quick access to climate devices

Examples:
```
!ha climate thermostat 72
!ha climate bedroom 68
!climate
```

### Automations

- `!ha automation` - List all automations
- `!ha automation <name>` - Trigger specific automation
- `!automation` - Quick access to automations

Examples:
```
!ha automation good night
!ha automation morning routine
!automation
```

### Network Monitoring

- `!ha connections` - Show status of all Ping(ICMP) sensors for network connectivity monitoring

Examples:
```
!ha connections
```

This command shows the online/offline status of devices monitored by Home Assistant's Ping(ICMP) integration, helping you track network connectivity of computers, servers, and other networked devices.

### Wake on LAN

- `!ha wake` - List all available Wake on LAN buttons (numbered list)
- `!ha wake list` - Same as above
- `!ha wake <number>` - Send Wake on LAN signal using button number
- `!ha wake <button_name>` - Send Wake on LAN signal using button name

Examples:
```
!ha wake                    # List all wake buttons (numbered)
!ha wake 1                  # Wake up button #1
!ha wake 2                  # Wake up button #2
!ha wake FRITZ!Box          # Wake up device by name
```

Wake on LAN functionality works with Home Assistant's Wake on LAN integration, allowing you to remotely power on computers and compatible devices. The numbered list makes it easy to select buttons even when they have complex MAC-address based names.

### Todo Lists

- `!ha todos` - List all Home Assistant todo lists
- `!ha todo <list>` - Show items in specific todo list
- `!ha todo <list> add <item>` - Add new item to todo list
- `!ha todo <list> done <item>` - Mark item as completed
- `!ha todo <list> undo <item>` - Mark completed item as pending

Examples:
```
!ha todos                           # List all todo lists
!ha todo shopping                   # Show shopping list items
!ha todo shopping add bread         # Add bread to shopping list
!ha todo shopping done milk         # Mark milk as bought
!ha todo work undo important task   # Mark task as pending again
```

Todo lists support smart matching - you can use partial names or aliases for both lists and items.

## Security Considerations

- **Access Token**: Keep your Home Assistant token secure. Don't share it or commit it to version control.
- **Network Access**: Ensure your bot can reach your Home Assistant instance.
- **Admin Only**: Consider setting `admin_only: true` in config if you want to restrict access.
- **Allowed Domains**: The plugin only works with safe domains by default (lights, switches, etc.).

## Configuration Options

Full configuration options in `config.yaml`:

```yaml
homeassistant:
  # Connection Settings
  host: "${HA_HOST:localhost}"
  port: "${HA_PORT:8123}"
  token: "${HA_TOKEN:}"
  ssl: "${HA_SSL:false}"
  timeout: 30
  verify_ssl: true
  
  # Cache Settings
  enable_cache: "${HA_ENABLE_CACHE:false}"  # Enable/disable API response caching
  # When enabled: Better performance, less bandwidth usage, 30-second cache
  # When disabled: Real-time updates, new/deleted entities appear immediately
  
  # Command Settings  
  command_prefix: "ha"
  admin_only: false
  
  # Entity Categories
  entities:
    lights: true
    switches: true
    sensors: true
    automation: true
    climate: true
    cover: true
    fan: true
    lock: true
    media_player: true
    vacuum: true
  
  # Security
  allowed_domains:
    - light
    - switch
    - automation
    - climate
    - cover
    - fan
    - lock
    - media_player
    - vacuum
  
  # Response Settings
  max_entities_per_response: 20
  include_state_attributes: false
```

### Cache Settings

The plugin supports configurable API response caching to balance performance and real-time updates:

#### Cache Enabled (`enable_cache: true`)
- **Performance**: Faster response times for repeated queries
- **Bandwidth**: Reduced network usage (important for remote/cloud HA instances)
- **HA Load**: Less API calls to your Home Assistant instance
- **Update Delay**: New or deleted entities may take up to 30 seconds to appear

#### Cache Disabled (`enable_cache: false`) - **Default**
- **Real-time**: New entities appear immediately
- **Responsiveness**: Deleted entities disappear immediately  
- **Accuracy**: Always shows current state
- **Performance**: Slightly slower response times
- **Bandwidth**: More network requests to Home Assistant

**Recommendation**: 
- Use `enable_cache: false` (default) for real-time monitoring and frequent entity changes
- Use `enable_cache: true` for better performance with stable setups or limited bandwidth

## Troubleshooting

### Connection Issues

1. **Check Network**: Ensure the bot can reach your HA instance
2. **Check Token**: Verify your long-lived access token is correct
3. **Check URL**: Make sure host/port/SSL settings are correct

### Command Issues

1. **Entity Names**: Use partial names - the plugin will match against entity IDs and friendly names
2. **Case Insensitive**: All commands and entity names are case-insensitive
3. **Permissions**: Check if your token has the necessary permissions

### Cache-Related Issues

1. **New entities not appearing**: 
   - If `enable_cache: true`, wait up to 30 seconds or restart the bot
   - If `enable_cache: false`, entities should appear immediately
   
2. **Deleted entities still showing**:
   - If `enable_cache: true`, wait up to 30 seconds or restart the bot
   - If `enable_cache: false`, entities should disappear immediately

3. **Performance issues**:
   - If commands are slow, consider setting `enable_cache: true`
   - Check network latency to your Home Assistant instance

### Wake on LAN Issues

1. **No wake buttons found**: 
   - Verify you have Wake on LAN integration configured in Home Assistant
   - Check that devices are configured as buttons (not switches)
   - Look for entity IDs starting with `button.` containing "wake" or "wol"

2. **Wake signal not working**:
   - Ensure target device supports Wake on LAN
   - Check network configuration (same subnet, firewall rules)
   - Verify MAC address is correct in Home Assistant configuration

### Connection Monitoring Issues

1. **No ping sensors found**:
   - Verify you have Ping(ICMP) integration configured in Home Assistant
   - Check that devices are configured as binary sensors
   - Look for entity IDs starting with `binary_sensor.` containing "ping"

### Debugging

Check the bot logs for detailed error messages:

```
docker compose logs -f simplex-bot | grep homeassistant
```

Look for cache status messages:
```
Home Assistant API caching: enabled/disabled
```

## Examples

Here are some real-world usage examples:

```
# Turn on living room lights
!ha light living on

# Set bedroom temperature
!ha climate bedroom 70

# Check all sensor readings
!sensors

# Run bedtime automation
!ha automation bedtime

# Get overall status
!ha status

# Check network connectivity
!ha connections

# Wake up computer
!ha wake desktop

# Manage todo lists
!ha todos
!ha todo shopping add milk
!ha todo shopping done bread

# Turn off all switches (list first, then control individually)
!switches
!ha switch fan off
!ha switch tv off
```

## Supported Entity Types

The plugin currently supports:

- **Lights** (`light.*`) - On/off control with smart alias matching
- **Switches** (`switch.*`) - On/off control with smart alias matching
- **Sensors** (`sensor.*`) - Read-only status and values
- **Climate** (`climate.*`) - Temperature control and status
- **Automations** (`automation.*`) - Trigger execution
- **Binary Sensors** (`binary_sensor.*`) - Connection monitoring (Ping/ICMP sensors)
- **Buttons** (`button.*`) - Wake on LAN and other button actions
- **Todo Lists** (`todo.*`) - Complete todo list management with item operations

### Smart Alias System

The plugin includes an intelligent alias system that automatically generates short, easy-to-use aliases from entity names:

- **Entity ID parsing**: `light.living_room_lamp` → aliases: `["living", "room", "lamp"]`
- **Friendly name parsing**: "Kitchen Counter Light" → aliases: `["kitchen", "counter"]`
- **Partial matching**: You can use `!ha light kitchen on` instead of the full name
- **Case insensitive**: `Kitchen`, `kitchen`, and `KITCHEN` all work

This makes controlling devices much easier - no need to remember exact entity names!

Additional entity types can be added by extending the plugin code.

## Integration Notes

This plugin is designed to work with the Universal Bot Framework and supports:

- **SimpleX Chat** - Full functionality
- **Matrix** - Full functionality
- **Discord/Telegram** - Can be added with appropriate adapters

The plugin uses async/await patterns and is thread-safe for concurrent access.