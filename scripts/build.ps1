# Build Jasper Finance Standalone Executable for Windows
# Usage: .\build.ps1

param(
    [string]$Version = "1.0.7",
    [switch]$OneFile = $false,
    [switch]$MinimalSize = $false
)

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         Building Jasper Finance Standalone Executable         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# Check prerequisites
Write-Host "`n[1/5] Checking prerequisites..." -ForegroundColor Yellow
$python = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python not found! Install Python 3.9+ first." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Python $python installed" -ForegroundColor Green

# Install/upgrade build dependencies
Write-Host "`n[2/5] Installing build dependencies..." -ForegroundColor Yellow
pip install --upgrade pyinstaller weasyprint > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Dependencies installed" -ForegroundColor Green

# Clean previous builds
Write-Host "`n[3/5] Cleaning previous builds..." -ForegroundColor Yellow
Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "*.spec" -Force -ErrorAction SilentlyContinue
Write-Host "✅ Old builds cleaned" -ForegroundColor Green

# Build with PyInstaller
Write-Host "`n[4/5] Building executable with PyInstaller..." -ForegroundColor Yellow

$pyinstallerArgs = @(
    "--name=jasper",
    "--onedir",
    "--console",
    "--icon=assets/jasper-icon.ico",  # Optional: provide icon if available
    "--collect-all=weasyprint",
    "--collect-all=langchain",
    "--hidden-import=weasyprint",
    "--hidden-import=cairocffi",
    "--hidden-import=xhtml2pdf",
    "--add-data=jasper/templates:jasper/templates",
    "--add-data=jasper/styles:jasper/styles",
    "jasper/__main__.py"
)

# Use --onefile if requested (produces single .exe, slower startup)
if ($OneFile) {
    $pyinstallerArgs[1] = "--onefile"
    Write-Host "  Building single-file executable..." -ForegroundColor Gray
}

pyinstaller @pyinstallerArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ PyInstaller build failed" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Executable built successfully" -ForegroundColor Green

# Create release package
Write-Host "`n[5/5] Creating release package..." -ForegroundColor Yellow
$releaseDir = "releases/jasper-$Version-windows"
New-Item -ItemType Directory -Path $releaseDir -Force > $null
Copy-Item -Path "dist/jasper" -Destination "$releaseDir/" -Recurse -Force
Copy-Item -Path "README.md" -Destination "$releaseDir/" -Force
Copy-Item -Path "LICENSE" -Destination "$releaseDir/" -Force
Copy-Item -Path ".env.example" -Destination "$releaseDir/" -Force

Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    BUILD SUCCESSFUL! ✅                         ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green

Write-Host "`n📦 Executable location:" -ForegroundColor Cyan
Write-Host "   $pwd/dist/jasper/jasper.exe" -ForegroundColor White

Write-Host "`n📋 Release package:" -ForegroundColor Cyan
Write-Host "   $pwd/$releaseDir/" -ForegroundColor White

Write-Host "`n🚀 Quick start:" -ForegroundColor Cyan
Write-Host "   .\dist\jasper\jasper.exe interactive" -ForegroundColor White

Write-Host "`n📝 Setup:" -ForegroundColor Cyan
Write-Host "   1. Create .env file with your API keys" -ForegroundColor Gray
Write-Host "   2. Run: jasper.exe interactive" -ForegroundColor Gray
Write-Host "   3. Enter financial queries" -ForegroundColor Gray

Write-Host ""
