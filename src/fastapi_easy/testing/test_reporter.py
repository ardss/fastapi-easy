"""
Comprehensive test execution reporting system for FastAPI-Easy.
Provides detailed timing reports, performance analysis, and trend tracking.
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict
import warnings

try:
    import matplotlib.pyplot as plt
    import pandas as pd
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False


@dataclass
class TestTiming:
    """Individual test timing information"""
    name: str
    duration: float
    start_time: float
    end_time: float
    markers: List[str]
    status: str  # "passed", "failed", "skipped"
    error_message: Optional[str] = None
    setup_time: Optional[float] = None
    teardown_time: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    cpu_percent: Optional[float] = None


@dataclass
class TestSuiteReport:
    """Complete test suite execution report"""
    session_start: datetime
    session_end: datetime
    total_duration: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    test_timings: List[TestTiming]
    slow_tests: List[TestTiming]
    failed_test_details: List[Dict[str, Any]]
    performance_summary: Dict[str, Any]
    trend_analysis: Optional[Dict[str, Any]] = None


class TestReporter:
    """Advanced test execution reporter with trend analysis"""

    def __init__(self, report_dir: Path = Path("test_reports")):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True)
        self.current_session: List[TestTiming] = []
        self.session_start = None
        self.session_end = None
        self._lock = threading.Lock()

        # Load historical data for trend analysis
        self.historical_data = self._load_historical_data()

    def _load_historical_data(self) -> List[Dict[str, Any]]:
        """Load historical test data for trend analysis"""
        history_file = self.report_dir / "test_history.json"
        if history_file.exists():
            try:
                with open(history_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return []

    def _save_historical_data(self):
        """Save current session to historical data"""
        if not self.current_session:
            return

        session_summary = {
            "timestamp": self.session_start.isoformat() if self.session_start else None,
            "total_duration": sum(t.duration for t in self.current_session),
            "total_tests": len(self.current_session),
            "passed_tests": len([t for t in self.current_session if t.status == "passed"]),
            "failed_tests": len([t for t in self.current_session if t.status == "failed"]),
            "avg_duration": sum(t.duration for t in self.current_session) / len(self.current_session),
            "max_duration": max(t.duration for t in self.current_session),
            "test_details": [asdict(t) for t in self.current_session]
        }

        self.historical_data.append(session_summary)

        # Keep only last 100 sessions
        self.historical_data = self.historical_data[-100:]

        # Save to file
        history_file = self.report_dir / "test_history.json"
        try:
            with open(history_file, "w") as f:
                json.dump(self.historical_data, f, indent=2)
        except IOError as e:
            warnings.warn(f"Could not save test history: {e}")

    def start_session(self):
        """Start a new test session"""
        with self._lock:
            self.session_start = datetime.now()
            self.current_session = []
            self.session_end = None

    def end_session(self):
        """End the current test session"""
        with self._lock:
            self.session_end = datetime.now()
            self._save_historical_data()

    def record_test(self, test_name: str, duration: float, status: str,
                   markers: Optional[List[str]] = None, error_message: Optional[str] = None,
                   setup_time: Optional[float] = None, teardown_time: Optional[float] = None,
                   memory_usage: Optional[float] = None, cpu_percent: Optional[float] = None):
        """Record timing for an individual test"""
        end_time = time.time()
        start_time = end_time - duration

        timing = TestTiming(
            name=test_name,
            duration=duration,
            start_time=start_time,
            end_time=end_time,
            markers=markers or [],
            status=status,
            error_message=error_message,
            setup_time=setup_time,
            teardown_time=teardown_time,
            memory_usage_mb=memory_usage,
            cpu_percent=cpu_percent
        )

        with self._lock:
            self.current_session.append(timing)

    def generate_report(self) -> TestSuiteReport:
        """Generate comprehensive test suite report"""
        if not self.current_session:
            raise ValueError("No test data available. Start a session and record tests first.")

        total_duration = sum(t.duration for t in self.current_session)
        passed_tests = len([t for t in self.current_session if t.status == "passed"])
        failed_tests = len([t for t in self.current_session if t.status == "failed"])
        skipped_tests = len([t for t in self.current_session if t.status == "skipped"])
        error_tests = len([t for t in self.current_session if t.status == "error"])

        # Identify slow tests (top 10% or tests > 1 second)
        slow_threshold = max(1.0, sorted([t.duration for t in self.current_session])[int(len(self.current_session) * 0.9)])
        slow_tests = [t for t in self.current_session if t.duration > slow_threshold]
        slow_tests.sort(key=lambda x: x.duration, reverse=True)

        # Failed test details
        failed_test_details = []
        for test in self.current_session:
            if test.status in ["failed", "error"]:
                failed_test_details.append({
                    "name": test.name,
                    "duration": test.duration,
                    "error": test.error_message,
                    "markers": test.markers
                })

        # Performance summary
        durations = [t.duration for t in self.current_session]
        performance_summary = {
            "total_duration": total_duration,
            "avg_duration": sum(durations) / len(durations),
            "median_duration": sorted(durations)[len(durations) // 2],
            "min_duration": min(durations),
            "max_duration": max(durations),
            "std_deviation": self._calculate_std_deviation(durations),
            "slow_tests_count": len(slow_tests),
            "slow_threshold": slow_threshold,
            "tests_per_second": len(self.current_session) / total_duration if total_duration > 0 else 0,
        }

        # Add marker-specific statistics
        marker_stats = defaultdict(list)
        for test in self.current_session:
            for marker in test.markers:
                marker_stats[marker].append(test.duration)

        performance_summary["marker_statistics"] = {
            marker: {
                "count": len(durations),
                "avg_duration": sum(durations) / len(durations),
                "max_duration": max(durations)
            }
            for marker, durations in marker_stats.items()
        }

        # Trend analysis
        trend_analysis = self._analyze_trends()

        return TestSuiteReport(
            session_start=self.session_start,
            session_end=self.session_end or datetime.now(),
            total_duration=total_duration,
            total_tests=len(self.current_session),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            error_tests=error_tests,
            test_timings=self.current_session,
            slow_tests=slow_tests,
            failed_test_details=failed_test_details,
            performance_summary=performance_summary,
            trend_analysis=trend_analysis
        )

    def _calculate_std_deviation(self, values: List[float]) -> float:
        """Calculate standard deviation of values"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def _analyze_trends(self) -> Optional[Dict[str, Any]]:
        """Analyze performance trends from historical data"""
        if len(self.historical_data) < 3:
            return None

        recent_sessions = self.historical_data[-10:]  # Last 10 sessions

        # Calculate trends
        durations = [s["total_duration"] for s in recent_sessions]
        test_counts = [s["total_tests"] for s in recent_sessions]
        avg_durations = [s["avg_duration"] for s in recent_sessions]

        # Simple linear regression for trend
        def linear_trend(values):
            n = len(values)
            if n < 2:
                return 0
            x = list(range(n))
            sum_x = sum(x)
            sum_y = sum(values)
            sum_xy = sum(x[i] * values[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))

            if n * sum_x2 - sum_x ** 2 == 0:
                return 0

            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            return slope

        return {
            "sessions_analyzed": len(recent_sessions),
            "duration_trend": linear_trend(durations),
            "avg_duration_trend": linear_trend(avg_durations),
            "test_count_trend": linear_trend(test_counts),
            "current_session_vs_avg": {
                "duration": self.current_session and (sum(t.duration for t in self.current_session) / sum(durations) - 1) * 100,
                "avg_test_time": self.current_session and (sum(t.duration for t in self.current_session) / len(self.current_session) / (sum(avg_durations) / len(avg_durations)) - 1) * 100
            }
        }

    def save_report(self, report: TestSuiteReport, format: str = "json") -> Path:
        """Save report to file in specified format"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format.lower() == "json":
            filename = f"test_report_{timestamp}.json"
            filepath = self.report_dir / filename

            report_data = {
                "session_start": report.session_start.isoformat(),
                "session_end": report.session_end.isoformat(),
                "total_duration": report.total_duration,
                "total_tests": report.total_tests,
                "passed_tests": report.passed_tests,
                "failed_tests": report.failed_tests,
                "skipped_tests": report.skipped_tests,
                "error_tests": report.error_tests,
                "test_timings": [asdict(t) for t in report.test_timings],
                "slow_tests": [asdict(t) for t in report.slow_tests],
                "failed_test_details": report.failed_test_details,
                "performance_summary": report.performance_summary,
                "trend_analysis": report.trend_analysis
            }

            with open(filepath, "w") as f:
                json.dump(report_data, f, indent=2)

        elif format.lower() == "html":
            filename = f"test_report_{timestamp}.html"
            filepath = self.report_dir / filename
            self._generate_html_report(report, filepath)

        elif format.lower() == "csv":
            filename = f"test_report_{timestamp}.csv"
            filepath = self.report_dir / filename
            self._generate_csv_report(report, filepath)

        else:
            raise ValueError(f"Unsupported format: {format}")

        return filepath

    def _generate_html_report(self, report: TestSuiteReport, filepath: Path):
        """Generate HTML report with visualizations"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Execution Report - {report.session_start.strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .skipped {{ color: orange; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .slow-test {{ background-color: #ffe6e6; }}
    </style>
