#!/usr/bin/env python3
"""
SimpleX Platform Services Implementation

This module provides SimpleX-specific implementations of the platform services
defined in platform_services.py, allowing plugins to access SimpleX functionality
without direct bot access.
"""

from typing import Dict, List, Optional, Any
import logging
import asyncio
import json
import sys
import os
from datetime import datetime

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from platform_services import (
    PlatformService, MessageHistoryService, ContactManagementService, 
    GroupManagementService, FileService, InviteManagementService,
    NotificationService, PlatformStatusService, PlatformServiceRegistry
)


class SimpleXMessageHistoryService(MessageHistoryService):
    """SimpleX implementation of message history service"""
    
    def __init__(self, bot_instance, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.bot = bot_instance
        self.message_cache: Dict[str, List[Dict]] = {}
        self.cache_size = 100  # Keep last 100 messages per chat
    
    async def is_available(self) -> bool:
        """Check if service is available"""
        return (self.bot and 
                hasattr(self.bot, 'websocket_manager') and 
                self.bot.websocket_manager.websocket is not None)
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service capabilities"""
        return {
            "name": "SimpleX Message History",
            "version": "1.0.0",
            "capabilities": [
                "get_recent_messages",
                "get_messages_by_criteria",
                "message_caching"
            ],
            "cache_size": self.cache_size,
            "available": asyncio.run(self.is_available()) if asyncio.get_event_loop().is_running() else False
        }
    
    async def get_recent_messages(self, chat_id: str, count: int = 10) -> List[Dict]:
        """Get recent messages from chat"""
        try:
            # Try to get from cache first
            if chat_id in self.message_cache:
                cached_messages = self.message_cache[chat_id][-count:]
                if cached_messages:
                    self.logger.debug(f"📋 MESSAGE HISTORY: Returning {len(cached_messages)} cached messages for {chat_id}")
                    return cached_messages
            
            # Fall back to CLI query (if available)
            return await self._fetch_messages_from_cli(chat_id, count)
            
        except Exception as e:
            self.logger.error(f"📋 MESSAGE HISTORY: Error getting recent messages: {e}")
            return []
    
    async def get_messages_by_criteria(self, chat_id: str, **kwargs) -> List[Dict]:
        """Get messages by various criteria"""
        try:
            # For now, implement basic filtering on cached messages
            messages = await self.get_recent_messages(chat_id, kwargs.get('count', 50))
            
            # Filter by sender if specified
            if 'sender' in kwargs:
                messages = [m for m in messages if m.get('sender') == kwargs['sender']]
            
            # Filter by content if specified
            if 'contains' in kwargs:
                search_term = kwargs['contains'].lower()
                messages = [m for m in messages if search_term in m.get('content', '').lower()]
            
            # Filter by message type if specified  
            if 'message_type' in kwargs:
                messages = [m for m in messages if m.get('type') == kwargs['message_type']]
            
            return messages
            
        except Exception as e:
            self.logger.error(f"📋 MESSAGE HISTORY: Error filtering messages: {e}")
            return []
    
    async def _fetch_messages_from_cli(self, chat_id: str, count: int) -> List[Dict]:
        """Fetch messages using SimpleX CLI"""
        try:
            # Use SimpleX CLI to get chat history
            # This is a placeholder - actual implementation would use CLI commands
            self.logger.debug(f"📋 MESSAGE HISTORY: CLI fetch not implemented yet for {chat_id}")
            return []
            
        except Exception as e:
            self.logger.error(f"📋 MESSAGE HISTORY: CLI fetch error: {e}")
            return []
    
    def store_message(self, chat_id: str, message_data: Dict):
        """Store message in cache for future retrieval"""
        try:
            if chat_id not in self.message_cache:
                self.message_cache[chat_id] = []
            
            # Add to cache
            self.message_cache[chat_id].append({
                'timestamp': datetime.now().isoformat(),
                'chat_id': chat_id,
                'sender': message_data.get('sender', 'unknown'),
                'content': message_data.get('content', ''),
                'type': message_data.get('type', 'text'),
                'raw_data': message_data
            })
            
            # Keep only recent messages
            if len(self.message_cache[chat_id]) > self.cache_size:
                self.message_cache[chat_id] = self.message_cache[chat_id][-self.cache_size:]
                
            self.logger.debug(f"📋 MESSAGE HISTORY: Stored message for {chat_id} (cache size: {len(self.message_cache[chat_id])})")
            
        except Exception as e:
            self.logger.error(f"📋 MESSAGE HISTORY: Error storing message: {e}")


class SimpleXContactService(ContactManagementService):
    """SimpleX implementation of contact management service"""
    
    def __init__(self, bot_instance, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.bot = bot_instance
        self.contact_cache: Optional[List[Dict]] = None
        self.cache_expiry = 300  # 5 minutes
        self.last_cache_update = 0
    
    async def is_available(self) -> bool:
        """Check if service is available"""
        return (self.bot and 
                hasattr(self.bot, 'websocket_manager') and 
                self.bot.websocket_manager.websocket is not None)
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service capabilities"""
        return {
            "name": "SimpleX Contact Management",
            "version": "1.0.0", 
            "capabilities": [
                "get_contacts",
                "get_contact_info",
                "contact_caching"
            ],
            "cache_expiry": self.cache_expiry,
            "available": asyncio.run(self.is_available()) if asyncio.get_event_loop().is_running() else False
        }
    
    async def get_contacts(self) -> List[Dict]:
        """Get all contacts"""
        try:
            # Check cache first
            current_time = asyncio.get_event_loop().time()
            if (self.contact_cache and 
                (current_time - self.last_cache_update) < self.cache_expiry):
                self.logger.debug("👥 CONTACTS: Returning cached contacts")
                return self.contact_cache
            
            # Fetch from SimpleX using WebSocket
            if self.bot and hasattr(self.bot, 'websocket_manager'):
                contacts_data = await self._fetch_contacts_via_websocket()
                if contacts_data:
                    self.contact_cache = contacts_data
                    self.last_cache_update = current_time
                    return contacts_data
            
            return []
            
        except Exception as e:
            self.logger.error(f"👥 CONTACTS: Error getting contacts: {e}")
            return []
    
    async def get_contact_info(self, contact_id: str) -> Dict:
        """Get specific contact information"""
        try:
            contacts = await self.get_contacts()
            for contact in contacts:
                if contact.get('contactId') == contact_id or contact.get('localDisplayName') == contact_id:
                    return contact
            
            self.logger.warning(f"👥 CONTACTS: Contact not found: {contact_id}")
            return {}
            
        except Exception as e:
            self.logger.error(f"👥 CONTACTS: Error getting contact info: {e}")
            return {}
    
    async def _fetch_contacts_via_websocket(self) -> List[Dict]:
        """Fetch contacts using WebSocket API"""
        try:
            # Use the bot's WebSocket manager to get contacts
            response = await self.bot.websocket_manager.send_command('/contacts')
            
            if response and 'contacts' in response:
                contacts = response['contacts']
                self.logger.info(f"👥 CONTACTS: Fetched {len(contacts)} contacts")
                return contacts
            
            return []
            
        except Exception as e:
            self.logger.error(f"👥 CONTACTS: WebSocket fetch error: {e}")
            return []


class SimpleXGroupService(GroupManagementService):
    """SimpleX implementation of group management service"""
    
    def __init__(self, bot_instance, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.bot = bot_instance
        self.group_cache: Optional[List[Dict]] = None
        self.cache_expiry = 300
        self.last_cache_update = 0
    
    async def is_available(self) -> bool:
        """Check if service is available"""
        return (self.bot and 
                hasattr(self.bot, 'websocket_manager') and 
                self.bot.websocket_manager.websocket is not None)
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service capabilities"""
        return {
            "name": "SimpleX Group Management", 
            "version": "1.0.0",
            "capabilities": [
                "get_groups", 
                "get_group_info",
                "get_group_members"
            ],
            "available": asyncio.run(self.is_available()) if asyncio.get_event_loop().is_running() else False
        }
    
    async def get_groups(self) -> List[Dict]:
        """Get all groups"""
        try:
            # Check cache first
            current_time = asyncio.get_event_loop().time()
            if (self.group_cache and 
                (current_time - self.last_cache_update) < self.cache_expiry):
                return self.group_cache
            
            # For now, extract groups from contacts that have groupInfo
            contacts = await self._get_contacts_with_groups()
            groups = []
            
            for contact in contacts:
                if 'groupInfo' in contact:
                    group_info = contact['groupInfo']
                    groups.append({
                        'groupId': group_info.get('groupId'),
                        'localDisplayName': group_info.get('localDisplayName'),
                        'groupProfile': group_info.get('groupProfile', {}),
                        'membership': group_info.get('membership', {}),
                        'hostConnId': group_info.get('hostConnId')
                    })
            
            self.group_cache = groups
            self.last_cache_update = current_time
            return groups
            
        except Exception as e:
            self.logger.error(f"🏢 GROUPS: Error getting groups: {e}")
            return []
    
    async def get_group_info(self, group_id: str) -> Dict:
        """Get specific group information"""
        try:
            groups = await self.get_groups()
            for group in groups:
                if group.get('groupId') == group_id or group.get('localDisplayName') == group_id:
                    return group
            return {}
            
        except Exception as e:
            self.logger.error(f"🏢 GROUPS: Error getting group info: {e}")
            return {}
    
    async def get_group_members(self, group_id: str) -> List[Dict]:
        """Get group members"""
        try:
            # This would require additional SimpleX CLI commands
            # For now, return empty list as placeholder
            self.logger.debug(f"🏢 GROUPS: Group member fetching not implemented for {group_id}")
            return []
            
        except Exception as e:
            self.logger.error(f"🏢 GROUPS: Error getting group members: {e}")
            return []
    
    async def _get_contacts_with_groups(self) -> List[Dict]:
        """Get contacts that include group information"""
        try:
            if self.bot and hasattr(self.bot, 'websocket_manager'):
                response = await self.bot.websocket_manager.send_command('/contacts')
                if response and 'contacts' in response:
                    return response['contacts']
            return []
        except Exception as e:
            self.logger.error(f"🏢 GROUPS: Error fetching contacts: {e}")
            return []


class SimpleXFileService(FileService):
    """SimpleX implementation of file service"""
    
    def __init__(self, bot_instance, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.bot = bot_instance
    
    async def is_available(self) -> bool:
        """Check if service is available"""
        return (self.bot and 
                hasattr(self.bot, 'file_download_manager') and
                hasattr(self.bot, 'websocket_manager'))
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service capabilities"""
        return {
            "name": "SimpleX File Operations",
            "version": "1.0.0",
            "capabilities": [
                "download_file",
                "send_file", 
                "xftp_support"
            ],
            "available": asyncio.run(self.is_available()) if asyncio.get_event_loop().is_running() else False
        }
    
    async def download_file(self, file_info: Dict) -> str:
        """Download file and return local path"""
        try:
            if self.bot and hasattr(self.bot, 'file_download_manager'):
                # Use the bot's existing file download manager
                return await self.bot.file_download_manager.download_file(file_info)
            
            raise Exception("File download manager not available")
            
        except Exception as e:
            self.logger.error(f"📁 FILES: Error downloading file: {e}")
            return ""
    
    async def send_file(self, chat_id: str, file_path: str, caption: str = "") -> bool:
        """Send file to chat"""
        try:
            if self.bot and hasattr(self.bot, 'websocket_manager'):
                # Use WebSocket to send file
                # This is a placeholder - would need actual SimpleX file send implementation
                self.logger.debug(f"📁 FILES: File sending not fully implemented yet")
                return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"📁 FILES: Error sending file: {e}")
            return False


class SimpleXInviteService(InviteManagementService):
    """SimpleX implementation of invite management service"""
    
    def __init__(self, bot_instance, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.bot = bot_instance
    
    async def is_available(self) -> bool:
        """Check if service is available"""
        return (self.bot and 
                hasattr(self.bot, 'invite_manager') and
                hasattr(self.bot, 'websocket_manager'))
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service capabilities"""
        return {
            "name": "SimpleX Invite Management",
            "version": "1.0.0", 
            "capabilities": [
                "generate_invite",
                "list_pending_invites"
            ],
            "available": asyncio.run(self.is_available()) if asyncio.get_event_loop().is_running() else False
        }
    
    async def generate_invite(self, requested_by: str) -> Optional[str]:
        """Generate connection invite"""
        try:
            if self.bot and hasattr(self.bot, 'invite_manager'):
                # Use the bot's existing invite manager
                invite_link = await self.bot.invite_manager.generate_invite_async()
                if invite_link:
                    self.logger.info(f"🎫 INVITES: Generated invite for {requested_by}")
                    return invite_link
            
            return None
            
        except Exception as e:
            self.logger.error(f"🎫 INVITES: Error generating invite: {e}")
            return None
    
    async def list_pending_invites(self) -> List[Dict]:
        """List pending invitations"""
        try:
            if self.bot and hasattr(self.bot, 'invite_manager'):
                # This would need to be implemented in the invite manager
                self.logger.debug("🎫 INVITES: Pending invite listing not implemented")
                return []
            
            return []
            
        except Exception as e:
            self.logger.error(f"🎫 INVITES: Error listing pending invites: {e}")
            return []


class SimpleXNotificationService(NotificationService):
    """SimpleX implementation of notification service"""
    
    def __init__(self, bot_instance, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.bot = bot_instance
    
    async def is_available(self) -> bool:
        """Check if service is available"""
        return (self.bot and 
                hasattr(self.bot, 'websocket_manager') and 
                self.bot.websocket_manager.websocket is not None)
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service capabilities"""
        return {
            "name": "SimpleX Notification Service",
            "version": "1.0.0",
            "capabilities": [
                "notify_groups",
                "notify_users", 
                "bulk_notify"
            ],
            "available": asyncio.run(self.is_available()) if asyncio.get_event_loop().is_running() else False
        }
    
    async def notify_groups(self, groups: List[str], message: str) -> Dict[str, bool]:
        """Send notification to multiple groups"""
        results = {}
        
        if not await self.is_available():
            self.logger.warning("📤 NOTIFY: WebSocket not available for group notifications")
            return {group: False for group in groups}
        
        for group_name in groups:
            try:
                await self.bot.websocket_manager.send_message(group_name, message, is_group=True)
                results[group_name] = True
                self.logger.info(f"📤 NOTIFY: Sent notification to group: {group_name}")
            except Exception as e:
                results[group_name] = False
                self.logger.error(f"📤 NOTIFY: Failed to send to group '{group_name}': {e}")
        
        return results
    
    async def notify_users(self, users: List[str], message: str) -> Dict[str, bool]:
        """Send notification to multiple users"""
        results = {}
        
        if not await self.is_available():
            self.logger.warning("📤 NOTIFY: WebSocket not available for user notifications")
            return {user: False for user in users}
        
        for user_name in users:
            try:
                await self.bot.websocket_manager.send_message(user_name, message, is_group=False)
                results[user_name] = True
                self.logger.info(f"📤 NOTIFY: Sent notification to user: {user_name}")
            except Exception as e:
                results[user_name] = False
                self.logger.error(f"📤 NOTIFY: Failed to send to user '{user_name}': {e}")
        
        return results
    
    async def bulk_notify(self, targets: Dict[str, List[str]], message: str) -> Dict[str, Dict[str, bool]]:
        """Send notifications to mixed targets"""
        results = {}
        
        # Send to groups
        if 'groups' in targets:
            results['groups'] = await self.notify_groups(targets['groups'], message)
        
        # Send to users  
        if 'users' in targets:
            results['users'] = await self.notify_users(targets['users'], message)
        
        # Log summary
        total_groups = len(targets.get('groups', []))
        total_users = len(targets.get('users', []))
        success_groups = sum(1 for success in results.get('groups', {}).values() if success)
        success_users = sum(1 for success in results.get('users', {}).values() if success)
        
        self.logger.info(f"📤 NOTIFY: Bulk notification complete - Groups: {success_groups}/{total_groups}, Users: {success_users}/{total_users}")
        
        return results


class SimpleXPlatformStatusService(PlatformStatusService):
    """SimpleX implementation of platform status service"""
    
    def __init__(self, bot_instance, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.bot = bot_instance
    
    async def is_available(self) -> bool:
        """Check if service is available"""
        return self.bot is not None
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service capabilities"""
        return {
            "name": "SimpleX Platform Status",
            "version": "1.0.0",
            "capabilities": [
                "get_connection_info",
                "get_platform_health",
                "get_diagnostic_info"
            ],
            "available": asyncio.run(self.is_available()) if asyncio.get_event_loop().is_running() else False
        }
    
    async def get_connection_info(self) -> Dict[str, Any]:
        """Get connection status information"""
        try:
            info = {
                "platform": "SimpleX Chat",
                "connected": False,
                "websocket_url": "N/A",
                "websocket_id": None
            }
            
            if self.bot and hasattr(self.bot, 'websocket_manager'):
                ws_manager = self.bot.websocket_manager
                info.update({
                    "connected": ws_manager.is_connected,
                    "websocket_url": getattr(ws_manager, 'websocket_url', 'N/A'),
                    "websocket_id": id(ws_manager.websocket) if ws_manager.websocket else None,
                    "pending_requests": len(getattr(ws_manager, 'pending_requests', {}))
                })
            
            return info
            
        except Exception as e:
            self.logger.error(f"🔧 STATUS: Error getting connection info: {e}")
            return {"error": str(e)}
    
    async def get_platform_health(self) -> Dict[str, Any]:
        """Get platform health metrics"""
        try:
            health = {
                "status": "unknown",
                "websocket_connected": False,
                "invite_manager_available": False,
                "file_manager_available": False,
                "admin_manager_available": False
            }
            
            if self.bot:
                health["websocket_connected"] = (hasattr(self.bot, 'websocket_manager') and 
                                               self.bot.websocket_manager.websocket is not None)
                health["invite_manager_available"] = hasattr(self.bot, 'invite_manager')
                health["file_manager_available"] = hasattr(self.bot, 'file_download_manager')
                health["admin_manager_available"] = hasattr(self.bot, 'admin_manager')
                
                # Overall status
                if health["websocket_connected"]:
                    health["status"] = "healthy"
                else:
                    health["status"] = "degraded"
            else:
                health["status"] = "offline"
            
            return health
            
        except Exception as e:
            self.logger.error(f"🔧 STATUS: Error getting platform health: {e}")
            return {"error": str(e), "status": "error"}
    
    async def get_diagnostic_info(self) -> Dict[str, Any]:
        """Get detailed diagnostic information"""
        try:
            diag = {
                "timestamp": datetime.now().isoformat(),
                "bot_instance": self.bot is not None
            }
            
            if self.bot:
                # WebSocket diagnostics
                if hasattr(self.bot, 'websocket_manager'):
                    ws_manager = self.bot.websocket_manager
                    diag["websocket"] = {
                        "connected": ws_manager.is_connected,
                        "url": getattr(ws_manager, 'websocket_url', 'N/A'),
                        "pending_requests": len(getattr(ws_manager, 'pending_requests', {})),
                        "message_count": getattr(ws_manager, 'message_count', 0)
                    }
                
                # Invite manager diagnostics
                if hasattr(self.bot, 'invite_manager'):
                    diag["invite_manager"] = {
                        "available": True,
                        "stats": getattr(self.bot.invite_manager, 'get_stats', lambda: {})()
                    }
                
                # Admin manager diagnostics
                if hasattr(self.bot, 'admin_manager'):
                    diag["admin_manager"] = {
                        "available": True,
                        "admin_count": len(getattr(self.bot.admin_manager, 'list_admins', lambda: {})())
                    }
                
                # Plugin system diagnostics
                if hasattr(self.bot, 'plugin_manager'):
                    diag["plugin_system"] = {
                        "available": True,
                        "plugin_count": len(getattr(self.bot.plugin_manager, 'plugins', {}))
                    }
            
            return diag
            
        except Exception as e:
            self.logger.error(f"🔧 STATUS: Error getting diagnostic info: {e}")
            return {"error": str(e)}


class SimpleXPlatformServices:
    """Collection of SimpleX-specific services"""
    
    def __init__(self, bot_instance, logger: Optional[logging.Logger] = None):
        self.bot = bot_instance
        self.logger = logger or logging.getLogger(__name__)
        
        # Create all SimpleX services
        self.services = {
            'message_history': SimpleXMessageHistoryService(bot_instance, logger),
            'contact_management': SimpleXContactService(bot_instance, logger), 
            'group_management': SimpleXGroupService(bot_instance, logger),
            'file_operations': SimpleXFileService(bot_instance, logger),
            'invite_management': SimpleXInviteService(bot_instance, logger),
            'notification': SimpleXNotificationService(bot_instance, logger),
            'platform_status': SimpleXPlatformStatusService(bot_instance, logger),
        }
        
        self.logger.info("🔧 SIMPLEX SERVICES: Initialized all SimpleX platform services")
    
    def register_all_services(self, registry: PlatformServiceRegistry):
        """Register all SimpleX services with the registry"""
        for name, service in self.services.items():
            registry.register_service(name, service)
            self.logger.info(f"🔧 SIMPLEX SERVICES: Registered {name} service")
        
        self.logger.info(f"🔧 SIMPLEX SERVICES: Registered {len(self.services)} services total")
    
    def get_message_history_service(self) -> SimpleXMessageHistoryService:
        """Get message history service for direct access"""
        return self.services['message_history']