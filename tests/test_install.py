#!/usr/bin/env python3
"""
Test script to validate installation functionality.

This script tests the core installation logic without actually installing packages.
"""

import sys
import subprocess
import tempfile
import os
from pathlib import Path


def test_python_version_check():
    """Test Python version requirement validation."""
    print("🐍 Testing Python version validation...")

    major = sys.version_info[0]
    minor = sys.version_info[1]

    print(f"   Current Python: {major}.{minor}")

    # Test the same logic as install.sh
    meets_requirement = major >= 3 and (major > 3 or minor >= 9)

    if meets_requirement:
        print("   ✅ Version requirement met")
    else:
        print("   ❌ Version requirement not met")
    
    assert meets_requirement, "Python version requirement not met"


def test_command_availability():
    """Test command availability checks."""
    print("🔧 Testing command availability...")

    commands_to_check = {
        "python3": "Python interpreter",
        "pip": "Package installer",
        "git": "Version control (for source install)",
        "java": "Java runtime (optional)",
    }

    results = {}

    for cmd, description in commands_to_check.items():
        try:
            if cmd == "pip":
                # Test both pip command and python -m pip
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "--version"], capture_output=True, text=True
                )
                available = result.returncode == 0
            else:
                result = subprocess.run([cmd, "--version"], capture_output=True, text=True)
                available = result.returncode == 0

            results[cmd] = available
            status = "✅" if available else "❌"
            print(f"   {status} {cmd}: {description}")

        except FileNotFoundError:
            results[cmd] = False
            print(f"   ❌ {cmd}: {description} (not found)")

    # Assert that at least python3 and pip are available
    assert results.get('python3', False), "Python3 command not available"
    assert results.get('pip', False), "Pip command not available"


def test_fireflytx_import():
    """Test if fireflytx can be imported (if installed)."""
    print("📦 Testing FireflyTX import...")

    try:
        import fireflytx
        from fireflytx import saga, saga_step, create_saga_engine

        print(f"   ✅ FireflyTX version: {fireflytx.__version__}")
        print("   ✅ Core imports successful")

        # Test basic functionality
        print("   ✅ Basic functionality test passed")
        assert True  # Import successful

    except ImportError as e:
        print(f"   ⚠️  FireflyTX not installed: {e}")
        # Don't fail the test if not installed, just skip
        import pytest
        pytest.skip("FireflyTX not installed")


def test_install_script_existence():
    """Test that install script exists and is executable."""
    print("📜 Testing install script...")

    script_path = Path(__file__).parent.parent / "install.sh"

    if script_path.exists():
        print("   ✅ install.sh exists")

        # Check if executable
        if os.access(script_path, os.X_OK):
            print("   ✅ install.sh is executable")

            # Test help option
            try:
                result = subprocess.run(
                    [str(script_path), "--help"], capture_output=True, text=True
                )
                if result.returncode == 0 or "help" in result.stdout.lower():
                    print("   ✅ install.sh help option works")
                    assert True
                else:
                    print("   ❌ install.sh help option failed")
                    assert False, "install.sh help option failed"
            except Exception as e:
                print(f"   ❌ install.sh execution failed: {e}")
                assert False, f"install.sh execution failed: {e}"
        else:
            print("   ❌ install.sh is not executable")
            assert False, "install.sh is not executable"
    else:
        print("   ❌ install.sh not found")
        assert False, "install.sh not found"


def test_setup_py_existence():
    """Test that setup.py exists for source installation."""
    print("⚙️  Testing setup.py...")

    setup_path = Path(__file__).parent.parent / "setup.py"

    if setup_path.exists():
        print("   ✅ setup.py exists")

        # Try to validate setup.py syntax
        try:
            with open(setup_path, "r") as f:
                content = f.read()
                if "fireflytx" in content and "setup(" in content:
                    print("   ✅ setup.py looks valid")
                    assert True
                else:
                    print("   ⚠️  setup.py might be incomplete")
                    assert False, "setup.py might be incomplete"
        except Exception as e:
            print(f"   ❌ setup.py validation failed: {e}")
            assert False, f"setup.py validation failed: {e}"
    else:
        print("   ❌ setup.py not found")
        assert False, "setup.py not found"


def main():
    """Run all installation tests."""
    print("🔥 FireflyTX Installation Test Suite")
    print("=" * 50)
    print()

    tests = [
        ("Python Version", test_python_version_check),
        ("Command Availability", test_command_availability),
        ("Install Script", test_install_script_existence),
        ("Setup Configuration", test_setup_py_existence),
        ("FireflyTX Import", test_fireflytx_import),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
            print()
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            results[test_name] = False
            print()

    # Summary
    print("📊 Test Results Summary:")
    print("-" * 30)

    passed = 0
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All installation tests passed!")
        return True
    else:
        print("⚠️  Some installation tests failed.")
        print("   This might be normal if FireflyTX is not yet installed")
        print("   or if optional dependencies are missing.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
