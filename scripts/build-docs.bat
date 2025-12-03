@echo off
REM FastAPI-Easy Documentation Build Script (Windows)
REM This script builds and validates the documentation locally

setlocal enabledelayedexpansion

echo.
echo 🚀 FastAPI-Easy Documentation Build Script
echo ===========================================
echo.

REM Check if mkdocs is installed
echo 📦 Checking dependencies...
where mkdocs >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ mkdocs is not installed
    echo Install it with: pip install mkdocs mkdocs-material pymdown-extensions
    exit /b 1
)
echo ✅ mkdocs found

REM Check if mkdocs.yml exists
echo.
echo 🔍 Validating documentation structure...
if not exist mkdocs.yml (
    echo ❌ mkdocs.yml not found!
    exit /b 1
)
echo ✅ mkdocs.yml found

REM Check if docs directory exists
if not exist docs (
    echo ❌ docs directory not found!
    exit /b 1
)
echo ✅ docs directory found

REM Check for required documentation files
echo.
echo 📄 Checking required files...
set "required_files=docs\index.md docs\getting-started.md docs\guides\index.md docs\reference\api.md docs\security\index.md"

for %%F in (%required_files%) do (
    if not exist %%F (
        echo ⚠️  Missing: %%F
    ) else (
        echo ✅ Found: %%F
    )
)

REM Build documentation
echo.
echo 🔨 Building documentation...
mkdocs build --strict
if %errorlevel% neq 0 (
    echo ❌ Documentation build failed
    exit /b 1
)
echo ✅ Documentation built successfully

REM Check build output
echo.
echo 📊 Build output statistics:
if exist site (
    echo ✅ site directory created
    
    REM Count files
    setlocal enabledelayedexpansion
    set "total=0"
    set "html=0"
    set "css=0"
    set "js=0"
    
    for /r site %%F in (*) do (
        set /a total+=1
        if "%%~xF"==".html" set /a html+=1
        if "%%~xF"==".css" set /a css+=1
        if "%%~xF"==".js" set /a js+=1
    )
    
    echo 📁 Total files: !total!
    echo 📄 HTML files: !html!
    echo 🎨 CSS files: !css!
    echo 📜 JS files: !js!
) else (
    echo ❌ site directory not found!
    exit /b 1
)

REM Serve documentation locally
echo.
echo 🌐 Starting local server...
echo ✅ Documentation is ready!
echo.
echo 📍 Local URL: http://localhost:8000
echo Press Ctrl+C to stop the server
echo.

mkdocs serve
