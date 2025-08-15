# SimpleX Platform Plugin

> **"One plugin to rule the platform"** - *The bridge between universal plugins and SimpleX Chat*

## 🎯 Purpose

The SimpleX plugin serves as the **platform-specific management layer** for SimpleX Chat operations. While other plugins remain platform-agnostic and cross-compatible, this plugin embraces SimpleX coupling to provide direct access to platform features that universal plugins shouldn't need to know about.

## 🏗️ Architecture Role

This plugin acts as the **service provider** and **administrative interface** that:

- ✅ **Exposes SimpleX Features** - Makes platform-specific functionality available
- ✅ **Handles Admin Operations** - Manages bot permissions and access control  
- ✅ **Provides Debug Tools** - Low-level platform diagnostics
- ✅ **Manages Connections** - Contact/group relationship management
- ✅ **Serves Other Plugins** - Provides platform services so other plugins stay universal

## 📋 Commands

### 🔗 Invite Management (`!invite`)
- `!invite generate` - Create one-time connection invites
- `!invite list` - Show pending invites  
- `!invite revoke <id>` - Cancel specific invites
- `!invite stats` - Display invite statistics

### 👥 Contact Management (`!contacts`)
- `!contacts list` - List all bot contacts
- `!contacts info <name>` - Get detailed contact information

### 👨‍👩‍👧‍👦 Group Management (`!groups`)
- `!groups list` - List all groups bot is in
- `!groups info <name>` - Get group details
- `!groups invite <name>` - Generate group invite links

### 🔧 Debug Tools (`!debug`)
- `!debug websocket` - WebSocket connection diagnostics
- `!debug ping` - Test SimpleX CLI connectivity  
- `!debug restart` - Force restart SimpleX CLI process

### 👑 Admin Management (`!admin`)
- `!admin list` - Show all configured admins
- `!admin add <user>` - Grant admin privileges
- `!admin remove <user>` - Revoke admin access
- `!admin permissions <user>` - Check user permissions
- `!admin reload` - Reload admin configuration

### 📊 System Stats (`!stats`)
- Bot runtime statistics
- Platform-specific metrics
- Connection health information

## 🌉 Platform Service Bridge

The SimpleX plugin works **with** the platform service architecture to provide:

- **Contact Data** through `ContactManagementService`
- **Group Information** via `GroupManagementService`  
- **Invite Generation** through `InviteManagementService`
- **Message History** via `MessageHistoryService`
- **File Operations** through `FileService`

## 🎭 Design Philosophy

**Platform Coupling by Design** - This plugin intentionally couples with SimpleX Chat features so that all other plugins (YouTube, AI, HomeAssistant, etc.) can remain beautifully separated and cross-platform compatible.

When other plugins need SimpleX-specific functionality, they access it through the platform service layer rather than direct bot access, keeping the architecture clean and maintainable.

## 🔒 Admin Requirements

Most commands require admin privileges. Admins are configured in `admin_config.yml` and can be managed through the `!admin` commands.

## 🧪 Testing & Debugging

Use the `!debug` commands to troubleshoot platform connectivity issues, WebSocket problems, or CLI communication failures.

---

*Part of the Universal Bot Plugin Architecture - Designed to keep the platform messy so other plugins can stay clean! 🧹*