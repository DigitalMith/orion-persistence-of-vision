# C:\Orion\run_orion_ingest.ps1

# --- config -------------------------------------------------------------------
$TGWUI_DIR   = "C:\Orion\text-generation-webui"
$VENV_DIR    = "C:\Orion\text-generation-webui\venv-orion"                           # <— your venv root
$PYTHON      = Join-Path $VENV_DIR "Scripts\python.exe"        # use venv python
$ORION_MODEL = "C:\Orion\text-generation-webui\user_data\models\openhermes-2.5-mistral-7b.Q5_K_M.gguf"
$NEMO_MODEL  = "C:\Orion\text-generation-webui\user_data\models\nomic-embed-text-v2-moe.Q6_K.gguf"  # replace with your Nemo chat model
$ORION_PORT  = 5001
$NEMO_PORT   = 5002

$INGEST_SCRIPT   = Join-Path $TGWUI_DIR "orion_cli\scripts\ingest_master.py"
$NORMALIZED_LOGS = "C:\Orion\data\normalized_logs"

# --- sanity checks ------------------------------------------------------------
if (!(Test-Path $PYTHON)) { Write-Host "Missing venv python: $PYTHON" -Foreground Red; exit 1 }
if (!(Test-Path $TGWUI_DIR)) { Write-Host "Missing TGWUI dir: $TGWUI_DIR" -Foreground Red; exit 1 }

# --- helpers ------------------------------------------------------------------
function Start-Server {
    param([string]$Title,[string]$Dir,[string]$Cmd)
    Start-Process powershell.exe -ArgumentList @(
        "-NoExit","-ExecutionPolicy","Bypass","-Command",
        "Set-Location `"$Dir`"; $Cmd"
    ) -WindowStyle Normal
    Write-Host "Launched $Title"
}

function Wait-Ready {
    param([string]$Url,[int]$TimeoutSec=120)
    $start=Get-Date
    while((Get-Date)-$start -lt [TimeSpan]::FromSeconds($TimeoutSec)){
        try{ $r=Invoke-WebRequest -UseBasicParsing -Uri $Url -Method GET -TimeoutSec 3
             if($r.StatusCode -ge 200 -and $r.StatusCode -lt 500){ return $true } }
        catch{ Start-Sleep -Milliseconds 800 }
    }
    return $false
}

# --- launch Orion (5001) ------------------------------------------------------
$orionCmd = "& `"$PYTHON`" server.py --api --listen --port $ORION_PORT --model `"$ORION_MODEL`""
Start-Server -Title "Orion@$ORION_PORT" -Dir $TGWUI_DIR -Cmd $orionCmd

# --- launch Nemo annotator (5002) ---------------------------------------------
# If your annotator is another TGWUI/OpenAI-compatible server:
$nemoCmd  = "& `"$PYTHON`" server.py --api --listen --port $NEMO_PORT --model `"$NEMO_MODEL`""
Start-Server -Title "Nemo@$NEMO_PORT" -Dir $TGWUI_DIR -Cmd $nemoCmd

# --- wait for both APIs -------------------------------------------------------
Write-Host "Waiting for Orion API…"
if(-not (Wait-Ready "http://127.0.0.1:$ORION_PORT/v1/models")){ Write-Host "Orion not ready." -Foreground Red }
Write-Host "Waiting for Nemo API…"
if(-not (Wait-Ready "http://127.0.0.1:$NEMO_PORT/v1/models")){ Write-Host "Nemo not ready." -Foreground Red }

# --- kick off ingest (new window) ---------------------------------------------
# Using Nemo as annotator:
$ingestArgs = "`"$INGEST_SCRIPT`" --source `"$NORMALIZED_LOGS`" --annotator nemo"
# Or, use Orion to annotate:
# $ingestArgs = "`"$TGWUI_DIR\orion_cli\scripts\annotate_with_orion.py`" --source `"$NORMALIZED_LOGS`""

$ingestCmd = "& `"$PYTHON`" $ingestArgs"
Start-Server -Title "CNS Ingest" -Dir $TGWUI_DIR -Cmd $ingestCmd

Write-Host "All processes launched."
