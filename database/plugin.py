from typing import List, Optional, Dict, Any
import logging
import aiohttp
import aiofiles
import json
import mimetypes
from datetime import datetime
from pathlib import Path
from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform


class ChatDatabaseClient:
    """Simplified client for interacting with the Matrix Chat Database API"""
    
    def __init__(self, base_url: str, api_key: str):
        """Initialize the API client with authentication"""
        # Remove trailing slash to prevent double slash issues
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        print(f"✅ ChatDatabaseClient initialized")
        print(f"📡 API Base URL: {self.base_url}")
        print(f"🔑 API Key: {api_key[:10]}...")
    
    async def health_check(self) -> bool:
        """Check if the API server is healthy"""
        try:
            url = f"{self.base_url}/health"
            print(f"🏥 Health check URL: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={'Authorization': f'Bearer {self.api_key}'},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    print(f"🏥 Health check response: {response.status}")
                    if response.status == 200:
                        result = await response.json()
                        print(f"🏥 Health check result: {result}")
                        return result.get('status') == 'healthy'
                    else:
                        print(f"🏥 Health check failed: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def store_message(self, room_id: str, event_id: str, sender: str, 
                           message_type: str, content: str = None, 
                           timestamp: datetime = None) -> Optional[Dict[str, Any]]:
        """Store a message in the database"""
        try:
            url = f"{self.base_url}/messages"
            
            data = {
                'room_id': room_id,
                'event_id': event_id,
                'sender': sender,
                'message_type': message_type,
                'content': content or '',
                'timestamp': (timestamp or datetime.now()).isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self.headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"❌ Store message failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ Store message error: {e}")
            return None
    
    async def get_messages(self, room_id: str, limit: int = 100, 
                          include_media: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Get messages from the database"""
        try:
            params = {
                'room_id': room_id,
                'limit': limit
            }
            if include_media:
                params['include_media'] = 'true'
            
            # Build query string
            query_params = '&'.join([f"{k}={v}" for k, v in params.items()])
            url = f"{self.base_url}/messages?{query_params}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"❌ Get messages failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ Get messages error: {e}")
            return None
    
    async def upload_media(self, message_id: int, file_path: str) -> Optional[Dict[str, Any]]:
        """Upload media file to the database"""
        try:
            url = f"{self.base_url}/media/upload"
            file_path = Path(file_path)
            
            if not file_path.exists():
                print(f"❌ File does not exist: {file_path}")
                return None
            
            # Prepare headers for multipart upload (no Content-Type for multipart)
            upload_headers = {"Authorization": f"Bearer {self.api_key}"}
            
            async with aiohttp.ClientSession() as session:
                # Create form data
                data = aiohttp.FormData()
                data.add_field('message_id', str(message_id))
                
                # Read and add file
                async with aiofiles.open(file_path, 'rb') as f:
                    file_content = await f.read()
                    # Detect proper MIME type based on file extension
                    mime_type, _ = mimetypes.guess_type(file_path.name)
                    content_type = mime_type or 'application/octet-stream'
                    
                    data.add_field(
                        'file', 
                        file_content,
                        filename=file_path.name,
                        content_type=content_type
                    )
                
                async with session.post(
                    url,
                    headers=upload_headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"❌ Upload media failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ Upload media error: {e}")
            return None
    
    async def get_database_stats(self) -> Optional[Dict[str, Any]]:
        """Get database statistics"""
        try:
            url = f"{self.base_url}/stats"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"❌ Get stats failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ Get stats error: {e}")
            return None
    
    async def delete_message(self, message_id: int) -> bool:
        """Delete a message from the database by ID"""
        try:
            url = f"{self.base_url}/messages/{message_id}"
            print(f"🗑️ Deleting message ID: {message_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        print(f"🗑️ Message {message_id} deleted successfully")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ Delete message failed: {response.status} - {error_text}")
                        return False
        except Exception as e:
            print(f"❌ Delete message error: {e}")
            return False


class UniversalDatabasePlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("database", logger=logger)
        self.version = "1.0.0"
        self.description = "Universal database integration for storing and retrieving messages"
        self.bot = None
        
        if not self.logger:
            self.logger = logging.getLogger(f"plugin.{self.name}")
    
    async def initialize(self, adapter) -> bool:
        """Initialize plugin with bot adapter"""
        # Call parent initialization
        if not await super().initialize(adapter):
            return False
            
        # Get bot instance from adapter
        self.bot = getattr(adapter, 'bot_instance', None)
        if not self.bot:
            self.logger.error("Cannot access bot instance from adapter")
            return False
        
        # Get database configuration from plugin config and environment
        try:
            # For now, disable database functionality as config access needs updating
            self.logger.warning("Database functionality temporarily disabled - needs config system update")
            self.enabled = False
            if hasattr(self.bot, 'db_enabled'):
                self.bot.db_enabled = False
                self.bot.db_client = None
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize database client: {e}")
            self.enabled = False
            if hasattr(self.bot, 'db_enabled'):
                self.bot.db_enabled = False
                self.bot.db_client = None
        
        return True
    
    def get_commands(self) -> List[str]:
        return ["db"]
    
    async def handle_command(self, context: CommandContext) -> Optional[str]:
        """Handle commands for this plugin"""
        self.logger.info(f"Handling {context.command} command from {context.user_display_name}")
        
        if not self.bot or not self.enabled:
            self.logger.error("Database functionality not available")
            return "❌ Database functionality not available"
        
        try:
            if context.command == "db":
                if context.has_args:
                    subcommand = context.args[0].lower()
                    if subcommand == "health":
                        return await self._handle_db_health()
                    elif subcommand == "stats" or subcommand == "status":
                        return await self._handle_db_stats()
                    else:
                        return "❌ Unknown database command. Use 'db health', 'db stats', or 'db status'"
                else:
                    return "❌ Database command requires arguments. Use 'db health', 'db stats', or 'db status'"
        except Exception as e:
            self.logger.error(f"Error handling {context.command} command: {str(e)}", exc_info=True)
            return f"❌ Error processing database command"
        
        return None
    
    async def _handle_db_health(self) -> str:
        """Handle database health check"""
        try:
            if not self.bot.db_client:
                return "❌ Database client not available"
            
            # health_check returns a boolean, not a dict
            is_healthy = await self.bot.db_client.health_check()
            
            if is_healthy:
                return "✅ Database is healthy!"
            else:
                return "❌ Database is unhealthy"
                
        except Exception as e:
            return f"❌ Database health check failed: {str(e)}"
    
    async def _handle_db_stats(self) -> str:
        """Handle database statistics"""
        try:
            if not self.bot.db_client:
                return "❌ Database client not available"
            
            stats = await self.bot.db_client.get_database_stats()
            
            if stats:
                total_messages = stats.get('total_messages', 'Unknown')
                total_media_files = stats.get('total_media_files', 'Unknown')
                database_size = stats.get('database_size', 'Unknown')
                
                return f"""📊 **DATABASE STATISTICS**
💬 Total Messages: {total_messages}
📎 Total Media Files: {total_media_files}
💾 Database Size: {database_size}"""
            else:
                return "❌ Could not retrieve database statistics"
                
        except Exception as e:
            return f"❌ Database stats failed: {str(e)}"