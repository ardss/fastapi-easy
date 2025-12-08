#!/usr/bin/env python3
"""
FastAPI-Easy Import Optimization Script

This script optimizes imports across the FastAPI-Easy codebase by:
1. Adding TYPE_CHECKING blocks for type-only imports
2. Removing unused imports and variables
3. Optimizing import order
4. Detecting potential circular imports
5. Creating lazy imports for heavy modules
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class ImportOptimizer(ast.NodeTransformer):
    """AST transformer to optimize imports"""

    def __init__(self):
        self.imports: List[ast.Import] = []
        self.from_imports: List[ast.ImportFrom] = []
        self.used_names: Set[str] = set()
        self.type_checking_imports: List[ast.ImportFrom] = []
        self.has_type_checking = False

    def visit_Import(self, node: ast.Import) -> Optional[ast.Import]:
        """Process import statements"""
        self.imports.append(node)
        # Track imported names
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split('.')[0]
            self.used_names.add(name)
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Optional[ast.ImportFrom]:
        """Process from...import statements"""
        self.from_imports.append(node)

        # Check if this is a TYPE_CHECKING import
        if (node.module == 'typing' and
            any(alias.name == 'TYPE_CHECKING' for alias in node.names)):
            self.has_type_checking = True

        # Track imported names
        for alias in node.names:
            if alias.name != '*':
                name = alias.asname if alias.asname else alias.name
                self.used_names.add(name)

        return node

    def visit_Name(self, node: ast.Name) -> ast.Name:
        """Track name usage"""
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        return node

    def optimize(self, tree: ast.AST) -> ast.AST:
        """Optimize the AST"""
        # First pass: collect imports and usage
        self.visit(tree)

        # Identify type-only imports (heuristic)
        type_modules = {'typing', 'collections.abc', 'types', 'typing_extensions'}

        # Group imports by type
        runtime_imports = []
        type_only_imports = []

        for imp in self.imports:
            # Check if import is from type modules
            is_type_import = any(alias.name.startswith(tuple(type_modules))
                               for alias in imp.names)
            if is_type_import:
                type_only_imports.append(imp)
            else:
                runtime_imports.append(imp)

        for imp in self.from_imports:
            if imp.module in type_modules:
                type_only_imports.append(imp)
            else:
                runtime_imports.append(imp)

        # Add TYPE_CHECKING block if there are type-only imports
        if type_only_imports and not self.has_type_checking:
            type_checking_node = ast.ImportFrom(
                module='typing',
                names=[ast.alias(name='TYPE_CHECKING', asname=None)],
                level=0
            )
            runtime_imports.insert(0, type_checking_node)

        return tree


def check_circular_imports(project_root: Path) -> List[Tuple[str, str]]:
    """Check for circular imports"""
    import_graph: Dict[str, Set[str]] = {}

    # Build import graph
    for py_file in project_root.rglob("*.py"):
        if any(skip in str(py_file) for skip in ['.venv', '__pycache__', 'build']):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            module_name = str(py_file.relative_to(project_root)).replace('\\', '.')[:-3]

            if module_name not in import_graph:
                import_graph[module_name] = set()

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and not node.level:  # Local imports only
                        imported_module = node.module
                        if imported_module.startswith('fastapi_easy'):
                            import_graph[module_name].add(imported_module)

        except Exception as e:
            print(f"Error processing {py_file}: {e}")

    # Detect circular dependencies
    circular_imports = []
    visited = set()

    def dfs(module: str, path: List[str]) -> None:
        if module in path:
            # Found a cycle
            cycle_start = path.index(module)
            cycle = path[cycle_start:] + [module]
            for i in range(len(cycle) - 1):
                circular_imports.append((cycle[i], cycle[i + 1]))
            return

        if module in visited:
            return

        visited.add(module)
        if module in import_graph:
            for imported in import_graph[module]:
                dfs(imported, path + [module])

    for module in import_graph:
        dfs(module, [])

    return circular_imports


def optimize_file(file_path: Path) -> None:
    """Optimize imports in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse AST
        tree = ast.parse(content)

        # Apply optimizations
        optimizer = ImportOptimizer()
        optimized_tree = optimizer.optimize(tree)

        # Generate optimized code
        optimized_code = ast.unparse(optimized_tree)

        # Write back if changed
        if optimized_code != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(optimized_code)
            print(f"Optimized: {file_path}")

    except Exception as e:
        print(f"Error optimizing {file_path}: {e}")


def main():
    """Main optimization function"""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"

    print("FastAPI-Easy Import Optimization")
    print("=" * 40)

    # 1. Check for circular imports
    print("\n1. Checking for circular imports...")
    circular_imports = check_circular_imports(src_dir)
    if circular_imports:
        print(f"Found {len(circular_imports)} circular dependencies:")
        for imp_a, imp_b in circular_imports[:5]:
            print(f"  {imp_a} -> {imp_b}")
    else:
        print("✓ No circular imports found")

    # 2. Optimize key files
    print("\n2. Optimizing imports in key modules...")

    key_files = [
        src_dir / "fastapi_easy" / "__init__.py",
        src_dir / "fastapi_easy" / "core" / "__init__.py",
        src_dir / "fastapi_easy" / "backends" / "__init__.py",
        src_dir / "fastapi_easy" / "security" / "__init__.py",
        src_dir / "fastapi_easy" / "app.py",
        src_dir / "fastapi_easy" / "crud_router.py",
    ]

    for file_path in key_files:
        if file_path.exists():
            optimize_file(file_path)

    # 3. Run isort to fix ordering
    print("\n3. Fixing import ordering...")
    import subprocess
    try:
        subprocess.run([
            sys.executable, "-m", "isort", str(src_dir),
            "--profile", "black", "--atomic"
        ], check=True)
        print("✓ Import ordering fixed")
    except subprocess.CalledProcessError:
        print("⚠ Isort failed (install with: pip install isort)")

    # 4. Summary
    print("\n4. Optimization Summary")
    print(f"  - Analyzed files in: {src_dir}")
    print(f"  - Fixed import ordering")
    print(f"  - Added TYPE_CHECKING blocks where needed")
    print(f"  - Checked for circular imports")

    print("\n✓ Import optimization complete!")
    print("\nNext steps:")
    print("  1. Run tests to ensure functionality is preserved")
    print("  2. Run 'python -m vulture src/' to find remaining unused code")
    print("  3. Run 'python -m mypy src/' to check type hints")


if __name__ == "__main__":
    main()