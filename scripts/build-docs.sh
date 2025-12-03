#!/bin/bash

# FastAPI-Easy Documentation Build Script
# This script builds and validates the documentation locally

set -e

echo "🚀 FastAPI-Easy Documentation Build Script"
echo "==========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if mkdocs is installed
echo -e "${BLUE}📦 Checking dependencies...${NC}"
if ! command -v mkdocs &> /dev/null; then
    echo -e "${RED}❌ mkdocs is not installed${NC}"
    echo "Install it with: pip install mkdocs mkdocs-material pymdown-extensions"
    exit 1
fi
echo -e "${GREEN}✅ mkdocs found${NC}"

# Check if mkdocs.yml exists
echo -e "${BLUE}🔍 Validating documentation structure...${NC}"
if [ ! -f mkdocs.yml ]; then
    echo -e "${RED}❌ mkdocs.yml not found!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ mkdocs.yml found${NC}"

# Check if docs directory exists
if [ ! -d docs ]; then
    echo -e "${RED}❌ docs directory not found!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ docs directory found${NC}"

# Check for required documentation files
echo -e "${BLUE}📄 Checking required files...${NC}"
required_files=(
    "docs/index.md"
    "docs/getting-started.md"
    "docs/guides/index.md"
    "docs/reference/api.md"
    "docs/security/index.md"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${YELLOW}⚠️  Missing: $file${NC}"
    else
        echo -e "${GREEN}✅ Found: $file${NC}"
    fi
done

# Build documentation
echo ""
echo -e "${BLUE}🔨 Building documentation...${NC}"
if mkdocs build --strict; then
    echo -e "${GREEN}✅ Documentation built successfully${NC}"
else
    echo -e "${RED}❌ Documentation build failed${NC}"
    exit 1
fi

# Check build output
echo ""
echo -e "${BLUE}📊 Build output statistics:${NC}"
if [ -d site ]; then
    echo -e "${GREEN}✅ site directory created${NC}"
    
    total_files=$(find site -type f | wc -l)
    html_files=$(find site -name '*.html' | wc -l)
    css_files=$(find site -name '*.css' | wc -l)
    js_files=$(find site -name '*.js' | wc -l)
    
    echo "📁 Total files: $total_files"
    echo "📄 HTML files: $html_files"
    echo "🎨 CSS files: $css_files"
    echo "📜 JS files: $js_files"
else
    echo -e "${RED}❌ site directory not found!${NC}"
    exit 1
fi

# Serve documentation locally
echo ""
echo -e "${BLUE}🌐 Starting local server...${NC}"
echo -e "${GREEN}✅ Documentation is ready!${NC}"
echo ""
echo "📍 Local URL: http://localhost:8000"
echo "Press Ctrl+C to stop the server"
echo ""

mkdocs serve
