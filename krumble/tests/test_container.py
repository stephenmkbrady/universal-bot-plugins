#!/usr/bin/env python3
"""
Container-specific tests for Rumble plugin
Tests Docker operations, networking, and service startup
"""

import subprocess
import time
import json
import requests
from pathlib import Path


class ContainerTester:
    def __init__(self):
        self.plugin_dir = Path(__file__).parent.parent
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
    
    def test_docker_compose_file(self):
        """Test docker-compose.yml file validity"""
        print("\n📄 Testing Docker Compose File")
        print("-" * 40)
        
        compose_file = self.plugin_dir / "docker-compose.yml"
        
        # Check file exists
        self.log_test("Compose file exists", compose_file.exists(), str(compose_file))
        
        if not compose_file.exists():
            return False
        
        # Test compose file syntax
        try:
            result = subprocess.run([
                "docker", "compose", "-f", str(compose_file), "config"
            ], capture_output=True, text=True, cwd=self.plugin_dir)
            
            if result.returncode == 0:
                self.log_test("Compose syntax", True, "Valid YAML syntax")
            else:
                self.log_test("Compose syntax", False, f"Syntax error: {result.stderr}")
                return False
        except Exception as e:
            self.log_test("Compose syntax", False, f"Error checking syntax: {e}")
            return False
        
        return True
    
    def test_dockerfile(self):
        """Test Dockerfile validity"""
        print("\n🐳 Testing Dockerfile")
        print("-" * 40)
        
        dockerfile = self.plugin_dir / "Dockerfile"
        
        # Check file exists
        self.log_test("Dockerfile exists", dockerfile.exists(), str(dockerfile))
        
        if not dockerfile.exists():
            return False
        
        # Check basic Dockerfile content
        try:
            with open(dockerfile, 'r') as f:
                content = f.read()
            
            required_elements = [
                "FROM node:",
                "WORKDIR",
                "COPY package",
                "RUN npm install",
                "CMD"
            ]
            
            for element in required_elements:
                found = element in content
                self.log_test(f"Dockerfile has {element}", found, f"Found: {found}")
                
        except Exception as e:
            self.log_test("Dockerfile content", False, f"Error reading file: {e}")
            return False
        
        return True
    
    def test_package_json(self):
        """Test package.json validity"""
        print("\n📦 Testing package.json")
        print("-" * 40)
        
        package_file = self.plugin_dir / "package.json"
        
        # Check file exists
        self.log_test("package.json exists", package_file.exists(), str(package_file))
        
        if not package_file.exists():
            return False
        
        try:
            with open(package_file, 'r') as f:
                package_data = json.load(f)
            
            # Check required dependencies
            dependencies = package_data.get('dependencies', {})
            required_deps = ['puppeteer', 'express']
            
            for dep in required_deps:
                found = dep in dependencies
                self.log_test(f"Has {dep} dependency", found, f"Version: {dependencies.get(dep, 'N/A')}")
                
        except Exception as e:
            self.log_test("package.json content", False, f"Error reading file: {e}")
            return False
        
        return True
    
    def test_container_build(self):
        """Test container build process"""
        print("\n🔨 Testing Container Build")
        print("-" * 40)
        
        try:
            result = subprocess.run([
                "docker", "compose", "build"
            ], capture_output=True, text=True, cwd=self.plugin_dir, timeout=300)
            
            if result.returncode == 0:
                self.log_test("Container build", True, "Built successfully")
                return True
            else:
                self.log_test("Container build", False, f"Build failed: {result.stderr}")
                print(f"   Build output: {result.stdout[-500:]}")  # Last 500 chars
                return False
                
        except subprocess.TimeoutExpired:
            self.log_test("Container build", False, "Build timeout (5 minutes)")
            return False
        except Exception as e:
            self.log_test("Container build", False, f"Build error: {e}")
            return False
    
    def test_container_start(self):
        """Test container startup"""
        print("\n🚀 Testing Container Start")
        print("-" * 40)
        
        # Ensure network exists
        try:
            subprocess.run([
                "docker", "network", "create", "simplex-net"
            ], capture_output=True, stderr=subprocess.DEVNULL)
        except:
            pass
        
        try:
            # Stop any existing containers first
            subprocess.run([
                "docker", "compose", "-p", "rumble-test", "down"
            ], capture_output=True, cwd=self.plugin_dir)
            
            # Start container with test project name
            env = {
                'PLUGIN_INSTANCE_ID': 'test',
                'PLUGIN_NAME': 'rumble'
            }
            
            result = subprocess.run([
                "docker", "compose", "-p", "rumble-test", "up", "-d"
            ], capture_output=True, text=True, cwd=self.plugin_dir, env={**env, **dict(subprocess.os.environ)})
            
            if result.returncode == 0:
                self.log_test("Container start", True, "Started successfully")
                
                # Wait for startup
                time.sleep(5)
                
                # Check if container is running
                ps_result = subprocess.run([
                    "docker", "ps", "--filter", "name=rumble-scraper", "--format", "{{.Names}}\t{{.Status}}"
                ], capture_output=True, text=True)
                
                if ps_result.returncode == 0 and ps_result.stdout.strip():
                    containers = ps_result.stdout.strip().split('\n')
                    for container in containers:
                        name, status = container.split('\t', 1)
                        self.log_test(f"Container {name} running", "Up" in status, status)
                else:
                    self.log_test("Container running check", False, "No containers found")
                
                return True
            else:
                self.log_test("Container start", False, f"Start failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_test("Container start", False, f"Start error: {e}")
            return False
    
    def test_network_connectivity(self):
        """Test network connectivity"""
        print("\n🌐 Testing Network Connectivity")
        print("-" * 40)
        
        # Test external connectivity (localhost)
        try:
            response = requests.get("http://localhost:8001/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("External connectivity", True, f"Health: {data.get('status')}")
            else:
                self.log_test("External connectivity", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("External connectivity", False, f"Connection error: {e}")
        
        # Test if port is bound
        try:
            result = subprocess.run([
                "docker", "port", "rumble-scraper-test"
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and "8001" in result.stdout:
                self.log_test("Port mapping", True, result.stdout.strip())
            else:
                self.log_test("Port mapping", False, "Port 8001 not mapped")
        except Exception as e:
            self.log_test("Port mapping", False, f"Port check error: {e}")
    
    def test_api_endpoints(self):
        """Test all API endpoints"""
        print("\n🔌 Testing API Endpoints")
        print("-" * 40)
        
        endpoints = [
            ("GET", "/health"),
            ("GET", "/status"),
            ("GET", "/data"),
        ]
        
        for method, endpoint in endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"http://localhost:8001{endpoint}", timeout=10)
                
                if response.status_code == 200:
                    self.log_test(f"{method} {endpoint}", True, f"HTTP {response.status_code}")
                else:
                    self.log_test(f"{method} {endpoint}", False, f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"{method} {endpoint}", False, f"Request error: {e}")
        
        # Test POST endpoint with data
        try:
            payload = {
                "channel_url": "https://rumble.com/c/test/livestreams",
                "options": {"detect_changes": False}
            }
            response = requests.post("http://localhost:8001/scrape", json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("POST /scrape", True, f"Success: {data.get('success')}")
            else:
                self.log_test("POST /scrape", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("POST /scrape", False, f"Request error: {e}")
    
    def test_container_logs(self):
        """Check container logs for issues"""
        print("\n📋 Testing Container Logs")
        print("-" * 40)
        
        try:
            result = subprocess.run([
                "docker", "logs", "rumble-scraper-test", "--tail", "50"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logs = result.stdout + result.stderr
                
                # Check for startup success
                startup_indicators = [
                    "server running on port",
                    "API server running",
                    "listening on"
                ]
                
                startup_found = any(indicator in logs.lower() for indicator in startup_indicators)
                self.log_test("Startup indicators", startup_found, "Found startup messages")
                
                # Check for errors
                error_lines = [line for line in logs.split('\n') if 'error' in line.lower() and line.strip()]
                if error_lines:
                    self.log_test("Error messages", False, f"Found {len(error_lines)} error lines")
                    for error in error_lines[:3]:  # Show first 3 errors
                        print(f"   🚨 {error}")
                else:
                    self.log_test("Error messages", True, "No error messages found")
                
                # Show recent logs
                recent_logs = logs.strip().split('\n')[-5:]
                print(f"   📝 Recent logs:")
                for log_line in recent_logs:
                    if log_line.strip():
                        print(f"   {log_line}")
                        
            else:
                self.log_test("Log retrieval", False, f"Failed to get logs: {result.stderr}")
                
        except Exception as e:
            self.log_test("Log retrieval", False, f"Log error: {e}")
    
    def cleanup(self):
        """Clean up test containers"""
        print("\n🧹 Cleanup")
        print("-" * 40)
        
        try:
            result = subprocess.run([
                "docker", "compose", "-p", "rumble-test", "down"
            ], capture_output=True, text=True, cwd=self.plugin_dir)
            
            if result.returncode == 0:
                self.log_test("Container cleanup", True, "Containers stopped")
            else:
                self.log_test("Container cleanup", False, f"Cleanup failed: {result.stderr}")
        except Exception as e:
            self.log_test("Container cleanup", False, f"Cleanup error: {e}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("🎯 CONTAINER TEST SUMMARY")
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
            print("\n🎉 ALL CONTAINER TESTS PASSED!")
        
        return passed == total


def run_container_tests():
    """Run all container tests"""
    print("🐳 RUMBLE PLUGIN CONTAINER TESTS")
    print("=" * 60)
    
    tester = ContainerTester()
    
    try:
        # Run tests in sequence
        tester.test_docker_compose_file()
        tester.test_dockerfile()
        tester.test_package_json()
        tester.test_container_build()
        tester.test_container_start()
        tester.test_network_connectivity()
        tester.test_api_endpoints()
        tester.test_container_logs()
        
    finally:
        tester.cleanup()
    
    # Print summary
    return tester.print_summary()


if __name__ == "__main__":
    import sys
    success = run_container_tests()
    sys.exit(0 if success else 1)