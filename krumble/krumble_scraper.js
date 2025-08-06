const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// For Node.js versions < 18, we might need to import fetch
let fetch;
if (typeof globalThis.fetch === 'undefined') {
    try {
        fetch = require('node-fetch');
    } catch (e) {
        // Fallback: use global fetch (Node 18+)
        fetch = globalThis.fetch;
    }
} else {
    fetch = globalThis.fetch;
}

// Constants
const BROWSER_TIMEOUT = 30000;
const CONTENT_LOAD_DELAY = 5000;
const KICK_BROWSER_TIMEOUT = 15000;
const KICK_CONTENT_DELAY = 3000;

const USER_AGENTS = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
];

const BROWSER_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-web-security'
];

// Selectors for different platforms
const RUMBLE_SELECTORS = [
    'article[data-js="videoListing"]',
    '.video-listing-entry',
    '.video-item',
    '[data-testid="video"]',
    '.listing-video',
    '.video-card',
    '.mediaItem',
    '.media-item', 
    '[class*="video"]',
    '[class*="media"]',
    'article',
    '.thumbnail-wrapper',
    '.video-thumbnail'
];

const KICK_SELECTORS = [
    '[data-testid="video-card"]',
    '.video-card',
    '[class*="video"]',
    'a[href*="/video/"]',
    'article'
];

class KrumbleScraper {
    constructor() {
        this.dataDir = path.join(__dirname, 'channel_data');
        
        // Ensure directories exist
        if (!fs.existsSync(this.dataDir)) {
            fs.mkdirSync(this.dataDir, { recursive: true });
        }
        
        // Platform-specific scrapers
        this.scrapers = {
            rumble: this.scrapeRumble.bind(this),
            kick: this.scrapeKick.bind(this)
        };
    }

    detectPlatform(url) {
        if (url.includes('rumble.com')) return 'rumble';
        if (url.includes('kick.com')) return 'kick';
        return 'unknown';
    }

    getChannelDataFile(channelUrl) {
        // Extract platform and channel name for filename
        const platform = this.detectPlatform(channelUrl);
        let channelName = 'unknown';
        
        if (platform === 'rumble') {
            const match = channelUrl.match(/\/c\/([^\/]+)/);
            channelName = match ? match[1] : 'unknown';
        } else if (platform === 'kick') {
            const match = channelUrl.match(/kick\.com\/([^\/]+)/);
            channelName = match ? match[1] : 'unknown';
        }
        
        return path.join(this.dataDir, `${platform}_${channelName}.json`);
    }

    loadPreviousData(channelUrl) {
        try {
            const dataFile = this.getChannelDataFile(channelUrl);
            if (fs.existsSync(dataFile)) {
                const data = fs.readFileSync(dataFile, 'utf8');
                return JSON.parse(data);
            }
        } catch (error) {
            console.log('⚠️  Could not load previous data:', error.message);
        }
        return { livestreams: [], lastCheck: null };
    }

    saveData(data, channelUrl) {
        try {
            const dataFile = this.getChannelDataFile(channelUrl);
            fs.writeFileSync(dataFile, JSON.stringify(data, null, 2));
            
            const platform = this.detectPlatform(channelUrl);
            console.log(`💾 Data saved successfully for ${platform} channel`);
        } catch (error) {
            console.error('❌ Error saving data:', error.message);
        }
    }

