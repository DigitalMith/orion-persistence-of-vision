<#
────────────────────────────────────────────────────────────
🧠 Orion CLI Manager — v1.2.0
By Uncle Aión | Orion AI Ecosystem
────────────────────────────────────────────────────────────
Unified management script for the Orion CLI subsystem.
Usage:
    ./manage_cli.ps1 --install     # Fresh install of Orion CLI
    ./manage_cli.ps1 --update      # Refresh pip and re-link editable mode
    ./manage_cli.ps1 --uninstall   # Full removal (alias + venv)
    ./manage_cli.ps1 --help        # Display usage and descriptions
────────────────────────────────────────────────────────────
#>

param(
    [switch]$install,
    [switch]$update,
    [switch]$uninstall,
    [switch]$help
)

# Normalize double-dash syntax for cross-platform consistency
$Args | ForEach-Object {
    switch -Regex ($_) {
        '^--install$'   { $install   = $true }
        '^--update$'    { $update    = $true }
        '^--uninstall$' { $uninstall = $true }
        '^--help$'      { $help      = $true }
    }
}

$ErrorActionPreference = "Stop"
$timestamp   = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$root        = "C:\Orion\text-generation-webui"
$cliPath     = Join-Path $root "orion_cli"
$venvPath    = Join-Path $root "venv-cli"
$pythonExe   = Join-Path $venvPath "Scripts\python.exe"
$logDir      = Join-Path $root "logs"
$logFile     = Join-Path $logDir "manage_cli_$timestamp.log"
$profilePath = $PROFILE.CurrentUserAllHosts
$aliasLine   = "Set-Alias orion-cli `"C:\Orion\text-generation-webui\venv-cli\Scripts\python.exe`" -ArgumentList '-m','orion_cli'"

# -----------------------------------------------------------
# Ensure log directory exists and start logging
# -----------------------------------------------------------
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
Start-Transcript -Path $logFile -Append | Out-Null

$global:transcribing = $true

Write-Host "🚀 Orion CLI Manager starting..." -ForegroundColor Cyan

try {
    # -----------------------------------------------------------
    # Display help or default help when no switch is used
    # -----------------------------------------------------------
    if (-not ($install -or $update -or $uninstall) -or $help) {
        Write-Host ""
        Write-Host "🧩 Orion CLI Manager — Command Reference" -ForegroundColor Cyan
        Write-Host "───────────────────────────────────────────────"
        Write-Host " --install    " -NoNewline; Write-Host "Create venv-cli, install CLI in editable mode, add alias" -ForegroundColor Gray
        Write-Host " --update     " -NoNewline; Write-Host "Refresh pip and re-link editable mode" -ForegroundColor Gray
        Write-Host " --uninstall  " -NoNewline; Write-Host "Remove alias and delete venv-cli" -ForegroundColor Gray
        Write-Host " --help       " -NoNewline; Write-Host "Display this command reference" -ForegroundColor Gray
        Write-Host "───────────────────────────────────────────────"
        Write-Host "Logs are written to: $logDir" -ForegroundColor DarkGray
        Write-Host ""
        Stop-Transcript | Out-Null
        exit 0
    }

    # -----------------------------------------------------------
    # Deactivate venv-orion if active
    # -----------------------------------------------------------
    if ($env:VIRTUAL_ENV -and $env:VIRTUAL_ENV -like "*venv-orion*") {
        Write-Host "🔌 Deactivating venv-orion..." -ForegroundColor Yellow
        deactivate 2>$null
        $env:VIRTUAL_ENV = $null
    }

    # ===========================================================
    # INSTALL MODE
    # ===========================================================
    if ($install) {
        if (-not (Test-Path $venvPath)) {
            Write-Host "🧱 Creating venv-cli..." -ForegroundColor Cyan
            python -m venv $venvPath
        } else {
            Write-Host "✅ venv-cli already exists." -ForegroundColor Green
        }

        Write-Host "📦 Installing Orion CLI (editable mode)..." -ForegroundColor Cyan
        & $pythonExe -m pip install --upgrade pip
        & $pythonExe -m pip install -e $cliPath

        & $pythonExe -m orion_cli --help | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Orion CLI installed successfully." -ForegroundColor Green
        } else {
            throw "Orion CLI installation failed verification."
        }

        # Add alias to PowerShell profile
        if (-not (Test-Path (Split-Path $profilePath))) {
            New-Item -ItemType Directory -Path (Split-Path $profilePath) -Force | Out-Null
        }

        $profileContent = if (Test-Path $profilePath) { Get-Content $profilePath -Raw } else { "" }

        if ($profileContent -notmatch "orion-cli") {
            Add-Content -Path $profilePath -Value "`n$aliasLine"
            Write-Host "🪄 Added 'orion-cli' alias to PowerShell profile." -ForegroundColor Green
        } else {
            Write-Host "ℹ️  Alias already exists in profile." -ForegroundColor Yellow
        }

        Write-Host "`n🌌 Orion CLI installation complete!" -ForegroundColor Cyan
    }

    # ===========================================================
    # UPDATE MODE
    # ===========================================================
    elseif ($update) {
        if (-not (Test-Path $venvPath)) {
            throw "venv-cli not found. Run with --install first."
        }

        Write-Host "🔄 Updating Orion CLI installation..." -ForegroundColor Cyan
        & $pythonExe -m pip install --upgrade pip
        & $pythonExe -m pip install -e $cliPath
        Write-Host "✅ Orion CLI updated successfully." -ForegroundColor Green
    }

    # ===========================================================
    # UNINSTALL MODE
    # ===========================================================
    elseif ($uninstall) {
        Write-Host "🧹 Uninstalling Orion CLI..." -ForegroundColor Yellow

        # Remove alias
        if (Test-Path $profilePath) {
            (Get-Content $profilePath) |
                Where-Object { $_ -notmatch "orion-cli" } |
                Set-Content $profilePath
            Write-Host "🧽 Removed alias from PowerShell profile." -ForegroundColor Green
        }

        # Remove venv
        if (Test-Path $venvPath) {
            Remove-Item -Recurse -Force $venvPath
            Write-Host "🗑️  Deleted venv-cli directory." -ForegroundColor Green
        } else {
            Write-Host "ℹ️  venv-cli not found — nothing to delete." -ForegroundColor Yellow
        }

        Write-Host "`n✅ Orion CLI successfully uninstalled." -ForegroundColor Green
    }

    Write-Host "`n🪵 Log saved to: $logFile" -ForegroundColor DarkGray
}
catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Check the log for details: $logFile" -ForegroundColor Yellow
}
finally {
    # Stop transcript safely if it was started
    try {
        if ($global:transcribing) {
            Stop-Transcript | Out-Null
        }
    } catch {
        # ignore if transcript already stopped
    }
}