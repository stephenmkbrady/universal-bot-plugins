"""
Universal SimpleX Plugin - SimpleX Chat specific commands

This plugin provides SimpleX Chat specific functionality including contact management,
group management, invite generation, and debug commands.
"""

import logging
from typing import List, Optional
from plugins.universal_plugin_base import UniversalBotPlugin, CommandContext, BotPlatform


class MockAdminManager:
    """Mock admin manager for testing purposes"""
    def __init__(self):
        self.mock_admins = {"test_admin": ["*"]}
    
    def is_admin(self, username: str) -> bool:
        return username in self.mock_admins
    
    def list_admins(self) -> dict:
        return self.mock_admins
    
    def add_admin(self, username: str) -> bool:
        self.mock_admins[username] = ["*"]
        return True
    
    def remove_admin(self, username: str) -> bool:
        return self.mock_admins.pop(username, None) is not None
    
    def get_user_permissions(self, username: str) -> dict:
        is_admin = username in self.mock_admins
        return {
            "is_admin": is_admin,
            "admin_commands": self.mock_admins.get(username, []),
            "public_commands": ["help", "info"]
        }
    
    def reload_config(self):
        pass


class UniversalSimplexPlugin(UniversalBotPlugin):
    def __init__(self, logger=None):
        super().__init__("simplex", logger=logger)
        self.version = "1.0.1"
        self.description = "SimpleX Chat specific commands for contact/group management, invites, and debugging"
        
        # This plugin only supports SimpleX platform
        self.supported_platforms = [BotPlatform.SIMPLEX]
        
        if not self.logger:
            self.logger = logging.getLogger(f"plugin.{self.name}")
    
    async def _on_initialize(self) -> bool:
        """Initialize plugin with platform services"""
        try:
            self.logger.info(f"Initializing SimpleX plugin for {self.adapter.platform.value} platform")
            
            # Get platform services
            self.contact_service = self.require_service('contact_management')
            self.group_service = self.require_service('group_management')
            self.invite_service = self.require_service('invite_management')
            self.file_service = self.require_service('file_operations')
            
            # Get access to bot instance through adapter (for admin manager only)
            self.bot_instance = getattr(self.adapter, 'bot_instance', None)
            if not self.bot_instance:
                self.bot_instance = getattr(self.adapter, 'bot', None)
            
            self.logger.info(f"🔧 INIT DEBUG: bot_instance available: {bool(self.bot_instance)}")
            if self.bot_instance:
                self.logger.info(f"🔧 INIT DEBUG: bot_instance type: {type(self.bot_instance)}")
                self.logger.info(f"🔧 INIT DEBUG: bot_instance has admin_manager: {hasattr(self.bot_instance, 'admin_manager')}")
            
            if not self.bot_instance:
                self.logger.warning("Cannot access bot instance from adapter - some features may not work")
                self.admin_manager = None
            else:
                # Get admin manager (this will be moved to a service later)
                self.admin_manager = getattr(self.bot_instance, 'admin_manager', None)
                self.logger.info(f"🔧 INIT DEBUG: admin_manager retrieved: {bool(self.admin_manager)}")
                if self.admin_manager:
                    self.logger.info(f"🔧 INIT DEBUG: admin_manager type: {type(self.admin_manager)}")
                    if hasattr(self.admin_manager, 'admins'):
                        self.logger.info(f"🔧 INIT DEBUG: admin_manager.admins: {list(self.admin_manager.admins)}")
                
                if not self.admin_manager:
                    self.logger.warning("Cannot access admin manager - admin commands will not work")
                    # Create a mock admin manager for testing
                    self.logger.warning("🔧 INIT DEBUG: Creating MockAdminManager as fallback")
                    self.admin_manager = MockAdminManager()
            
            # Log available services
            available_services = self.get_available_services()
            self.logger.info(f"Available platform services: {available_services}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SimpleX plugin: {e}")
            return False
    
    def get_commands(self) -> List[str]:
        """Return list of commands this plugin handles"""
        return ["invite", "contacts", "groups", "debug", "admin", "reload_admin", "stats", "whoami"]
    
    async def handle_command(self, context: CommandContext) -> Optional[str]:
        """Handle commands for this plugin"""
        self.logger.info(f"Handling {context.command} command from {context.user_display_name} on {context.platform.value}")
        
        try:
            if context.command == "invite":
                return await self._handle_invite_command(context)
            elif context.command == "contacts":
                return await self._handle_contacts_command(context)
            elif context.command == "groups":
                return await self._handle_groups_command(context)
            elif context.command == "debug":
                return await self._handle_debug_command(context)
            elif context.command == "admin":
                return await self._handle_admin_command(context)
            elif context.command == "reload_admin":
                return await self._handle_reload_admin_command(context)
            elif context.command == "stats":
                return await self._handle_stats_command(context)
            elif context.command == "whoami":
                return await self._handle_whoami_command(context)
                
        except Exception as e:
            self.logger.error(f"Error handling {context.command} command: {str(e)}", exc_info=True)
            return f"❌ Error processing {context.command} command"
        
        return None
    
    async def _handle_invite_command(self, context: CommandContext) -> str:
        """Handle invite management commands"""
        # Check admin permissions
        if not self.admin_manager or not self.admin_manager.is_admin(context.user_display_name):
            return "Access denied. Only admins can manage invites."
        
        if not context.has_args:
            return """Invite commands:
!invite generate - Generate a one-time connection invite
!invite list - List pending invites
!invite revoke <invite_id> - Revoke a pending invite
!invite stats - Show invite statistics"""
        
        subcommand = context.args[0].lower()
        
        if subcommand == "generate":
            return await self._generate_invite(context)
        elif subcommand == "list":
            return await self._list_invites(context)
        elif subcommand == "revoke":
            return await self._revoke_invite(context)
        elif subcommand == "stats":
            return await self._invite_stats(context)
        else:
            return f"Unknown invite subcommand: {subcommand}"
    
    async def _generate_invite(self, context: CommandContext) -> str:
        """Generate connection invite using platform service"""
        if not self.invite_service:
            return "❌ Invite service not available"
        
        try:
            # Send progress message
            await self.adapter.send_message("🔄 Generating invite...", context)
            
            # Generate invite using platform service
            invite_link = await self.invite_service.generate_invite(context.user_display_name)
            
            if invite_link:
                response = f"""🔗 One-time connection invite generated:

{invite_link}

Share this link with the user and ask them to connect using:
/c {invite_link}

This invite will be auto-accepted when used and expires in 24 hours."""
                
                self.logger.info(f"🎫 INVITE: Generated invite for {context.user_display_name}")
                return response
            else:
                return "❌ Failed to generate invite. Check logs for details."
        
        except Exception as e:
            self.logger.error(f"Error generating invite: {e}")
            return f"❌ Error generating invite: {e}"
    
    async def _list_invites(self, context: CommandContext) -> str:
        """List pending invites using platform service"""
        if not self.invite_service:
            return "❌ Invite service not available"
        
        try:
            pending_invites = await self.invite_service.list_pending_invites()
            
            if not pending_invites:
                return "📋 No pending invites."
            
            response = "📋 Pending invites:\n\n"
            for invite in pending_invites:
                response += f"• ID: {invite.get('id', 'unknown')}\n"
                response += f"  Requested by: {invite.get('requested_by', 'unknown')}\n"
                if 'created_at' in invite:
                    response += f"  Created: {invite['created_at']}\n"
                if 'expires_at' in invite:
                    response += f"  Expires: {invite['expires_at']}\n"
                response += "\n"
            
            return response
        except Exception as e:
            self.logger.error(f"Error listing invites: {e}")
            return f"❌ Error listing invites: {e}"
    
    async def _revoke_invite(self, context: CommandContext) -> str:
        """Revoke an invite using platform service"""
        if context.arg_count < 2:
            return "Usage: !invite revoke <invite_id>"
        
        invite_id = context.args[1]
        
        if not self.invite_service:
            return "❌ Invite service not available"
        
        try:
            # For now, fall back to direct bot access since revoke isn't implemented in service yet
            if self.bot_instance and hasattr(self.bot_instance, 'invite_manager'):
                invite_manager = self.bot_instance.invite_manager
                
                if invite_manager.revoke_invite(invite_id):
                    return f"Invite {invite_id} revoked successfully."
                else:
                    return f"Invite {invite_id} not found."
            else:
                return "❌ Invite manager not available"
        except Exception as e:
            self.logger.error(f"Error revoking invite: {e}")
            return f"❌ Error revoking invite: {e}"
    
    async def _invite_stats(self, context: CommandContext) -> str:
        """Show invite statistics using platform service"""
        if not self.invite_service:
            return "❌ Invite service not available"
        
        try:
            # For now, fall back to direct bot access since stats aren't implemented in service yet
            if self.bot_instance and hasattr(self.bot_instance, 'invite_manager'):
                invite_manager = self.bot_instance.invite_manager
                stats = invite_manager.get_stats()
                
                return f"""📊 Invite Statistics:

Pending invites: {stats['pending_invites']}/{stats['max_pending_invites']}
Invite expiry: {stats['invite_expiry_hours']} hours"""
            else:
                return "❌ Invite manager not available"
        except Exception as e:
            self.logger.error(f"Error getting invite stats: {e}")
            return f"❌ Error getting invite stats: {e}"
    
    async def _handle_contacts_command(self, context: CommandContext) -> str:
        """Handle contact management commands"""
        # Check admin permissions
        self.logger.info(f"🔐 ADMIN CHECK: user_display_name='{context.user_display_name}', admin_manager={bool(self.admin_manager)}")
        if self.admin_manager:
            is_admin = self.admin_manager.is_admin(context.user_display_name)
            self.logger.info(f"🔐 ADMIN CHECK: is_admin={is_admin}")
        
        if not self.admin_manager or not self.admin_manager.is_admin(context.user_display_name):
            self.logger.warning(f"🔐 ADMIN DENIED: '{context.user_display_name}' attempted to access contacts")
            return "Access denied. Only admins can list contacts."
        
        if not context.has_args:
            return """Contact commands:
!contacts list - List all contacts
!contacts info <name> - Get contact details"""
        
        subcommand = context.args[0].lower()
        
        if subcommand == "list":
            return await self._list_contacts(context)
        elif subcommand == "info":
            return await self._contact_info(context)
        else:
            return f"Unknown contacts subcommand: {subcommand}"
    
    async def _list_contacts(self, context: CommandContext) -> str:
        """List all contacts using platform service"""
        if not self.contact_service:
            return "❌ Contact service not available"
        
        try:
            await self.adapter.send_message("🔄 Loading contacts...", context)
            
            contacts_info = await self.contact_service.get_contacts()
            
            if contacts_info:
                contact_list = []
                for i, contact in enumerate(contacts_info, 1):
                    name = contact.get('localDisplayName', 'Unknown')
                    contact_status = contact.get('contactStatus', 'unknown')
                    conn_status = 'disconnected'
                    if 'activeConn' in contact and contact['activeConn']:
                        conn_status = contact['activeConn'].get('connStatus', 'unknown')
                    contact_list.append(f"{i}. {name} (Contact: {contact_status}, Connection: {conn_status})")
                
                return f"📋 Bot Contacts ({len(contacts_info)} total):\n\n" + "\n".join(contact_list)
            else:
                return "No contacts found."
            
        except Exception as e:
            self.logger.error(f"Error listing contacts: {e}")
            return f"❌ Error listing contacts: {e}"
    
    async def _contact_info(self, context: CommandContext) -> str:
        """Get contact information using platform service"""
        if context.arg_count < 2:
            return "Usage: !contacts info <contact_name>"
        
        contact_to_check = " ".join(context.args[1:])
        
        if not self.contact_service:
            return "❌ Contact service not available"
        
        try:
            await self.adapter.send_message(f"🔄 Getting info for '{contact_to_check}'...", context)
            
            contact_info = await self.contact_service.get_contact_info(contact_to_check)
            
            if contact_info:
                info_text = f"📋 Contact Info for {contact_to_check}:\n\n"
                info_text += f"Display Name: {contact_info.get('localDisplayName', 'Unknown')}\n"
                info_text += f"Profile Name: {contact_info.get('profile', {}).get('displayName', 'Unknown')}\n"
                info_text += f"Connection: {contact_info.get('activeConn', 'Unknown')}\n"
                info_text += f"Created: {contact_info.get('createdAt', 'Unknown')}"
                return info_text
            else:
                return f"Contact '{contact_to_check}' not found."
            
        except Exception as e:
            self.logger.error(f"Error getting contact info: {e}")
            return f"❌ Error getting contact info: {e}"
    
    async def _handle_groups_command(self, context: CommandContext) -> str:
        """Handle group management commands"""
        # Check admin permissions
        if not self.admin_manager or not self.admin_manager.is_admin(context.user_display_name):
            return "Access denied. Only admins can list groups."
        
        if not context.has_args:
            return """Group commands:
!groups list - List all groups
!groups info <name> - Get group details
!groups invite <name> - Generate group invite link"""
        
        subcommand = context.args[0].lower()
        
        if subcommand == "list":
            return await self._list_groups(context)
        elif subcommand == "info":
            return await self._group_info(context)
        elif subcommand == "invite":
            return await self._group_invite(context)
        else:
            return f"Unknown groups subcommand: {subcommand}"
    
    async def _list_groups(self, context: CommandContext) -> str:
        """List all groups using platform service"""
        if not self.group_service:
            return "❌ Group service not available"
        
        try:
            await self.adapter.send_message("🔄 Loading groups...", context)
            
            groups_info = await self.group_service.get_groups()
            
            if groups_info:
                group_list = []
                for i, group in enumerate(groups_info, 1):
                    name = group.get('localDisplayName', group.get('displayName', 'Unknown'))
                    members = group.get('membership', {}).get('memberRole', 'Unknown')
                    group_list.append(f"{i}. {name} (Role: {members})")
                
                return f"📋 Bot Groups ({len(groups_info)} total):\n\n" + "\n".join(group_list)
            else:
                return "No groups found."
            
        except Exception as e:
            self.logger.error(f"Error listing groups: {e}")
            return f"❌ Error listing groups: {e}"
    
    async def _group_info(self, context: CommandContext) -> str:
        """Get group information using platform service"""
        if context.arg_count < 2:
            return "Usage: !groups info <group_name>"
        
        group_to_check = " ".join(context.args[1:])
        
        if not self.group_service:
            return "❌ Group service not available"
        
        try:
            await self.adapter.send_message(f"🔄 Getting info for '{group_to_check}'...", context)
            
            group_info = await self.group_service.get_group_info(group_to_check)
            
            if group_info:
                info_text = f"📋 Group Info for {group_to_check}:\n\n"
                info_text += f"Display Name: {group_info.get('localDisplayName', group_info.get('displayName', 'Unknown'))}\n"
                info_text += f"Description: {group_info.get('groupProfile', {}).get('description', 'None')}\n"
                info_text += f"Member Role: {group_info.get('membership', {}).get('memberRole', 'Unknown')}\n"
                info_text += f"Group ID: {group_info.get('groupId', 'Unknown')}"
                return info_text
            else:
                return f"Group '{group_to_check}' not found."
            
        except Exception as e:
            self.logger.error(f"Error getting group info: {e}")
            return f"❌ Error getting group info: {e}"
    
    async def _group_invite(self, context: CommandContext) -> str:
        """Generate group invite link"""
        if context.arg_count < 2:
            return "Usage: !groups invite <group_name>"
        
        group_name = " ".join(context.args[1:])
        
        if not (self.bot_instance and hasattr(self.bot_instance, 'websocket_manager')):
            return "WebSocket manager not available."
        
        ws_manager = self.bot_instance.websocket_manager
        
        try:
            await self.adapter.send_message(f"🔄 Generating group invite for '{group_name}'...", context)
            
            # Send command to generate group invite (fixed format)
            response = await ws_manager.send_command(f"/g {group_name} /add", wait_for_response=False)
            
            if response:
                invite_link = self._parse_group_invite_response(response)
                if invite_link:
                    return f"""🔗 Group invite generated for '{group_name}':

{invite_link}

Share this link to invite users to the group.
Note: Group invite permissions depend on your role in the group."""
                else:
                    return f"Failed to generate invite for group '{group_name}'. Check if you have permission to invite members."
            else:
                return f"Failed to generate invite for group '{group_name}'."
                
        except Exception as e:
            return f"Error generating group invite: {type(e).__name__}: {e}"
    
    async def _handle_debug_command(self, context: CommandContext) -> str:
        """Handle debug commands"""
        # Check admin permissions
        if not self.admin_manager or not self.admin_manager.is_admin(context.user_display_name):
            return "Access denied. Only admins can use debug commands."
        
        if not context.has_args:
            return """Debug commands:
!debug websocket - Test WebSocket connection
!debug ping - Send test ping to SimpleX CLI
!debug restart - Force restart SimpleX CLI process"""
        
        subcommand = context.args[0].lower()
        
        if subcommand == "websocket":
            return await self._debug_websocket(context)
        elif subcommand == "ping":
            return await self._debug_ping(context)
        elif subcommand == "restart":
            return await self._debug_restart(context)
        else:
            return f"Unknown debug subcommand: {subcommand}"
    
    async def _debug_websocket(self, context: CommandContext) -> str:
        """Debug WebSocket connection"""
        if self.bot_instance and hasattr(self.bot_instance, 'websocket_manager'):
            ws_manager = self.bot_instance.websocket_manager
            ws_id = id(ws_manager.websocket) if ws_manager.websocket else None
            
            return f"""🔌 WebSocket Debug Info:
ID: {ws_id}
Connected: {ws_manager.websocket is not None}
URL: {ws_manager.websocket_url}
Pending requests: {len(ws_manager.pending_requests)}"""
        else:
            return "WebSocket manager not available"
    
    async def _debug_ping(self, context: CommandContext) -> str:
        """Send test ping to CLI"""
        if not (self.bot_instance and hasattr(self.bot_instance, 'websocket_manager')):
            return "WebSocket manager not available"
        
        ws_manager = self.bot_instance.websocket_manager
        
        await self.adapter.send_message("🏓 Testing SimpleX CLI commands...", context)
        
        # Test valid SimpleX CLI commands
        test_commands = [
            "/help",            # Show available commands
            "/contacts",        # List contacts
            "/groups",          # List groups
            "/c",               # Contact shorthand
            "/g",               # Groups shorthand
            "/connect",         # Connection command
        ]
        
        working_commands = []
        for cmd in test_commands:
            try:
                self.logger.info(f"🔍 Testing CLI command: {cmd}")
                response = await ws_manager.send_command(cmd, wait_for_response=False)
                if response:
                    working_commands.append(cmd)
                    self.logger.info(f"✅ Command {cmd} works!")
                else:
                    self.logger.info(f"❌ Command {cmd} timeout")
            except Exception as e:
                self.logger.info(f"❌ Command {cmd} failed: {e}")
        
        if working_commands:
            return f"🏓 CLI responding! Working commands: {', '.join(working_commands)}"
        else:
            return "🏓 CLI not responding to any test commands"
    
    async def _debug_restart(self, context: CommandContext) -> str:
        """Force restart SimpleX CLI"""
        if not (self.bot_instance and hasattr(self.bot_instance, 'websocket_manager')):
            return "WebSocket manager not available"
        
        ws_manager = self.bot_instance.websocket_manager
        
        await self.adapter.send_message("🔄 Force restarting SimpleX CLI process...", context)
        
        try:
            if await ws_manager.restart_cli_process():
                return "✅ CLI restart successful! User messages should now flow."
            else:
                return "❌ CLI restart failed. Check logs for details."
                
        except Exception as e:
            return f"🔄 Restart failed: {type(e).__name__}: {e}"
    
    # Response parsing helper methods
    def _parse_contacts_response(self, response):
        """Parse SimpleX CLI /contacts command response"""
        try:
            self.logger.info(f"Parsing contacts response: {type(response)}: {str(response)[:200]}...")
            
            if isinstance(response, dict):
                resp = response.get('resp', {})
                if 'Right' in resp:
                    actual_resp = resp['Right']
                    # Check if this is a contactsList response
                    if isinstance(actual_resp, dict) and actual_resp.get('type') == 'contactsList':
                        contacts = actual_resp.get('contacts', [])
                        self.logger.info(f"Found {len(contacts)} contacts in response")
                        return contacts
                # Handle error responses
                elif 'Left' in resp:
                    error_info = resp['Left']
                    self.logger.error(f"CLI error response: {error_info}")
                    return []
            
            return []
        except Exception as e:
            self.logger.error(f"Error parsing contacts response: {e}")
            return []
    
    def _parse_contact_info_response(self, response):
        """Parse SimpleX CLI contact info response"""
        try:
            if isinstance(response, dict):
                resp = response.get('resp', {})
                if 'Right' in resp:
                    actual_resp = resp['Right']
                    if 'contact' in actual_resp:
                        return actual_resp['contact']
                    elif isinstance(actual_resp, dict) and 'localDisplayName' in actual_resp:
                        return actual_resp
            return None
        except Exception as e:
            self.logger.error(f"Error parsing contact info response: {e}")
            return None
    
    def _parse_groups_response(self, response):
        """Parse SimpleX CLI /groups command response"""
        try:
            self.logger.info(f"Parsing groups response: {type(response)}: {str(response)[:200]}...")
            
            if isinstance(response, dict):
                resp = response.get('resp', {})
                if 'Right' in resp:
                    actual_resp = resp['Right']
                    # Check if this is a groupsList response
                    if isinstance(actual_resp, dict) and actual_resp.get('type') == 'groupsList':
                        groups = actual_resp.get('groups', [])
                        self.logger.info(f"Found {len(groups)} groups in response")
                        return groups
                # Handle error responses
                elif 'Left' in resp:
                    error_info = resp['Left']
                    self.logger.error(f"CLI error response: {error_info}")
                    return []
            
            return []
        except Exception as e:
            self.logger.error(f"Error parsing groups response: {e}")
            return []
    
    def _parse_group_info_response(self, response):
        """Parse SimpleX CLI group info response"""
        try:
            if isinstance(response, dict):
                resp = response.get('resp', {})
                if 'Right' in resp:
                    actual_resp = resp['Right']
                    if 'group' in actual_resp:
                        return actual_resp['group']
                    elif isinstance(actual_resp, dict) and 'displayName' in actual_resp:
                        return actual_resp
            return None
        except Exception as e:
            self.logger.error(f"Error parsing group info response: {e}")
            return None
    
    def _parse_group_invite_response(self, response):
        """Parse SimpleX CLI group invite response to extract invite link"""
        try:
            if isinstance(response, dict):
                resp = response.get('resp', {})
                if 'Right' in resp:
                    actual_resp = resp['Right']
                    # Look for invitation link in various possible fields
                    if isinstance(actual_resp, str):
                        if 'https://simplex.chat/invitation' in actual_resp:
                            import re
                            match = re.search(r'https://simplex\.chat/invitation[^\s]*', actual_resp)
                            if match:
                                return match.group(0)
                    elif isinstance(actual_resp, dict):
                        for key, value in actual_resp.items():
                            if isinstance(value, str) and 'https://simplex.chat/invitation' in value:
                                import re
                                match = re.search(r'https://simplex\.chat/invitation[^\s]*', value)
                                if match:
                                    return match.group(0)
            return None
        except Exception as e:
            self.logger.error(f"Error parsing group invite response: {e}")
            return None
    
    async def _handle_admin_command(self, context: CommandContext) -> str:
        """Handle admin management commands"""
        # Debug logging to track the admin check issue
        self.logger.info(f"Handling admin command from {context.user_display_name} on {context.platform.value}")
        self.logger.info(f"🔍 ADMIN DEBUG: user_id='{context.user_id}', user_display_name='{context.user_display_name}', chat_id='{context.chat_id}'")
        
        # Check admin permissions
        if not self.admin_manager or not self.admin_manager.is_admin(context.user_display_name):
            return "Access denied. Only admins can use admin commands."
        
        if not context.has_args:
            return """Admin commands:
!admin list - List all admins
!admin add <username> - Add admin with full permissions
!admin remove <username> - Remove admin
!admin permissions <username> - Show user permissions
!admin reload - Reload admin config"""
        
        subcommand = context.args[0].lower()
        
        if subcommand == "list":
            admins = self.admin_manager.list_admins()
            if not admins:
                return "No admins configured."
            
            admin_list = []
            for admin_name, commands in admins.items():
                cmd_str = "all commands" if "*" in commands else ", ".join(commands)
                admin_list.append(f"• {admin_name}: {cmd_str}")
            
            return "Current admins:\n" + "\n".join(admin_list)
        
        elif subcommand == "add":
            if context.arg_count < 2:
                return "Usage: !admin add <username>"
            
            username = context.args[1]
            if self.admin_manager.add_admin(username):
                return f"Added {username} as admin with full permissions."
            else:
                return f"Failed to add {username} as admin."
        
        elif subcommand == "remove":
            if context.arg_count < 2:
                return "Usage: !admin remove <username>"
            
            username = context.args[1]
            if username == context.user_display_name:
                return "You cannot remove yourself as admin."
            
            if self.admin_manager.remove_admin(username):
                return f"Removed {username} from admins."
            else:
                return f"Failed to remove {username} or user not found."
        
        elif subcommand == "permissions":
            if context.arg_count < 2:
                return "Usage: !admin permissions <username>"
            
            username = context.args[1]
            perms = self.admin_manager.get_user_permissions(username)
            
            if perms['is_admin']:
                cmd_str = "all commands" if "*" in perms['admin_commands'] else ", ".join(perms['admin_commands'])
                return f"User {username} is an admin with permissions: {cmd_str}"
            else:
                return f"User {username} is not an admin. Can only run public commands: {', '.join(perms['public_commands'])}"
        
        elif subcommand == "reload":
            self.admin_manager.reload_config()
            return "Admin configuration reloaded."
        
        else:
            return f"Unknown admin subcommand: {subcommand}"
    
    async def _handle_reload_admin_command(self, context: CommandContext) -> str:
        """Handle admin configuration reload"""
        # Check admin permissions
        if not self.admin_manager or not self.admin_manager.is_admin(context.user_display_name):
            return "Access denied. Only admins can reload admin config."
        
        self.admin_manager.reload_config()
        return "Admin configuration reloaded successfully."
    
    async def _handle_stats_command(self, context: CommandContext) -> str:
        """Handle stats command"""
        # Check admin permissions
        if not self.admin_manager or not self.admin_manager.is_admin(context.user_display_name):
            return "Access denied. Only admins can view stats."
        
        if not (self.bot_instance and hasattr(self.bot_instance, 'websocket_manager')):
            return "WebSocket manager not available for stats."
        
        ws_manager = self.bot_instance.websocket_manager
        
        # Get basic stats
        stats_text = f"""📊 **SimpleX Bot Statistics**

**WebSocket Status:**
• Connected: {'✅ Yes' if ws_manager.websocket else '❌ No'}
• URL: {ws_manager.websocket_url}
• Pending Requests: {len(ws_manager.pending_requests)}

**Plugin Status:**
• Loaded Plugins: {len(getattr(self.adapter.bot, 'plugin_manager', {}).plugins) if hasattr(self.adapter.bot, 'plugin_manager') else 'Unknown'}
• Plugin System: {'✅ Active' if hasattr(self.adapter.bot, 'plugin_manager') else '❌ Inactive'}

**Admin Status:**
• Total Admins: {len(self.admin_manager.list_admins())}
• Admin Config: {'✅ Loaded' if self.admin_manager else '❌ Not Available'}"""

        return stats_text
    
    async def _handle_whoami_command(self, context: CommandContext) -> str:
        """Debug command to show user identity and admin status"""
        try:
            user_info = f"""🔍 **User Identity Debug**
            
**User Display Name:** '{context.user_display_name}'
**User ID:** '{context.user_id}'
**Chat ID:** '{context.chat_id}'
**Platform:** {context.platform.value}

**Admin Manager Available:** {bool(self.admin_manager)}
**Admin Manager Type:** {type(self.admin_manager).__name__ if self.admin_manager else 'None'}
"""
            
            if self.admin_manager:
                is_admin = self.admin_manager.is_admin(context.user_display_name)
                admins_list = list(self.admin_manager.admins) if hasattr(self.admin_manager, 'admins') else []
                user_info += f"""
**Is Admin:** {is_admin}
**All Admins:** {admins_list}
**Exact Match Check:** '{context.user_display_name}' in {admins_list}
"""
            
            return user_info
            
        except Exception as e:
            self.logger.error(f"Error in whoami command: {e}")
            return f"❌ Error in whoami command: {e}"

    async def cleanup(self):
        """Cleanup when plugin is unloaded"""
        self.logger.info("SimpleX plugin cleanup completed")