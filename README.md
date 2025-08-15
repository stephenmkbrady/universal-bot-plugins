# Universal Bot Plugins

A collection of universal plugins for the Universal Chat Bot Framework. These plugins work across multiple bot platforms using a 100% decoupled plugin architecture.

🔗 **Repository**: https://github.com/stephenmkbrady/universal-bot-plugins  
⚠️ **Required**: The bot framework requires platform plugins to function

## 🔌 Available Plugins

- **core** - Essential bot commands (ping, uptime, plugin management) 
- **ai** - AI-powered features (magic 8-ball, advice, content generation with message context)
- **youtube** - YouTube video processing, summarization, and Q&A
- **homeassistant** - Home Assistant integration and control
- **loupe** - Website monitoring and content tracking
- **simplex** - ⚠️ **REQUIRED** Platform plugin for SimpleX Chat integration
- **stt_openai** - Speech-to-text processing using OpenAI Whisper
- **example** - Template plugin for developers and testing

## 📋 Plugin Commands & Features

### Core Plugin Commands
- `!ping` - Test bot responsiveness
- `!uptime` - Show how long the bot has been running
- `!plugins` - List all loaded plugins with status
- `!reload <plugin>` - Manually reload a specific plugin
- `!enable <plugin>` - Enable a disabled plugin
- `!disable <plugin>` - Disable a plugin (core cannot be disabled)
- `!start <plugin>` - Start a plugin
- `!stop <plugin>` - Stop a plugin
- `!status` - Show overall bot status
- `!platform` - Show platform-specific information
- `!commands` - List all available commands across plugins
- `!container <action>` - Manage containerized plugins
- `!containers` - List container status

**Features:**
- Universal bot management commands
- Hot plugin reloading
- Platform detection and information
- Container management for advanced plugins

### Bot Core Commands
- `!help` - Show comprehensive help with bot information and all available plugin commands

### AI Plugin Commands
- `!8ball <question>` - Magic 8-ball with NIST randomness and AI responses
- `!advice [topic]` - Get AI-generated advice on any topic
- `!advise [topic]` - Alias for advice command
- `!bible [topic]` - Get relevant Bible verses with explanations
- `!song [theme]` - Generate custom songs about any theme
- `!nist` - Show current NIST Randomness Beacon value
- `!ai <question>` - Ask the AI assistant anything
- `!ask [options] <question>` - Ask AI assistant with message context
- `!msghistory` - Debug message history storage

**Advanced Context Usage:**
- `!ask -m 1 <question>` - Use the last 1 message as context
- `!ask -m 1-3 <question>` - Use last 3 messages as context
- `!ask -m 1,4,6 <question>` - Use specific message indices
- `!ask -m 2-5,8 <question>` - Use ranges and specific messages

**Features:**
- Integration with NIST Randomness Beacon for true randomness
- Multiple AI models via OpenRouter API
- Message context awareness with flexible selection
- Bible verse recommendations with explanations
- Creative content generation (songs, advice)
- Configurable token limits and API timeouts
- Rolling message history with configurable limits

### YouTube Plugin Commands
- `!youtube <url>` - Process and summarize YouTube videos with AI
- `!yt <url>` - Alias for the youtube command
- `!video <url>` - Alternative alias for video processing
- `!youtube <question>` - Ask questions about the last processed video
- `!summary` - Show information about the last processed video
- `!summary <question>` - Ask specific questions about the last video
- `!ytconfig` - Show YouTube plugin configuration

**Features:**
- Automatic subtitle extraction from YouTube videos
- AI-powered video summarization using OpenRouter
- Q&A functionality for processed videos
- Support for multiple subtitle languages
- Per-chat video history and caching
- Configurable processing options

### Home Assistant Plugin Commands
- `!ha <command>` - General Home Assistant commands
- `!homeassistant <command>` - Full plugin name alias
- `!lights [action]` - Control smart lights
- `!switches [action]` - Control smart switches
- `!sensors` - View sensor data
- `!climate [action]` - Control climate systems
- `!automation [action]` - Manage automations
- `!entities` - List available entities

