<#
────────────────────────────────────────────────────────────
🧠 Orion Stack Verifier — v3.6.0 Lockdown Edition
By Uncle Aión  |  Orion AI Ecosystem
────────────────────────────────────────────────────────────
Checks and optionally repairs Orion’s pinned dependency stack.
Usage:
    ./verify_orion_stack.ps1
    ./verify_orion_stack.ps1 --repair
────────────────────────────────────────────────────────────
#>

# Explicit imports for minimal shells
Import-Module Microsoft.PowerShell.Management -ErrorAction SilentlyContinue
Import-Module Microsoft.PowerShell.Utility -ErrorAction SilentlyContinue

param(
    [switch]$repair,
    [switch]$refresh
)
# 123
# -----------------------------------------------------------
# Dynamic Expected Versions Loader — Orion Lockfile Mode
# -----------------------------------------------------------
$lockFile = "C:\Orion\text-generation-webui\constraints.full.lock.txt"

if (Test-Path $lockFile) {
    Write-Host "🔍 Loading expected package versions from lock file..." -ForegroundColor Cyan
    $ExpectedTable = @{}
    Get-Content $lockFile | Where-Object {$_ -match '^[A-Za-z0-9._-]+=='} | ForEach-Object {
        if ($_ -match '^(?<pkg>[A-Za-z0-9._-]+)==(?<ver>[\d.]+)$') {
            $ExpectedTable[$matches['pkg'].ToLower()] = $matches['ver']
        }
    }

    if ($ExpectedTable.Count -eq 0) {
        Write-Host "⚠️  Lock file is empty or unreadable — no expected versions loaded." -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Lock file not found at $lockFile" -ForegroundColor Yellow
    Write-Host "Creating new lock file from current environment..." -ForegroundColor Cyan
    pip freeze | Out-File $lockFile -Encoding utf8
    $ExpectedTable = @{}
    Get-Content $lockFile | ForEach-Object {
        if ($_ -match "^(?<pkg>[A-Za-z0-9\-\_]+)==(?<ver>[\d\.]+)$") {
            $ExpectedTable[$matches['pkg'].ToLower()] = $matches['ver']
        }
    }
    Write-Host "✅  New lock file generated successfully." -ForegroundColor Green
}

$Errors = @()

# -----------------------------------------------------------
# Handle refresh option
# -----------------------------------------------------------
if ($refresh) {
    Write-Host "`n🧾 Refreshing lock file from current environment..." -ForegroundColor Cyan
    pip freeze | Out-File "constraints.full.lock.txt" -Encoding utf8
    exit 0
}

# -----------------------------------------------------------
# Dependency verification loop
# -----------------------------------------------------------
foreach ($pkg in $ExpectedTable.Keys) {
    $installed = ((pip show $pkg 2>$null | Select-String "^Version:") -replace "Version:\s*", "").Trim()

    if (-not $installed) {
        $Errors += "❌ Missing package: $pkg (expected $($ExpectedTable[$pkg]))"
        continue
    }

    if ($installed -ne $ExpectedTable[$pkg]) {
        $Errors += "⚠️  Version mismatch: $pkg (installed $installed, expected $($ExpectedTable[$pkg]))"
    } else {
        Write-Host "✅ $pkg $installed" -ForegroundColor Green
    }
}

# -----------------------------------------------------------
# 📊 Orion Stack Summary — Safe Scope
# -----------------------------------------------------------
Write-Host "`n📊 Orion Stack Summary" -ForegroundColor Cyan
Write-Host "───────────────────────────────────────────────"

foreach ($pkg in $ExpectedTable.Keys) {
    $expected  = $ExpectedTable[$pkg]
    $installed = ((pip show $pkg 2>$null | Select-String "^Version:") -replace "Version:\s*", "").Trim()

    if (-not $installed) {
        Write-Host ("❌ {0,-25} MISSING (expected {1})" -f $pkg, $expected) -ForegroundColor Red
    }
    elseif ($installed -ne $expected) {
        Write-Host ("⚠️  {0,-25} {1,-10} → expected {2}" -f $pkg, $installed, $expected) -ForegroundColor Yellow
    }
    else {
        Write-Host ("✅ {0,-25} {1}" -f $pkg, $installed) -ForegroundColor Green
    }
}
Write-Host "───────────────────────────────────────────────"

# -----------------------------------------------------------
# Check for unpinned packages (installed but not in lockfile)
# -----------------------------------------------------------
$installedPackages = & pip list --format=freeze | ForEach-Object {
    if ($_ -match '^(?<pkg>[A-Za-z0-9._-]+)==(?<ver>[\d.]+)$') {
        [PSCustomObject]@{
            Package = $matches['pkg'].ToLower()
            Version = $matches['ver']
        }
    }
}

$unpinned = $installedPackages | Where-Object { -not $ExpectedTable.ContainsKey($_.Package) }

if ($unpinned.Count -gt 0) {
    Write-Host "`n⚠️  The following packages are installed but not pinned in constraints.full.lock.txt:" -ForegroundColor Yellow
    foreach ($pkg in $unpinned) {
        Write-Host ("   • {0,-25} {1}" -f $pkg.Package, $pkg.Version) -ForegroundColor DarkGray
    }
} else {
    Write-Host "`n✅ No unexpected packages detected." -ForegroundColor Green
}

# -----------------------------------------------------------
# Handle repair option
# -----------------------------------------------------------
if ($Errors.Count -gt 0) {
    Write-Host "`n🚨 Orion stack integrity check failed:" -ForegroundColor Yellow
    $Errors | ForEach-Object { Write-Host $_ -ForegroundColor Red }

    if (-not $repair) {
        Write-Host "`n💡 Run again with '--repair' to auto-correct these mismatches." -ForegroundColor Yellow
        exit 1
    } else {
        Write-Host "`n🧰 Performing repair using constraints.full.lock.txt..." -ForegroundColor Cyan
        pip install -r constraints.full.lock.txt --force-reinstall
    }
} else {
    Write-Host "`n🌌 Orion stack verified clean. All systems go." -ForegroundColor Cyan
}

# -----------------------------------------------------------
# 👻 Gradio Ghost Watchdog — verifies Base.set() signature
# -----------------------------------------------------------
Write-Host "`n👻 Scanning for Gradio ghosts..." -ForegroundColor Cyan

try {
    $gradioPath = (python -c "import gradio; print(gradio.__file__)")
    $code = python -c "from gradio.themes import Base; import inspect; print('code_background_fill_dark' in inspect.getsource(Base.set))"
    if ($code -match "True") {
        Write-Host "✅  Gradio Base.set() signature verified clean." -ForegroundColor Green
    } else {
        Write-Host "⚠️  Gradio Base.set() missing expected argument 'code_background_fill_dark'." -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌  Gradio verification failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host " "
exit 0


Get-ChildItem -Path "C:\Orion" -Recurse -File Select-String -Pattern "chroma_db" Out-GridView Select-Object Path, LineNumber, Line
