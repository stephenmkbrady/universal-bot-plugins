# Rumble Plugin

Monitors Rumble channels for new livestreams and videos using Puppeteer web scraping.

## Features

- 🔍 Detects new livestreams and videos on Rumble channels
- 📸 Takes screenshots for debugging
- 💾 Stores previous state to detect changes
- 🚨 Exit codes indicate if changes were found
- 🐳 Docker-based for easy deployment

## Usage

### One-time Check
```bash
docker compose up rumble-scraper
```

### Continuous Monitoring (every 5 minutes)
```bash
docker compose --profile monitor up rumble-monitor
```

### Custom Channel
```bash
RUMBLE_CHANNEL_URL=https://rumble.com/c/yourchannel/livestreams docker compose up rumble-scraper
```

## Exit Codes

- `0`: No changes detected
- `1`: Changes detected (new/removed content)
- `2`: Error occurred

## Files Created

- `rumble_data.json`: Stores previous state for comparison
- `screenshots/`: Debug screenshots with timestamps
- `package.json`: Auto-generated Node.js dependencies

## How It Works

1. **Scrapes** the Rumble channel page using Puppeteer
2. **Extracts** livestream/video data (title, URL, timestamps)
3. **Compares** with previously stored data
4. **Reports** new or removed content
5. **Saves** current state for next check

## Debugging

Check screenshots in `screenshots/` folder to see what the scraper is detecting on the page.

## Channel URL Format

- Livestreams: `https://rumble.com/c/channelname/livestreams`
- All videos: `https://rumble.com/c/channelname`
- User profile: `https://rumble.com/user/username`