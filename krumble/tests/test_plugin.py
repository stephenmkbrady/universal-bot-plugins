#!/usr/bin/env python3
"""
Comprehensive test suite for Krumble plugin
Tests plugin initialization, container management, API communication, and core functionality
"""

import asyncio
import sys
import os
import subprocess
import time
import json
from pathlib import Path
import requests
import tempfile
import yaml

# Add the project root to the path
try:
    plugin_dir = Path(__file__).parent.parent
    project_root = plugin_dir.parent.parent.parent
except NameError:
    # Handle case when __file__ is not defined (e.g., running in exec)
    plugin_dir = Path("/app/plugins/external/krumble")
    project_root = Path("/app")
sys.path.insert(0, str(project_root))

from plugins.external.krumble.plugin import UniversalKrumblePlugin
from plugins.universal_plugin_base import CommandContext, BotPlatform


class MockAdapter:
    """Mock adapter for testing"""
    def __init__(self):
        self.platform = BotPlatform.SIMPLEX
        self.sent_messages = []
        
        # Mock bot for plugin manager access
        class MockBot:
            def __init__(self):
                self.plugin_manager = None
        self.bot = MockBot()
    
    async def send_message(self, message: str, context: CommandContext) -> bool:
        print(f"📤 Mock message to {context.chat_id}: {message[:100]}...")
        self.sent_messages.append((context.chat_id, message))
        return True
    
    async def send_file(self, file_path: str, context: CommandContext, caption: str = "") -> bool:
        print(f"📤 Mock file {file_path} to {context.chat_id}")
        return True