**Features:**
- Full Home Assistant API integration
- Control lights, switches, climate, and sensors
- Automation management
- Entity discovery and status monitoring
- Secure authentication with HA tokens

### Loupe Plugin Commands  
- `!loupe` - Show configured monitoring sites and help
- `!loupe <site_key>` - Manually trigger monitoring for a specific site

**Features:**
- Automated website monitoring and change detection
- HTML to text conversion with configurable selectors
- Diff-based change notifications
- Multi-site configuration with YAML
- Scheduled monitoring with customizable intervals
- Notification delivery to multiple channels

### SimpleX Platform Plugin Commands
- `!invite` - Generate invitation links
- `!contacts` - List bot contacts
- `!groups` - List bot groups
- `!debug` - Show platform debug information
- `!admin` - Show admin information
- `!reload_admin` - Reload admin configuration
- `!stats` - Show platform statistics
- `!whoami` - Show user identity and admin status

**Features:**
- SimpleX Chat CLI integration
- Contact and group management
- Invitation link generation
- Admin permission system
- Platform-specific debugging tools

### Speech-to-Text Plugin Commands
- `!transcribe` - Transcribe audio files using OpenAI Whisper
- `!stt` - Alias for transcribe command
- `!sttconfig` - Show STT plugin configuration

**Features:**
- OpenAI Whisper integration for speech recognition
- Multiple audio format support
- Configurable transcription options
- Automatic file download and processing

### Example Plugin Commands  
- `!echo <message>` - Echo back user messages with platform info
- `!repeat <message>` - Repeat messages (configurable count)
- `!example` - Show plugin demonstration and capabilities
- `!platform` - Show detailed platform information

**Features:**
- Demonstrates universal plugin architecture
- Platform-aware responses with detailed info
- Configurable demo mode and limits
- Developer template for creating new plugins
- Environment variable configuration support

## 🚀 Supported Platforms

- ✅ **SimpleX Chat** - End-to-end encrypted messaging
- ✅ **Matrix** - Federated messaging protocol

## 💡 Usage Examples

### YouTube Video Processing
```
# Summarize a YouTube video
!youtube https://youtube.com/watch?v=dQw4w9WgXcQ

# Ask questions about the last processed video
!youtube What are the main points discussed?
!youtube How long is this video?
!summary What was the conclusion?
```

### AI Assistant Features
```
# Magic 8-ball with cosmic randomness
!8ball Will I have a good day today?

# Get personalized advice
!advice career development
!advice relationships

# Ask the AI anything
!ai Explain quantum computing in simple terms
!ai What's the weather like on Mars?

# Generate creative content
!song happiness
!bible hope
```

### Bot Management
```
# Check bot status and get help
!help
!plugins
!uptime

# Manage plugins
!reload youtube
!disable example
!enable ai
```

### Development and Testing
```
# Test bot responsiveness
!ping

# Get platform information and help
!platform
!help

# Echo test with platform details
!echo Hello from SimpleX!
```

## 📦 Installation

### As Git Submodule
```bash
git submodule add https://github.com/stephenmkbrady/universal-bot-plugins.git plugins/external
```

### Direct Clone
```bash
git clone https://github.com/stephenmkbrady/universal-bot-plugins.git plugins/external
```

## 🔧 Requirements

Install plugin dependencies:
```bash
pip install -r requirements.txt
```

## 🏗️ Plugin Architecture

Each plugin implements the `UniversalBotPlugin` base class and uses platform-specific adapters to provide consistent functionality across different bot platforms.

### Plugin Structure
```
plugin_name/
├── __init__.py
├── plugin.py              # Entry point
└── universal_plugin.py    # Universal implementation
```

## 🔑 Environment Variables

