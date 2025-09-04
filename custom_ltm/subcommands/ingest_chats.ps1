param(
  [string]$ChatDir = "C:\Orion\memory\chat",
  [string]$ModuleDir = "C:\Orion\text-generation-webui\custom_ltm",
  [string]$Py = "C:\Orion\text-generation-webui\installer_files\env\python.exe"
)

$files = Get-ChildItem -LiteralPath $ChatDir -Filter *.json -File | Select-Object -Expand FullName
if (-not $files) { Write-Host "No chat JSON found in $ChatDir"; exit 0 }

$code = @"
import sys, os, json, uuid
sys.path.insert(0, r'$ModuleDir')
from orion_ltm_integration import initialize_chromadb_for_ltm

persona, episodic = initialize_chromadb_for_ltm()

def load_msgs(fp):
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict) and 'messages' in data:
        return data['messages']
    if isinstance(data, list):
        return data
    return []

added = 0
for fp in r'''<<<FILES>>>'''.split('|'):
    fp = fp.strip()
    if not fp: continue
    msgs = load_msgs(fp)
    docs, metas, ids = [], [], []
    for m in msgs:
        role = m.get('role') or m.get('author') or 'user'
        content = m.get('content') or m.get('text') or ''
        if not content: continue
        did = str(uuid.uuid4())
        docs.append(f"[{role}] {content}")
        metas.append({'role': role, 'source': os.path.basename(fp)})
        ids.append(did)
    if docs:
        episodic.add(documents=docs, metadatas=metas, ids=ids)
        added += len(docs)

print("Ingested docs:", added)
print("Counts → Persona:", persona.count(), "Episodic:", episodic.count())
"@

$joined = ($files -join '|').Replace('\','\\')
$code = $code.Replace('<<<FILES>>>', $joined)

& $Py -c $code
