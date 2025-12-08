#!/usr/bin/env python3
"""
Dependency security checker for FastAPI-Easy
Checks for known vulnerabilities in project dependencies
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp
import packaging.version

logger = logging.getLogger(__name__)


class DependencyChecker:
    """Checks project dependencies for security vulnerabilities"""

    def __init__(self):
        self.osv_api_url = "https://api.osv.dev/v1/query"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def check_vulnerability(self, package_name: str, version: str) -> List[Dict]:
        """Check a specific package version for vulnerabilities"""
        if not self.session:
            raise RuntimeError("DependencyChecker must be used as async context manager")

        payload = {
            "package": {
                "name": package_name,
                "ecosystem": "PyPI"
            },
            "version": version
        }

        try:
            async with self.session.post(
                self.osv_api_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("vulns", [])
                else:
                    logger.error(f"Error checking {package_name}: HTTP {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error checking {package_name}: {str(e)}")
            return []

    def parse_requirements(self, requirements_file: Path) -> List[Tuple[str, str]]:
        """Parse requirements.txt file"""
        dependencies = []

        if not requirements_file.exists():
            logger.warning(f"Requirements file not found: {requirements_file}")
            return dependencies

        with open(requirements_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse package and version
                if '>=' in line:
                    package, version = line.split('>=', 1)
                    version = version.split(',')[0].strip()  # Take minimum version
                elif '==' in line:
                    package, version = line.split('==', 1)
                else:
                    # Package without version constraint
                    package = line
                    version = "0.0.0"  # Placeholder, will fetch latest

                dependencies.append((package.strip(), version.strip()))

        return dependencies

    async def check_dependencies(self, requirements_file: Path) -> Dict:
        """Check all dependencies in requirements file"""
        results = {
            "total_packages": 0,
            "vulnerable_packages": 0,
            "vulnerabilities": {},
            "safe_packages": []
        }

        dependencies = self.parse_requirements(requirements_file)
        results["total_packages"] = len(dependencies)

        logger.info(f"Checking {len(dependencies)} dependencies...")

        for package, version in dependencies:
            logger.info(f"Checking {package}=={version}")
            vulnerabilities = await self.check_vulnerability(package, version)

            if vulnerabilities:
                results["vulnerable_packages"] += 1
                results["vulnerabilities"][package] = {
                    "version": version,
                    "vulnerabilities": vulnerabilities
                }
                logger.warning(f"Found {len(vulnerabilities)} vulnerabilities in {package}")
            else:
                results["safe_packages"].append(package)
                logger.info(f"No vulnerabilities found in {package}")

        return results


async def main():
    """Main check function"""
    import argparse

    parser = argparse.ArgumentParser(description="Check dependencies for security vulnerabilities")
    parser.add_argument(
        "--requirements",
        "-r",
        default="requirements.txt",
        help="Path to requirements file (default: requirements.txt)"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output JSON file for results"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    requirements_path = Path(args.requirements)

    if not requirements_path.exists():
        logger.error(f"Requirements file not found: {requirements_path}")
        sys.exit(1)

    # Run vulnerability check
    async with DependencyChecker() as checker:
        results = await checker.check_dependencies(requirements_path)

    # Print summary
    print("\n" + "="*60)
    print("DEPENDENCY SECURITY CHECK SUMMARY")
    print("="*60)
    print(f"Total packages checked: {results['total_packages']}")
    print(f"Vulnerable packages: {results['vulnerable_packages']}")
    print(f"Safe packages: {len(results['safe_packages'])}")

    if results['vulnerabilities']:
        print("\nVULNERABILITIES FOUND:")
        print("-"*40)
        for package, info in results['vulnerabilities'].items():
            print(f"\n{package}=={info['version']}:")
            for vuln in info['vulnerabilities']:
                print(f"  - {vuln.get('id', 'Unknown ID')}")
                print(f"    Summary: {vuln.get('summary', 'No summary')}")
                if vuln.get('severity'):
                    print(f"    Severity: {vuln['severity']}")
    else:
        print("\n✅ No vulnerabilities found!")

    # Save results to file if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_path}")

    # Exit with error code if vulnerabilities found
    if results['vulnerable_packages'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())