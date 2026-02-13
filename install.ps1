# Open-EGM4 Installation Script for Windows
# This script manages installation, updates, and maintenance for Open-EGM4.

function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Success { param($Message) Write-Host "[SUCCESS] $Message" -ForegroundColor Green }
function Write-Warn { param($Message) Write-Host "[WARNING] $Message" -ForegroundColor Yellow }
function Write-Err { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

$InstallDir = "$env:USERPROFILE\.open-egm4"
$VenvDir = "$InstallDir\venv"
$BinDir = "$env:USERPROFILE\.local\bin"
$GlobalDB = "$InstallDir\egm4_data.sqlite"
$WrapperPath = "$BinDir\open-egm4.cmd"
$RepoTagsApiUrl = "https://api.github.com/repos/mmorgans/open-egm4/tags?per_page=100"

function Get-InstalledVersion {
    $pythonExe = "$VenvDir\Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) {
        return "not installed"
    }

    $code = @"
import importlib.metadata
try:
    version = importlib.metadata.version("open-egm4").strip()
except Exception:
    print("unknown")
else:
    if version and not version.startswith("v"):
        version = f"v{version}"
    print(version or "unknown")
"@

    $version = & $pythonExe -c $code 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($version)) {
        return "unknown"
    }
    return $version.Trim()
}

function Get-LatestAvailableVersion {
    try {
        $tags = Invoke-RestMethod -Uri $RepoTagsApiUrl -Headers @{ "User-Agent" = "open-egm4-installer" } -TimeoutSec 8
    } catch {
        return "unknown"
    }

    $semverTags = @()
    foreach ($tag in $tags) {
        $name = [string]$tag.name
        if ($name -match "^v?(\d+)\.(\d+)\.(\d+)$") {
            $semverTags += [PSCustomObject]@{
                Major = [int]$Matches[1]
                Minor = [int]$Matches[2]
                Patch = [int]$Matches[3]
                Tag   = "v$($Matches[1]).$($Matches[2]).$($Matches[3])"
            }
        }
    }

    if ($semverTags.Count -eq 0) {
        return "unknown"
    }

    return ($semverTags | Sort-Object Major, Minor, Patch | Select-Object -Last 1).Tag
}

function Get-VersionRelation {
    param(
        [string]$Installed,
        [string]$Latest
    )

    $installedMatch = [regex]::Match($Installed, "^v?(\d+)\.(\d+)\.(\d+)$")
    $latestMatch = [regex]::Match($Latest, "^v?(\d+)\.(\d+)\.(\d+)$")
    if (-not $installedMatch.Success -or -not $latestMatch.Success) {
        return "unknown"
    }

    $left = @(
        [int]$installedMatch.Groups[1].Value,
        [int]$installedMatch.Groups[2].Value,
        [int]$installedMatch.Groups[3].Value
    )
    $right = @(
        [int]$latestMatch.Groups[1].Value,
        [int]$latestMatch.Groups[2].Value,
        [int]$latestMatch.Groups[3].Value
    )

    for ($i = 0; $i -lt 3; $i++) {
        if ($left[$i] -lt $right[$i]) { return "update_available" }
        if ($left[$i] -gt $right[$i]) { return "ahead_of_release" }
    }
    return "up_to_date"
}

function Show-VersionStatus {
    param(
        [string]$Installed,
        [string]$Latest
    )

    Write-Info "Installed version: $Installed"
    Write-Info "Latest available: $Latest"

    $relation = Get-VersionRelation -Installed $Installed -Latest $Latest
    switch ($relation) {
        "update_available" { Write-Warn "Update available." }
        "up_to_date" { Write-Success "You are on the latest release." }
        "ahead_of_release" { Write-Info "Installed build is newer than latest tagged release." }
        default { Write-Warn "Unable to compare versions right now." }
    }
}

