#!/bin/bash
# Smoke test script for validating basic project setup
# Run this before full installation to catch setup issues early

set -e  # Exit on error

echo "🔍 Running Smoke Tests for YouTube Explainer Automation System"
echo "=============================================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Test 1: Check Python version
echo "Test 1: Python Version"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ]; then
        pass "Python $PYTHON_VERSION (requires 3.11+)"
    else
        fail "Python $PYTHON_VERSION (requires 3.11+)"
    fi
else
    fail "Python 3 not found"
fi
echo ""

# Test 2: Check Node.js version
echo "Test 2: Node.js Version"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1)

    if [ "$MAJOR" -ge 18 ]; then
        pass "Node.js v$NODE_VERSION (requires 18+)"
    else
        fail "Node.js v$NODE_VERSION (requires 18+)"
    fi
else
    fail "Node.js not found"
fi
echo ""

# Test 3: Check required files exist
echo "Test 3: Required Files"
FILES=(
    "README.md"
    "requirements.txt"
    ".env.template"
    ".gitignore"
    "pytest.ini"
    "PRODUCTION_GUIDE_V2.md"
    "config/settings.py"
    "src/__init__.py"
    "remotion/package.json"
    "remotion/tsconfig.json"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        pass "$file exists"
    else
        fail "$file missing"
    fi
done
echo ""

# Test 4: Check directory structure
echo "Test 4: Directory Structure"
DIRS=(
    "src"
    "config"
    "remotion"
    "tests"
    ".github"
    "scripts"
    "docs"
)

for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        pass "$dir/ exists"
    else
        fail "$dir/ missing"
    fi
done
echo ""

# Test 5: Validate JSON files
echo "Test 5: JSON Syntax Validation"
JSON_FILES=(
    "remotion/package.json"
    "remotion/tsconfig.json"
)

for file in "${JSON_FILES[@]}"; do
    if command -v python3 &> /dev/null; then
        if python3 -c "import json; json.load(open('$file'))" 2>/dev/null; then
            pass "$file is valid JSON"
        else
            fail "$file has JSON syntax errors"
        fi
    else
        warn "Cannot validate $file (python3 not available)"
    fi
done
echo ""

# Test 6: Check YAML files
echo "Test 6: YAML Syntax Validation"
if [ -f ".github/workflows/ci.yml" ]; then
    if command -v python3 &> /dev/null; then
        if python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" 2>/dev/null; then
            pass "GitHub Actions workflow is valid YAML"
        else
            fail "GitHub Actions workflow has YAML syntax errors"
        fi
    else
        warn "Cannot validate YAML (PyYAML not available)"
    fi
fi
echo ""

# Test 7: Check for FFmpeg
echo "Test 7: External Dependencies"
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n1 | cut -d' ' -f3)
    pass "FFmpeg installed (version $FFMPEG_VERSION)"
else
    warn "FFmpeg not found (required for video rendering)"
fi

if command -v git &> /dev/null; then
    pass "Git installed"
else
    fail "Git not found"
fi
echo ""

# Test 8: Python import test (without full dependencies)
echo "Test 8: Python Import Structure"
if python3 -c "import sys; sys.path.insert(0, '.'); import src" 2>/dev/null; then
    pass "src package can be imported"
else
    fail "src package import failed"
fi

# Test config import (will fail without pydantic-settings, which is expected)
if python3 -c "from config.settings import get_settings" 2>/dev/null; then
    pass "config.settings can be imported"
else
    warn "config.settings import failed (expected without dependencies)"
fi
echo ""

# Test 9: Check for sensitive files
echo "Test 9: Security Check"
if [ -f ".env" ]; then
    warn ".env file exists (should not be committed to git)"
else
    pass "No .env file (using .env.template only)"
fi

if [ -f ".git" ]; then
    if git check-ignore .env > /dev/null 2>&1; then
        pass ".env is properly ignored by git"
    else
        fail ".env not in .gitignore"
    fi
fi
echo ""

# Test 10: Check requirements.txt syntax
echo "Test 10: Requirements File Validation"
if grep -q "pydantic-settings" requirements.txt; then
    pass "pydantic-settings dependency present"
else
    fail "pydantic-settings missing from requirements.txt"
fi

if grep -q "pydantic==" requirements.txt; then
    pass "pydantic dependency present"
else
    fail "pydantic missing from requirements.txt"
fi
echo ""

# Summary
echo "=============================================================="
echo "Smoke Test Summary"
echo "=============================================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All smoke tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Create virtual environment: python3 -m venv venv"
    echo "2. Activate it: source venv/bin/activate"
    echo "3. Install dependencies: pip install -r requirements.txt"
    echo "4. Install Node packages: cd remotion && npm install"
    echo "5. Configure environment: cp .env.template .env"
    exit 0
else
    echo -e "${RED}✗ Some smoke tests failed${NC}"
    echo "Please fix the issues above before proceeding"
    exit 1
fi
