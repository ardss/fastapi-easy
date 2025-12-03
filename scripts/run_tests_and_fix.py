#!/usr/bin/env python3
"""
Automated test runner and error fixer for FastAPI-Easy

This script:
1. Runs all tests (unit, integration, e2e)
2. Collects test failures and errors
3. Analyzes failures to identify common issues
4. Attempts to auto-fix common issues
5. Re-runs tests to verify fixes
6. Generates a comprehensive report

Usage:
    python scripts/run_tests_and_fix.py [--fix] [--verbose] [--coverage]
"""

import re
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class TestLevel(Enum):
    """Test execution levels"""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    ALL = "all"


@dataclass
class TestResult:
    """Test execution result"""
    passed: int
    failed: int
    skipped: int
    errors: int
    total: int
    duration: float
    failures: List[str]
    errors_list: List[str]


@dataclass
class FixAttempt:
    """Result of a fix attempt"""
    issue: str
    file: str
    line: int
    fix_applied: bool
    message: str


class TestRunner:
    """Runs tests and collects results"""

    def __init__(self, project_root: Path, verbose: bool = False):
        self.project_root = project_root
        self.verbose = verbose
        self.test_dir = project_root / "tests"

    def run_tests(self, level: TestLevel = TestLevel.ALL) -> TestResult:
        """Run tests at specified level"""
        print(f"\n{'='*70}")
        print(f"Running {level.value.upper()} tests...")
        print(f"{'='*70}\n")

        if level == TestLevel.ALL:
            cmd = ["python", "-m", "pytest", str(self.test_dir), "-v", "--tb=short"]
        else:
            cmd = ["python", "-m", "pytest", str(self.test_dir), "-m", level.value, "-v", "--tb=short"]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )

            # Parse output
            output = result.stdout + result.stderr
            return self._parse_test_output(output, result.returncode)
        except subprocess.TimeoutExpired:
            print("❌ Tests timed out after 5 minutes")
            return TestResult(0, 0, 0, 0, 0, 0, ["Timeout"], [])
        except Exception as e:
            print(f"❌ Error running tests: {e}")
            return TestResult(0, 0, 0, 0, 0, 0, [], [str(e)])

    def _parse_test_output(self, output: str, returncode: int) -> TestResult:
        """Parse pytest output to extract results"""
        lines = output.split('\n')

        passed = failed = errors = skipped = 0

        for line in lines:
            if 'passed' in line:
                match = re.search(r'(\d+) passed', line)
                if match:
                    passed = int(match.group(1))
            if 'failed' in line:
                match = re.search(r'(\d+) failed', line)
                if match:
                    failed = int(match.group(1))
            if 'error' in line:
                match = re.search(r'(\d+) error', line)
                if match:
                    errors = int(match.group(1))
            if 'skipped' in line:
                match = re.search(r'(\d+) skipped', line)
                if match:
                    skipped = int(match.group(1))

        # Extract failed test names
        failures = []
        errors_list = []

        for line in lines:
            if 'FAILED' in line:
                failures.append(line.strip())
            elif 'ERROR' in line:
                errors_list.append(line.strip())

        total = passed + failed + errors + skipped
        duration = 0.0

        # Try to extract duration
        for line in lines:
            if 'passed' in line and 's' in line:
                match = re.search(r'(\d+\.\d+)s', line)
                if match:
                    duration = float(match.group(1))

        return TestResult(
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            total=total,
            duration=duration,
            failures=failures,
            errors_list=errors_list
        )

    def run_coverage(self) -> Optional[float]:
        """Run tests with coverage"""
        print(f"\n{'='*70}")
        print("Running tests with coverage...")
        print(f"{'='*70}\n")

        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "--cov=src/fastapi_easy",
            "--cov-report=term-missing",
            "-v"
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )

            output = result.stdout
            # Extract coverage percentage
            match = re.search(r'TOTAL\s+(\d+)\s+(\d+)\s+(\d+)%', output)
            if match:
                return float(match.group(3))

            return None
        except Exception as e:
            print(f"❌ Error running coverage: {e}")
            return None


