<#
.SYNOPSIS
    Installs a FaTest shortcut (with icon) on the Desktop and in the Start Menu.
    The shortcut opens the default terminal (cmd.exe) and runs "fatest" in it.

.USAGE
    powershell -ExecutionPolicy Bypass -File install-shortcut.ps1
#>

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent (Split-Path -Parent $scriptDir)
$iconPath  = Join-Path $repoRoot "assets\fatest.ico"

if (-not (Test-Path $iconPath)) {
    Write-Warning "Icon not found at $iconPath - the shortcut will be created without a custom icon."
    $iconPath = $null
}

# Check whether 'fatest' is available on PATH
$fatestCmd = Get-Command fatest -ErrorAction SilentlyContinue
if (-not $fatestCmd) {
    Write-Warning "The 'fatest' command was not found on PATH."
    Write-Warning "Build and install it first - see the README's 'Build from source' section."
    Write-Warning "(Creating the shortcut anyway.)"
}

# cmd.exe /K runs the command and does NOT close the window afterwards,
# so the result stays visible.
$targetExe  = "$env:WINDIR\System32\cmd.exe"
$targetArgs = "/K fatest"

function New-FaTestShortcut {
    param(
        [Parameter(Mandatory)] [string]$Path
    )
    $shell    = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($Path)
    $shortcut.TargetPath       = $targetExe
    $shortcut.Arguments        = $targetArgs
    $shortcut.WorkingDirectory = "$env:USERPROFILE"
    $shortcut.Description      = "Fast, clean terminal speedtest tool"
    if ($iconPath) {
        $shortcut.IconLocation = "$iconPath,0"
    }
    $shortcut.WindowStyle = 1  # normal window
    $shortcut.Save()
    Write-Host "Created: $Path"
}

# 1) Desktop shortcut
$desktopPath = [Environment]::GetFolderPath("Desktop")
New-FaTestShortcut -Path (Join-Path $desktopPath "FaTest.lnk")

# 2) Start Menu shortcut (in a "FaTest" submenu)
$startMenuDir = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs\FaTest"
New-Item -ItemType Directory -Force -Path $startMenuDir | Out-Null
New-FaTestShortcut -Path (Join-Path $startMenuDir "FaTest.lnk")

Write-Host ""
Write-Host "Done. FaTest now has a shortcut icon on the Desktop and in the Start Menu."
Write-Host "Launching it opens cmd.exe and runs 'fatest' - its interactive menu."
