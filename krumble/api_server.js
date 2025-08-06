const express = require('express');
const KrumbleScraper = require('./krumble_scraper');

class KrumblePluginAPIServer {
    constructor() {
        this.app = express();
        this.scraper = new KrumbleScraper();
        this.setupRoutes();
    }
    
    setupRoutes() {
        this.app.use(express.json());
        
        // Health check endpoint (required for all plugin services)
        this.app.get('/health', (req, res) => {
            res.json({ 
                status: 'healthy', 
                timestamp: new Date().toISOString(),
                service: 'krumble-scraper',
                version: '1.0.0'
            });
        });
        
        // Service status endpoint
        this.app.get('/status', (req, res) => {
            res.json({
                service: 'krumble-scraper',
                version: '1.0.0',
                uptime: process.uptime(),
                memory: process.memoryUsage(),
                pid: process.pid,
                node_version: process.version
            });
        });
        
        // Main scraping endpoint
        this.app.post('/scrape', async (req, res) => {
            try {
                const { channel_url, options = {} } = req.body;
                
                if (!channel_url) {
                    return res.status(400).json({
                        success: false,
                        error: 'channel_url is required'
                    });
                }
                
                console.log(`🔍 Scraping request for: ${channel_url}`);
                
                const result = await this.scraper.detectChanges(channel_url);
                
                // Transform result to match expected format
                const response = {
                    success: result.success,
                    newStreams: result.newStreams || [],
                    removedStreams: result.removedStreams || [],
                    totalStreams: result.totalStreams || 0,
                    hasChanges: result.hasChanges || false,
                    platform: result.platform || 'unknown',
                    timestamp: new Date().toISOString()
                };
                
                if (!result.success) {
                    response.error = result.error || 'Unknown error';
                }
                
                console.log(`📊 Scraping result: ${result.success ? 'Success' : 'Failed'}, Changes: ${response.hasChanges}, New: ${response.newStreams.length}`);
                
                res.json(response);
            } catch (error) {
                console.error('❌ Scraping error:', error.message);
                res.status(500).json({
                    success: false,
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
            }
        });
        
        // Manual scraping endpoint (for testing)
        this.app.get('/scrape/:channel', async (req, res) => {
            try {
                const channel = req.params.channel;
                // Default to Rumble for backward compatibility
                const url = `https://rumble.com/c/${channel}/livestreams`;
                
                console.log(`🔍 Manual scraping request for channel: ${channel}`);
                
                const result = await this.scraper.scrapeChannel(url);
                
                res.json({
                    success: result.success,
                    livestreams: result.livestreams || [],
                    total: (result.livestreams || []).length,
                    timestamp: new Date().toISOString(),
                    url: url
                });
            } catch (error) {
                console.error('❌ Manual scraping error:', error.message);
                res.status(500).json({
                    success: false,
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
            }
        });
        
        // Get cached data
        this.app.get('/data', (req, res) => {
            try {
                const cachedData = this.scraper.loadPreviousData();
                res.json({
                    success: true,
                    data: cachedData,
                    timestamp: new Date().toISOString()
                });
            } catch (error) {
                res.status(500).json({
                    success: false,
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
            }
        });
        
        // Error handling middleware
        this.app.use((error, req, res, next) => {
            console.error('🚨 Unhandled API error:', error);
            res.status(500).json({
                success: false,
                error: 'Internal server error',
                timestamp: new Date().toISOString()
            });
        });
        
        // 404 handler
        this.app.use('*', (req, res) => {
            res.status(404).json({
                success: false,
                error: `Endpoint not found: ${req.method} ${req.originalUrl}`,
                available_endpoints: [
                    'GET /health',
                    'GET /status', 
                    'POST /scrape',
                    'GET /scrape/:channel',
                    'GET /data'
                ],
                timestamp: new Date().toISOString()
            });
        });
    }
    
    start(port = 8001) {
        const server = this.app.listen(port, '0.0.0.0', () => {
            console.log(`🚀 Krumble Plugin API server running on port ${port}`);
            console.log(`📋 Available endpoints:`);
            console.log(`   GET  /health - Health check`);
            console.log(`   GET  /status - Service status`);
            console.log(`   POST /scrape - Scrape channel with change detection`);
            console.log(`   GET  /scrape/:channel - Manual scrape specific channel`);
            console.log(`   GET  /data - Get cached data`);
        });
        
        // Graceful shutdown
        process.on('SIGTERM', () => {
            console.log('🛑 SIGTERM received, shutting down gracefully...');
            server.close(() => {
                console.log('✅ Server closed');
                process.exit(0);
            });
        });
        
        process.on('SIGINT', () => {
            console.log('🛑 SIGINT received, shutting down gracefully...');
            server.close(() => {
                console.log('✅ Server closed');
                process.exit(0);
            });
        });
        
        return server;
    }
}

// Start server
const server = new KrumblePluginAPIServer();
server.start(process.env.PLUGIN_API_PORT || 8001);