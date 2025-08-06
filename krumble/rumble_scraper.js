const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

class RumbleScraper {
    constructor() {
        this.dataDir = path.join(__dirname, 'channel_data');
        this.screenshotDir = path.join(__dirname, 'screenshots');
        
        // Ensure directories exist
        if (!fs.existsSync(this.dataDir)) {
            fs.mkdirSync(this.dataDir, { recursive: true });
        }
        if (!fs.existsSync(this.screenshotDir)) {
            fs.mkdirSync(this.screenshotDir, { recursive: true });
        }
    }

    getChannelDataFile(channelUrl) {
        // Extract channel name from URL for filename
        const match = channelUrl.match(/\/c\/([^\/]+)/);
        const channelName = match ? match[1] : 'unknown';
        return path.join(this.dataDir, `${channelName}.json`);
    }

    loadPreviousData(channelUrl) {
        try {
            const dataFile = this.getChannelDataFile(channelUrl);
            if (fs.existsSync(dataFile)) {
                const data = fs.readFileSync(dataFile, 'utf8');
                return JSON.parse(data);
            }
        } catch (error) {
            console.log('⚠️ Could not load previous data:', error.message);
        }
        return { livestreams: [], lastCheck: null };
    }

    saveData(data, channelUrl) {
        try {
            const dataFile = this.getChannelDataFile(channelUrl);
            fs.writeFileSync(dataFile, JSON.stringify(data, null, 2));
            console.log(`💾 Data saved successfully for channel: ${channelUrl.match(/\/c\/([^\/]+)/)?.[1] || 'unknown'}`);
        } catch (error) {
            console.error('❌ Error saving data:', error.message);
        }
    }

