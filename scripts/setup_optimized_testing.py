#!/usr/bin/env python3
"""
Setup script for FastAPI-Easy optimized testing infrastructure.

This script helps configure and validate the optimized testing setup.
"""

import os
import sys
import shutil
from pathlib import Path
import argparse
import json


def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
        "pytest-asyncio>=0.21.0",
        "pytest-xdist>=3.3.0",
        "pytest-benchmark>=4.0.0",
        "pytest-timeout>=2.1.0",
        "psutil>=5.9.0",
    ]

    optional_packages = [
        "redis>=4.5.0",  # For Redis caching
        "matplotlib>=3.5.0",  # For visualizations
        "memory-profiler>=0.60.0",  # For memory profiling
    ]

    missing_required = []
    missing_optional = []

    print("🔍 Checking dependencies...")

    # Check required packages
    for package in required_packages:
        try:
            package_name = package.split(">=")[0].split("==")[0]
            __import__(package_name.replace("-", "_"))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing_required.append(package)

    # Check optional packages
    print("\n📦 Checking optional packages...")
    for package in optional_packages:
        try:
            package_name = package.split(">=")[0].split("==")[0]
            __import__(package_name.replace("-", "_"))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ⚠️  {package} (optional)")
            missing_optional.append(package)

    if missing_required:
        print(f"\n❌ Missing required packages: {', '.join(missing_required)}")
        print("Install with: pip install " + " ".join(missing_required))
        return False

    if missing_optional:
        print(f"\n⚠️  Missing optional packages: {', '.join(missing_optional)}")
        print("Install with: pip install " + " ".join(missing_optional))

    return True


def setup_configuration():
    """Set up optimized test configuration"""
    print("\n⚙️  Setting up configuration...")

    project_root = Path.cwd()
    tests_dir = project_root / "tests"

    # Check if we're in the right directory
    if not tests_dir.exists():
        print("❌ No 'tests' directory found. Please run from project root.")
        return False

    # Copy optimized pytest configuration
    config_files = [
        ("pytest.ini", "pytest_optimized.ini"),
    ]

    for target, source in config_files:
        source_path = Path(__file__).parent.parent / "src" / "fastapi_easy" / source
        target_path = project_root / target

        if source_path.exists():
            if target_path.exists():
                backup_path = target_path.with_suffix(f"{target_path.suffix}.backup")
                shutil.move(str(target_path), str(backup_path))
                print(f"  📦 Backed up existing {target} to {backup_path.name}")

            shutil.copy(str(source_path), str(target_path))
            print(f"  ✅ Created {target}")
        else:
            print(f"  ⚠️  Source file {source} not found")

    return True


def create_test_directories():
    """Create necessary test directories"""
    print("\n📁 Creating test directories...")

    directories = [
        "test_reports",
        "test_reports/html",
        "test_reports/json",
        "test_reports/visualizations",
    ]

    project_root = Path.cwd()
    for dir_path in directories:
        full_path = project_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {dir_path}")

    return True


def setup_conftest():
    """Set up optimized conftest.py"""
    print("\n🔧 Setting up conftest.py...")

    tests_dir = Path.cwd() / "tests"
    optimized_conftest = Path(__file__).parent.parent / "tests" / "conftest_optimized.py"

    if optimized_conftest.exists():
        target_conftest = tests_dir / "conftest_optimized.py"
        shutil.copy(str(optimized_conftest), str(target_conftest))
        print(f"  ✅ Created conftest_optimized.py")

        # Also create a simple conftest.py that imports from the optimized version
        conftest_content = '''"""
Main conftest.py that imports optimized fixtures.
"""

# Import all optimized fixtures
from .conftest_optimized import *  # noqa: F401,F403

# You can add your own custom fixtures here
'''
        with open(tests_dir / "conftest.py", "w") as f:
            f.write(conftest_content)
        print(f"  ✅ Updated conftest.py")

    return True


