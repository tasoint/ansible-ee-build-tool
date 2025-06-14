#!/usr/bin/env python3
"""
Test script for Ansible Custom EE Builder
"""

import os
import sys
import subprocess
import tempfile
import yaml
from pathlib import Path

def test_ee_file_validity():
    """Test that execution-environment.yml is valid YAML."""
    ee_file = Path("execution-environment.yml")
    
    if not ee_file.exists():
        print("❌ execution-environment.yml not found")
        return False
    
    try:
        with open(ee_file, 'r') as f:
            yaml.safe_load(f)
        print("✅ execution-environment.yml is valid YAML")
        return True
    except yaml.YAMLError as e:
        print(f"❌ execution-environment.yml has YAML syntax error: {e}")
        return False

def test_ansible_cfg_validity():
    """Test that ansible.cfg exists and has required sections."""
    cfg_file = Path("ansible.cfg")
    
    if not cfg_file.exists():
        print("❌ ansible.cfg not found")
        return False
    
    # Basic check for required sections
    with open(cfg_file, 'r') as f:
        content = f.read()
    
    required_sections = ['[defaults]', '[galaxy]']
    missing_sections = []
    
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)
    
    if missing_sections:
        print(f"❌ ansible.cfg missing sections: {missing_sections}")
        return False
    
    print("✅ ansible.cfg has required sections")
    return True

def test_scripts_executable():
    """Test that scripts are executable."""
    scripts_dir = Path("scripts")
    
    if not scripts_dir.exists():
        print("❌ scripts directory not found")
        return False
    
    script_files = list(scripts_dir.glob("*.sh")) + list(scripts_dir.glob("*.py"))
    
    if not script_files:
        print("❌ No script files found")
        return False
    
    non_executable = []
    for script in script_files:
        if not os.access(script, os.X_OK):
            non_executable.append(script.name)
    
    if non_executable:
        print(f"❌ Scripts not executable: {non_executable}")
        return False
    
    print("✅ All scripts are executable")
    return True

def test_makefile_targets():
    """Test that Makefile has required targets."""
    makefile = Path("Makefile")
    
    if not makefile.exists():
        print("❌ Makefile not found")
        return False
    
    required_targets = ['help', 'build', 'test', 'clean', 'setup']
    
    with open(makefile, 'r') as f:
        content = f.read()
    
    missing_targets = []
    for target in required_targets:
        if f"{target}:" not in content:
            missing_targets.append(target)
    
    if missing_targets:
        print(f"❌ Makefile missing targets: {missing_targets}")
        return False
    
    print("✅ Makefile has required targets")
    return True

def test_examples_validity():
    """Test that example files are valid."""
    examples_dir = Path("examples")
    
    if not examples_dir.exists():
        print("❌ examples directory not found")
        return False
    
    yaml_files = list(examples_dir.glob("*.yml")) + list(examples_dir.glob("*.yaml"))
    
    if not yaml_files:
        print("❌ No example YAML files found")
        return False
    
    invalid_files = []
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r') as f:
                yaml.safe_load(f)
        except yaml.YAMLError:
            invalid_files.append(yaml_file.name)
    
    if invalid_files:
        print(f"❌ Invalid example YAML files: {invalid_files}")
        return False
    
    print("✅ All example files are valid YAML")
    return True

def test_directory_structure():
    """Test that required directories exist."""
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
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False
    
    print("✅ All required directories exist")
    return True

def test_github_workflows():
    """Test that GitHub workflow files are valid."""
    workflows_dir = Path(".github/workflows")
    
    if not workflows_dir.exists():
        print("❌ .github/workflows directory not found")
        return False
    
    workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
    
    if not workflow_files:
        print("❌ No workflow files found")
        return False
    
    invalid_workflows = []
    for workflow_file in workflow_files:
        try:
            with open(workflow_file, 'r') as f:
                workflow_data = yaml.safe_load(f)
            
            # Basic structure check (handle 'on' parsed as True in YAML)
            has_on = 'on' in workflow_data or True in workflow_data
            if 'name' not in workflow_data or not has_on or 'jobs' not in workflow_data:
                invalid_workflows.append(workflow_file.name)
        except yaml.YAMLError:
            invalid_workflows.append(workflow_file.name)
    
    if invalid_workflows:
        print(f"❌ Invalid workflow files: {invalid_workflows}")
        return False
    
    print("✅ All GitHub workflow files are valid")
    return True

def run_all_tests():
    """Run all tests and return overall result."""
    tests = [
        test_directory_structure,
        test_ee_file_validity,
        test_ansible_cfg_validity,
        test_scripts_executable,
        test_makefile_targets,
        test_examples_validity,
        test_github_workflows
    ]
    
    print("🧪 Running Ansible Custom EE Builder tests...\n")
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
            results.append(False)
        print()  # Empty line for readability
    
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print(f"💥 {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)