# Universal Bot Plugins

A collection of universal plugins that work across multiple bot platforms (Matrix, SimpleX) using a unified plugin architecture.

## 🔌 Available Plugins

### Core Plugins
- **core** - Essential bot commands (help, status, ping, plugin management)
- **example** - Template plugin for developers

### Feature Plugins  
- **youtube** - YouTube video processing, summarization, and Q&A
- **ai** - AI-powered features (magic 8-ball, advice, content generation)
- **auth** - PIN-based authentication system
- **database** - Database interaction and management

## 📋 Plugin Commands & Features

### Core Plugin Commands
- `!help` - Show comprehensive help with all available commands
- `!status` - Display bot status, uptime, and plugin health
- `!ping` - Test bot responsiveness
- `!uptime` - Show how long the bot has been running
- `!plugins` - List all loaded plugins with status
- `!reload <plugin>` - Manually reload a specific plugin
- `!enable <plugin>` - Enable a disabled plugin
- `!disable <plugin>` - Disable a plugin (core cannot be disabled)
- `!platform` - Show platform-specific information
- `!commands` - List all available commands across plugins
- `!info` - Show detailed bot information

### YouTube Plugin Commands
- `!youtube <url>` - Process and summarize YouTube videos with AI
- `!yt <url>` - Alias for the youtube command
- `!video <url>` - Alternative alias for video processing
- `!youtube <question>` - Ask questions about the last processed video
- `!summary` - Show information about the last processed video
- `!summary <question>` - Ask specific questions about the last video

**Features:**
- Automatic subtitle extraction from YouTube videos
- AI-powered video summarization using OpenRouter
- Q&A functionality for processed videos
- Support for multiple subtitle languages
- Per-chat video history and caching

### AI Plugin Commands
- `!8ball <question>` - Magic 8-ball with NIST randomness and AI responses
- `!advice [topic]` - Get AI-generated advice on any topic
- `!advise [topic]` - Alias for advice command
- `!bible [topic]` - Get relevant Bible verses with explanations
- `!song [theme]` - Generate custom songs about any theme
- `!nist` - Show current NIST Randomness Beacon value
- `!ai <question>` - Ask the AI assistant anything
- `!ask <question>` - Alias for AI assistant

**Features:**
- Integration with NIST Randomness Beacon for true randomness
- Multiple AI models via OpenRouter API
- Context-aware responses
- Bible verse recommendations with explanations
- Creative content generation (songs, advice)

### Auth Plugin Commands
- `!pin` - Request a new authentication PIN for the current room
- `!request` - Alias for PIN request
- `!auth <pin>` - Verify authentication using a PIN
- `!verify <pin>` - Alias for authentication verification

**Features:**
- Room-based PIN authentication
- Secure API integration for PIN verification
- User access control for database features
- Platform-agnostic authentication system

### Example Plugin Commands  
- `!echo <message>` - Echo back user messages with platform info
- `!repeat <message>` - Repeat messages multiple times
- `!example` - Show plugin demonstration and capabilities

**Features:**
- Demonstrates universal plugin architecture
- Platform-aware responses
- Configurable demo mode
- Developer template for creating new plugins

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
# Check bot status
!status
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

# Get platform information
!platform
!info

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

Some plugins require API keys:

- `OPENROUTER_API_KEY` - For AI and YouTube summarization features
- `DATABASE_API_URL` - For database plugin functionality  
- `DATABASE_API_KEY` - For database authentication

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