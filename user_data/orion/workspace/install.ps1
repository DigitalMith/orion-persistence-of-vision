# install-tone.ps1
# Setup script for tone classification using quesmed/tone

# Optional: create virtual environment
$venvPath = "venv-tone"
if (-Not (Test-Path $venvPath)) {
  python -m venv $venvPath
}

# Activate virtual environment
& "$venvPath\Scripts\Activate.ps1"

# Pin versions (optional for consistency)
$requirements = @"
transformers==4.35.2
torch==2.1.2
"@
$requirements | Out-File -Encoding ASCII -FilePath ".\requirements-tone.txt"

# Install dependencies
$testScript = @"
from transformers import pipeline
clf = pipeline("text-classification", model="quesmed/tone")
print(clf("Why is everything always on fire when a user opens PowerShell?"))
"@

python -c $testScript

Write-Host "`n✅ Tone model setup complete. Virtual env: $venvPath" -ForegroundColor Green


Write-Host "`n📘 Applying Orion chat-log patch..." -ForegroundColor Cyan

$patchScript = @"
import re
from pathlib import Path

PATCH_HEADER = "# ORION_CHATLOG_PATCH"

REPLACEMENT_BLOCK = f"""{PATCH_HEADER}
import json
from pathlib import Path

def get_history_file_path(unique_id, character, mode):
    if mode == 'instruct':
        p = Path(f'user_data/logs/instruct/{{unique_id}}.json')
    else:
        p = Path(f'user_data/logs/chat/{{character}}/{{unique_id}}.json')
    return p

def save_history(history, unique_id, character, mode):
    p = get_history_file_path(unique_id, character, mode)
    p.parent.mkdir(parents=True, exist_ok=True)

    normalized = []
    for msg in history:
        role = msg.get("role")
        content = msg.get("content")
        ts = msg.get("timestamp") or ""
        entry = {
            "timestamp": ts,
            "user": content if role == "user" else "",
            "orion": content if role != "user" else "",
            "mode": mode,
            "character": character,
        }
        normalized.append(entry)

    with open(p, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=4, ensure_ascii=False)
"""

def apply_patch():
    chat_py = Path("modules/chat.py")
    if not chat_py.exists():
        print("❌ Cannot find modules/chat.py")
        return

    text = chat_py.read_text(encoding="utf-8")

    if PATCH_HEADER in text:
        print("✔ Patch already applied. Nothing to do.")
        return

    new_text = re.sub(
        r"def get_history_file_path[\\s\\S]*?def save_history[\\s\\S]*?\n\n",
        REPLACEMENT_BLOCK + "\n\n",
        text,
        flags=re.MULTILINE,
    )

    chat_py.write_text(new_text, encoding="utf-8")
    print("✔ Orion chat-log format patch applied successfully!")

if __name__ == "__main__":
    apply_patch()
"@

# Write patch file
$patchFile = "orion_chatlog_patch.py"
$patchScript | Out-File -Encoding UTF8 -FilePath $patchFile

# Execute patch
python $patchFile
Remove-Item $patchFile -Force

Write-Host "✅ Orion chat-log patch complete." -ForegroundColor Green