#Requires -Version 5.1
<#
.SYNOPSIS
    Builds the KNWLDGBox Windows installer (KNWLDGBox-Setup-<version>.exe).

.DESCRIPTION
    Assembles installer\payload\ with everything the installer needs, then
    compiles installer.iss with Inno Setup:

      1. Builds the Vue frontend (npm)                -> payload\app\dist
      2. Downloads a standalone CPython runtime       -> payload\python
      3. Downloads all pip dependencies as wheels     -> payload\wheels
      4. Copies the backend source (no secrets!)      -> payload\backend
      5. Downloads ffmpeg                             -> payload\tools\ffmpeg
      6. Downloads Chromium via Playwright (optional) -> payload\playwright-browsers
      7. Downloads the WebView2 bootstrapper          -> payload\
      8. Copies icon.ico from app\src\assets\knwldgbox.ico
      9. Compiles the installer with ISCC.exe

    Prerequisites on the BUILD machine (Windows 10/11 x64):
      - Node.js + npm        (https://nodejs.org)
      - Inno Setup 6         (https://jrsoftware.org/isdl.php) unless -PayloadOnly
      - Internet access, ~2 GB free disk space

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1

.EXAMPLE
    # Smaller installer without the bundled Chromium (~170 MB less):
    powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -BundleChromium $false

.EXAMPLE
    # Only assemble the payload, don't compile the .exe:
    powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -PayloadOnly
#>

[CmdletBinding()]
param(
    # Version embedded in the installer filename and Add/Remove Programs
    [string]$Version = "1.0.0",

    # CPython version + python-build-standalone release tag.
    # Check https://github.com/astral-sh/python-build-standalone/releases for updates.
    [string]$PythonVersion = "3.12.13",
    [string]$PbsTag = "20260718",

    # Bundle Chromium (~170 MB) so the Archives/TikTok modules work without Chrome
    [bool]$BundleChromium = $true,

    # Skip the frontend build (reuse the existing app\dist)
    [switch]$SkipFrontend,

    # Skip bundling ffmpeg (yt-dlp audio conversion will need ffmpeg on PATH)
    [switch]$SkipFfmpeg,

    # Stop after assembling installer\payload (do not run Inno Setup)
    [switch]$PayloadOnly,

    # Explicit path to ISCC.exe (auto-detected if omitted)
    [string]$InnoSetupCompiler = ""
)

$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'   # much faster Invoke-WebRequest

# ------------------------------------------------------------------ paths ---
$InstallerDir = $PSScriptRoot
$Root         = Split-Path $InstallerDir -Parent
$Payload      = Join-Path $InstallerDir 'payload'
$Downloads    = Join-Path $InstallerDir '.downloads'
$IssFile      = Join-Path $InstallerDir 'installer.iss'

function Write-Step([string]$Message) {
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Invoke-Download([string]$Url, [string]$OutFile) {
    Write-Host "Downloading $Url"
    Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
}

function Assert-ExitCode([string]$What, [int[]]$OkCodes = @(0)) {
    if ($OkCodes -notcontains $LASTEXITCODE) {
        throw "$What failed with exit code $LASTEXITCODE"
    }
    $global:LASTEXITCODE = 0
}

# ------------------------------------------------------------- 1. frontend ---
if (-not $SkipFrontend) {
    Write-Step "Building frontend (Vue/Vite)"
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npm) { throw "npm not found. Install Node.js first: https://nodejs.org" }
    # The installed app resolves the API from window.location.port â€” make sure
    # no build-time port override leaks in.
    Remove-Item Env:VITE_API_PORT -ErrorAction SilentlyContinue
    Push-Location (Join-Path $Root 'app')
    try {
        npm install
        Assert-ExitCode "npm install"
        npm run build
        Assert-ExitCode "npm run build"
    } finally {
        Pop-Location
    }
}
if (-not (Test-Path (Join-Path $Root 'app\dist\index.html'))) {
    throw "app\dist\index.html not found. Run without -SkipFrontend first."
}

# ------------------------------------------------------- 2. clean payload ---
Write-Step "Preparing payload directory"
if (Test-Path $Payload)   { Remove-Item $Payload -Recurse -Force }
if (Test-Path $Downloads) { Remove-Item $Downloads -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Payload, $Downloads | Out-Null

# ---------------------------------------------- 3. standalone CPython -------
Write-Step "Python runtime (python-build-standalone $PythonVersion+$PbsTag)"
$PyArchive = Join-Path $Downloads 'python.tar.gz'
Invoke-Download `
    "https://github.com/astral-sh/python-build-standalone/releases/download/$PbsTag/cpython-$PythonVersion%2B$PbsTag-x86_64-pc-windows-msvc-install_only.tar.gz" `
    $PyArchive
tar -xzf $PyArchive -C $Downloads
Assert-ExitCode "tar extract (python)"
Move-Item (Join-Path $Downloads 'python') (Join-Path $Payload 'python')
$Py = Join-Path $Payload 'python\python.exe'
if (-not (Test-Path $Py)) { throw "python.exe not found after extraction." }
& $Py -m pip install --upgrade pip | Out-Host
Assert-ExitCode "pip self-upgrade"

# ----------------------------------------------------------- 4. wheels ------
Write-Step "Downloading Python dependencies as wheels (offline install)"
$Wheels = Join-Path $Payload 'wheels'
$Reqs   = Join-Path $Root 'backend\requirements.txt'
& $Py -m pip download -r $Reqs -d $Wheels --only-binary=:all: | Out-Host
if ($LASTEXITCODE -ne 0) {
    $global:LASTEXITCODE = 0
    Write-Warning "Binary-only download failed; retrying including source distributions."
    & $Py -m pip download -r $Reqs -d $Wheels | Out-Host
    Assert-ExitCode "pip download"
}
# Build tooling for any source distributions at install time
& $Py -m pip download pip setuptools wheel -d $Wheels --only-binary=:all: | Out-Host
Assert-ExitCode "pip download (build tooling)"
$sdists = Get-ChildItem $Wheels -Filter *.tar.gz -ErrorAction SilentlyContinue
if ($sdists) {
    Write-Warning ("Source distributions bundled (will be compiled at install time): " + ($sdists.Name -join ', '))
}

# ----------------------------------------------------------- 5. backend -----
Write-Step "Copying backend source (excluding secrets and local data)"
robocopy (Join-Path $Root 'backend') (Join-Path $Payload 'backend') /MIR /NFL /NDL /NJH /NJS /NP `
    /XD __pycache__ archives data venv .pytest_cache `
    /XF .env *.session *.pyc *.log testcom.txt | Out-Host
Assert-ExitCode "robocopy backend" @(0,1,2,3,4,5,6,7)

# Safety net: never ship credentials or sessions inside the installer
$leaks = Get-ChildItem (Join-Path $Payload 'backend') -Recurse -Force -Include '.env','*.session' -ErrorAction SilentlyContinue
if ($leaks) {
    throw "Secret files would be shipped: $($leaks.FullName -join ', '). Aborting."
}

# ------------------------------------------------------------- 6. dist ------
Write-Step "Copying built frontend"
robocopy (Join-Path $Root 'app\dist') (Join-Path $Payload 'app\dist') /MIR /NFL /NDL /NJH /NJS /NP | Out-Host
Assert-ExitCode "robocopy frontend" @(0,1,2,3,4,5,6,7)

# ------------------------------------------------------------- 7. ffmpeg ----
if (-not $SkipFfmpeg) {
    Write-Step "Downloading ffmpeg"
    $FfmpegZip = Join-Path $Downloads 'ffmpeg.zip'
    Invoke-Download "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" $FfmpegZip
    Expand-Archive $FfmpegZip -DestinationPath (Join-Path $Downloads 'ffmpeg') -Force
    $bin = Get-ChildItem (Join-Path $Downloads 'ffmpeg') -Recurse -Filter ffmpeg.exe |
           Select-Object -First 1 -ExpandProperty DirectoryName
    if (-not $bin) { throw "ffmpeg.exe not found in the downloaded archive." }
    $FfmpegDest = Join-Path $Payload 'tools\ffmpeg'
    New-Item -ItemType Directory -Force -Path $FfmpegDest | Out-Null
    Copy-Item (Join-Path $bin 'ffmpeg.exe'), (Join-Path $bin 'ffprobe.exe') $FfmpegDest
}

# ------------------------------------------- 8. Chromium (Playwright) -------
if ($BundleChromium) {
    Write-Step "Bundling Chromium via Playwright (~170 MB)"
    & $Py -m pip install --no-index --find-links $Wheels playwright | Out-Host
    Assert-ExitCode "pip install playwright (build-time)"
    $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $Payload 'playwright-browsers'
    try {
        & $Py -m playwright install chromium | Out-Host
        Assert-ExitCode "playwright install chromium"
    } finally {
        Remove-Item Env:PLAYWRIGHT_BROWSERS_PATH -ErrorAction SilentlyContinue
    }
}

# -------------------------------------------------- 9. WebView2 bootstrap ---
Write-Step "Downloading WebView2 bootstrapper"
Invoke-Download "https://go.microsoft.com/fwlink/p/?LinkId=2124703" `
    (Join-Path $Payload 'MicrosoftEdgeWebview2Setup.exe')

# ------------------------------------------------------------ 10. icon ------
Write-Step "Copying icon.ico"
$SrcIco = Join-Path $Root 'app\src\assets\knwldgbox.ico'
$DstIco = Join-Path $Payload 'icon.ico'

if (Test-Path $SrcIco) {
    Copy-Item $SrcIco $DstIco
    Write-Host "Copied $SrcIco -> $DstIco"
} else {
    Write-Warning "app\src\assets\knwldgbox.ico not found - installer will use default icon."
}

# -------------------------------------------------------- 11. Inno Setup ----
if ($PayloadOnly) {
    Write-Step "Done (payload only)"
    Write-Host "Payload ready at: $Payload" -ForegroundColor Green
    exit 0
}

Write-Step "Compiling installer with Inno Setup"
$Iscc = $InnoSetupCompiler
if (!$Iscc) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 7\ISCC.exe"
    )
    $Iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (!$Iscc) {
        $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        if ($cmd) { $Iscc = $cmd.Source }
    }
}

if (!$Iscc) {
    Write-Warning "Inno Setup 6 not found."
    Write-Host "Payload ready at: $Payload" -ForegroundColor Green
    exit 0
}

& $Iscc "/DAppVersion=$Version" $IssFile | Out-Host
Assert-ExitCode "Inno Setup compilation"

Write-Step "Done"
$exes = Get-ChildItem (Join-Path $InstallerDir 'Output\*.exe')
foreach ($exe in $exes) {
    $sz = [math]::Round($exe.Length / 1048576)
    $msg = "Installer created: " + $exe.FullName + " (" + $sz + " MB)"
    Write-Host $msg -ForegroundColor Green
}