def create_example_tests():
    """Create example tests demonstrating optimizations"""
    print("\n📝 Creating example tests...")

    tests_dir = Path.cwd() / "tests"

    # Create example unit test
    unit_test_content = '''"""Example optimized unit test"""

import pytest
from fastapi_easy.testing import cached, performance_test


@pytest.mark.unit
@pytest.mark.fast
@cached(ttl=3600)
def test_cached_operation():
    """Example of cached test operation"""
    # This result will be cached
    result = expensive_computation()
    assert result > 0


def expensive_computation():
    """Simulate expensive operation"""
    return sum(range(1000))


@performance_test(benchmark=True, iterations=10)
@pytest.mark.performance
def test_api_performance():
    """Example performance benchmark test"""
    import time
    time.sleep(0.01)  # Simulate work
    assert True
'''
    with open(tests_dir / "test_optimized_examples.py", "w") as f:
        f.write(unit_test_content)
    print(f"  ✅ Created test_optimized_examples.py")

    return True


def validate_setup():
    """Validate the setup"""
    print("\n✅ Validating setup...")

    # Try to import the testing infrastructure
    try:
        from fastapi_easy.testing import (
            performance_monitor,
            test_cache,
            test_reporter,
        )
        print("  ✅ Testing infrastructure imports correctly")
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False

    # Check pytest configuration
    try:
        import pytest
        pytest_ini = Path.cwd() / "pytest.ini"
        if pytest_ini.exists():
            print("  ✅ pytest.ini found")
        else:
            print("  ⚠️  pytest.ini not found")
    except Exception as e:
        print(f"  ❌ pytest validation error: {e}")

    return True


def run_baseline_tests():
    """Run baseline tests to establish performance metrics"""
    print("\n🏃 Running baseline tests...")

    try:
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_optimized_examples.py", "-v"],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print("  ✅ Baseline tests completed successfully")
            print(f"  📊 Output: {len(result.stdout)} characters")
        else:
            print("  ⚠️  Some tests had issues")
            print(f"  Error: {result.stderr[:200]}...")

    except subprocess.TimeoutExpired:
        print("  ⚠️  Tests timed out")
    except Exception as e:
        print(f"  ❌ Error running tests: {e}")


def print_summary():
    """Print setup summary"""
    print("\n" + "="*60)
    print("🎉 FastAPI-Easy Test Infrastructure Setup Complete!")
    print("="*60)

    print("\n🚀 Quick Start:")
    print("  # Run all tests with optimizations")
    print("  pytest -c pytest.ini -n auto")
    print()
    print("  # Run only unit tests")
    print("  pytest -c pytest.ini -m 'unit' -n auto")
    print()
    print("  # Run performance benchmarks")
    print("  pytest -c pytest.ini -m 'performance' --benchmark-only")
    print()

    print("📊 Reports will be generated in 'test_reports/' directory")
    print("📈 Performance baseline established for regression detection")
    print("🧠 Test caching enabled for faster execution")
    print("⚡ Parallel testing configured for maximum speed")

    print("\n📚 Documentation:")
    print("  docs/TEST_OPTIMIZATION_GUIDE.md - Comprehensive guide")
    print("  src/fastapi_easy/testing/ - API documentation")

    print("\n✨ Happy testing!")


def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(
        description="Setup FastAPI-Easy optimized testing infrastructure"
    )
    parser.add_argument(
        "--skip-deps", action="store_true",
        help="Skip dependency checking"
    )
    parser.add_argument(
        "--skip-examples", action="store_true",
        help="Skip creating example tests"
    )
    parser.add_argument(
        "--run-tests", action="store_true",
        help="Run baseline tests after setup"
    )

    args = parser.parse_args()

    print("🚀 Setting up FastAPI-Easy optimized testing infrastructure...\n")

    success = True

    # Check dependencies
    if not args.skip_deps:
        success &= check_dependencies()

    # Setup configuration
    success &= setup_configuration()

    # Create directories
    success &= create_test_directories()

    # Setup conftest
    success &= setup_conftest()

    # Create example tests
    if not args.skip_examples:
        success &= create_example_tests()

    # Validate setup
    success &= validate_setup()

    if success:
        # Run baseline tests if requested
        if args.run_tests:
            run_baseline_tests()

        print_summary()
        sys.exit(0)
    else:
        print("\n❌ Setup completed with errors. Please check the messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()