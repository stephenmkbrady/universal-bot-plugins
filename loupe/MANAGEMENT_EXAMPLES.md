# Loupe Management Commands Examples

This document shows practical examples of using the dynamic management commands.

## Enable Monitoring

```bash
# Enable monitoring with default interval (1 hour)
!loupe enable reddit_python

# Enable monitoring with custom interval (30 minutes = 1800 seconds)  
!loupe enable reddit_python 1800

# Enable monitoring with custom interval (2 hours = 7200 seconds)
!loupe enable bbc_tech 7200
```

## Manage Notification Targets

```bash
# Add groups to receive notifications
!loupe add-group reddit_python "Python Developers"
!loupe add-group reddit_python "Tech Team"

# Add users to receive notifications  
!loupe add-user reddit_python alice
!loupe add-user reddit_python bob

# Remove notification targets
!loupe remove-group reddit_python "Tech Team"
!loupe remove-user reddit_python alice
```

## Manage Intervals

```bash
# Change monitoring interval
!loupe interval reddit_python 3600  # 1 hour
!loupe interval bbc_tech 1800       # 30 minutes
!loupe interval hacker_news 900     # 15 minutes
```

## Disable Monitoring

```bash
# Disable monitoring (removes all monitoring settings)
!loupe disable reddit_python
```

## View Status and Test

```bash
# View monitoring status for all sites
!loupe monitor

# View recent notifications
!loupe notifications

# Test notifications for a site (triggers immediate check)
!loupe test hacker_news
```

## Complete Workflow Example

```bash
# 1. Enable monitoring for a new site
!loupe enable stackoverflow_python 2700  # 45 minutes

# 2. Add notification targets
!loupe add-group stackoverflow_python "Python Help"
!loupe add-user stackoverflow_python developer1
!loupe add-user stackoverflow_python developer2

# 3. Check status
!loupe monitor

# 4. Test notifications
!loupe test stackoverflow_python

# 5. Adjust interval if needed
!loupe interval stackoverflow_python 1800  # 30 minutes

# 6. Add more targets later
!loupe add-group stackoverflow_python "Senior Devs"

# 7. Remove targets when no longer needed
!loupe remove-user stackoverflow_python developer1

# 8. Disable when no longer needed
!loupe disable stackoverflow_python
```

## Current Monitoring Status

After running the examples above, you can check the current status:

```bash
!loupe monitor
```

This will show something like:
```
🔍 Monitoring Status:

🟢 Hacker News (hacker_news)
   ⏱️ Interval: 1800s (30m)
   📊 Status: Running
   🎯 Notifies: 👥 Cosmic Encabulator, 👥 Tech News, 👤 cosmic, 👤 TestUser
   🕐 Last check: 2025-08-06 19:46:31

🟢 Site Name (kf)
   ⏱️ Interval: 3600s (60m)
   📊 Status: Running
   🎯 Notifies: 👥 Cosmic Encabulator
   🕐 Last check: 2025-08-06 19:46:31

🔴 GitHub Trending (github_trending) - Monitoring disabled
🔴 Reddit r/Python (reddit_python) - Monitoring disabled
🔴 Stack Overflow Python (stackoverflow_python) - Monitoring disabled
🔴 BBC Technology News (bbc_tech) - Monitoring disabled

📈 Total monitored sites: 2/6
```

## Notes

- All configuration changes are automatically saved to `config.yml`
- Monitoring tasks are automatically started/stopped/restarted as needed
- Group names with spaces are supported (use quotes: "My Group Name")
- Minimum interval is 60 seconds
- Changes take effect immediately without needing to restart the bot