#!/usr/bin/env python3
"""
Integration Tests for Ansible Custom EE Builder
"""

import os
import sys
import subprocess
import tempfile
import yaml
import json
import time
from pathlib import Path

class IntegrationTestSuite:
    def __init__(self):
        self.project_root = Path.cwd()
        self.test_results = []
        self.test_image_name = "localhost/integration-test-ee:test"
        
    def log_test(self, name, status, message=""):
        """Log test result."""
        icon = "✅" if status else "❌"
        print(f"{icon} {name}: {message}")
        self.test_results.append({"name": name, "status": status, "message": message})
    
    def run_command(self, command, cwd=None, timeout=300):
        """Run command and return result."""
        try:
            result = subprocess.run(
                command, shell=True, cwd=cwd, timeout=timeout,
                capture_output=True, text=True
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", str(e)

    def create_minimal_ee_config(self):
        """Create minimal EE config for testing."""
        test_config = {
            "version": 3,
            "images": {
                "base_image": {
                    "name": "quay.io/ansible/creator-ee:latest"
                }
            },
            "dependencies": {
                "galaxy": "---\ncollections:\n  - name: ansible.posix\n    version: \">=1.5.0\"",
                "python": "requests>=2.31.0\njmespath>=1.0.0"
            },
            "options": {
                "container_init": {
                    "package_pip": "ansible-core>=2.15"
                }
            }
        }
        
        test_config_path = self.project_root / "test-integration-ee.yml"
        with open(test_config_path, 'w') as f:
            yaml.dump(test_config, f, default_flow_style=False)
        
        return test_config_path

    def create_test_playbook(self):
        """Create a simple test playbook."""
        playbook_content = [
            {
                "name": "Integration Test Playbook",
                "hosts": "localhost",
                "gather_facts": True,
                "connection": "local",
                "tasks": [
                    {
                        "name": "Test Ansible version",
                        "debug": {
                            "var": "ansible_version.full"
                        }
                    },
                    {
                        "name": "Test Python modules",
                        "debug": {
                            "msg": "Testing Python import"
                        }
                    },
                    {
                        "name": "Test collections",
                        "shell": "ansible-galaxy collection list",
                        "register": "collections"
                    },
                    {
                        "name": "Show collections",
                        "debug": {
                            "var": "collections.stdout_lines"
                        }
                    }
                ]
            }
        ]
        
        test_playbook_path = self.project_root / "test-integration.yml"
        with open(test_playbook_path, 'w') as f:
            yaml.dump(playbook_content, f, default_flow_style=False)
        
        return test_playbook_path

    def create_test_inventory(self):
        """Create a simple test inventory."""
        inventory_content = {
            "all": {
                "hosts": {
                    "localhost": {
                        "ansible_connection": "local"
                    }
                }
            }
        }
        
        test_inventory_path = self.project_root / "test-inventory.yml"
        with open(test_inventory_path, 'w') as f:
            yaml.dump(inventory_content, f, default_flow_style=False)
        
        return test_inventory_path

    def test_ansible_builder_availability(self):
        """Test if ansible-builder is available."""
        success, stdout, stderr = self.run_command("pip show ansible-builder")
        if success:
            self.log_test("Ansible Builder Available", True, "Package found")
        else:
            # Try to install it
            success, stdout, stderr = self.run_command("pip install --break-system-packages ansible-builder")
            if success:
                self.log_test("Ansible Builder Install", True, "Installed successfully")
            else:
                self.log_test("Ansible Builder Install", False, f"Failed to install: {stderr}")

    def test_ee_build_with_examples(self):
        """Test EE build using example configuration."""
        example_ee_path = self.project_root / "examples/execution-environment.yml"
        
        if not example_ee_path.exists():
            self.log_test("Example EE Build", False, "Example EE file not found")
            return
        
        # Create a build command using the script
        build_cmd = f"export PATH=$PATH:/home/taso/.local/bin && ./scripts/build-local.sh --file {example_ee_path} --tag {self.test_image_name} --registry localhost"
        
        start_time = time.time()
        success, stdout, stderr = self.run_command(build_cmd, timeout=600)
        build_time = time.time() - start_time
        
        if success:
            self.log_test("Example EE Build", True, f"Built in {build_time:.1f}s")
        else:
            self.log_test("Example EE Build", False, f"Build failed: {stderr}")

    def test_minimal_ee_build(self):
        """Test minimal EE build."""
        test_config_path = self.create_minimal_ee_config()
        
        try:
            # Create a simple Dockerfile for testing
            dockerfile_content = f"""FROM quay.io/ansible/creator-ee:latest

USER root

# Install basic Python packages
RUN python3 -m pip install --no-cache-dir requests jmespath

# Install ansible.posix collection
RUN ansible-galaxy collection install ansible.posix --force

# Test commands
RUN ansible --version
RUN python3 -c "import requests, jmespath; print('Python modules OK')"

WORKDIR /runner
USER 1000

LABEL ansible-execution-environment=true
"""
            
            dockerfile_path = self.project_root / "test.Dockerfile"
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)
            
            # Build with podman directly
            build_cmd = f"podman build -f test.Dockerfile -t {self.test_image_name} ."
            
            start_time = time.time()
            success, stdout, stderr = self.run_command(build_cmd, timeout=600)
            build_time = time.time() - start_time
            
            if success:
                self.log_test("Minimal EE Build", True, f"Built in {build_time:.1f}s")
            else:
                self.log_test("Minimal EE Build", False, f"Build failed: {stderr}")
                
        except Exception as e:
            self.log_test("Minimal EE Build", False, f"Exception: {e}")
        finally:
            # Cleanup
            if test_config_path.exists():
                test_config_path.unlink()
            dockerfile_path = self.project_root / "test.Dockerfile"
            if dockerfile_path.exists():
                dockerfile_path.unlink()

    def test_ee_functionality(self):
        """Test EE functionality."""
        # Check if image exists
        success, stdout, stderr = self.run_command(f"podman images {self.test_image_name}")
        if not success:
            self.log_test("EE Functionality", False, "Test image not found")
            return
        
        # Test basic ansible command
        test_cmd = f"podman run --rm {self.test_image_name} ansible --version"
        success, stdout, stderr = self.run_command(test_cmd)
        
        if success and "ansible" in stdout.lower():
            self.log_test("EE Ansible Command", True, "Ansible works in EE")
        else:
            self.log_test("EE Ansible Command", False, f"Ansible test failed: {stderr}")
        
        # Test collection listing
        test_cmd = f"podman run --rm {self.test_image_name} ansible-galaxy collection list"
        success, stdout, stderr = self.run_command(test_cmd)
        
        if success:
            self.log_test("EE Collection List", True, "Collections accessible")
        else:
            self.log_test("EE Collection List", False, f"Collection test failed: {stderr}")

    def test_ansible_navigator_integration(self):
        """Test ansible-navigator integration."""
        # Check if ansible-navigator is available
        success, stdout, stderr = self.run_command("export PATH=$PATH:/home/taso/.local/bin && which ansible-navigator")
        if not success:
            self.log_test("Navigator Integration", False, "ansible-navigator not found")
            return
        
        # Create test files
        test_playbook_path = self.create_test_playbook()
        test_inventory_path = self.create_test_inventory()
        
        try:
            # Create a simple navigator config for testing
            navigator_config = {
                "ansible-navigator": {
                    "execution-environment": {
                        "enabled": True,
                        "image": self.test_image_name,
                        "container-engine": "auto",
                        "pull": {"policy": "missing"}
                    },
                    "mode": "stdout"
                }
            }
            
            nav_config_path = self.project_root / "test-navigator.yml"
            with open(nav_config_path, 'w') as f:
                yaml.dump(navigator_config, f, default_flow_style=False)
            
            # Create a temporary directory for test
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                
                # Copy test files to temp directory
                temp_playbook = temp_dir_path / "test-playbook.yml"
                temp_inventory = temp_dir_path / "test-inventory.yml"
                temp_config = temp_dir_path / "ansible-navigator.yml"
                
                temp_playbook.write_text(test_playbook_path.read_text())
                temp_inventory.write_text(test_inventory_path.read_text())
                temp_config.write_text(yaml.dump(navigator_config, default_flow_style=False))
                
                # Test ansible-navigator run from temp directory
                nav_cmd = f"export PATH=$PATH:/home/taso/.local/bin && cd {temp_dir} && ansible-navigator run test-playbook.yml -i test-inventory.yml --mode stdout"
                success, stdout, stderr = self.run_command(nav_cmd, timeout=120)
            
            if success and "PLAY RECAP" in stdout:
                self.log_test("Navigator Integration", True, "Playbook executed successfully")
            else:
                self.log_test("Navigator Integration", False, f"Navigator test failed: {stderr}")
                
        except Exception as e:
            self.log_test("Navigator Integration", False, f"Exception: {e}")
        finally:
            # Cleanup test files
            for path in [test_playbook_path, test_inventory_path, nav_config_path]:
                if path.exists():
                    path.unlink()

    def test_make_targets(self):
        """Test Make targets that involve building."""
        # Test make info
        success, stdout, stderr = self.run_command("make info")
        if success:
            self.log_test("Make Info Target", True, "Info target works")
        else:
            self.log_test("Make Info Target", False, f"Error: {stderr}")
        
        # Test make version
        success, stdout, stderr = self.run_command("make version")
        if success:
            self.log_test("Make Version Target", True, "Version target works")
        else:
            self.log_test("Make Version Target", False, f"Error: {stderr}")

    def cleanup_test_artifacts(self):
        """Clean up test artifacts."""
        # Remove test image
        self.run_command(f"podman rmi {self.test_image_name} 2>/dev/null || true")
        
        # Remove any remaining test files
        test_files = [
            "test-integration-ee.yml",
            "test-integration.yml", 
            "test-inventory.yml",
            "test-navigator.yml",
            "test.Dockerfile"
        ]
        
        for file_name in test_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                file_path.unlink()

    def run_all_tests(self):
        """Run all integration tests."""
        print("🔧 Running Integration Test Suite...\n")
        
        try:
            self.test_ansible_builder_availability()
            self.test_minimal_ee_build()
            self.test_ee_functionality()
            self.test_ansible_navigator_integration()
            self.test_make_targets()
            
            # Summary
            passed = sum(1 for test in self.test_results if test["status"])
            total = len(self.test_results)
            
            print(f"\n📊 Integration Test Results: {passed}/{total} tests passed")
            
            if passed == total:
                print("🎉 All integration tests passed!")
                return True
            else:
                print(f"💥 {total - passed} integration tests failed.")
                
                # Show failed tests
                failed_tests = [test for test in self.test_results if not test["status"]]
                print("\nFailed tests:")
                for test in failed_tests:
                    print(f"  ❌ {test['name']}: {test['message']}")
                
                return False
                
        finally:
            self.cleanup_test_artifacts()

if __name__ == "__main__":
    suite = IntegrationTestSuite()
    success = suite.run_all_tests()
    sys.exit(0 if success else 1)