</head>
<body>
    <h1>Test Execution Report</h1>

    <div class="summary">
        <h2>Session Summary</h2>
        <p><strong>Start:</strong> {report.session_start.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>End:</strong> {report.session_end.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Total Duration:</strong> {report.total_duration:.2f} seconds</p>
        <p><strong>Total Tests:</strong> {report.total_tests}</p>
        <p class="passed"><strong>Passed:</strong> {report.passed_tests}</p>
        <p class="failed"><strong>Failed:</strong> {report.failed_tests}</p>
        <p class="skipped"><strong>Skipped:</strong> {report.skipped_tests}</p>
    </div>

    <div class="summary">
        <h2>Performance Summary</h2>
        <p><strong>Average Test Duration:</strong> {report.performance_summary['avg_duration']:.3f} seconds</p>
        <p><strong>Median Test Duration:</strong> {report.performance_summary['median_duration']:.3f} seconds</p>
        <p><strong>Slowest Test:</strong> {report.performance_summary['max_duration']:.3f} seconds</p>
        <p><strong>Fastest Test:</strong> {report.performance_summary['min_duration']:.3f} seconds</p>
        <p><strong>Tests Per Second:</strong> {report.performance_summary['tests_per_second']:.1f}</p>
        <p><strong>Slow Tests Count:</strong> {report.performance_summary['slow_tests_count']}</p>
    </div>

    <h2>Slow Tests ({len(report.slow_tests)})</h2>
    <table>
        <tr><th>Test Name</th><th>Duration (s)</th><th>Markers</th></tr>
        {"".join([
            f'<tr class="slow-test"><td>{test.name}</td><td>{test.duration:.3f}</td><td>{", ".join(test.markers)}</td></tr>'
            for test in report.slow_tests[:10]
        ])}
    </table>

    {f'''
    <div class="summary">
        <h2>Trend Analysis</h2>
        <p><strong>Sessions Analyzed:</strong> {report.trend_analysis["sessions_analyzed"]}</p>
        <p><strong>Duration Trend:</strong> {"↗️ Increasing" if report.trend_analysis["duration_trend"] > 0 else "↘️ Decreasing" if report.trend_analysis["duration_trend"] < 0 else "→ Stable"}</p>
        <p><strong>Average Test Time Trend:</strong> {"↗️ Increasing" if report.trend_analysis["avg_duration_trend"] > 0 else "↘️ Decreasing" if report.trend_analysis["avg_duration_trend"] < 0 else "→ Stable"}</p>
        <p><strong>Current Session vs Average:</strong> {report.trend_analysis["current_session_vs_avg"]["duration"]:+.1f}% duration, {report.trend_analysis["current_session_vs_avg"]["avg_test_time"]:+.1f}% avg test time</p>
    </div>
    ''' if report.trend_analysis else ''}

</body>
</html>
        """

        with open(filepath, "w") as f:
            f.write(html_content)

    def _generate_csv_report(self, report: TestSuiteReport, filepath: Path):
        """Generate CSV report of test timings"""
        import csv

        with open(filepath, "w", newline="") as csvfile:
            fieldnames = ["test_name", "duration", "status", "markers", "error_message"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for test in report.test_timings:
                writer.writerow({
                    "test_name": test.name,
                    "duration": test.duration,
                    "status": test.status,
                    "markers": ", ".join(test.markers),
                    "error_message": test.error_message or ""
                })

    def generate_visualizations(self, report: TestSuiteReport) -> Optional[Path]:
        """Generate performance visualizations if matplotlib is available"""
        if not VISUALIZATION_AVAILABLE:
            warnings.warn("Matplotlib not available. Skipping visualizations.")
            return None

        try:
            # Create figure with subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Test Performance Analysis', fontsize=16)

            # Test duration histogram
            durations = [t.duration for t in report.test_timings]
            ax1.hist(durations, bins=20, alpha=0.7, color='skyblue')
            ax1.set_title('Test Duration Distribution')
            ax1.set_xlabel('Duration (seconds)')
            ax1.set_ylabel('Number of Tests')

            # Test status pie chart
            status_counts = {
                'passed': report.passed_tests,
                'failed': report.failed_tests,
                'skipped': report.skipped_tests,
                'error': report.error_tests
            }
            ax2.pie(status_counts.values(), labels=status_counts.keys(), autopct='%1.1f%%')
            ax2.set_title('Test Status Distribution')

            # Slow tests bar chart
            slow_tests = report.slow_tests[:10]  # Top 10 slowest
            if slow_tests:
                test_names = [t.name.split('::')[-1] for t in slow_tests]
                test_durations = [t.duration for t in slow_tests]
                ax3.barh(range(len(test_names)), test_durations, color='lightcoral')
                ax3.set_yticks(range(len(test_names)))
                ax3.set_yticklabels(test_names)
                ax3.set_xlabel('Duration (seconds)')
                ax3.set_title('Top 10 Slowest Tests')

            # Timeline of test execution
            if report.test_timings:
                start_time = min(t.start_time for t in report.test_timings)
                relative_times = [(t.start_time - start_time) for t in report.test_timings]
                colors = ['green' if t.status == 'passed' else 'red' for t in report.test_timings]
                ax4.scatter(relative_times, [t.duration for t in report.test_timings], c=colors, alpha=0.6)
                ax4.set_xlabel('Relative Time (seconds)')
                ax4.set_ylabel('Test Duration (seconds)')
                ax4.set_title('Test Execution Timeline')

            plt.tight_layout()

            # Save the figure
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.report_dir / f"test_visualizations_{timestamp}.png"
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()

            return filepath

        except Exception as e:
            warnings.warn(f"Could not generate visualizations: {e}")
            return None


# Global test reporter instance
test_reporter = TestReporter()


# Convenience functions for pytest integration
def pytest_runtest_setup(item):
    """Pytest hook called before each test"""
    if not test_reporter.session_start:
        test_reporter.start_session()


def pytest_runtest_teardown(item, nextitem):
    """Pytest hook called after each test"""
    # Record test timing will be done in pytest_runtest_logreport
    pass


def pytest_runtest_logreport(report):
    """Pytest hook called with test report"""
    if report.when == "call":
        test_name = f"{report.nodeid}"
        duration = report.duration
        status = report.outcome

        markers = []
        if hasattr(report, "item") and report.item:
            markers = [marker.name for marker in report.item.iter_markers()]

        error_message = None
        if report.failed:
            error_message = str(getattr(report, "longrepr", ""))

        test_reporter.record_test(
            test_name=test_name,
            duration=duration,
            status=status,
            markers=markers,
            error_message=error_message
        )


def pytest_sessionfinish(session, exitstatus):
    """Pytest hook called at end of session"""
    test_reporter.end_session()

    # Generate and save report
    try:
        report = test_reporter.generate_report()
        report_file = test_reporter.save_report(report, format="json")
        html_file = test_reporter.save_report(report, format="html")

        print(f"\n📊 Test report saved to: {report_file}")
        print(f"🌐 HTML report saved to: {html_file}")

        # Generate visualizations
        viz_file = test_reporter.generate_visualizations(report)
        if viz_file:
            print(f"📈 Visualizations saved to: {viz_file}")

    except Exception as e:
        warnings.warn(f"Could not generate test report: {e}")


# Export public API
__all__ = [
    "TestTiming",
    "TestSuiteReport",
    "TestReporter",
    "test_reporter",
]