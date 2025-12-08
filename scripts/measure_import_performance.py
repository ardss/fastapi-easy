#!/usr/bin/env python3
"""
Measure import performance for FastAPI-Easy

This script measures import times and memory usage to verify optimization improvements.
"""

import sys
import time
import tracemalloc
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


def measure_import_time(module_name: str) -> Tuple[float, int]:
    """Measure import time for a specific module"""
    # Start tracing memory
    tracemalloc.start()

    # Measure import time
    start_time = time.perf_counter()

    try:
        # Clear module cache if already imported
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Import the module
        __import__(module_name)

        import_time = time.perf_counter() - start_time

        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return import_time, peak

    except Exception as e:
        tracemalloc.stop()
        return 0, 0


def run_benchmark() -> Dict[str, Dict[str, float]]:
    """Run comprehensive import benchmark"""

    modules_to_test = [
        "fastapi_easy",
        "fastapi_easy.core",
        "fastapi_easy.backends.sqlalchemy",
        "fastapi_easy.security",
        "fastapi_easy.crud_router",
        "fastapi_easy.app",
    ]

    results = {}

    print("FastAPI-Easy Import Performance Benchmark")
    print("=" * 50)

    for module in modules_to_test:
        print(f"\nTesting: {module}")

        # Run multiple measurements for accuracy
        times = []
        memory_usage = []

        for _ in range(3):
            import_time, memory = measure_import_time(module)
            if import_time > 0:
                times.append(import_time)
                memory_usage.append(memory)

        if times:
            avg_time = sum(times) / len(times)
            avg_memory = sum(memory_usage) / len(memory_usage)

            results[module] = {
                "import_time": avg_time,
                "memory_usage": avg_memory,
                "min_time": min(times),
                "max_time": max(times),
            }

            print(f"  Import Time: {avg_time:.3f}s (+/- {max(times) - min(times):.3f}s)")
            print(f"  Memory Usage: {avg_memory / 1024 / 1024:.1f} MB")
        else:
            print(f"  Failed to import {module}")

    return results


def compare_with_baseline(results: Dict) -> None:
    """Compare results with baseline (if available)"""
    baseline_file = Path(__file__).parent / "baseline_performance.json"

    if not baseline_file.exists():
        print("\nBaseline not found. Saving current results as baseline...")
        import json
        with open(baseline_file, 'w') as f:
            json.dump(results, f, indent=2)
        return

    import json
    with open(baseline_file, 'r') as f:
        baseline = json.load(f)

    print("\nPerformance Comparison (Current vs Baseline):")
    print("-" * 50)

    for module in results:
        if module in baseline:
            current_time = results[module]["import_time"]
            baseline_time = baseline[module]["import_time"]

            if baseline_time > 0:
                improvement = ((baseline_time - current_time) / baseline_time) * 100
                status = "[OK]" if improvement > 0 else "[REGRESSION]"
                print(f"{status} {module}: {improvement:+.1f}% "
                      f"({baseline_time:.3f}s → {current_time:.3f}s)")


def analyze_import_patterns() -> Dict[str, int]:
    """Analyze import patterns across the codebase"""
    import_count = {}

    src_dir = Path(__file__).parent.parent / "src"

    for py_file in src_dir.rglob("*.py"):
        if 'test' in py_file.name or '__pycache__' in str(py_file):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Count import statements
            import_lines = [line for line in content.split('\n')
                           if line.strip().startswith(('import ', 'from '))]

            import_count[str(py_file.relative_to(src_dir))] = len(import_lines)

        except Exception:
            pass

    # Get top 10 files with most imports
    sorted_imports = sorted(import_count.items(), key=lambda x: x[1], reverse=True)[:10]

    print("\nTop 10 Files by Import Count:")
    print("-" * 30)
    for file_path, count in sorted_imports:
        print(f"{file_path}: {count} imports")

    return import_count


def check_optional_imports() -> List[str]:
    """Check which optional imports are available"""
    optional_modules = [
        ("sqlalchemy", "SQLAlchemy database backend"),
        ("tortoise", "Tortoise ORM backend"),
        ("motor", "MongoDB backend"),
        ("sqlmodel", "SQLModel backend"),
        ("jwt", "JWT authentication"),
        ("bcrypt", "Password hashing"),
        ("cryptography", "Encryption support"),
        ("redis", "Redis caching"),
        ("prometheus_client", "Metrics collection"),
        ("sentry_sdk", "Error tracking"),
    ]

    print("\nOptional Dependencies Status:")
    print("-" * 30)

    available = []
    for module, description in optional_modules:
        try:
            __import__(module)
            status = "[OK] Available"
            available.append(module)
        except ImportError:
            status = "[X] Not installed"

        print(f"{module:20} - {description:30} [{status}]")

    return available


def generate_optimization_suggestions(results: Dict) -> List[str]:
    """Generate optimization suggestions based on results"""
    suggestions = []

    # Check for slow imports
    slow_threshold = 0.1  # 100ms
    slow_modules = [m for m, r in results.items() if r["import_time"] > slow_threshold]

    if slow_modules:
        suggestions.append(
            f"Consider lazy loading for slow modules: {', '.join(slow_modules)}"
        )

    # Check for memory-heavy modules
    memory_threshold = 10 * 1024 * 1024  # 10MB
    heavy_modules = [m for m, r in results.items() if r["memory_usage"] > memory_threshold]

    if heavy_modules:
        suggestions.append(
            f"Memory-heavy modules detected: {', '.join(heavy_modules)}"
        )

    # General suggestions
    suggestions.extend([
        "Consider splitting large modules into smaller, focused modules",
        "Use TYPE_CHECKING for type-only imports to reduce runtime overhead",
        "Implement lazy loading for optional features",
        "Regularly profile imports to catch regressions",
    ])

    return suggestions


def main():
    """Main benchmark function"""

    print("FastAPI-Easy Import Performance Analysis")
    print("=" * 50)
    print(f"Python version: {sys.version}")
    print(f"Working directory: {Path.cwd()}")

    # Run benchmarks
    results = run_benchmark()

    # Compare with baseline
    compare_with_baseline(results)

    # Analyze patterns
    analyze_import_patterns()

    # Check optional imports
    check_optional_imports()

    # Generate suggestions
    suggestions = generate_optimization_suggestions(results)

    if suggestions:
        print("\nOptimization Suggestions:")
        print("-" * 25)
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")

    print("\n[Benchmark complete]")

    return results


if __name__ == "__main__":
    results = main()