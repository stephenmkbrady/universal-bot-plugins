# Complete Loupe Management Commands

This document provides a comprehensive guide to all available Loupe commands for complete site and monitoring management.

## Basic Commands

### View and Information
```bash
!loupe                           # Show all configured sites
!loupe list                      # List all available sites  
!loupe <site_name>              # Scrape a specific site
!loupe reload                   # Reload configuration
```

### Monitoring Status
```bash
!loupe monitor                  # Show monitoring status
!loupe status                   # Show monitoring status (alias)
!loupe notifications            # Show recent change notifications
```

## Site Management Commands

### Add/Remove Sites
```bash
# Add new site
!loupe add-site techcrunch https://techcrunch.com "TechCrunch News"

# Remove site completely (stops monitoring, removes all data)
!loupe remove-site techcrunch
```

### Edit Site Properties
```bash
# Edit site URL
!loupe edit-site techcrunch url https://techcrunch.com/latest

# Edit site display name  
!loupe edit-site techcrunch name "TechCrunch Latest"

# Edit site description
!loupe edit-site techcrunch description "Latest technology news and startup updates"
```

## Selector Management Commands

### View Selectors
```bash
# Show all selectors for a site
!loupe selectors techcrunch
```

### Add/Edit/Remove Selectors
```bash
# Add CSS selectors
!loupe add-selector techcrunch headlines "h2.post__title > a"
!loupe add-selector techcrunch summaries ".post-excerpt p"
!loupe add-selector techcrunch dates ".post__date"

# Edit existing selector
!loupe edit-selector techcrunch headlines "h1.post-title a"

# Remove selector
!loupe remove-selector techcrunch dates
```

### Test Selectors
```bash
# Test existing selector against live site
!loupe test-selector techcrunch headlines

# Try new selector without saving (for development)
!loupe try-selector techcrunch "h3.article-title"
```

## Monitoring Management Commands

### Enable/Disable Monitoring
```bash
# Enable monitoring with default interval (1 hour)
!loupe enable techcrunch

# Enable monitoring with custom interval (30 minutes = 1800 seconds)
!loupe enable techcrunch 1800

# Disable monitoring (removes all monitoring settings)
!loupe disable techcrunch
```

### Interval Management
```bash
# Change monitoring interval (15 minutes = 900 seconds)
!loupe interval techcrunch 900

# Change to 2 hours (7200 seconds)
!loupe interval techcrunch 7200
```

### Notification Target Management
```bash
# Add notification targets
!loupe add-group techcrunch "Tech Team"
!loupe add-group techcrunch "News Alerts"
!loupe add-user techcrunch alice
!loupe add-user techcrunch bob

# Remove notification targets
!loupe remove-group techcrunch "News Alerts"
!loupe remove-user techcrunch alice
```

### Diff System Management
```bash
# Set diff mode for a site
!loupe diff-mode techcrunch lines       # Show only changed lines (default)
!loupe diff-mode techcrunch full        # Show complete new content
!loupe diff-mode techcrunch disabled    # No change notifications

# View diff configuration
!loupe diff-config techcrunch
```

### Testing and Debugging
```bash
# Test monitoring and notifications manually
!loupe test techcrunch
```

## Complete Workflow Examples

### Example 1: Setting up a new news site
```bash
# 1. Add the site
!loupe add-site devto https://dev.to "Dev.to Articles"

# 2. Add CSS selectors for content extraction
!loupe add-selector devto titles "h3.crayons-story__title > a"
!loupe add-selector devto authors ".crayons-story__secondary .crayons-link"
!loupe add-selector devto tags ".crayons-story__tags .crayons-tag"

# 3. Test selectors to make sure they work
!loupe test-selector devto titles

# 4. Enable monitoring every 2 hours
!loupe enable devto 7200

# 5. Set up notifications
!loupe add-group devto "Development Team"
!loupe add-user devto developer1

# 6. Test the complete system
!loupe test devto

# 7. Configure diff mode (optional)
!loupe diff-mode devto lines

# 8. Check monitoring status
!loupe monitor
```

### Example 2: Modifying an existing site
```bash
# View current selectors
!loupe selectors hacker_news

# Update a selector that's not working well
!loupe edit-selector hacker_news stories ".titleline > a"

# Test the updated selector
!loupe test-selector hacker_news stories

# Add a new selector for metadata
!loupe add-selector hacker_news scores ".subtext .score"

# Change monitoring interval to 15 minutes
!loupe interval hacker_news 900

# Add new notification target
!loupe add-group hacker_news "HN Alerts"

# Configure diff mode for better change tracking
!loupe diff-mode hacker_news lines
!loupe diff-config hacker_news
```

### Example 3: Experimenting with selectors
```bash
# Try different selectors without saving them
!loupe try-selector reddit_python ".thing .title a"
!loupe try-selector reddit_python "article h3 a[data-click-id='body']"
!loupe try-selector reddit_python ".Post h3 a"

# When you find one that works, save it
!loupe add-selector reddit_python post_titles "article h3 a[data-click-id='body']"

# Test the saved selector
!loupe test-selector reddit_python post_titles
```

### Example 4: Complete site cleanup
```bash
# View what's configured
!loupe selectors old_site
!loupe monitor

# Remove specific selectors first if needed
!loupe remove-selector old_site outdated_selector

# Disable monitoring (removes intervals and notification targets)
!loupe disable old_site

# Finally remove the entire site
!loupe remove-site old_site
```

## Advanced Usage Tips

### CSS Selector Development
1. Use browser developer tools (F12) to find element selectors
2. Test selectors with `!loupe try-selector` before saving
3. Use specific selectors to avoid false matches
4. Test after saving with `!loupe test-selector`

### Monitoring Best Practices
1. Start with longer intervals (1-2 hours) to avoid rate limiting
2. Add notification targets before enabling monitoring
3. Test with `!loupe test` to verify the complete workflow
4. Monitor `!loupe notifications` to see change history

### Site Organization
- Use descriptive site IDs: `techcrunch_startup`, `hn_frontpage`, `reddit_python`
- Use clear selector names: `headlines`, `article_links`, `post_titles`
- Set meaningful display names and descriptions

## Error Handling

Common errors and solutions:
- **"Site not found"**: Check `!loupe list` for correct site ID
- **"Selector not found"**: Check `!loupe selectors <site>` for available selectors  
- **"No elements found"**: Selector may be incorrect, use browser dev tools to verify
- **"HTTP error"**: Site may be down or blocking requests
- **"Invalid interval"**: Minimum interval is 60 seconds

All configuration changes are automatically saved and persistent across bot restarts.