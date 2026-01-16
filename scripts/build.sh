#!/bin/bash
# Build Jasper Finance Standalone Executable for Linux/macOS
# Usage: chmod +x build.sh && ./build.sh

set -e

VERSION="${1:-1.0.4}"
ONEFILE="${2:-false}"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Building Jasper Finance Standalone Executable         ║"
echo "╚════════════════════════════════════════════════════════════════╝"

# Check prerequisites
echo ""
echo "[1/5] Checking prerequisites..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found! Install Python 3.9+ first."
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION installed"

# Install/upgrade build dependencies
echo ""
echo "[2/5] Installing build dependencies..."
python3 -m pip install --upgrade pyinstaller weasyprint > /dev/null 2>&1
echo "✅ Dependencies installed"

# Clean previous builds
echo ""
echo "[3/5] Cleaning previous builds..."
rm -rf build dist *.spec
echo "✅ Old builds cleaned"

# Build with PyInstaller
echo ""
echo "[4/5] Building executable with PyInstaller..."

PYINSTALLER_ARGS=(
    "--name=jasper"
    "--onedir"
    "--console"
    "--collect-all=weasyprint"
    "--collect-all=langchain"
    "--hidden-import=weasyprint"
    "--hidden-import=cairocffi"
    "--hidden-import=xhtml2pdf"
    "--add-data=jasper/templates:jasper/templates"
    "--add-data=jasper/styles:jasper/styles"
    "jasper/__main__.py"
)

# Use --onefile if requested
if [ "$ONEFILE" = "true" ]; then
    PYINSTALLER_ARGS[1]="--onefile"
    echo "  Building single-file executable..."
fi

python3 -m pyinstaller "${PYINSTALLER_ARGS[@]}"
if [ $? -ne 0 ]; then
    echo "❌ PyInstaller build failed"
    exit 1
fi
echo "✅ Executable built successfully"

# Create release package
echo ""
echo "[5/5] Creating release package..."
RELEASE_DIR="releases/jasper-${VERSION}-$(uname -s | tr '[:upper:]' '[:lower:]')"
mkdir -p "$RELEASE_DIR"
cp -r dist/jasper/* "$RELEASE_DIR/"
cp README.md "$RELEASE_DIR/"
cp LICENSE "$RELEASE_DIR/"
cp .env.example "$RELEASE_DIR/"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    BUILD SUCCESSFUL! ✅                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"

echo ""
echo "📦 Executable location:"
echo "   $(pwd)/dist/jasper/jasper"

echo ""
echo "📋 Release package:"
echo "   $(pwd)/$RELEASE_DIR/"

echo ""
echo "🚀 Quick start:"
echo "   ./dist/jasper/jasper interactive"

echo ""
echo "📝 Setup:"
echo "   1. Create .env file with your API keys"
echo "   2. Run: ./jasper interactive"
echo "   3. Enter financial queries"
echo ""