    async scrapeRumble(channelUrl) {
        console.log('🟡 Scraping Rumble channel...');
        
        let browser;
        try {
            browser = await puppeteer.launch({
                headless: 'new',
                args: BROWSER_ARGS
            });

            const page = await browser.newPage();
            await page.setUserAgent(USER_AGENTS[2]); // Use desktop Chrome
            
            console.log(`🌐 Navigating to: ${channelUrl}`);
            await page.goto(channelUrl, { 
                waitUntil: 'networkidle2', 
                timeout: BROWSER_TIMEOUT 
            });

            // Wait for content to load
            await new Promise(resolve => setTimeout(resolve, CONTENT_LOAD_DELAY));

            let livestreams = [];
            
            for (const selector of RUMBLE_SELECTORS) {
                try {
                    const elements = await page.$$(selector);
                    if (elements.length > 0) {
                        console.log(`✅ Found ${elements.length} elements with selector: ${selector}`);
                        
                        livestreams = await page.evaluate((sel) => {
                            const elements = document.querySelectorAll(sel);
                            const streams = [];
                            
                            elements.forEach((element, index) => {
                                try {
                                    const titleElement = element.querySelector('h3, .video-item--title, .listing-video--title, [data-js="title"]') ||
                                                        element.querySelector('a[title]');
                                    
                                    const linkElement = element.querySelector('a[href*="/v/"], a[href*="/video/"]') ||
                                                       element.querySelector('a');
                                    
                                    const timeElement = element.querySelector('.video-item--meta time, .listing-video--meta time, time') ||
                                                       element.querySelector('[datetime]');
                                    
                                    const thumbnailElement = element.querySelector('img');
                                    
                                    const title = titleElement ? 
                                                 (titleElement.textContent?.trim() || titleElement.title?.trim() || titleElement.getAttribute('title')) : 
                                                 `Stream ${index + 1}`;
                                    
                                    const url = linkElement ? 
                                               (linkElement.href.startsWith('http') ? linkElement.href : `https://rumble.com${linkElement.href}`) :
                                               null;
                                    
                                    const publishTime = timeElement ? 
                                                       (timeElement.getAttribute('datetime') || timeElement.textContent?.trim()) :
                                                       null;
                                    
                                    const thumbnail = thumbnailElement ? thumbnailElement.src : null;
                                    
                                    const isLive = element.textContent.toLowerCase().includes('live') ||
                                                  element.className.toLowerCase().includes('live') ||
                                                  element.querySelector('[class*="live"], [data-live="true"]');
                                    
                                    if (title && url) {
                                        streams.push({
                                            id: url.split('/').pop() || `stream_${index}`,
                                            title: title,
                                            url: url,
                                            publishTime: publishTime,
                                            thumbnail: thumbnail,
                                            isLive: isLive,
                                            scraped: new Date().toISOString(),
                                            platform: 'rumble'
                                        });
                                    }
                                } catch (err) {
                                    console.error(`Error processing element ${index}:`, err.message);
                                }
                            });
                            
                            return streams;
                        }, selector);
                        
                        if (livestreams.length > 0) {
                            break;
                        }
                    }
                } catch (error) {
                    console.log(`⚠️  Selector ${selector} failed:`, error.message);
                }
            }

            console.log(`📺 Found ${livestreams.length} Rumble items`);
            
            return {
                success: true,
                livestreams: livestreams,
                scrapedAt: new Date().toISOString(),
                url: channelUrl,
                platform: 'rumble'
            };

        } catch (error) {
            console.error('❌ Error during Rumble scraping:', error.message);
            return {
                success: false,
                error: error.message,
                livestreams: [],
                scrapedAt: new Date().toISOString(),
                url: channelUrl,
                platform: 'rumble'
            };
        } finally {
            if (browser) {
                await browser.close();
            }
        }
    }

    async scrapeKick(channelUrl) {
        console.log('🟢 Scraping Kick channel using API approach...');
        
        // Extract channel name from URL
        const channelMatch = channelUrl.match(/kick\.com\/([^\/]+)/);
        if (!channelMatch) {
            return {
                success: false,
                error: 'Invalid Kick.com URL format',
                livestreams: [],
                scrapedAt: new Date().toISOString(),
                url: channelUrl,
                platform: 'kick'
            };
        }
        
        const channelSlug = channelMatch[1];
        console.log(`📺 Fetching data for channel: ${channelSlug}`);
        
        // Try API approach first (proven to work)
        try {
            const apiResult = await this.fetchKickChannelViaAPI(channelSlug);
            if (apiResult.success) {
                console.log(`✅ API approach successful: ${apiResult.livestreams.length} items found`);
                return apiResult;
            } else {
                console.log(`⚠️ API approach failed: ${apiResult.error}, falling back to web scraping`);
            }
        } catch (e) {
            console.log(`❌ API approach error: ${e.message}, falling back to web scraping`);
        }
        
        // Fallback to web scraping (will likely be blocked but worth trying)
        console.log('🌐 Falling back to web scraping approach...');
        return await this.scrapeKickViaBrowser(channelUrl);
    }

