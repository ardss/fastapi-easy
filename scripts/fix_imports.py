#!/usr/bin/env python3
"""Simple import fixer for FastAPI-Easy"""

import ast
import sys
from pathlib import Path
from typing import List, Set


def add_type_checking_to_file(file_path: Path) -> bool:
    """Add TYPE_CHECKING block to a file if needed"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse the file
        tree = ast.parse(content)

        # Check if TYPE_CHECKING already exists
        has_type_checking = False
        type_imports = []
        runtime_imports = []

        # Separate imports
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == 'typing' and any(
                    alias.name == 'TYPE_CHECKING' for alias in node.names
                ):
                    has_type_checking = True
                elif node.module and node.module.startswith('typing'):
                    type_imports.append(node)
                else:
                    runtime_imports.append(node)

        # If we have type imports but no TYPE_CHECKING, add it
        if type_imports and not has_type_checking:
            # Create TYPE_CHECKING import
            type_checking_import = ast.ImportFrom(
                module='typing',
                names=[ast.alias(name='TYPE_CHECKING', asname=None)],
                level=0
            )

            # Reconstruct the AST with proper import organization
            new_tree = ast.Module(body=[], type_ignores=[])

            # Add standard library imports first
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if node not in type_imports:
                        new_tree.body.append(node)
                else:
                    break

            # Add TYPE_CHECKING block
            if type_imports:
                # Create if TYPE_CHECKING: block
                type_checking_body = type_imports
                if_stmt = ast.If(
                    test=ast.Name(id='TYPE_CHECKING', ctx=ast.Load()),
                    body=type_checking_body,
                    orelse=[]
                )
                new_tree.body.append(if_stmt)

            # Add the rest of the code
            added_imports = False
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if not added_imports:
                        added_imports = True
                else:
                    new_tree.body.append(node)

            # Generate the new code
            import astor  # Need to install this
            new_content = astor.to_source(new_tree)

            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f"Added TYPE_CHECKING to {file_path}")
            return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return False


def remove_unused_imports(file_path: Path) -> bool:
    """Remove obviously unused imports"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Simple heuristics for unused imports
        unused_imports = [
            'from typing import Text',  # Python 3+
            'from typing import AsyncIterator',
            'from typing import Coroutine',
            'from typing import Iterator',
            'from typing import Sequence',
            'from typing import Mapping',
            'from cryptography.hazmat.primitives.cmac import CMAC',
            'from cryptography.hazmat.primitives.ciphers.aead import AESGCM',
        ]

        modified = False
        new_lines = []

        for line in lines:
            skip_line = False
            for unused in unused_imports:
                if unused in line:
                    skip_line = True
                    modified = True
                    break
            if not skip_line:
                new_lines.append(line)

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"Removed unused imports from {file_path}")
            return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return False


def main():
    """Main function"""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"

    print("Fixing imports in FastAPI-Easy...")

    # Files to optimize
    key_files = list(src_dir.rglob("*.py"))
    key_files = [f for f in key_files if 'test' not in f.name and f.name != '__init__.py']

    modified_count = 0

    for file_path in key_files[:20]:  # Limit to first 20 files
        if remove_unused_imports(file_path):
            modified_count += 1

    print(f"\nModified {modified_count} files")
    print("\nImport fixing complete!")


if __name__ == "__main__":
    main()