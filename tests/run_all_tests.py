#!/usr/bin/env python3
"""
Complete Test Suite Runner for Ansible Custom EE Builder
"""

import sys
import subprocess
from pathlib import Path

def run_test_suite(test_script, description):
    """Run a test suite and return results."""
    print(f"\n{'='*60}")
    print(f"🧪 Running {description}")
    print('='*60)
    
    try:
        result = subprocess.run([sys.executable, test_script], 
                              capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running {test_script}: {e}")
        return False

def main():
    """Run all test suites."""
    project_root = Path.cwd()
    test_scripts = [
        (project_root / "tests/test_build.py", "Project Structure Tests"),
        (project_root / "tests/test_release.py", "Release Readiness Tests"),
        (project_root / "tests/test_integration.py", "Integration Tests"),
        (project_root / "tests/test_workflows.py", "GitHub Actions Workflow Tests"),
    ]
    
    print("🚀 Ansible Custom EE Builder - Complete Test Suite")
    print("=" * 60)
    
    results = []
    
    for test_script, description in test_scripts:
        if test_script.exists():
            success = run_test_suite(test_script, description)
            results.append((description, success))
        else:
            print(f"❌ Test script not found: {test_script}")
            results.append((description, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUITE SUMMARY")
    print('='*60)
    
    passed = 0
    total = len(results)
    
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {description}")
        if success:
            passed += 1
    
    print(f"\n📈 Overall Results: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Project is ready for release! 🎉")
        print("\n✅ Next steps:")
        print("   1. Commit your changes")
        print("   2. Create a release tag (e.g., git tag v1.0.0)")
        print("   3. Push to GitHub (git push origin v1.0.0)")
        print("   4. GitHub Actions will automatically build and test")
        return True
    else:
        print(f"💥 {total - passed} test suite(s) failed. Please fix issues before release.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)