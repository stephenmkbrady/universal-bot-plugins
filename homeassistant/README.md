# Home Assistant Plugin

This plugin provides Home Assistant integration for the Universal Bot Framework, allowing you to control and monitor your Home Assistant instance via chat commands.

## Features

- **Device Control**: Turn lights and switches on/off
- **Sensor Monitoring**: Get real-time sensor readings
- **Climate Control**: Set temperatures for thermostats and HVAC systems
- **Automation Triggers**: Run Home Assistant automations
- **Status Monitoring**: Get overview of your entire HA setup
- **Entity Management**: List and inspect all entities

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
```

Or use environment variables:

```bash
export HA_HOST="192.168.1.100"
export HA_PORT="8123" 
export HA_TOKEN="your-long-lived-token"
export HA_SSL="false"
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

## Troubleshooting

### Connection Issues

1. **Check Network**: Ensure the bot can reach your HA instance
2. **Check Token**: Verify your long-lived access token is correct
3. **Check URL**: Make sure host/port/SSL settings are correct

### Command Issues

1. **Entity Names**: Use partial names - the plugin will match against entity IDs and friendly names
2. **Case Insensitive**: All commands and entity names are case-insensitive
3. **Permissions**: Check if your token has the necessary permissions

### Debugging

Check the bot logs for detailed error messages:

```
docker compose logs -f simplex-bot | grep homeassistant
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

# Turn off all switches (list first, then control individually)
!switches
!ha switch fan off
!ha switch tv off
```

## Supported Entity Types

The plugin currently supports:

- **Lights** (`light.*`) - On/off control
- **Switches** (`switch.*`) - On/off control  
- **Sensors** (`sensor.*`) - Read-only status
- **Climate** (`climate.*`) - Temperature control
- **Automations** (`automation.*`) - Trigger execution

Additional entity types can be added by extending the plugin code.

## Integration Notes

This plugin is designed to work with the Universal Bot Framework and supports:

- **SimpleX Chat** - Full functionality
- **Matrix** - Full functionality
- **Discord/Telegram** - Can be added with appropriate adapters

The plugin uses async/await patterns and is thread-safe for concurrent access.