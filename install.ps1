# Open-EGM4 Installation Script for Windows
# This script installs Open-EGM4 into a dedicated virtual environment
# and sets up the command line tool.

function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Success { param($Message) Write-Host "[SUCCESS] $Message" -ForegroundColor Green }
function Write-Warn { param($Message) Write-Host "[WARNING] $Message" -ForegroundColor Yellow }
function Write-Err { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

try {

# 1. Check Prerequisites and Install if Missing
Write-Info "Checking prerequisites..."

# Check for winget (Windows Package Manager)
$hasWinget = Get-Command winget -ErrorAction SilentlyContinue

# Check and install Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    if ($hasWinget) {
        Write-Info "Git not found. Installing via winget..."
        winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
            throw "Git installation failed. Please install Git manually and try again."
        }
        Write-Success "Git installed successfully."
    } else {
        throw "Git is not installed. Please install Git from https://git-scm.com/download/win and try again."
    }
}

# Check and install Python
# Note: Windows has "App Execution Aliases" that make `python` open the Store
# So we need to check if Python actually runs and isn't the Store alias
$pythonWorks = $false
$pythonOutput = python --version 2>&1 | Out-String
if ($pythonOutput -notmatch "Microsoft Store" -and $pythonOutput -match "Python \d") {
    $pythonWorks = $true
}

if (-not $pythonWorks) {
    if ($hasWinget) {
        Write-Info "Python not found. Installing via winget..."
        winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        # Verify installation
        $pythonOutput = python --version 2>&1 | Out-String
        if ($pythonOutput -notmatch "Python \d") {
            throw "Python installation failed. Please restart your terminal and try again."
        }
        Write-Success "Python installed successfully."
    } else {
        throw "Python is not installed. Please install Python 3.10+ from https://python.org and try again."
    }
}

# Check Python version (>= 3.10)
$pythonVersion = $null
try {
    $pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $pythonVersion = $null
    }
} catch {
    $pythonVersion = $null
}

if (-not $pythonVersion) {
    throw "Python is not working properly. Please restart your terminal and try again, or install Python manually from https://python.org"
}

$versionParts = $pythonVersion -split '\.'
if ([int]$versionParts[0] -lt 3 -or ([int]$versionParts[0] -eq 3 -and [int]$versionParts[1] -lt 10)) {
    throw "Open-EGM4 requires Python 3.10 or newer. Your version is $pythonVersion. Please upgrade Python."
}

# 2. Setup Directories
$InstallDir = "$env:USERPROFILE\.open-egm4"
$VenvDir = "$InstallDir\venv"
$BinDir = "$env:USERPROFILE\.local\bin"

# Detect if updating
if (Test-Path $VenvDir) {
    Write-Info "Existing installation detected. Updating..."
    $IsUpdate = $true
} else {
    Write-Info "Installing fresh to $InstallDir..."
    $IsUpdate = $false
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

New-Item -ItemType Directory -Path $BinDir -Force | Out-Null

# 3. Create/Verify Virtual Environment
if (-not (Test-Path $VenvDir)) {
    Write-Info "Creating virtual environment..."
    python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create virtual environment."
    }
} else {
    if (-not (Test-Path "$VenvDir\Scripts\pip.exe")) {
        Write-Warn "Virtual environment appears broken. Recreating..."
        Remove-Item -Recurse -Force $VenvDir
        python -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to recreate virtual environment."
        }
    }
}

# 4. Install/Update Package
Write-Info "Fetching latest version and installing dependencies..."
& "$VenvDir\Scripts\pip.exe" install --upgrade pip 2>&1 | Out-Null

& "$VenvDir\Scripts\pip.exe" install --upgrade git+https://github.com/mmorgans/open-egm4.git
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install Open-EGM4. Please check your internet connection and git configuration."
}

# 5. Create Batch Wrapper
$TargetExe = "$VenvDir\Scripts\open-egm4.exe"
$WrapperPath = "$BinDir\open-egm4.cmd"

if (Test-Path $TargetExe) {
    Write-Info "Creating command wrapper at $WrapperPath..."
    $WrapperContent = "@echo off`r`n`"$TargetExe`" %*"
    Set-Content -Path $WrapperPath -Value $WrapperContent -Encoding ASCII
} else {
    throw "Installation failed: Executable not found at $TargetExe"
}

# 6. Check PATH
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
$PathUpdated = $false

if ($CurrentPath -notlike "*$BinDir*") {
    Write-Info "Adding $BinDir to your PATH..."
    $NewPath = "$CurrentPath;$BinDir"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    $env:Path = "$env:Path;$BinDir"
    $PathUpdated = $true
} else {
    Write-Info "PATH already correctly configured."
}

# 7. Finish
Write-Host ""
if ($IsUpdate) {
    Write-Success "Update complete! You are now running the latest version."
} else {
    Write-Success "Installation complete!"
}

Write-Host ""
Write-Host "To start the application, run:"
Write-Host "open-egm4" -ForegroundColor Green
Write-Host ""

if ($PathUpdated) {
    Write-Host "NOTE: You may need to restart your terminal for the command to become available." -ForegroundColor Blue
}

} catch {
    Write-Err "An error occurred: $_"
} finally {
    Write-Host ""
    Write-Host "Press any key to close..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
