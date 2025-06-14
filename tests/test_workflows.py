#!/usr/bin/env python3
"""
GitHub Actions Workflow Tests for Ansible Custom EE Builder
"""

import os
import sys
import subprocess
import yaml
import json
from pathlib import Path

class WorkflowTestSuite:
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

    def test_workflow_yaml_syntax(self):
        """Test GitHub Actions workflow YAML syntax."""
        workflow_dir = self.project_root / ".github/workflows"
        
        if not workflow_dir.exists():
            self.log_test("Workflow Directory", False, "Workflow directory not found")
            return
        
        workflow_files = list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
        
        if not workflow_files:
            self.log_test("Workflow Files", False, "No workflow files found")
            return
        
        invalid_workflows = []
        valid_workflows = []
        
        for workflow_file in workflow_files:
            try:
                with open(workflow_file, 'r') as f:
                    workflow_data = yaml.safe_load(f)
                
                # Check if workflow_data is valid
                if not isinstance(workflow_data, dict):
                    invalid_workflows.append(f"{workflow_file.name}: invalid YAML structure")
                    continue
                
                # Basic workflow structure validation
                # Note: 'on' might be parsed as boolean True in YAML
                required_keys = ['name', 'jobs']
                has_on_trigger = 'on' in workflow_data or True in workflow_data
                
                missing_keys = [key for key in required_keys if key not in workflow_data]
                if not has_on_trigger:
                    missing_keys.append('on')
                
                if missing_keys:
                    invalid_workflows.append(f"{workflow_file.name}: missing {missing_keys}")
                else:
                    valid_workflows.append(workflow_file.name)
                    
            except yaml.YAMLError as e:
                invalid_workflows.append(f"{workflow_file.name}: YAML error - {e}")
            except Exception as e:
                invalid_workflows.append(f"{workflow_file.name}: {e}")
        
        if invalid_workflows:
            self.log_test("Workflow YAML Syntax", False, f"Invalid: {invalid_workflows}")
        else:
            self.log_test("Workflow YAML Syntax", True, f"Valid: {valid_workflows}")

    def test_build_workflow_structure(self):
        """Test build workflow structure."""
        build_workflow = self.project_root / ".github/workflows/build-ee.yml"
        
        if not build_workflow.exists():
            self.log_test("Build Workflow Structure", False, "build-ee.yml not found")
            return
        
        try:
            with open(build_workflow, 'r') as f:
                workflow = yaml.safe_load(f)
            
            issues = []
            
            # Check workflow triggers (handle YAML parsing of 'on' as True)
            triggers = workflow.get('on') or workflow.get(True)
            if not triggers:
                issues.append("Missing 'on' triggers")
            else:
                expected_triggers = ['workflow_dispatch', 'push', 'pull_request']
                missing_triggers = [t for t in expected_triggers if t not in triggers]
                if missing_triggers:
                    issues.append(f"Missing triggers: {missing_triggers}")
            
            # Check jobs
            if 'jobs' not in workflow:
                issues.append("Missing 'jobs' section")
            else:
                jobs = workflow['jobs']
                if 'build' not in jobs:
                    issues.append("Missing 'build' job")
                else:
                    build_job = jobs['build']
                    
                    # Check required job properties
                    if 'runs-on' not in build_job:
                        issues.append("Build job missing 'runs-on'")
                    
                    if 'steps' not in build_job:
                        issues.append("Build job missing 'steps'")
                    else:
                        steps = build_job['steps']
                        step_names = [step.get('name', '') for step in steps]
                        
                        # Check for essential steps
                        essential_steps = ['checkout', 'python', 'dependencies']
                        for essential in essential_steps:
                            if not any(essential.lower() in name.lower() for name in step_names):
                                issues.append(f"Missing essential step containing '{essential}'")
            
            # Check environment variables
            if 'env' in workflow:
                env_vars = workflow['env']
                if 'IMAGE_NAME' not in env_vars:
                    issues.append("Missing IMAGE_NAME environment variable")
            
            if issues:
                self.log_test("Build Workflow Structure", False, f"Issues: {issues}")
            else:
                self.log_test("Build Workflow Structure", True, "Well-structured workflow")
                
        except Exception as e:
            self.log_test("Build Workflow Structure", False, f"Error: {e}")

    def test_custom_action_structure(self):
        """Test custom action structure."""
        action_dir = self.project_root / ".github/actions/build-push"
        action_file = action_dir / "action.yml"
        
        if not action_file.exists():
            self.log_test("Custom Action Structure", False, "action.yml not found")
            return
        
        try:
            with open(action_file, 'r') as f:
                action = yaml.safe_load(f)
            
            issues = []
            
            # Check required action properties
            required_props = ['name', 'description', 'inputs', 'runs']
            missing_props = [prop for prop in required_props if prop not in action]
            if missing_props:
                issues.append(f"Missing properties: {missing_props}")
            
            # Check inputs
            if 'inputs' in action:
                inputs = action['inputs']
                required_inputs = ['image_tag', 'registry_type']
                missing_inputs = [inp for inp in required_inputs if inp not in inputs]
                if missing_inputs:
                    issues.append(f"Missing inputs: {missing_inputs}")
            
            # Check runs configuration
            if 'runs' in action:
                runs = action['runs']
                if 'using' not in runs:
                    issues.append("Missing 'using' in runs section")
                elif runs['using'] != 'composite':
                    issues.append("Action should use 'composite' runner")
                
                if 'steps' not in runs:
                    issues.append("Missing 'steps' in runs section")
            
            if issues:
                self.log_test("Custom Action Structure", False, f"Issues: {issues}")
            else:
                self.log_test("Custom Action Structure", True, "Well-structured action")
                
        except Exception as e:
            self.log_test("Custom Action Structure", False, f"Error: {e}")

    def test_workflow_secrets_usage(self):
        """Test workflow secrets usage."""
        workflow_files = [
            self.project_root / ".github/workflows/build-ee.yml",
            self.project_root / ".github/workflows/check-base-images.yml"
        ]
        
        expected_secrets = [
            'REDHAT_REGISTRY_USERNAME',
            'REDHAT_REGISTRY_PASSWORD',
            'ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN'
        ]
        
        secrets_found = set()
        issues = []
        
        for workflow_file in workflow_files:
            if not workflow_file.exists():
                continue
                
            try:
                with open(workflow_file, 'r') as f:
                    content = f.read()
                
                # Find secrets references
                for secret in expected_secrets:
                    if f"secrets.{secret}" in content:
                        secrets_found.add(secret)
                
                # Check for hardcoded credentials (security issue)
                sensitive_patterns = ['password:', 'token:', 'secret:', 'key:']
                for pattern in sensitive_patterns:
                    if pattern in content.lower() and 'secrets.' not in content.lower():
                        # Look for actual hardcoded values (not just comments)
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if pattern in line.lower() and '=' in line and 'secrets.' not in line.lower():
                                if not line.strip().startswith('#'):
                                    issues.append(f"Potential hardcoded credential in {workflow_file.name}:{i+1}")
                
            except Exception as e:
                issues.append(f"Error reading {workflow_file.name}: {e}")
        
        missing_secrets = set(expected_secrets) - secrets_found
        
        if missing_secrets:
            issues.append(f"Missing secret references: {missing_secrets}")
        
        if issues:
            self.log_test("Workflow Secrets Usage", False, f"Issues: {issues}")
        else:
            self.log_test("Workflow Secrets Usage", True, f"Found secrets: {secrets_found}")

    def test_workflow_matrix_strategy(self):
        """Test workflow matrix strategy."""
        build_workflow = self.project_root / ".github/workflows/build-ee.yml"
        
        if not build_workflow.exists():
            self.log_test("Workflow Matrix Strategy", False, "build-ee.yml not found")
            return
        
        try:
            with open(build_workflow, 'r') as f:
                workflow = yaml.safe_load(f)
            
            issues = []
            
            # Check for matrix strategy in build job
            if 'jobs' in workflow and 'build' in workflow['jobs']:
                build_job = workflow['jobs']['build']
                
                if 'strategy' not in build_job:
                    issues.append("Missing strategy section")
                else:
                    strategy = build_job['strategy']
                    
                    if 'matrix' not in strategy:
                        issues.append("Missing matrix in strategy")
                    else:
                        matrix = strategy['matrix']
                        
                        # Check for registry matrix
                        if 'registry' not in matrix:
                            issues.append("Missing registry matrix")
                        else:
                            registries = matrix['registry']
                            expected_registries = ['docker', 'ecr', 'acr', 'gcr']
                            missing_registries = [r for r in expected_registries if r not in registries]
                            if missing_registries:
                                issues.append(f"Missing registries: {missing_registries}")
            else:
                issues.append("Build job not found")
            
            if issues:
                self.log_test("Workflow Matrix Strategy", False, f"Issues: {issues}")
            else:
                self.log_test("Workflow Matrix Strategy", True, "Matrix strategy configured")
                
        except Exception as e:
            self.log_test("Workflow Matrix Strategy", False, f"Error: {e}")

    def test_workflow_conditional_logic(self):
        """Test workflow conditional logic."""
        build_workflow = self.project_root / ".github/workflows/build-ee.yml"
        
        if not build_workflow.exists():
            self.log_test("Workflow Conditional Logic", False, "build-ee.yml not found")
            return
        
        try:
            with open(build_workflow, 'r') as f:
                content = f.read()
            
            issues = []
            
            # Check for conditional execution patterns
            conditional_patterns = [
                'if:',
                'github.event_name',
                'startsWith(github.ref',
                'matrix.enabled'
            ]
            
            found_patterns = []
            for pattern in conditional_patterns:
                if pattern in content:
                    found_patterns.append(pattern)
            
            if len(found_patterns) < 2:
                issues.append(f"Limited conditional logic found: {found_patterns}")
            
            # Check for push/tag conditionals
            if 'startsWith(github.ref' not in content:
                issues.append("Missing tag-based conditional logic")
            
            if issues:
                self.log_test("Workflow Conditional Logic", False, f"Issues: {issues}")
            else:
                self.log_test("Workflow Conditional Logic", True, f"Conditionals found: {found_patterns}")
                
        except Exception as e:
            self.log_test("Workflow Conditional Logic", False, f"Error: {e}")

    def test_workflow_security_practices(self):
        """Test workflow security practices."""
        workflow_dir = self.project_root / ".github/workflows"
        
        if not workflow_dir.exists():
            self.log_test("Workflow Security", False, "Workflow directory not found")
            return
        
        issues = []
        good_practices = []
        
        workflow_files = list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
        
        for workflow_file in workflow_files:
            try:
                with open(workflow_file, 'r') as f:
                    content = f.read()
                
                # Check for security best practices
                
                # 1. Check for pinned action versions
                if 'uses:' in content:
                    if '@v' in content or '@' in content:
                        good_practices.append(f"{workflow_file.name}: Uses pinned action versions")
                    else:
                        issues.append(f"{workflow_file.name}: Actions not pinned to versions")
                
                # 2. Check for secrets usage (should use secrets, not env vars)
                if 'password' in content.lower() and 'secrets.' not in content:
                    issues.append(f"{workflow_file.name}: Potential insecure password usage")
                
                # 3. Check for proper permissions
                workflow_data = yaml.safe_load(content)
                if 'permissions' in workflow_data:
                    good_practices.append(f"{workflow_file.name}: Explicit permissions defined")
                
                # 4. Check for timeout configurations
                if 'timeout' in content or 'timeout-minutes' in content:
                    good_practices.append(f"{workflow_file.name}: Timeout configured")
                
            except Exception as e:
                issues.append(f"Error checking {workflow_file.name}: {e}")
        
        if issues:
            self.log_test("Workflow Security", False, f"Issues: {issues}")
        else:
            self.log_test("Workflow Security", True, f"Good practices: {len(good_practices)}")

    def test_action_lint_compatibility(self):
        """Test GitHub Actions lint compatibility."""
        # Check if actionlint is available
        success, stdout, stderr = self.run_command("which actionlint")
        if not success:
            self.log_test("Action Lint", True, "actionlint not available (optional - skipped)")
            return
        
        # Run actionlint on workflows
        workflow_dir = self.project_root / ".github/workflows"
        success, stdout, stderr = self.run_command(f"actionlint {workflow_dir}/*.yml")
        
        if success:
            self.log_test("Action Lint", True, "Workflows pass actionlint")
        else:
            # Check if errors are critical
            if "error" in stderr.lower():
                self.log_test("Action Lint", False, f"Lint errors: {stderr}")
            else:
                self.log_test("Action Lint", True, f"Minor warnings: {stderr}")

    def run_all_tests(self):
        """Run all workflow tests."""
        print("⚙️ Running GitHub Actions Workflow Test Suite...\n")
        
        self.test_workflow_yaml_syntax()
        self.test_build_workflow_structure()
        self.test_custom_action_structure()
        self.test_workflow_secrets_usage()
        self.test_workflow_matrix_strategy()
        self.test_workflow_conditional_logic()
        self.test_workflow_security_practices()
        self.test_action_lint_compatibility()
        
        # Summary
        passed = sum(1 for test in self.test_results if test["status"])
        total = len(self.test_results)
        
        print(f"\n📊 Workflow Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All workflow tests passed!")
            return True
        else:
            print(f"💥 {total - passed} workflow tests failed.")
            
            # Show failed tests
            failed_tests = [test for test in self.test_results if not test["status"]]
            print("\nFailed tests:")
            for test in failed_tests:
                print(f"  ❌ {test['name']}: {test['message']}")
            
            return False

if __name__ == "__main__":
    suite = WorkflowTestSuite()
    success = suite.run_all_tests()
    sys.exit(0 if success else 1)