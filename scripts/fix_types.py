#!/usr/bin/env python3
"""
Automated Type Fixing Script for FastAPI-Easy

This script helps fix common type annotation issues throughout the codebase.
It can be used as a reference for manual fixes or as a template for automation.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Common patterns to fix
TYPE_FIXES = {
    # Function definitions missing return types
    r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*:":
        lambda m: f"def {m.group(1)}() -> None:",

    # Async functions missing return types
    r"async def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*:":
        lambda m: f"async def {m.group(1)}() -> None:",

    # Method definitions missing return types
    r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*self[^)]*\)\s*:":
        lambda m: f"def {m.group(1)}(self) -> None:",

    # Async method definitions missing return types
    r"async def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*self[^)]*\)\s*:":
        lambda m: f"async def {m.group(1)}(self) -> None:",

    # Generic dict without type parameters
    r": Dict\[?\]?": " -> Dict[str, Any]",

    # Generic list without type parameters
    r": List\[?\]?": " -> List[Any]",

    # Callable without type parameters
    r": Callable\[?\]?": " -> Callable[..., Any]",

    # Untyped variables with None assignment
    r"(\w+):\s*None\s*=": r"\1: Optional[Any] = None",
}

# Common imports to add
COMMON_IMPORTS = {
    "Any": "typing.Any",
    "Dict": "typing.Dict",
    "List": "typing.List",
    "Optional": "typing.Optional",
    "Callable": "typing.Callable",
    "Awaitable": "typing.Awaitable",
    "Union": "typing.Union",
    "Type": "typing.Type",
    "TypeVar": "typing.TypeVar",
}

def find_functions_missing_types(file_path: Path) -> List[Tuple[int, str, str]]:
    """Find functions/methods missing type annotations."""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    issues = []

    for i, line in enumerate(lines, 1):
        line = line.strip()

        # Skip comments and empty lines
        if line.startswith('#') or not line:
            continue

        # Check for function definitions without return types
        if re.match(r'^(async )?def\s+\w+\([^)]*\)\s*:\s*$', line):
            issues.append((i, line, "Missing return type annotation"))

    return issues

def suggest_fixes_for_function(line: str) -> str:
    """Suggest fixes for a function definition."""

    # Check if it's async
    is_async = line.strip().startswith('async ')

    # Extract function name and parameters
    func_match = re.match(r'(?:async )?def\s+(\w+)\s*\(([^)]*)\)', line)
    if not func_match:
        return line

    func_name = func_match.group(1)
    params = func_match.group(2)

    # Determine return type based on function name patterns
    return_type = "None"

    if any(word in func_name.lower() for word in ['get', 'find', 'fetch']):
        return_type = "Optional[Any]"
    elif any(word in func_name.lower() for word in ['list', 'all', 'get_all', 'find_all']):
        return_type = "List[Any]"
    elif any(word in func_name.lower() for word in ['create', 'add', 'insert']):
        return_type = "Any"
    elif any(word in func_name.lower() for word in ['update', 'edit', 'modify']):
        return_type = "Any"
    elif any(word in func_name.lower() for word in ['delete', 'remove']):
        return_type = "bool"
    elif func_name.startswith('_'):
        return_type = "None"  # Private methods often don't return

    # Reconstruct function signature
    async_prefix = "async " if is_async else ""
    return f"{async_prefix}def {func_name}({params}) -> {return_type}:"

def generate_import_suggestions(file_path: Path) -> List[str]:
    """Generate import suggestions based on usage."""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    needed_imports = set()

    # Find type annotations in the file
    for type_name, import_path in COMMON_IMPORTS.items():
        if type_name in content and f"from {import_path}" not in content:
            needed_imports.add(import_path)

    return sorted(needed_imports)

def create_type_report(directory: Path) -> Dict[str, List[Tuple[int, str, str]]]:
    """Create a report of type issues in the directory."""

    report = {}

    for py_file in directory.rglob('*.py'):
        # Skip __pycache__ and test files
        if '__pycache__' in str(py_file) or py_file.name.startswith('test_'):
            continue

        issues = find_functions_missing_types(py_file)
        if issues:
            report[str(py_file)] = issues

    return report

if __name__ == "__main__":
    import sys

    # Create report for src directory
    src_dir = Path("src")
    if not src_dir.exists():
        print("src directory not found")
        sys.exit(1)

    report = create_type_report(src_dir)

    # Print summary
    total_issues = sum(len(issues) for issues in report.values())
    print(f"Found {total_issues} type issues across {len(report)} files")

    # Print details for each file
    for file_path, issues in report.items():
        print(f"\n{file_path}:")
        for line_num, line, issue in issues:
            print(f"  Line {line_num}: {issue}")
            print(f"    {line}")
            suggestion = suggest_fixes_for_function(line)
            if suggestion != line:
                print(f"    Suggestion: {suggestion}")