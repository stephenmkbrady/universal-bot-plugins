#!/usr/bin/env python3
"""
Simple test script for the Loupe plugin (without external dependencies)
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def test_plugin_structure():
    """Test plugin file structure"""
    plugin_dir = Path(__file__).parent
    
    required_files = ['plugin.py', 'config.yml', 'requirements.txt', '__init__.py']
    
    print("🔍 Testing plugin structure...")
    for file in required_files:
        file_path = plugin_dir / file
        if file_path.exists():
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
    
    print("\n📋 Plugin files:")
    for file in plugin_dir.iterdir():
        if file.is_file():
            size = file.stat().st_size
            print(f"  {file.name} ({size} bytes)")

def test_config_loading():
    """Test configuration loading"""
    print("\n🔍 Testing configuration...")
    
    try:
        import yaml
        config_file = Path(__file__).parent / 'config.yml'
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        sites = config.get('sites', {})
        print(f"✅ Configuration loaded successfully")
        print(f"✅ Found {len(sites)} configured sites:")
        
        for site_id, site_config in sites.items():
            name = site_config.get('name', site_id)
            url = site_config.get('url', 'N/A')
            selectors = len(site_config.get('selectors', {}))
            print(f"  • {site_id}: {name} ({selectors} selectors)")
    
    except ImportError:
        print("❌ PyYAML not available, skipping config test")
    except Exception as e:
        print(f"❌ Error loading config: {e}")

def test_basic_plugin_properties():
    """Test basic plugin properties without imports"""
    print("\n🔍 Testing basic plugin structure...")
    
    plugin_file = Path(__file__).parent / 'plugin.py'
    content = plugin_file.read_text()
    
    # Check for essential components
    checks = [
        ('class LoupePlugin', 'Plugin class defined'),
        ('def get_commands', 'get_commands method defined'),
        ('def handle_command', 'handle_command method defined'),
        ('loupe', 'Command name present'),
        ('aiohttp', 'HTTP client import'),
        ('BeautifulSoup', 'HTML parser import'),
        ('html2text', 'HTML to text converter import')
    ]
    
    for check, description in checks:
        if check in content:
            print(f"✅ {description}")
        else:
            print(f"❌ {description}")

if __name__ == "__main__":
    print("🧪 Loupe Plugin Test Suite\n")
    
    test_plugin_structure()
    test_config_loading()
    test_basic_plugin_properties()
    
    print("\n✅ Basic tests completed!")
    print("\n💡 To fully test the plugin:")
    print("   1. Install dependencies: pip install -r requirements.txt")
    print("   2. Restart the bot to load the plugin")
    print("   3. Use !loupe commands in chat")