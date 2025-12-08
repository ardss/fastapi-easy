"""Dependency security checker for FastAPI-Easy"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from packaging import version

logger = logging.getLogger(__name__)


class Vulnerability:
    """Represents a security vulnerability"""

    def __init__(
        self,
        package_name: str,
        installed_version: str,
        advisory_id: str,
        severity: str,
        summary: str,
        affected_versions: Optional[List[str]] = None,
        fixed_versions: Optional[List[str]] = None,
        references: Optional[List[str]] = None,
    ):
        """Initialize vulnerability

        Args:
            package_name: Name of the vulnerable package
            installed_version: Currently installed version
            advisory_id: Advisory ID (e.g., CVE, GHSA)
            severity: Severity level (critical, high, medium, low)
            summary: Vulnerability summary
            affected_versions: List of affected version ranges
            fixed_versions: List of fixed versions
            references: Reference links
        """
        self.package_name = package_name
        self.installed_version = installed_version
        self.advisory_id = advisory_id
        self.severity = severity.lower()
        self.summary = summary
        self.affected_versions = affected_versions or []
        self.fixed_versions = fixed_versions or []
        self.references = references or []

    def to_dict(self) -> Dict:
        """Convert vulnerability to dictionary"""
        return {
            "package": self.package_name,
            "installed_version": self.installed_version,
            "advisory_id": self.advisory_id,
            "severity": self.severity,
            "summary": self.summary,
            "affected_versions": self.affected_versions,
            "fixed_versions": self.fixed_versions,
            "references": self.references,
        }


class DependencyChecker:
    """Security dependency checker with vulnerability scanning"""

    # Known vulnerable packages and their safe versions
    SECURITY_ADVISORIES = {
        # Flask
        "flask": {
            "2.0.0": {"severity": "critical", "fixed": "2.0.1", "cve": "CVE-2021-23385"},
            "1.0.0": {"severity": "high", "fixed": "1.0.1", "cve": "CVE-2019-1010083"},
        },
        # Jinja2
        "jinja2": {
            "2.11.2": {"severity": "critical", "fixed": "2.11.3", "cve": "CVE-2020-28493"},
        },
        # urllib3
        "urllib3": {
            "1.25.9": {"severity": "high", "fixed": "1.26.5", "cve": "CVE-2021-28363"},
        },
        # requests
        "requests": {
            "2.25.0": {"severity": "high", "fixed": "2.25.1", "cve": "CVE-2021-33503"},
        },
        # PyYAML
        "pyyaml": {
            "5.4.0": {"severity": "critical", "fixed": "5.4.1", "cve": "CVE-2021-3574"},
        },
        # Pickle (built-in, but used by many packages)
        "pickle": {
            "all": {"severity": "high", "advisory": "Never unpickle untrusted data"},
        },
        # Django
        "django": {
            "3.2.0": {"severity": "high", "fixed": "3.2.13", "cve": "CVE-2022-28347"},
            "4.0.0": {"severity": "critical", "fixed": "4.0.8", "cve": "CVE-2022-34265"},
        },
    }

    # Insecure packages that should never be used
    BLACKLISTED_PACKAGES = {
        "pickle": "Use secure alternatives like json",
        "eval": "Use ast.literal_eval instead",
        "exec": "Use proper templating or configuration files",
        "subprocess.call": "Use subprocess.run with proper validation",
        "input": "Python 2's input() is unsafe in Python 3",
    }

    # Required security packages
    REQUIRED_SECURITY_PACKAGES = {
        "cryptography": ">=3.0.0",
        "bcrypt": ">=3.2.0",
        "argon2-cffi": ">=21.0.0",
        "pyjwt": ">=2.4.0",
        "python-multipart": ">=0.0.5",
    }

    def __init__(self, requirements_path: Optional[str] = None):
        """Initialize dependency checker

        Args:
            requirements_path: Path to requirements.txt file
        """
        self.requirements_path = requirements_path or "requirements.txt"
        self.installed_packages = self._get_installed_packages()
        self.vulnerabilities = []

    def _get_installed_packages(self) -> Dict[str, str]:
        """Get list of installed packages with versions

        Returns:
            Dictionary of package_name -> version
        """
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                check=True,
            )
            packages = json.loads(result.stdout)
            return {pkg["name"].lower(): pkg["version"] for pkg in packages}
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get installed packages: {e}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse pip list output: {e}")
            return {}

    def check_vulnerabilities(self) -> List[Vulnerability]:
        """Check for known vulnerabilities in installed packages

        Returns:
            List of vulnerabilities found
        """
        vulnerabilities = []

        for package_name, installed_version in self.installed_packages.items():
            # Check security advisories
            if package_name in self.SECURITY_ADVISORIES:
                advisories = self.SECURITY_ADVISORIES[package_name]

                for advisory_version, advisory in advisories.items():
                    if advisory_version == "all" or self._is_version_affected(
                        installed_version, advisory_version
                    ):
                        vulnerability = Vulnerability(
                            package_name=package_name,
                            installed_version=installed_version,
                            advisory_id=advisory.get("cve", "ADVISORY"),
                            severity=advisory["severity"],
                            summary=f"Security vulnerability in {package_name}",
                            fixed_versions=[advisory.get("fixed")],
                        )
                        vulnerabilities.append(vulnerability)

        self.vulnerabilities = vulnerabilities
        return vulnerabilities

    def check_required_packages(self) -> Dict[str, Tuple[str, str]]:
        """Check if required security packages are installed

        Returns:
            Dictionary of package -> (installed_version, required_version)
        """
        missing_or_outdated = {}

        for package, required_version in self.REQUIRED_SECURITY_PACKAGES.items():
            installed = self.installed_packages.get(package)

            if not installed:
                missing_or_outdated[package] = ("not installed", required_version)
            elif not self._meets_version_requirement(installed, required_version):
                missing_or_outdated[package] = (installed, required_version)

        return missing_or_outdated

    def check_insecure_dependencies(self) -> List[str]:
        """Check for known insecure dependencies

        Returns:
            List of insecure package names
        """
        insecure = []

        for package_name in self.installed_packages:
            # Check if package is blacklisted
            if package_name in self.BLACKLISTED_PACKAGES:
                insecure.append(package_name)

            # Check for packages with known security issues in their names
            insecure_keywords = ["test", "debug", "dev", "demo"]
            for keyword in insecure_keywords:
                if keyword in package_name and "fastapi-easy" not in package_name:
                    insecure.append(f"{package_name} (contains '{keyword}')")

        return insecure

    def check_requirements_file(self) -> Tuple[List[str], List[str]]:
        """Check requirements.txt for security issues

        Returns:
            Tuple of (warnings, errors)
        """
        warnings = []
        errors = []

        requirements_path = Path(self.requirements_path)
        if not requirements_path.exists():
            errors.append(f"Requirements file not found: {self.requirements_path}")
            return warnings, errors

        with open(requirements_path) as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Check for unpinned versions
            if "==" not in line and ">=" not in line and "<=" not in line:
                warnings.append(
                    f"Line {line_num}: Unpinned version '{line}' - consider pinning for security"
                )

            # Check for insecure packages
            package_name = line.split("==")[0].split(">=")[0].split("<=")[0].strip().lower()
            if package_name in self.BLACKLISTED_PACKAGES:
                errors.append(
                    f"Line {line_num}: Blacklisted package '{package_name}' - {self.BLACKLISTED_PACKAGES[package_name]}"
                )

        return warnings, errors

    def generate_report(self) -> Dict:
        """Generate comprehensive security report

        Returns:
            Security report dictionary
        """
        vulnerabilities = self.check_vulnerabilities()
        missing_packages = self.check_required_packages()
        insecure_deps = self.check_insecure_dependencies()
        requirements_warnings, requirements_errors = self.check_requirements_file()

        # Calculate severity counts
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for vuln in vulnerabilities:
            severity_counts[vuln.severity] = severity_counts.get(vuln.severity, 0) + 1

        # Calculate security score (0-100)
        security_score = 100
        security_score -= severity_counts["critical"] * 25
        security_score -= severity_counts["high"] * 15
        security_score -= severity_counts["medium"] * 10
        security_score -= severity_counts["low"] * 5
        security_score -= len(missing_packages) * 20
        security_score -= len(insecure_deps) * 30
        security_score -= len(requirements_errors) * 20
        security_score = max(0, security_score)

        return {
            "security_score": security_score,
            "summary": {
                "total_vulnerabilities": len(vulnerabilities),
                "critical": severity_counts["critical"],
                "high": severity_counts["high"],
                "medium": severity_counts["medium"],
                "low": severity_counts["low"],
                "missing_security_packages": len(missing_packages),
                "insecure_dependencies": len(insecure_deps),
                "requirements_warnings": len(requirements_warnings),
                "requirements_errors": len(requirements_errors),
            },
            "vulnerabilities": [v.to_dict() for v in vulnerabilities],
            "missing_security_packages": {
                pkg: {"installed": ver[0], "required": ver[1]}
                for pkg, ver in missing_packages.items()
            },
            "insecure_dependencies": insecure_deps,
            "requirements_file": {
                "warnings": requirements_warnings,
                "errors": requirements_errors,
            },
            "recommendations": self._generate_recommendations(
                vulnerabilities, missing_packages, insecure_deps
            ),
        }

    def _generate_recommendations(
        self,
        vulnerabilities: List[Vulnerability],
        missing_packages: Dict[str, Tuple[str, str]],
        insecure_deps: List[str],
    ) -> List[str]:
        """Generate security recommendations

        Args:
            vulnerabilities: List of vulnerabilities
            missing_packages: Missing security packages
            insecure_deps: Insecure dependencies

        Returns:
            List of recommendations
        """
        recommendations = []

        # Critical vulnerabilities
        critical_vulns = [v for v in vulnerabilities if v.severity == "critical"]
        if critical_vulns:
            recommendations.append("URGENT: Update critical vulnerable packages immediately")
            for vuln in critical_vulns[:3]:  # Show first 3
                if vuln.fixed_versions:
                    recommendations.append(
                        f"  - Update {vuln.package_name} to {vuln.fixed_versions[0]} or later"
                    )

        # High vulnerabilities
        high_vulns = [v for v in vulnerabilities if v.severity == "high"]
        if high_vulns:
            recommendations.append(
                "HIGH: Update high-severity vulnerable packages as soon as possible"
            )

        # Missing security packages
        if missing_packages:
            recommendations.append("Install missing security packages:")
            for pkg, (installed, required) in missing_packages.items():
                recommendations.append(f"  - pip install '{pkg}>={required}'")

        # Insecure dependencies
        if insecure_deps:
            recommendations.append("Remove or replace insecure dependencies:")
            for dep in insecure_deps[:5]:  # Show first 5
                recommendations.append(f"  - {dep}")

        # General recommendations
        if vulnerabilities or missing_packages or insecure_deps:
            recommendations.extend(
                [
                    "Run 'pip audit' for comprehensive vulnerability scanning",
                    "Set up automated dependency scanning in CI/CD pipeline",
                    "Subscribe to security advisories for your dependencies",
                    "Use virtual environments to isolate dependencies",
                ]
            )

        return recommendations

    def _is_version_affected(self, installed: str, advisory_version: str) -> bool:
        """Check if installed version is affected by advisory

        Args:
            installed: Installed version
            advisory_version: Advisory version

        Returns:
            True if affected
        """
        try:
            installed_ver = version.parse(installed)
            advisory_ver = version.parse(advisory_version)
            return installed_ver <= advisory_ver
        except version.InvalidVersion:
            logger.warning(f"Invalid version comparison: {installed} vs {advisory_version}")
            return False

    def _meets_version_requirement(self, installed: str, required: str) -> bool:
        """Check if installed version meets requirement

        Args:
            installed: Installed version
            required: Required version (e.g., ">=3.0.0")

        Returns:
            True if requirement is met
        """
        try:
            # Simple version comparison for requirements like ">=3.0.0"
            if required.startswith(">="):
                min_version = required[2:]
                return version.parse(installed) >= version.parse(min_version)
            return True
        except version.InvalidVersion:
            return False

    def auto_update_safe_packages(self, dry_run: bool = True) -> List[str]:
        """Automatically update safe packages

        Args:
            dry_run: If True, only show what would be updated

        Returns:
            List of update commands
        """
        updates = []

        # Get outdated packages
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                check=True,
            )
            outdated = json.loads(result.stdout)

            for pkg in outdated:
                package_name = pkg["name"].lower()
                current_version = pkg["version"]
                latest_version = pkg["latest_version"]
                pkg_type = pkg.get("type", "package")

                # Skip if it's a system package or has known vulnerabilities
                if pkg_type != "package" or self._has_known_vulnerabilities(package_name):
                    continue

                # Create update command
                update_cmd = f"pip install --upgrade {package_name}=={latest_version}"
                updates.append(
                    {
                        "package": package_name,
                        "current": current_version,
                        "latest": latest_version,
                        "command": update_cmd,
                    }
                )

                if not dry_run:
                    try:
                        subprocess.run(update_cmd.split(), capture_output=True, check=True)
                        logger.info(f"Updated {package_name} to {latest_version}")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Failed to update {package_name}: {e}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get outdated packages: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse pip list output: {e}")

        return updates

    def _has_known_vulnerabilities(self, package_name: str) -> bool:
        """Check if package has known vulnerabilities

        Args:
            package_name: Package name

        Returns:
            True if vulnerabilities exist
        """
        return any(vuln.package_name == package_name for vuln in self.vulnerabilities)


def check_all() -> Dict:
    """Run all security checks

    Returns:
        Security report
    """
    checker = DependencyChecker()
    return checker.generate_report()


def check_requirements_file(path: str = "requirements.txt") -> Tuple[List[str], List[str]]:
    """Check requirements file for security issues

    Args:
        path: Path to requirements file

    Returns:
        Tuple of (warnings, errors)
    """
    checker = DependencyChecker(requirements_path=path)
    return checker.check_requirements_file()


def scan_vulnerabilities() -> List[Dict]:
    """Scan for vulnerabilities in installed packages

    Returns:
        List of vulnerability dictionaries
    """
    checker = DependencyChecker()
    vulnerabilities = checker.check_vulnerabilities()
    return [v.to_dict() for v in vulnerabilities]
