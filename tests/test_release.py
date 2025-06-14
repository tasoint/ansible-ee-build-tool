#!/usr/bin/env python3
"""
Release Testing Framework for Ansible Custom EE Builder
"""

import os
import sys
import subprocess
import tempfile
import yaml
import json
from pathlib import Path
import shutil

class ReleaseTestSuite:
    def __init__(self):
        self.project_root = Path.cwd()
        self.test_results = []
        
    def log_test(self, name, status, message=""):
        """Log test result."""
        icon = "✅" if status else "❌"
        print(f"{icon} {name}: {message}")
        self.test_results.append({"name": name, "status": status, "message": message})
    
    def run_command(self, command, cwd=None, timeout=60):
        """Run command and return result."""
        try:
            result = subprocess.run(
                command, shell=True, cwd=cwd, timeout=timeout,
                capture_output=True, text=True
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    # === ユニットテスト ===
    def test_project_structure(self):
        """Test project directory structure."""
        required_dirs = [
            ".github/workflows",
            ".github/actions/build-push", 
            "scripts",
            "examples",
            "tests",
            "docs"
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            if not (self.project_root / dir_path).exists():
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            self.log_test("Project Structure", False, f"Missing: {missing_dirs}")
        else:
            self.log_test("Project Structure", True, "All directories present")

    def test_required_files(self):
        """Test required files exist."""
        required_files = [
            "execution-environment.yml",
            "ansible.cfg", 
            "Makefile",
            "requirements-dev.txt",
            ".env.example",
            ".gitignore"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            self.log_test("Required Files", False, f"Missing: {missing_files}")
        else:
            self.log_test("Required Files", True, "All files present")

    def test_yaml_validity(self):
        """Test YAML files are valid."""
        yaml_files = [
            "execution-environment.yml",
            "ansible-navigator.yml",
            ".github/workflows/build-ee.yml",
            ".github/workflows/check-base-images.yml",
            ".github/actions/build-push/action.yml",
            "examples/execution-environment.yml",
            "examples/ansible-navigator.yml",
            "examples/inventory.yml",
            "examples/site.yml"
        ]
        
        invalid_files = []
        for yaml_file in yaml_files:
            file_path = self.project_root / yaml_file
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        yaml.safe_load(f)
                except yaml.YAMLError:
                    invalid_files.append(yaml_file)
        
        if invalid_files:
            self.log_test("YAML Validity", False, f"Invalid: {invalid_files}")
        else:
            self.log_test("YAML Validity", True, "All YAML files valid")

    def test_script_executability(self):
        """Test scripts are executable."""
        script_files = [
            "scripts/build-local.sh",
            "scripts/check-base-images.sh", 
            "scripts/generate-navigator-config.py",
            "tests/test_build.py"
        ]
        
        non_executable = []
        for script in script_files:
            script_path = self.project_root / script
            if script_path.exists() and not os.access(script_path, os.X_OK):
                non_executable.append(script)
        
        if non_executable:
            self.log_test("Script Executability", False, f"Not executable: {non_executable}")
        else:
            self.log_test("Script Executability", True, "All scripts executable")

    # === 統合テスト ===
    def test_makefile_targets(self):
        """Test Makefile targets work."""
        success, stdout, stderr = self.run_command("make help")
        if success and "Ansible Custom EE Builder" in stdout:
            self.log_test("Makefile Help", True, "Help target works")
        else:
            self.log_test("Makefile Help", False, f"Error: {stderr}")
        
        success, stdout, stderr = self.run_command("make check-deps")
        if success:
            self.log_test("Dependency Check", True, "Dependencies available")
        else:
            self.log_test("Dependency Check", False, f"Missing dependencies: {stderr}")

    def test_script_functionality(self):
        """Test script basic functionality."""
        # Test generate-navigator-config.py
        success, stdout, stderr = self.run_command(
            "python3 scripts/generate-navigator-config.py --help"
        )
        if success:
            self.log_test("Navigator Config Script", True, "Script help works")
        else:
            self.log_test("Navigator Config Script", False, f"Error: {stderr}")
        
        # Test build-local.sh
        success, stdout, stderr = self.run_command("scripts/build-local.sh --help")
        if success:
            self.log_test("Build Script", True, "Script help works")
        else:
            self.log_test("Build Script", False, f"Error: {stderr}")

    # === 互換性テスト ===
    def test_container_runtime_compatibility(self):
        """Test container runtime compatibility."""
        # Test podman
        success, stdout, stderr = self.run_command("podman --version")
        if success:
            self.log_test("Podman Compatibility", True, f"Version: {stdout.strip()}")
        else:
            self.log_test("Podman Compatibility", False, "Podman not available")
        
        # Test docker
        success, stdout, stderr = self.run_command("docker --version")
        if success:
            self.log_test("Docker Compatibility", True, f"Version: {stdout.strip()}")
        else:
            self.log_test("Docker Compatibility", False, "Docker not available")

    def test_ansible_compatibility(self):
        """Test Ansible compatibility."""
        success, stdout, stderr = self.run_command("ansible --version")
        if success:
            version_line = stdout.split('\n')[0]
            self.log_test("Ansible Compatibility", True, version_line)
        else:
            self.log_test("Ansible Compatibility", False, "Ansible not available")

    # === セキュリティテスト ===
    def test_secret_exposure(self):
        """Test for exposed secrets."""
        sensitive_patterns = [
            "password", "token", "secret", "key", "credential"
        ]
        
        exposed_files = []
        for file_path in self.project_root.rglob("*"):
            if file_path.is_file() and not any(exclude in str(file_path) for exclude in ['.git', '__pycache__', '.venv']):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        for pattern in sensitive_patterns:
                            if f"{pattern}=" in content and \
                               "example" not in str(file_path) and \
                               "claude.md" not in str(file_path).lower() and \
                               "readme" not in str(file_path).lower():
                                exposed_files.append(str(file_path))
                                break
                except Exception:
                    continue
        
        if exposed_files:
            self.log_test("Secret Exposure", False, f"Potential secrets in: {exposed_files}")
        else:
            self.log_test("Secret Exposure", True, "No exposed secrets found")

    def test_file_permissions(self):
        """Test file permissions are appropriate."""
        # Only check truly sensitive files
        sensitive_files = [".env"]
        issues = []
        
        for file_name in sensitive_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                stat = file_path.stat()
                # Check if world-readable (sensitive files should not be)
                if stat.st_mode & 0o004:
                    issues.append(f"{file_name} is world-readable")
        
        if issues:
            self.log_test("File Permissions", False, f"Issues: {issues}")
        else:
            self.log_test("File Permissions", True, "Appropriate permissions")

    # === ドキュメントテスト ===
    def test_documentation_completeness(self):
        """Test documentation completeness."""
        readme_path = self.project_root / "README.md"
        claude_path = self.project_root / "CLAUDE.md"
        
        if not readme_path.exists():
            self.log_test("README Documentation", False, "README.md missing")
            return
        
        with open(readme_path, 'r') as f:
            readme_content = f.read()
        
        required_sections = ["setup", "使用方法", "install", "build"]
        missing_sections = []
        for section in required_sections:
            if section.lower() not in readme_content.lower():
                missing_sections.append(section)
        
        if missing_sections:
            self.log_test("README Documentation", False, f"Missing sections: {missing_sections}")
        else:
            self.log_test("README Documentation", True, "Complete documentation")

    def test_example_validity(self):
        """Test example files are usable."""
        example_ee = self.project_root / "examples/execution-environment.yml"
        if not example_ee.exists():
            self.log_test("Example Validity", False, "Example EE file missing")
            return
        
        try:
            with open(example_ee, 'r') as f:
                ee_config = yaml.safe_load(f)
            
            # Check required fields
            required_fields = ["version", "images", "dependencies"]
            missing_fields = []
            for field in required_fields:
                if field not in ee_config:
                    missing_fields.append(field)
            
            if missing_fields:
                self.log_test("Example Validity", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("Example Validity", True, "Example files valid")
                
        except Exception as e:
            self.log_test("Example Validity", False, f"Error: {e}")

    def run_all_tests(self):
        """Run all test suites."""
        print("🧪 Running Release Test Suite...\n")
        
        print("=== Unit Tests ===")
        self.test_project_structure()
        self.test_required_files()
        self.test_yaml_validity()
        self.test_script_executability()
        
        print("\n=== Integration Tests ===")
        self.test_makefile_targets()
        self.test_script_functionality()
        
        print("\n=== Compatibility Tests ===")
        self.test_container_runtime_compatibility()
        self.test_ansible_compatibility()
        
        print("\n=== Security Tests ===")
        self.test_secret_exposure()
        self.test_file_permissions()
        
        print("\n=== Documentation Tests ===")
        self.test_documentation_completeness()
        self.test_example_validity()
        
        # Summary
        passed = sum(1 for test in self.test_results if test["status"])
        total = len(self.test_results)
        
        print(f"\n📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Ready for release.")
            return True
        else:
            print(f"💥 {total - passed} tests failed. Fix issues before release.")
            
            # Show failed tests
            failed_tests = [test for test in self.test_results if not test["status"]]
            print("\nFailed tests:")
            for test in failed_tests:
                print(f"  ❌ {test['name']}: {test['message']}")
            
            return False

if __name__ == "__main__":
    suite = ReleaseTestSuite()
    success = suite.run_all_tests()
    sys.exit(0 if success else 1)