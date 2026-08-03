$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent (Split-Path -Parent $scriptDir)
$iconPath  = Join-Path $repoRoot "assets\fatest.ico"

if (-not (Test-Path $iconPath)) {
    Write-Warning "Icon not found at $iconPath - the shortcut will be created without a custom icon."
    $iconPath = $null
}

$fatestCmd = Get-Command fatest -ErrorAction SilentlyContinue
if (-not $fatestCmd) {
    Write-Warning "The 'fatest' command was not found on PATH."
    Write-Warning "Build and install it first - see the README's 'Build from source' section."
    Write-Warning "(Creating the shortcut anyway.)"
}

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
    $shortcut.WindowStyle = 1
    $shortcut.Save()
    Write-Host "Created: $Path"
}

$desktopPath = [Environment]::GetFolderPath("Desktop")
New-FaTestShortcut -Path (Join-Path $desktopPath "FaTest.lnk")

$startMenuDir = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs\FaTest"
New-Item -ItemType Directory -Force -Path $startMenuDir | Out-Null
New-FaTestShortcut -Path (Join-Path $startMenuDir "FaTest.lnk")

Write-Host ""
Write-Host "Done. FaTest now has a shortcut icon on the Desktop and in the Start Menu."
Write-Host "Launching it opens cmd.exe and runs 'fatest' - its interactive menu."
