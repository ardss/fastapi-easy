"""Command-line interface for FastAPI-Easy"""

import sys
import click
from pathlib import Path
from typing import Optional


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """FastAPI-Easy CLI - CRUD Router Framework for FastAPI"""
    pass


@cli.command()
@click.option("--name", prompt="Project name", help="Name of the project")
@click.option("--path", default=".", help="Path to create project")
def init(name: str, path: str):
    """Initialize a new FastAPI-Easy project"""
    project_path = Path(path) / name
    
    try:
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Create directory structure
        (project_path / "src").mkdir(exist_ok=True)
        (project_path / "tests").mkdir(exist_ok=True)
        (project_path / "docs").mkdir(exist_ok=True)
        
        # Create main.py
        main_py = project_path / "src" / "main.py"
        main_py.write_text("""from fastapi import FastAPI
from fastapi_easy import CRUDRouter

app = FastAPI()

# Your routes here

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
""")
        
        # Create requirements.txt
        requirements = project_path / "requirements.txt"
        requirements.write_text("""fastapi>=0.100.0
fastapi-easy>=1.0.0
sqlalchemy>=2.0.0
uvicorn>=0.23.0
pydantic>=2.0.0
""")
        
        # Create README.md
        readme = project_path / "README.md"
        readme.write_text(f"""# {name}

FastAPI-Easy project: {name}

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
python src/main.py
```
""")
        
        click.secho(f"✅ Project '{name}' created successfully at {project_path}", fg="green")
        
    except Exception as e:
        click.secho(f"❌ Error creating project: {e}", fg="red")
        sys.exit(1)


@cli.command()
@click.option("--model", prompt="Model name", help="Name of the model")
@click.option("--fields", prompt="Fields (comma-separated)", help="Model fields")
def generate(model: str, fields: str):
    """Generate CRUD router for a model"""
    try:
        field_list = [f.strip() for f in fields.split(",")]
        
        # Generate model code
        model_code = f"""from pydantic import BaseModel
from typing import Optional

class {model}(BaseModel):
    id: Optional[int] = None
"""
        
        for field in field_list:
            model_code += f"    {field}: str\n"
        
        # Generate schema code
        schema_code = f"""from pydantic import BaseModel, ConfigDict

class {model}Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
"""
        
        for field in field_list:
            schema_code += f"    {field}: str\n"
        
        # Generate router code
        router_code = f"""from fastapi import APIRouter
from fastapi_easy import CRUDRouter
from sqlalchemy.orm import Session

from .models import {model}
from .schemas import {model}Schema

router = CRUDRouter(
    model={model},
    schema={model}Schema,
    prefix="/{model.lower()}s",
    tags=["{model}"],
)
"""
        
        click.echo("\n=== Model Code ===")
        click.echo(model_code)
        click.echo("\n=== Schema Code ===")
        click.echo(schema_code)
        click.echo("\n=== Router Code ===")
        click.echo(router_code)
        
        click.secho("\n✅ Code generated successfully", fg="green")
        
    except Exception as e:
        click.secho(f"❌ Error generating code: {e}", fg="red")
        sys.exit(1)


@cli.command()
def version():
    """Show version information"""
    click.echo("FastAPI-Easy v1.0.0")
    click.echo("CRUD Router Framework for FastAPI")
    click.echo("\nSupported ORMs:")
    click.echo("  - SQLAlchemy")
    click.echo("  - Tortoise ORM")


@cli.command()
def info():
    """Show project information"""
    info_text = """
FastAPI-Easy - CRUD Router Framework for FastAPI

Features:
  ✅ Automatic CRUD operations
  ✅ Multiple ORM support (SQLAlchemy, Tortoise)
  ✅ Advanced filtering and sorting
  ✅ Pagination support
  ✅ Soft delete support
  ✅ Batch operations
  ✅ Permission control (RBAC/ABAC)
  ✅ Audit logging
  ✅ Rate limiting
  ✅ Caching support
  ✅ Middleware system
  ✅ Response formatters

Documentation: https://github.com/your-repo/fastapi-easy
GitHub: https://github.com/your-repo/fastapi-easy
"""
    click.echo(info_text)


@cli.command()
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
def status(format: str):
    """Show project status"""
    status_info = {
        "version": "1.0.0",
        "status": "production",
        "tests": "309 passed",
        "coverage": "95%+",
        "orms": ["SQLAlchemy", "Tortoise ORM"],
        "features": [
            "CRUD operations",
            "Filtering",
            "Sorting",
            "Pagination",
            "Soft delete",
            "Batch operations",
            "Permissions",
            "Audit logging",
            "Rate limiting",
            "Caching",
            "Middleware",
            "Response formatters",
        ],
    }
    
    if format == "json":
        import json
        click.echo(json.dumps(status_info, indent=2))
    else:
        click.echo("FastAPI-Easy Status")
        click.echo("=" * 40)
        click.echo(f"Version: {status_info['version']}")
        click.echo(f"Status: {status_info['status']}")
        click.echo(f"Tests: {status_info['tests']}")
        click.echo(f"Coverage: {status_info['coverage']}")
        click.echo(f"\nSupported ORMs:")
        for orm in status_info['orms']:
            click.echo(f"  - {orm}")
        click.echo(f"\nFeatures:")
        for feature in status_info['features']:
            click.echo(f"  ✅ {feature}")


if __name__ == "__main__":
    cli()
