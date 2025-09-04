# custom_ltm\Run_Research.ps1 (clean, self-contained)
$ProjectRoot = "C:\Orion\text-generation-webui"
$Policy      = "$ProjectRoot\orion_policy.yaml"
$Py          = "$ProjectRoot\installer_files\env\python.exe"  # or your venv python

# Always run from project root so imports like 'custom_ltm' work
Push-Location $ProjectRoot

# ---- Prompts ----
$Url   = Read-Host "Seed URL (e.g. https://docs.python.org/3/)"
$Topic = Read-Host "Topic tag (e.g. python-docs)"
$Depth = Read-Host "Depth (default 1)"
$Pages = Read-Host "Pages cap (default 6)"

$depthVal = if ($Depth) { $Depth } else { 1 }
$pagesVal = if ($Pages) { $Pages } else { 6 }

function QuoteIfNeeded([string]$s) {
  if ($s -match '\s') { return "'$s'" } else { return $s }
}
$topicShown = QuoteIfNeeded $Topic

<# # Show the normalized chat command a user could paste into Orion
Write-Host ("Use '/research {0} {1} --depth {2} --pages {3}'" -f $Url, $topicShown, $depthVal, $pagesVal)
 #>
# ---- Python code as a here-string (UTF-8, no BOM) ----
$code = @"
import sys
sys.path.insert(0, r"$ProjectRoot")

# Echo the normalized /research command inside Python too (optional)
print("Use '/research {url} {topic} --depth {depth} --pages {pages}'".format(
    url=r"$Url", topic=r"$Topic", depth=int($depthVal), pages=int($pagesVal)
))

import custom_ltm.orion_net_ingest as oni

# Try to find an OrionMemory-like class dynamically
OrionMemory = None
mem_mod = None
try:
    import orion_mem as om
    OrionMemory = getattr(om, "OrionMemory", None)
    mem_mod = "orion_mem"
except Exception:
    pass

if OrionMemory is None:
    try:
        import custom_ltm.orion_ltm_integration as omi
        for name in ("OrionMemory", "Memory", "OrionLTM", "OrionMemoryClient"):
            OrionMemory = getattr(omi, name, None)
            if OrionMemory:
                mem_mod = f"custom_ltm.orion_ltm_integration:{name}"
                break
    except Exception:
        pass

print(f"[mem] provider:", mem_mod if mem_mod else "NONE (dry-run)")

ing = oni.OrionNetIngest(r"$Policy")

store_cb = None
if OrionMemory is not None:
    try:
        mem = OrionMemory(chroma_url="http://127.0.0.1:8000", collection="orion")
        store_cb = oni.orion_store_callback_factory(mem)
    except Exception as e:
        print("[mem] init failed:", e)

res = ing.ingest_web(
    url=r"$Url",
    topic=r"$Topic",
    crawl_depth=int($depthVal),
    crawl_pages_cap=int($pagesVal),
    store_callback=store_cb
)

if store_cb is None:
    print("[warn] No OrionMemory class found; ran in DRY-RUN (nothing stored).")
print(res)
"@

# Write temp file WITHOUT BOM (important for stable imports)
$Temp = Join-Path $env:TEMP "orion_research_tmp.py"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($Temp, $code, $utf8NoBom)

# Execute and clean up
& $Py $Temp
Remove-Item $Temp -Force -ErrorAction SilentlyContinue

Pop-Location