class KrumblePluginTester:
    def __init__(self):
        self.plugin = None
        self.adapter = None
        self.container_running = False
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
        
    async def test_plugin_creation(self):
        """Test basic plugin creation and properties"""
        print("\n🧪 Testing Plugin Creation")
        print("-" * 40)
        
        try:
            self.plugin = UniversalKrumblePlugin()
            self.log_test("Plugin instantiation", True, f"Created plugin: {self.plugin.name}")
            
            # Test basic properties
            self.log_test("Plugin name", self.plugin.name == "krumble", f"Name: {self.plugin.name}")
            self.log_test("Requires container", self.plugin.requires_container() == True, "Container required")
            commands = self.plugin.get_commands()
            expected_commands = ['krumble', 'kmonitor', 'klist', 'kadd', 'kremove', 'kstatus', 'khelp', 'kcheck']
            self.log_test("Commands available", all(cmd in commands for cmd in expected_commands), f"Commands: {commands}")
            self.log_test("Docker compose path", self.plugin.get_docker_compose_path().exists(), f"Path: {self.plugin.get_docker_compose_path()}")
            
        except Exception as e:
            self.log_test("Plugin creation", False, f"Error: {e}")
            return False
            
        return True
    
    async def test_container_operations(self):
        """Test container lifecycle operations"""
        print("\n🐳 Testing Container Operations")
        print("-" * 40)
        
        if not self.plugin:
            self.log_test("Container operations", False, "Plugin not created")
            return False
        
        # Test container stop (cleanup any existing)
        try:
            await self.plugin.stop_services()
            self.log_test("Container stop", True, "Stopped any existing containers")
        except Exception as e:
            self.log_test("Container stop", False, f"Stop error: {e}")
        
        # Test container start
        try:
            success = await self.plugin.start_services()
            self.log_test("Container start", success, "Started plugin containers")
            if success:
                self.container_running = True
                
                # Wait a bit for container to fully start
                await asyncio.sleep(5)
                
        except Exception as e:
            self.log_test("Container start", False, f"Start error: {e}")
            return False
        
        # Test container status
        try:
            status = await self.plugin.get_container_status()
            containers = status.get('containers', [])
            self.log_test("Container status", len(containers) > 0, f"Found {len(containers)} containers")
            
            # Log container details
            for container in containers:
                name = container.get('Name', 'Unknown')
                state = container.get('State', 'Unknown')
                print(f"   📦 Container: {name} - State: {state}")
                
        except Exception as e:
            self.log_test("Container status", False, f"Status error: {e}")
        
        return self.container_running
    
    async def test_health_check(self):
        """Test plugin health check"""
        print("\n💓 Testing Health Check")
        print("-" * 40)
        
        if not self.container_running:
            self.log_test("Health check", False, "Container not running")
            return False
        
        # Test health check multiple times with backoff
        for attempt in range(3):
            try:
                healthy = await self.plugin.health_check()
                if healthy:
                    self.log_test("Health check", True, f"Plugin healthy on attempt {attempt + 1}")
                    return True
                else:
                    print(f"   ⏳ Health check failed, attempt {attempt + 1}/3, waiting...")
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"   ⚠️ Health check error on attempt {attempt + 1}: {e}")
                await asyncio.sleep(2)
        
        self.log_test("Health check", False, "Plugin unhealthy after 3 attempts")
        return False
    
    async def test_http_api(self):
        """Test HTTP API endpoints"""
        print("\n🌐 Testing HTTP API")
        print("-" * 40)
        
        if not self.container_running:
            self.log_test("HTTP API", False, "Container not running")
            return False
        
        # Test health endpoint via HTTP directly (use container hostname)
        base_url = "http://krumble-scraper:8001"
        try:
            response = requests.get(f"{base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("HTTP health endpoint", True, f"Status: {data.get('status')}")
                service_name = data.get('service', '')
                self.log_test("Service name correct", 'krumble' in service_name, f"Service: {service_name}")
            else:
                self.log_test("HTTP health endpoint", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("HTTP health endpoint", False, f"HTTP error: {e}")
        
        # Test status endpoint
        try:
            response = requests.get(f"{base_url}/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("HTTP status endpoint", True, f"Service: {data.get('service')}")
            else:
                self.log_test("HTTP status endpoint", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("HTTP status endpoint", False, f"HTTP error: {e}")
        
        # Test scraping endpoint with Rumble URL
        try:
            payload = {
                "channel_url": "https://rumble.com/c/madattheinternet/livestreams",
                "options": {"detect_changes": True}
            }
            response = requests.post(f"{base_url}/scrape", json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                self.log_test("HTTP scrape endpoint (Rumble)", True, f"Success: {data.get('success')}")
            else:
                self.log_test("HTTP scrape endpoint (Rumble)", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("HTTP scrape endpoint (Rumble)", False, f"HTTP error: {e}")
        
        # Test scraping endpoint with Kick URL
        try:
            payload = {
                "channel_url": "https://kick.com/kinocasinogaming",
                "options": {"detect_changes": True}
            }
            response = requests.post(f"{base_url}/scrape", json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                self.log_test("HTTP scrape endpoint (Kick)", True, f"Success: {data.get('success')}")
            else:
                self.log_test("HTTP scrape endpoint (Kick)", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("HTTP scrape endpoint (Kick)", False, f"HTTP error: {e}")
    
    async def test_plugin_initialization(self):
        """Test plugin initialization with adapter"""
        print("\n🚀 Testing Plugin Initialization")
        print("-" * 40)
        
        if not self.plugin:
            self.log_test("Plugin initialization", False, "Plugin not created")
            return False
        
        try:
            self.adapter = MockAdapter()
            success = await self.plugin.initialize(self.adapter)
            self.log_test("Plugin initialization", success, "Plugin initialized with adapter")
            
            if success:
                # Test that adapter is set
                self.log_test("Adapter assignment", self.plugin.adapter is not None, "Adapter assigned")
                
        except Exception as e:
            self.log_test("Plugin initialization", False, f"Init error: {e}")
            return False
        
        return True
    
    async def test_channel_management(self):
        """Test adding, listing, and removing channels"""
        print("\n📺 Testing Channel Management")
        print("-" * 40)
        
        if not self.adapter:
            self.log_test("Channel management", False, "Plugin not initialized")
            return False
        
        # Create test context
        test_context = CommandContext(
            command="kadd",
            args=["madattheinternet"],
            args_raw="madattheinternet",
            user_id="test_user",
            chat_id="test_chat_12345",
            user_display_name="Test User",
            platform=BotPlatform.SIMPLEX,
            raw_message={}
        )
        
        # Test adding a Rumble channel
        try:
            response = await self.plugin.handle_command(test_context)
            self.log_test("Add Rumble channel", response is not None and "Added" in response, f"Response: {response[:100] if response else 'None'}...")
        except Exception as e:
            self.log_test("Add Rumble channel", False, f"Add error: {e}")
        
        # Test adding a Kick channel
        try:
            kick_context = CommandContext(
                command="kadd",
                args=["https://kick.com/kinocasinogaming"],
                args_raw="https://kick.com/kinocasinogaming",
                user_id="test_user",
                chat_id="test_chat_12345",
                user_display_name="Test User",
                platform=BotPlatform.SIMPLEX,
                raw_message={}
            )
            response = await self.plugin.handle_command(kick_context)
            self.log_test("Add Kick channel", response is not None and "Added" in response, f"Response: {response[:100] if response else 'None'}...")
        except Exception as e:
            self.log_test("Add Kick channel", False, f"Add error: {e}")
        
        # Test listing channels
        try:
            list_context = CommandContext(
                command="klist",
                args=[],
                args_raw="",
                user_id="test_user",
                chat_id="test_chat_12345",
                user_display_name="Test User",
                platform=BotPlatform.SIMPLEX,
                raw_message={}
            )
            response = await self.plugin.handle_command(list_context)
            self.log_test("List channels", response is not None and "Monitored Channels" in response, f"Response: {response[:100] if response else 'None'}...")
        except Exception as e:
            self.log_test("List channels", False, f"List error: {e}")
        
        # Test manual check
        try:
            check_context = CommandContext(
                command="kcheck",
                args=["madattheinternet"],
                args_raw="madattheinternet",
                user_id="test_user",
                chat_id="test_chat_12345",
                user_display_name="Test User",
                platform=BotPlatform.SIMPLEX,
                raw_message={}
            )
            response = await self.plugin.handle_command(check_context)
            self.log_test("Manual check", response is not None, f"Response: {response[:100] if response else 'None'}...")
        except Exception as e:
            self.log_test("Manual check", False, f"Check error: {e}")
        
        # Test removing a channel
        try:
            remove_context = CommandContext(
                command="kremove",
                args=["madattheinternet"],
                args_raw="madattheinternet",
                user_id="test_user",
                chat_id="test_chat_12345",
                user_display_name="Test User",
                platform=BotPlatform.SIMPLEX,
                raw_message={}
            )
            response = await self.plugin.handle_command(remove_context)
            self.log_test("Remove channel", response is not None and ("Removed" in response or "not found" in response), f"Response: {response[:100] if response else 'None'}...")
        except Exception as e:
            self.log_test("Remove channel", False, f"Remove error: {e}")
    
    async def test_plugin_commands(self):
        """Test plugin command handling"""
        print("\n⌨️ Testing Plugin Commands")
        print("-" * 40)
        
        if not self.adapter:
            self.log_test("Plugin commands", False, "Plugin not initialized")
            return False
        
        # Test help command
        try:
            help_text = self.plugin.get_help()
            self.log_test("Help command", len(help_text) > 0 and "krumble" in help_text.lower(), f"Help text length: {len(help_text)}")
        except Exception as e:
            self.log_test("Help command", False, f"Help error: {e}")
        
        # Test status command
        try:
            context = CommandContext(
                command="kstatus",
                args=[],
                args_raw="",
                user_id="test_user",
                chat_id="test_chat",
                user_display_name="Test User",
                platform=BotPlatform.SIMPLEX,
                raw_message={}
            )
            
            response = await self.plugin.handle_command(context)
            self.log_test("Status command", response is not None and "Status" in response, f"Response length: {len(response) if response else 0}")
            
        except Exception as e:
            self.log_test("Status command", False, f"Command error: {e}")
        
        # Test krumble help command
        try:
            context = CommandContext(
                command="krumble",
                args=["help"],
                args_raw="help",
                user_id="test_user",
                chat_id="test_chat",
                user_display_name="Test User",
                platform=BotPlatform.SIMPLEX,
                raw_message={}
            )
            
            response = await self.plugin.handle_command(context)
            self.log_test("Krumble help command", response is not None and "Krumble" in response, f"Response length: {len(response) if response else 0}")
            
        except Exception as e:
            self.log_test("Krumble help command", False, f"Command error: {e}")
    
    async def test_platform_detection(self):
        """Test platform detection logic"""
        print("\n🔍 Testing Platform Detection")
        print("-" * 40)
        
        if not self.plugin:
            self.log_test("Platform detection", False, "Plugin not created")
            return False
        
        # Test Rumble URL detection
        rumble_result = self.plugin._parse_channel_info("https://rumble.com/c/madattheinternet")
        self.log_test("Rumble URL detection", rumble_result and rumble_result['platform'] == 'rumble', f"Result: {rumble_result}")
        
        # Test Kick URL detection  
        kick_result = self.plugin._parse_channel_info("https://kick.com/kinocasinogaming")
        self.log_test("Kick URL detection", kick_result and kick_result['platform'] == 'kick', f"Result: {kick_result}")
        
        # Test direct channel name (defaults to Rumble)
        direct_result = self.plugin._parse_channel_info("madattheinternet")
        self.log_test("Direct channel name", direct_result and direct_result['platform'] == 'rumble', f"Result: {direct_result}")
        
        # Test invalid URL
        invalid_result = self.plugin._parse_channel_info("https://youtube.com/invalid")
        self.log_test("Invalid URL rejection", invalid_result is None, f"Result: {invalid_result}")
    
    async def test_container_logs(self):
        """Check container logs for errors"""
        print("\n📋 Checking Container Logs")
        print("-" * 40)
        
        try:
            # Find the running krumble container
            ps_result = subprocess.run([
                "docker", "ps", "--filter", "name=krumble-scraper", "--format", "{{.Names}}"
            ], capture_output=True, text=True)
            
            if ps_result.returncode != 0 or not ps_result.stdout.strip():
                self.log_test("Container logs", False, "No krumble containers found")
                return
                
            container_name = ps_result.stdout.strip().split('\n')[0]
            
            # Get container logs
            result = subprocess.run([
                "docker", "logs", container_name
            ], capture_output=True, text=True, timeout=10)
            
            logs = result.stdout + result.stderr
            
            # Check for errors
            error_keywords = ["error", "failed", "exception", "cannot", "timeout"]
            errors_found = []
            
            for line in logs.split('\n'):
                line_lower = line.lower()
                for keyword in error_keywords:
                    if keyword in line_lower and line.strip():
                        errors_found.append(line.strip())
            
            if errors_found:
                self.log_test("Container logs", False, f"Found {len(errors_found)} error lines")
                for error in errors_found[:5]:  # Show first 5 errors
                    print(f"   🚨 {error}")
            else:
                self.log_test("Container logs", True, "No obvious errors in logs")
                
            # Show last few log lines for context
            log_lines = logs.strip().split('\n')
            if log_lines:
                print(f"   📝 Last few log lines:")
                for line in log_lines[-3:]:
                    if line.strip():
                        print(f"   {line}")
                        
        except Exception as e:
            self.log_test("Container logs", False, f"Log check error: {e}")
    
    async def cleanup(self):
        """Cleanup test environment"""
        print("\n🧹 Cleanup")
        print("-" * 40)
        
        if self.plugin:
            try:
                await self.plugin.cleanup()
                self.log_test("Plugin cleanup", True, "Plugin cleaned up")
            except Exception as e:
                self.log_test("Plugin cleanup", False, f"Cleanup error: {e}")
        
        # Clean up test data files
        try:
            data_dir = plugin_dir / "data"
            if data_dir.exists():
                for test_file in data_dir.glob("test_*.yml"):
                    test_file.unlink()
                self.log_test("Test data cleanup", True, "Test data files removed")
        except Exception as e:
            self.log_test("Test data cleanup", False, f"Data cleanup error: {e}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("🎯 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        print(f"Success rate: {(passed/total)*100:.1f}%" if total > 0 else "No tests run")
        
        if passed < total:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   • {result['test']}: {result['message']}")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
        
        return passed == total


async def run_all_tests():
    """Run all plugin tests"""
    print("🧪 KRUMBLE PLUGIN TEST SUITE")
    print("=" * 60)
    
    tester = KrumblePluginTester()
    
    try:
        # Run tests in sequence
        await tester.test_plugin_creation()
        await tester.test_container_operations()
        await tester.test_health_check()
        await tester.test_http_api()
        await tester.test_plugin_initialization()
        await tester.test_platform_detection()
        await tester.test_plugin_commands()
        await tester.test_channel_management()
        await tester.test_container_logs()
        
    finally:
        await tester.cleanup()
    
    # Print summary
    all_passed = tester.print_summary()
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)