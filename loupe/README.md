# Loupe Plugin

A comprehensive web scraper and monitoring plugin with intelligent change detection and notifications.

## 🚀 Features

- 🔍 **Smart Web Scraping**: Extract content using CSS selectors from any website
- 📊 **Automated Monitoring**: Track websites for changes with configurable intervals  
- 🔄 **Intelligent Diff System**: Generic line-based change detection (works with any content type)
- 🔔 **Flexible Notifications**: Send updates to specific groups and users
- ⚙️ **Complete Management**: Add, edit, and remove sites without touching config files
- 🎯 **CSS Selector Testing**: Test selectors against live websites before saving
- 🛠️ **Dynamic Configuration**: All settings managed through chat commands
- 📝 **Clean Text Output**: Convert HTML to readable text automatically

## 📚 Quick Start

### Basic Commands
```bash
!loupe                           # Show help and configured sites
!loupe <site_name>              # Scrape a specific site manually
!loupe list                     # List all sites  
!loupe monitor                  # Show monitoring status
!loupe notifications            # Show recent change alerts
```

### Add Your First Site
```bash
# Add a website (automatically configures notifications for you)
!loupe add-site hn https://news.ycombinator.com "Hacker News"

# Add CSS selectors to extract content  
!loupe add-selector hn titles ".athing .titleline > a"
!loupe add-selector hn scores ".score"

# Test that selectors work
!loupe test-selector hn titles

# Enable monitoring (check every 30 minutes)
!loupe enable hn 1800

# Test the complete system
!loupe test hn
```

## 🎯 Site Management

### Adding and Removing Sites
```bash
# Add new sites
!loupe add-site tech_blog https://techblog.com "Tech Blog"
!loupe add-site news_site https://news.com "Daily News"

# Remove sites completely  
!loupe remove-site old_site

# Edit site properties
!loupe edit-site tech_blog url https://techblog.com/latest
!loupe edit-site tech_blog name "Updated Tech Blog"
```

### CSS Selector Management
```bash
# View current selectors
!loupe selectors tech_blog

# Add selectors for content extraction
!loupe add-selector tech_blog headlines "h1.post-title"
!loupe add-selector tech_blog summaries ".post-excerpt p"
!loupe add-selector tech_blog dates ".post-date"

# Test selectors against live site
!loupe test-selector tech_blog headlines

# Try new selectors without saving (for development)
!loupe try-selector tech_blog "h2.article-title"

# Edit existing selectors
!loupe edit-selector tech_blog headlines "h1.title a"

# Remove selectors
!loupe remove-selector tech_blog dates
```

## 📊 Monitoring & Notifications

### Monitoring Control
```bash
# Enable monitoring with default interval (1 hour)
!loupe enable tech_blog

# Enable with custom interval (15 minutes = 900 seconds)  
!loupe enable tech_blog 900

# Disable monitoring
!loupe disable tech_blog

# Change monitoring interval
!loupe interval tech_blog 1800  # 30 minutes
```

### Notification Targets
```bash
# Add notification targets
!loupe add-group tech_blog "Development Team"
!loupe add-group tech_blog "Tech Alerts"
!loupe add-user tech_blog alice
!loupe add-user tech_blog bob

# Remove notification targets
!loupe remove-group tech_blog "Tech Alerts"
!loupe remove-user tech_blog alice

# Test notifications manually
!loupe test tech_blog
```

## 🔄 Intelligent Diff System

The plugin features a content-agnostic diff system that works with any website type - news sites, blogs, forums, documentation, etc.

### Diff Modes
```bash
# Set diff mode for a site
!loupe diff-mode tech_blog lines     # Show only changed lines (default)
!loupe diff-mode tech_blog full      # Show complete new content  
!loupe diff-mode tech_blog disabled  # No change notifications

# View diff configuration
!loupe diff-config tech_blog
```

### Example Diff Output (Generic Format)
```
🔔 Tech Blog Updated

➕ Added (2):
• New Framework Released: FastAPI 2.0 Now Available
• Tutorial: Building Scalable Applications with Docker

➖ Removed (1):
• Outdated Post: Legacy Python 2.7 Migration Guide

📊 Summary: 2 added, 1 removed
```

### Advanced Diff Configuration

Edit `config.yml` for advanced diff settings:

```yaml
sites:
  tech_blog:
    diff_mode: lines                    # lines, full, or disabled
    max_diff_lines: 20                  # Limit output for large changes
    major_change_threshold: 0.5         # When to show summary vs detailed diff
    ignore_patterns:                    # Regex patterns to filter noise
      - '\(\d+ points\)'                # Ignore vote counts
      - 'Posted \d{4}-\d{2}-\d{2}:'     # Ignore date prefixes
```

## 🛠️ CSS Selectors Guide

### Selector Types
| Selector Type | Example | Description |
|---------------|---------|-------------|
| **Class** | `.post-title` | Elements with CSS class |
| **ID** | `#main-content` | Element with specific ID |
| **Tag** | `h1`, `a`, `div` | HTML tag elements |
| **Attribute** | `[href*="blog"]` | Elements with attributes |
| **Combined** | `article h1 a` | Links in h1s inside articles |
| **Child** | `.post > h2` | Direct child elements |
| **Descendant** | `.content a` | All descendant elements |

### Development Workflow
1. **Inspect HTML**: Use browser developer tools (F12) to examine page structure
2. **Test Selectors**: Use `document.querySelectorAll('selector')` in browser console
3. **Try in Loupe**: Use `!loupe try-selector site "selector"` to test without saving
4. **Save Working Selectors**: Use `!loupe add-selector site name "selector"`
5. **Verify Results**: Use `!loupe test-selector site name` to confirm