try {
    Clear-Host
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "     Open-EGM4 Installer & Manager         " -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""

    $InstalledVersion = Get-InstalledVersion
    $LatestVersion = Get-LatestAvailableVersion
    Show-VersionStatus -Installed $InstalledVersion -Latest $LatestVersion
    Write-Host ""

    # Check for existing installation
    $IsInstalled = Test-Path $VenvDir

    if ($IsInstalled) {
        Write-Info "Existing installation detected at $InstallDir"
        Write-Host ""
        Write-Host "  1) Update    (Pull latest version, keep data)" -ForegroundColor Green
        Write-Host "  2) Repair    (Reinstall dependencies, keep data)" -ForegroundColor Green
        Write-Host "  3) Uninstall (Remove application)" -ForegroundColor Green
        Write-Host "  4) Quit" -ForegroundColor Green
        Write-Host ""
        
        while ($true) {
            $choice = Read-Host "Select an option [1-4]"
            if ($choice -in "1","2","3","4") { break }
            Write-Warn "Invalid option. Please try again."
        }
        
        switch ($choice) {
            "1" { $Action = "Update" }
            "2" { $Action = "Repair" }
            "3" { $Action = "Uninstall" }
            "4" { exit }
        }
    } else {
        $Action = "Install"
        Write-Info "Ready to install Open-EGM4 to $InstallDir"
        Write-Host ""
        Write-Host "Press ENTER to continue, or Ctrl+C to cancel..."
        $null = Read-Host
    }

    # ==========================================
    # WORKFLOW: UNINSTALL
    # ==========================================
    if ($Action -eq "Uninstall") {
        Write-Info "Uninstalling Open-EGM4..."
        
        if (Test-Path $GlobalDB) {
            $keepData = Read-Host "Keep database file ($GlobalDB)? [Y/n]"
            if ($keepData -notmatch "n") {
                Write-Info "Preserving database..."
                # Move to temp or just don't delete it?
                # We'll just delete everything else.
            } else {
                Remove-Item $GlobalDB -Force
            }
        }
        
        # Remove venv
        if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
        
        # Remove wrapper
        if (Test-Path $WrapperPath) { Remove-Item -Force $WrapperPath }
        
        # We don't remove $InstallDir completely if data is kept
        # But if data is deleted, we can remove the dir if empty
        if (-not (Test-Path $GlobalDB)) {
             if ((Get-ChildItem $InstallDir).Count -eq 0) {
                 Remove-Item -Force $InstallDir
             }
        }

        Write-Success "Uninstalled successfully."
        exit
    }

    # ==========================================
    # WORKFLOW: INSTALL / UPDATE / REPAIR
    # ==========================================
    
    # 1. Check Prerequisites (Git & Python)
    Write-Info "Checking prerequisites..."
    $hasWinget = Get-Command winget -ErrorAction SilentlyContinue

    # Git
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        if ($hasWinget) {
            Write-Info "Git not found. Installing via winget..."
            winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        } else {
            throw "Git is required but not found. Install from https://git-scm.com/"
        }
    }

    # Python
    $pythonWorks = $false
    $pythonOutput = python --version 2>&1 | Out-String
    if ($pythonOutput -notmatch "Microsoft Store" -and $pythonOutput -match "Python \d") { $pythonWorks = $true }

    if (-not $pythonWorks) {
        if ($hasWinget) {
            Write-Info "Python not found. Installing via winget..."
            winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        } else {
            throw "Python 3.10+ is required via https://python.org"
        }
    }

    # 2. Setup Directories & Database Migration
    if (-not (Test-Path $InstallDir)) { New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null }
    if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir -Force | Out-Null }

    # DATA MIGRATION CHECK
    $LocalDB = ".\egm4_data.sqlite"
    if (Test-Path $LocalDB) {
        if (-not (Test-Path $GlobalDB)) {
            Write-Info "Migrating existing database from current folder to installation directory..."
            Copy-Item $LocalDB $GlobalDB
            Write-Success "Database migrated successfully."
        } else {
            Write-Warn "Found a local database ($LocalDB) but a global one already exists."
            Write-Warn "Using the existing global database. You can manually merge them if needed."
        }
    }

    # 3. Virtual Environment
    if ($Action -eq "Repair" -or -not (Test-Path $VenvDir)) {
        Write-Info "Creating/Recreating virtual environment..."
        if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
        
        python -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) { throw "Failed to create venv." }
    }

    # 4. Install Package
    Write-Info "Installing/Updating Open-EGM4..."
    & "$VenvDir\Scripts\pip.exe" install --upgrade pip 2>&1 | Out-Null
    
    # We always pull latest unless it's a specific version repair, but for now git URL is fine
    & "$VenvDir\Scripts\pip.exe" install --upgrade git+https://github.com/mmorgans/open-egm4.git
    if ($LASTEXITCODE -ne 0) { throw "Pip install failed. Check internet connection." }

    # 5. Wrapper
    if (Test-Path "$VenvDir\Scripts\open-egm4.exe") {
        Write-Info "Updating command wrapper..."
        $WrapperContent = "@echo off`r`n`"$VenvDir\Scripts\open-egm4.exe`" %*"
        Set-Content -Path $WrapperPath -Value $WrapperContent -Encoding ASCII
    }

    # 6. PATH
    $CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $PathUpdated = $false
    if ($CurrentPath -notlike "*$BinDir*") {
        Write-Info "Adding $BinDir to PATH..."
        [Environment]::SetEnvironmentVariable("Path", "$CurrentPath;$BinDir", "User")
        $env:Path = "$env:Path;$BinDir"
        $PathUpdated = $true
    }

    # Finish
    Write-Host ""
    Write-Success "$Action completed successfully!"
    Write-Host "Database Location: $GlobalDB"
    $FinalVersion = Get-InstalledVersion
    if ($FinalVersion -ne "unknown" -and $FinalVersion -ne "not installed") {
        Write-Host "Installed Version: $FinalVersion"
    }
    Write-Host "Run with: " -NoNewline; Write-Host "open-egm4" -ForegroundColor Green
    
    if ($PathUpdated) {
        Write-Warn "You may need to restart your terminal for the command to work."
    }

} catch {
    Write-Err "Error: $_"
} finally {
    Write-Host ""
    Write-Host "Press any key to close..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