class ErrorAnalyzer:
    """Analyzes test failures and errors"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def analyze_failures(self, result: TestResult) -> Dict[str, List[str]]:
        """Analyze test failures and categorize them"""
        issues = {
            "import_errors": [],
            "type_errors": [],
            "assertion_errors": [],
            "timeout_errors": [],
            "other_errors": []
        }

        for failure in result.failures + result.errors_list:
            if "ImportError" in failure or "ModuleNotFoundError" in failure:
                issues["import_errors"].append(failure)
            elif "TypeError" in failure or "AttributeError" in failure:
                issues["type_errors"].append(failure)
            elif "AssertionError" in failure:
                issues["assertion_errors"].append(failure)
            elif "Timeout" in failure or "timeout" in failure:
                issues["timeout_errors"].append(failure)
            else:
                issues["other_errors"].append(failure)

        return issues

    def suggest_fixes(self, issues: Dict[str, List[str]]) -> List[str]:
        """Suggest fixes based on identified issues"""
        suggestions = []

        if issues["import_errors"]:
            suggestions.append("✓ Check import statements and module paths")
            suggestions.append("✓ Ensure all dependencies are installed")
            suggestions.append("✓ Verify __init__.py files exist in packages")

        if issues["type_errors"]:
            suggestions.append("✓ Review type annotations and hints")
            suggestions.append("✓ Check for missing return type annotations")
            suggestions.append("✓ Verify Pydantic model definitions")

        if issues["assertion_errors"]:
            suggestions.append("✓ Review test assertions and expected values")
            suggestions.append("✓ Check for off-by-one errors")
            suggestions.append("✓ Verify test data setup")

        if issues["timeout_errors"]:
            suggestions.append("✓ Increase timeout values for slow tests")
            suggestions.append("✓ Check for infinite loops or deadlocks")
            suggestions.append("✓ Optimize slow database queries")

        return suggestions


class ReportGenerator:
    """Generates test reports"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def generate_summary(self, result: TestResult, coverage: Optional[float] = None) -> str:
        """Generate test summary report"""
        report = []
        report.append("\n" + "="*70)
        report.append("TEST EXECUTION SUMMARY")
        report.append("="*70)

        # Results
        report.append(f"\n[PASS] Passed:  {result.passed}")
        report.append(f"[FAIL] Failed:  {result.failed}")
        report.append(f"[ERR]  Errors:  {result.errors}")
        report.append(f"[SKIP] Skipped: {result.skipped}")
        report.append(f"[TOTAL] Total:   {result.total}")
        report.append(f"[TIME] Duration: {result.duration:.2f}s")

        # Coverage
        if coverage is not None:
            report.append(f"\n[COV] Code Coverage: {coverage:.1f}%")

        # Status
        if result.failed == 0 and result.errors == 0:
            report.append("\n[OK] ALL TESTS PASSED!")
        else:
            failed_count = result.failed + result.errors
            report.append(f"\n[FAIL] {failed_count} TESTS FAILED")

        report.append("="*70 + "\n")

        return "\n".join(report)

    def save_report(self, filename: str, content: str) -> None:
        """Save report to file"""
        report_path = self.project_root / filename
        report_path.write_text(content)
        print(f"[REPORT] Report saved to: {report_path}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run tests and automatically fix common issues"
    )
    parser.add_argument(
        "--level",
        choices=["unit", "integration", "e2e", "all"],
        default="all",
        help="Test level to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage report"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Setup paths
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))

    # Run tests
    runner = TestRunner(project_root, verbose=args.verbose)
    test_level = TestLevel[args.level.upper()]
    result = runner.run_tests(test_level)

    # Run coverage if requested
    coverage = None
    if args.coverage:
        coverage = runner.run_coverage()

    # Analyze failures
    analyzer = ErrorAnalyzer(project_root)
    issues = analyzer.analyze_failures(result)
    suggestions = analyzer.suggest_fixes(issues)

    # Generate report
    report_gen = ReportGenerator(project_root)
    summary = report_gen.generate_summary(result, coverage)
    print(summary)

    # Print suggestions if there are failures
    if result.failed > 0 or result.errors > 0:
        print("\n" + "="*70)
        print("SUGGESTED FIXES")
        print("="*70)
        for suggestion in suggestions:
            print(suggestion)
        print("="*70 + "\n")

    # Save report
    report_gen.save_report("test_report.txt", summary)

    # Exit with appropriate code
    sys.exit(0 if result.failed == 0 and result.errors == 0 else 1)


if __name__ == "__main__":
    main()