    async fetchKickChannelViaAPI(channelSlug) {
        console.log('🔗 Attempting API access for Kick channel...');
        
        const apiEndpoints = [
            // Private API endpoints (most likely to work)
            `https://api.kick.com/private/v1/channels/${channelSlug}`,
            // Public API endpoints (backup)
            `https://kick.com/api/v2/channels/${channelSlug}`,
            `https://kick.com/api/v1/channels/${channelSlug}`,
        ];


        let livestreams = [];
        let channelData = null;

        // Try to get channel info
        for (const endpoint of apiEndpoints) {
            try {
                console.log(`📡 Trying endpoint: ${endpoint}`);
                
                const response = await fetch(endpoint, {
                    headers: {
                        'User-Agent': USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)],
                        'Accept': 'application/json',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                        'Sec-Fetch-Dest': 'empty',
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'same-origin',
                        'Sec-CH-UA': '"Not_A Brand";v="8", "Chromium";v="120"',
                        'Sec-CH-UA-Mobile': '?1',
                        'Sec-CH-UA-Platform': '"Android"'
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    console.log(`✅ Successfully fetched channel data from: ${endpoint}`);
                    channelData = data;
                    break;
                } else {
                    console.log(`❌ Endpoint failed with status: ${response.status}`);
                }
            } catch (error) {
                console.log(`❌ Endpoint error: ${error.message}`);
            }
        }

        if (!channelData) {
            return {
                success: false,
                error: 'Failed to fetch channel data from any API endpoint',
                livestreams: [],
                scrapedAt: new Date().toISOString(),
                platform: 'kick'
            };
        }

        // Extract channel ID for additional endpoints
        const channelId = channelData.id || 
                         channelData.data?.id || 
                         channelData.data?.account?.channel?.id;
        console.log(`📊 Channel ID: ${channelId}, Slug: ${channelSlug}`);

        // Try to get livestream data
        const livestreamEndpoints = [
            `https://api.kick.com/private/v1/channels/${channelSlug}/livestream`,
            `https://kick.com/api/v2/channels/${channelSlug}/livestream`,
            `https://kick.com/api/v1/channels/${channelSlug}/livestream`,
        ];
        
        // Add ID-based endpoints if we have channel ID
        if (channelId) {
            livestreamEndpoints.unshift(`https://api.kick.com/channels/${channelId}/livestream`);
        }

        for (const endpoint of livestreamEndpoints) {
            try {
                console.log(`📡 Trying livestream endpoint: ${endpoint}`);
                
                const response = await fetch(endpoint, {
                    headers: {
                        'User-Agent': USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)],
                        'Accept': 'application/json',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': `https://kick.com/${channelSlug}`
                    }
                });

                if (response.ok) {
                    const livestreamData = await response.json();
                    console.log(`✅ Successfully fetched livestream data from: ${endpoint}`);
                    
                    if (livestreamData && livestreamData.data && livestreamData.data.livestream) {
                        const stream = livestreamData.data.livestream;
                        if (stream.is_live || stream.session_title) {
                            livestreams.push({
                                id: `kick_live_${stream.id || Date.now()}`,
                                title: stream.session_title || `${channelSlug} Live Stream`,
                                url: `https://kick.com/${channelSlug}`,
                                publishTime: stream.created_at || new Date().toISOString(),
                                thumbnail: stream.thumbnail?.url || null,
                                isLive: stream.is_live || false,
                                scraped: new Date().toISOString(),
                                platform: 'kick',
                                viewers: stream.viewer_count || 0
                            });
                        }
                    }
                    break;
                } else {
                    console.log(`❌ Livestream endpoint failed with status: ${response.status}`);
                }
            } catch (error) {
                console.log(`❌ Livestream endpoint error: ${error.message}`);
            }
        }

        // Note: Kick.com videos API endpoints are blocked (403 Forbidden)
        // Only livestreams are accessible via API

        console.log(`📊 API fetch complete: ${livestreams.length} items found`);
        
        return {
            success: true,
            livestreams: livestreams,
            scrapedAt: new Date().toISOString(),
            url: `https://kick.com/${channelSlug}`,
            platform: 'kick'
        };
    }

    async scrapeKickViaBrowser(channelUrl) {
        console.log('🌐 Attempting web scraping fallback for Kick (likely to be blocked)...');
        
        let browser;
        try {
            browser = await puppeteer.launch({
                headless: 'new',
                args: BROWSER_ARGS
            });

            const page = await browser.newPage();
            await page.setUserAgent(USER_AGENTS[0]); // Use mobile iOS user agent for Kick
            
            console.log(`🌐 Navigating to: ${channelUrl}`);
            await page.goto(channelUrl, { 
                waitUntil: 'networkidle2', 
                timeout: KICK_BROWSER_TIMEOUT
            });

            // Quick check if we're blocked
            const isBlocked = await page.evaluate(() => {
                return document.body.textContent.includes('Request blocked by security policy');
            });

            if (isBlocked) {
                console.log('❌ Confirmed: Request blocked by Cloudflare security policy');
                return {
                    success: false,
                    error: 'Request blocked by security policy - web scraping approach failed',
                    livestreams: [],
                    scrapedAt: new Date().toISOString(),
                    url: channelUrl,
                    platform: 'kick'
                };
            }

            // If not blocked, continue with basic scraping
            await new Promise(resolve => setTimeout(resolve, KICK_CONTENT_DELAY));

            let livestreams = [];
            
            for (const selector of KICK_SELECTORS) {
                try {
                    const elements = await page.$$(selector);
                    if (elements.length > 0) {
                        console.log(`✅ Found ${elements.length} Kick elements with selector: ${selector}`);
                        
                        livestreams = await page.evaluate((sel) => {
                            const elements = document.querySelectorAll(sel);
                            const streams = [];
                            
                            elements.forEach((element, index) => {
                                try {
                                    const titleElement = element.querySelector('h3, h4, .title, [class*="title"]');
                                    const linkElement = element.querySelector('a');
                                    const thumbnailElement = element.querySelector('img');
                                    
                                    const title = titleElement ? titleElement.textContent?.trim() : `Kick Stream ${index + 1}`;
                                    const url = linkElement ? linkElement.href : null;
                                    const thumbnail = thumbnailElement ? thumbnailElement.src : null;
                                    
                                    if (title && url) {
                                        streams.push({
                                            id: `kick_${index}_${Date.now()}`,
                                            title: title,
                                            url: url,
                                            publishTime: null,
                                            thumbnail: thumbnail,
                                            isLive: !url.includes('/video/'),
                                            scraped: new Date().toISOString(),
                                            platform: 'kick'
                                        });
                                    }
                                } catch (err) {
                                    console.error(`Error processing Kick element ${index}:`, err.message);
                                }
                            });
                            
                            return streams;
                        }, selector);
                        
                        if (livestreams.length > 0) {
                            break;
                        }
                    }
                } catch (error) {
                    console.log(`⚠️ Kick selector ${selector} failed:`, error.message);
                }
            }

            console.log(`📺 Web scraping found ${livestreams.length} Kick items`);
            
            return {
                success: true,
                livestreams: livestreams,
                scrapedAt: new Date().toISOString(),
                url: channelUrl,
                platform: 'kick'
            };

        } catch (error) {
            console.error('❌ Error during Kick web scraping:', error.message);
            return {
                success: false,
                error: `Web scraping failed: ${error.message}`,
                livestreams: [],
                scrapedAt: new Date().toISOString(),
                url: channelUrl,
                platform: 'kick'
            };
        } finally {
            if (browser) {
                await browser.close();
            }
        }
    }


    async scrapeChannel(channelUrl) {
        const platform = this.detectPlatform(channelUrl);
        console.log(`🔍 Detected platform: ${platform}`);
        
        const scraper = this.scrapers[platform];
        if (!scraper) {
            return {
                success: false,
                error: `Unsupported platform: ${platform}`,
                livestreams: [],
                scrapedAt: new Date().toISOString(),
                url: channelUrl,
                platform: platform
            };
        }
        
        return await scraper(channelUrl);
    }

    async detectChanges(channelUrl) {
        console.log('🔍 Checking for new content...');
        
        // Load previous data for this specific channel
        const previousData = this.loadPreviousData(channelUrl);
        
        // Scrape current data
        const currentResult = await this.scrapeChannel(channelUrl);
        
        if (!currentResult.success) {
            console.error('❌ Scraping failed:', currentResult.error);
            return {
                success: false,
                error: currentResult.error
            };
        }

        const currentStreams = currentResult.livestreams;
        const previousStreams = previousData.livestreams || [];
        
        // Find new streams (not in previous data)
        const newStreams = currentStreams.filter(current => 
            !previousStreams.some(previous => 
                previous.id === current.id || 
                previous.url === current.url ||
                previous.title === current.title
            )
        );

        // Find removed streams
        const removedStreams = previousStreams.filter(previous => 
            !currentStreams.some(current => 
                current.id === previous.id || 
                current.url === previous.url ||
                current.title === previous.title
            )
        );

        // Save current data for this specific channel
        this.saveData({
            livestreams: currentStreams,
            lastCheck: new Date().toISOString(),
            channelUrl: channelUrl,
            platform: currentResult.platform
        }, channelUrl);

        const platform = currentResult.platform;
        console.log(`📊 ${platform} Results:`);
        console.log(`   Total items: ${currentStreams.length}`);
        console.log(`   New items: ${newStreams.length}`);
        console.log(`   Removed items: ${removedStreams.length}`);

        if (newStreams.length > 0) {
            console.log(`\\n🆕 NEW ${platform.toUpperCase()} CONTENT DETECTED:`);
            newStreams.forEach((stream, index) => {
                console.log(`${index + 1}. ${stream.title}`);
                console.log(`   URL: ${stream.url}`);
                console.log(`   Live: ${stream.isLive ? 'Yes' : 'No'}`);
            });
        }

        return {
            success: true,
            newStreams: newStreams,
            removedStreams: removedStreams,
            totalStreams: currentStreams.length,
            hasChanges: newStreams.length > 0 || removedStreams.length > 0,
            platform: platform
        };
    }
}

module.exports = KrumbleScraper;