    async scrapeRumbleLivestreams(channelUrl) {
        console.log('🚀 Starting Rumble livestream scraper...');
        console.log(`🔗 Target URL: ${channelUrl}`);

        let browser;
        try {
            browser = await puppeteer.launch({
                headless: 'new',
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security'
                ]
            });

            const page = await browser.newPage();
            
            // Set user agent to avoid bot detection
            await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
            
            console.log('🌐 Navigating to Rumble channel...');
            await page.goto(channelUrl, { 
                waitUntil: 'networkidle2', 
                timeout: 30000 
            });

            // Screenshot disabled

            // Wait for content to load
            console.log('⏳ Waiting for livestream content to load...');
            await new Promise(resolve => setTimeout(resolve, 5000));

            // Debug: Check page content
            const pageTitle = await page.title();
            console.log(`📄 Page title: "${pageTitle}"`);
            
            const bodyText = await page.evaluate(() => document.body.textContent.substring(0, 200));
            console.log(`📝 Page content preview: "${bodyText}"`);
            
            // Check if we're blocked or redirected
            const currentUrl = page.url();
            console.log(`🔗 Current URL: ${currentUrl}`);
            if (!currentUrl.includes('/c/')) {
                console.log('⚠️ WARNING: May have been redirected away from channel page');
            }

            // Try multiple selectors to find livestream elements (updated for current Rumble)
            const livestreamSelectors = [
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

            let livestreams = [];
            
            for (const selector of livestreamSelectors) {
                try {
                    const elements = await page.$$(selector);
                    if (elements.length > 0) {
                        console.log(`✅ Found ${elements.length} elements with selector: ${selector}`);
                        
                        livestreams = await page.evaluate((sel) => {
                            const elements = document.querySelectorAll(sel);
                            const streams = [];
                            
                            elements.forEach((element, index) => {
                                try {
                                    // Extract data from each livestream element
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
                                    
                                    // Check if this looks like a livestream
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
                                            elementHtml: element.outerHTML.substring(0, 500) // First 500 chars for debugging
                                        });
                                    }
                                } catch (err) {
                                    console.error(`Error processing element ${index}:`, err.message);
                                }
                            });
                            
                            return streams;
                        }, selector);
                        
                        if (livestreams.length > 0) {
                            break; // Found streams, stop trying other selectors
                        }
                    }
                } catch (error) {
                    console.log(`⚠️ Selector ${selector} failed:`, error.message);
                }
            }

            // If no specific selectors worked, try a more general approach
            if (livestreams.length === 0) {
                console.log('🔍 Trying general link extraction...');
                
                livestreams = await page.evaluate(() => {
                    const links = Array.from(document.querySelectorAll('a[href*="/v/"], a[href*="/video/"]'));
                    const streams = [];
                    
                    links.forEach((link, index) => {
                        try {
                            const title = link.textContent?.trim() || 
                                         link.title || 
                                         link.getAttribute('aria-label') ||
                                         `Video ${index + 1}`;
                            
                            const url = link.href.startsWith('http') ? link.href : `https://rumble.com${link.href}`;
                            
                            // Skip if title is too short (likely not a real video title)
                            if (title.length > 3 && !title.toLowerCase().includes('rumble')) {
                                streams.push({
                                    id: url.split('/').pop() || `video_${index}`,
                                    title: title,
                                    url: url,
                                    publishTime: null,
                                    thumbnail: null,
                                    isLive: title.toLowerCase().includes('live'),
                                    scraped: new Date().toISOString(),
                                    method: 'general_link_extraction'
                                });
                            }
                        } catch (err) {
                            console.error(`Error processing link ${index}:`, err.message);
                        }
                    });
                    
                    return streams;
                });
            }

            console.log(`📺 Found ${livestreams.length} livestreams/videos`);
            
            // Log found streams for debugging
            livestreams.forEach((stream, index) => {
                console.log(`${index + 1}. ${stream.title}`);
                console.log(`   URL: ${stream.url}`);
                console.log(`   Live: ${stream.isLive ? 'Yes' : 'No'}`);
                console.log(`   Time: ${stream.publishTime || 'Unknown'}`);
                console.log('');
            });

            return {
                success: true,
                livestreams: livestreams,
                scrapedAt: new Date().toISOString(),
                url: channelUrl
            };

        } catch (error) {
            console.error('❌ Error during scraping:', error.message);
            return {
                success: false,
                error: error.message,
                livestreams: [],
                scrapedAt: new Date().toISOString(),
                url: channelUrl
            };
        } finally {
            if (browser) {
                await browser.close();
                console.log('🔒 Browser closed');
            }
        }
    }

    async detectChanges(channelUrl) {
        console.log('🔍 Checking for new livestreams...');
        
        // Load previous data for this specific channel
        const previousData = this.loadPreviousData(channelUrl);
        
        // Scrape current data
        const currentResult = await this.scrapeRumbleLivestreams(channelUrl);
        
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
            channelUrl: channelUrl
        }, channelUrl);

        console.log(`📊 Results:`);
        console.log(`   Total streams: ${currentStreams.length}`);
        console.log(`   New streams: ${newStreams.length}`);
        console.log(`   Removed streams: ${removedStreams.length}`);

        if (newStreams.length > 0) {
            console.log('\n🆕 NEW STREAMS DETECTED:');
            newStreams.forEach((stream, index) => {
                console.log(`${index + 1}. ${stream.title}`);
                console.log(`   URL: ${stream.url}`);
                console.log(`   Live: ${stream.isLive ? 'Yes' : 'No'}`);
            });
        }

        if (removedStreams.length > 0) {
            console.log('\n🗑️ REMOVED STREAMS:');
            removedStreams.forEach((stream, index) => {
                console.log(`${index + 1}. ${stream.title}`);
            });
        }

        return {
            success: true,
            newStreams: newStreams,
            removedStreams: removedStreams,
            totalStreams: currentStreams.length,
            hasChanges: newStreams.length > 0 || removedStreams.length > 0
        };
    }
}

// Main execution
async function main() {
    const scraper = new RumbleScraper();
    const channelUrl = process.argv[2] || 'https://rumble.com/c/madattheinternet/livestreams';
    
    console.log('🔥 Rumble Livestream Monitor Starting...');
    console.log(`📺 Channel: ${channelUrl}`);
    console.log('');
    
    try {
        const result = await scraper.detectChanges(channelUrl);
        
        if (result.success) {
            if (result.hasChanges) {
                console.log('\n🚨 CHANGES DETECTED!');
                process.exit(1); // Exit with code 1 to indicate changes found
            } else {
                console.log('\n✅ No changes detected');
                process.exit(0);
            }
        } else {
            console.error('\n❌ Monitoring failed:', result.error);
            process.exit(2); // Exit with code 2 to indicate error
        }
    } catch (error) {
        console.error('\n💥 Unexpected error:', error.message);
        process.exit(2);
    }
}

// Run if called directly
if (require.main === module) {
    main();
}

module.exports = RumbleScraper;