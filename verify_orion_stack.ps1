# Orion Stack Verifier — v3.3.0 Stable
# Uncle Aión’s post-party security system
# --------------------------------------------------------
# Checks that all pinned dependencies match Orion’s locked stack.
# Run inside the (venv-orion) PowerShell 7 session.

$Expected = @{
    "transformers"         = "4.39.3"
    "huggingface-hub"      = "0.22.2"
    "sentence-transformers"= "2.2.2"
    "chromadb"             = "0.4.15"
    "fastapi"              = "0.110.0"
    "starlette"            = "0.36.3"
    "gradio"               = "3.44.0"
    "pydantic"             = "1.10.13"
}

Write-Host "🧠 Verifying Orion dependency stack..." -ForegroundColor Cyan
$Errors = @()

foreach ($pkg in $Expected.Keys) {
    $installed = ((pip show $pkg 2>$null | Select-String "^Version:") -replace "Version:\s*", "").Trim()
    if (-not $installed) {
        $Errors += "❌ Missing package: $pkg (expected $($Expected[$pkg]))"
        continue
    }

    if ($installed -ne $Expected[$pkg]) {
        $Errors += "⚠️  Version mismatch: $pkg (installed $installed, expected $($Expected[$pkg]))"
    } else {
        Write-Host "✅ $pkg $installed" -ForegroundColor Green
    }
}

if ($Errors.Count -gt 0) {
    Write-Host "`n🚨 Orion stack integrity check failed:" -ForegroundColor Yellow
    $Errors | ForEach-Object { Write-Host $_ -ForegroundColor Red }
    Write-Host "`n💡 To repair:" -ForegroundColor Yellow
    Write-Host "pip install -r constraints.full.lock.txt --force-reinstall" -ForegroundColor White
    exit 1
} else {
    Write-Host "`n🌌 Orion stack verified clean. All systems go." -ForegroundColor Cyan
    exit 0
}