### Required API Keys
- `OPENROUTER_API_KEY` - For AI and YouTube summarization features

### AI Plugin Configuration
- `AI_MODEL` - AI model to use (default: "cognitivecomputations/dolphin3.0-mistral-24b:free")
- `AI_MAX_MESSAGES` - Message history limit per chat (default: 50)
- `AI_MAX_RECENT_DISPLAY` - Recent messages to show in debug (default: 10)
- `AI_MAX_PREVIEW_LENGTH` - Message preview character limit (default: 100)
- `AI_NIST_UPDATE_INTERVAL` - NIST beacon update interval in seconds (default: 60)
- `AI_API_TIMEOUT` - API request timeout in seconds (default: 10)
- `AI_TOKENS_8BALL` - Token limit for 8-ball responses (default: 100)
- `AI_TOKENS_ADVICE` - Token limit for advice responses (default: 200)
- `AI_TOKENS_BIBLE` - Token limit for Bible responses (default: 300)
- `AI_TOKENS_SONG` - Token limit for song generation (default: 400)
- `AI_TOKENS_AI` - Token limit for general AI responses (default: 500)
- `AI_TOKENS_ASK` - Token limit for context-aware responses (default: 600)

### Example Plugin Configuration
- `EXAMPLE_DEMO_MODE` - Enable demo mode (default: true)
- `EXAMPLE_MAX_ECHO_LENGTH` - Maximum echo message length (default: 1000)
- `EXAMPLE_REPEAT_COUNT` - Number of times to repeat messages (default: 3)

### Other Plugin Configuration
- `NIST_BEACON_URL` - Custom NIST beacon endpoint
- `OPENROUTER_API_URL` - Custom OpenRouter API endpoint

## 🛠️ Creating New Plugins

### Quick Start Guide

1. **Create Plugin Directory**
```bash
mkdir plugins/external/myplugin
cd plugins/external/myplugin
```

2. **Create Required Files**
```bash
touch __init__.py
touch plugin.py
touch universal_plugin.py
```

3. **Implement Universal Plugin** (`universal_plugin.py`)
```python
from typing import List, Optional
from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform

class UniversalMyPlugin(UniversalBotPlugin):
    def __init__(self):
        super().__init__("myplugin")
        self.version = "1.0.0"
        self.description = "My custom plugin description"
        self.supported_platforms = [BotPlatform.SIMPLEX, BotPlatform.MATRIX]
    
    def get_commands(self) -> List[str]:
        return ["mycommand", "myalias"]
    
    async def handle_command(self, context: CommandContext) -> Optional[str]:
        if context.command == "mycommand":
            return f"Hello {context.user_display_name} from {context.platform.value}!"
        return None
```

4. **Create Entry Point** (`plugin.py`)
```python
from .universal_plugin import UniversalMyPlugin

# Export for compatibility
MyPlugin = UniversalMyPlugin
```

5. **Test Your Plugin**
```bash
# Plugin will be automatically discovered and loaded
# Test with: !mycommand
```

### Plugin Development Best Practices

- **Platform Agnostic**: Use `context.platform` to adapt behavior per platform
- **Error Handling**: Always wrap command logic in try/catch blocks  
- **Logging**: Use `self.logger` for debug information
- **Configuration**: Support environment variables for API keys
- **Documentation**: Add docstrings and usage examples
- **Testing**: Test on both SimpleX and Matrix platforms

### Plugin API Reference

**Key Classes:**
- `UniversalBotPlugin` - Base class for all plugins
- `CommandContext` - Contains command information and user context
- `BotPlatform` - Enum for supported platforms (SIMPLEX, MATRIX)

**Required Methods:**
- `get_commands()` - Return list of command names
- `handle_command(context)` - Process commands and return responses

**Optional Methods:**
- `initialize(adapter)` - Setup plugin with bot adapter
- `cleanup()` - Cleanup when plugin is unloaded

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your plugin using the universal architecture
4. Add tests and documentation
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details.