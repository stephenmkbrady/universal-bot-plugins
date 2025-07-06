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

## 🚀 Supported Platforms

- ✅ **SimpleX Chat** - End-to-end encrypted messaging
- ✅ **Matrix** - Federated messaging protocol

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

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your plugin using the universal architecture
4. Add tests and documentation
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details.