## 📖 Complete Command Reference

### Information & Status
```bash
!loupe                          # Help and site overview
!loupe list                     # List all sites
!loupe monitor                  # Monitoring status  
!loupe status                   # Monitoring status (alias)
!loupe notifications            # Recent change alerts
!loupe reload                   # Reload configuration
```

### Site Management
```bash
!loupe add-site <id> <url> <name>           # Add new site
!loupe remove-site <id>                     # Remove site completely
!loupe edit-site <id> <field> <value>      # Edit site properties
```

### Selector Management  
```bash
!loupe selectors <site>                     # Show all selectors
!loupe add-selector <site> <name> <css>     # Add CSS selector
!loupe edit-selector <site> <name> <css>    # Edit existing selector
!loupe remove-selector <site> <name>        # Remove selector
!loupe test-selector <site> <name>          # Test existing selector
!loupe try-selector <site> <css>            # Try selector without saving
```

### Monitoring Control
```bash
!loupe enable <site> [interval]             # Enable monitoring
!loupe disable <site>                       # Disable monitoring  
!loupe interval <site> <seconds>            # Set check interval
!loupe test <site>                          # Test monitoring manually
```

### Notification Management
```bash
!loupe add-group <site> <group>             # Add notification group
!loupe remove-group <site> <group>          # Remove notification group
!loupe add-user <site> <user>               # Add notification user  
!loupe remove-user <site> <user>            # Remove notification user
```

### Diff Configuration
```bash
!loupe diff-mode <site> <mode>              # Set diff mode (lines/full/disabled)
!loupe diff-config <site>                   # Show diff settings
```

## 📋 Example Workflows

### Setting Up News Site Monitoring
```bash
# 1. Add the site
!loupe add-site devto https://dev.to "Dev.to Articles"

# 2. Add content selectors
!loupe add-selector devto titles "h3.crayons-story__title > a"  
!loupe add-selector devto authors ".crayons-story__secondary .crayons-link"

# 3. Test selectors work
!loupe test-selector devto titles

# 4. Enable monitoring every 2 hours
!loupe enable devto 7200

# 5. Add notification targets
!loupe add-group devto "Development Team"

# 6. Test complete system
!loupe test devto
```

### Updating Existing Site
```bash
# Check current setup
!loupe selectors hacker_news
!loupe diff-config hacker_news

# Update selector that's not working
!loupe edit-selector hacker_news stories ".titleline > a"
!loupe test-selector hacker_news stories  

# Change to faster monitoring
!loupe interval hacker_news 900  # 15 minutes

# Switch to line-based diffs
!loupe diff-mode hacker_news lines
```

## 🔧 Configuration File Structure

```yaml
sites:
  site_name:
    url: https://example.com                 # Website URL
    name: "Display Name"                     # Human-readable name  
    description: "Site description"          # Optional description
    monitor: false                           # Enable/disable monitoring
    interval: 3600                          # Check interval in seconds
    notify_groups: ["Group 1", "Group 2"]   # Groups to notify
    notify_users: ["user1", "user2"]        # Users to notify
    diff_mode: lines                        # lines, full, or disabled
    max_diff_lines: 20                      # Max lines in diff output
    major_change_threshold: 0.5             # Threshold for major changes
    ignore_patterns: []                     # Regex patterns to ignore
    selectors:                              # CSS selectors for content
      selector_name: "css.selector"
      another_selector: ".other-selector"
```

## 🚨 Smart Auto-Configuration

When you add a new site with `!loupe add-site`, the plugin automatically:

- ✅ **Sets monitoring to disabled** by default (use `!loupe enable` when ready)
- 🔔 **Configures notifications** to send to you and your current group
- ⚙️ **Sets sensible defaults**: 1-hour intervals, line-based diffs
- 🎯 **Ready for selectors**: Just add CSS selectors and enable monitoring

## 🔍 Troubleshooting

### Common Issues
- **"Site not found"**: Check `!loupe list` for correct site ID
- **"Selector not found"**: Use `!loupe selectors <site>` to see available selectors
- **"No elements found"**: CSS selector may be incorrect, use browser dev tools to verify
- **"HTTP error"**: Website may be down or blocking requests  
- **"Invalid interval"**: Minimum interval is 60 seconds

### Monitoring Not Working?
1. Check monitoring status: `!loupe monitor`
2. Verify selectors work: `!loupe test-selector <site> <selector>`
3. Test full monitoring: `!loupe test <site>`
4. Check notification targets: `!loupe <site>` (shows configured targets)
5. Review recent alerts: `!loupe notifications`

## 📦 Dependencies

The plugin automatically installs these dependencies:

- `aiohttp` - Async HTTP client for web requests
- `beautifulsoup4` - HTML parsing and element selection  
- `html2text` - Convert HTML to clean text
- `pyyaml` - Configuration file parsing
- `lxml` - Fast XML/HTML parsing backend

## 🎯 Best Practices

### Site Organization
- Use descriptive site IDs: `techcrunch_startup`, `hn_frontpage`, `reddit_python`
- Use clear selector names: `headlines`, `article_links`, `post_titles`
- Set meaningful display names and descriptions

### Monitoring Strategy  
- Start with longer intervals (1-2 hours) to avoid rate limiting
- Add notification targets before enabling monitoring
- Test selectors thoroughly with `!loupe try-selector` before saving
- Use `!loupe test` to verify complete workflow

### Performance Tips
- Limit selectors to essential content only
- Use specific selectors to avoid false matches
- Set reasonable diff thresholds for busy sites
- Monitor `!loupe notifications` to track system health

---

**Need help?** Run `!loupe` for interactive help, or see `COMPLETE_COMMANDS.md` for comprehensive command documentation.