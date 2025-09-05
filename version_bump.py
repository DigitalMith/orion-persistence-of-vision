import re
import yaml
from pathlib import Path
import shutil

# Paths
source_version_file = "version.py"
copy_targets = [
    "internal/orion/src/version.py",
    "internal/orion_perseverance_of_vision/version.py",
]
source_changelog_file = "CHANGELOG.md"
copy_targets = [
    "internal/orion/src/CHANGELOG.md",
    "internal/orion_perseverance_of_vision/CHANGELOG.md",
]
source_readme_file = "README.md"
copy_targets = [
    "internal/orion/src/README.md",
    "internal/orion_perseverance_of_vision/README.md",
]


# Copy the updated version.py to internal paths
for target in copy_targets:
    try:
        shutil.copy(source_version_file, target)
        print(f"[OK] Copied version.py to → {target}")
    except Exception as e:
        print(f"[ERROR] Failed to copy to {target}: {e}")


ROOT = Path(__file__).parent

# === Targets ================================================================

# version.py files (now includes ROOT/version.py)
VERSION_FILES = [
    ROOT / "version.py",  # NEW: root version.py
    ROOT / "internal" / "orion" / "src" / "orion" / "version.py",
    ROOT / "internal" / "orion_perseverance_of_vision" / "orion_perseverance_of_vision" / "version.py",
]

# pyproject.toml files (unchanged)
PYPROJECT_FILES = [
    ROOT / "internal" / "orion" / "pyproject.toml",
    ROOT / "internal" / "orion_perseverance_of_vision" / "pyproject.toml",
]

# README files (now includes ROOT/README.md and both internal READMEs)
README_FILES = [
    ROOT / "README.md",
    ROOT / "internal" / "orion" / "README.md",
    ROOT / "internal" / "orion_perseverance_of_vision" / "README.md",
]

CHANGELOG_FILES = [
    ROOT / "CHANGELOG.md",
    ROOT / "internal" / "orion" / "CHANGELOG.md",
    ROOT / "internal" / "orion_perseverance_of_vision" / "CHANGELOG.md",
]

# === Helpers ================================================================

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

def clean(text: str) -> str:
    """Strip non-printing control chars that break markdown."""
    return CONTROL_CHARS.sub("", text)

def load_version_data(yaml_path: Path) -> dict:
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# === Updaters ===============================================================

def update_version_py(file_path: Path, version: str):
    if not file_path.exists():
        print(f"⚠️  Skipping (missing): {file_path}")
        return
    text = file_path.read_text(encoding="utf-8")
    if "__VERSION__" in text:
        text = text.replace("__VERSION__", version)
    else:
        if re.search(r'__version__\s*=\s*["\'].*?["\']', text):
            text = re.sub(r'(__version__\s*=\s*["\']).*?(["\'])', lambda m: f'{m.group(1)}{version}{m.group(2)}', text)
        else:
            text = f'__version__ = "{version}"\n' + text
    file_path.write_text(text, encoding="utf-8")
    print(f"✔️ Updated version.py → {file_path}")

def update_pyproject(file_path: Path, version: str):
    if not file_path.exists():
        print(f"⚠️  Skipping (missing): {file_path}")
        return
    text = file_path.read_text(encoding="utf-8")
    if "__VERSION__" in text:
        text = text.replace("__VERSION__", version)
    else:
        # Replace `version = "..."` keeping original quotes
        text = re.sub(
            r'(^\s*version\s*=\s*["\'])(.*?)((["\']))',
            lambda m: f'{m.group(1)}{version}{m.group(3)}',
            text,
            flags=re.MULTILINE
        )
    file_path.write_text(text, encoding="utf-8")
    print(f"✔️ Updated pyproject.toml → {file_path}")

def update_readme(file_path: Path, version: str, badge: dict, description_lines: list[str]):
    if not file_path.exists():
        print(f"⚠️  Skipping (missing): {file_path}")
        return

    readme = clean(file_path.read_text(encoding="utf-8"))

    # Build the Version badge
    # badge = {"label": "version", "value": "3.0.1", "color": "purple"}
    label = badge.get("label", "version")
    value = badge.get("value", version)
    color = badge.get("color", "purple")
    badge_url = f"https://img.shields.io/badge/{label}-{value}-{color}"
    badge_md  = f"[![Version]({badge_url})]()"

    # 1) Replace explicit placeholder OR replace any existing Version badge line
    if "<!--VERSION_BADGE-->" in readme:
        readme = readme.replace("<!--VERSION_BADGE-->", badge_md)
    else:
        # Replace a whole line that begins with a Version badge
        replaced = re.sub(
            r'^[ \t]*\[\!\[Version\]\([^\)]*\)\]\([^\)]*\)[ \t]*\r?\n',
            badge_md + "\n",
            readme,
            flags=re.MULTILINE
        )
        if replaced == readme:
            # No existing badge found; insert just under the H1 title if possible
            lines = readme.splitlines()
            inserted = False
            for i, line in enumerate(lines):
                if line.lstrip().startswith("# "):
                    insert_at = min(i + 2, len(lines))
                    lines.insert(insert_at, badge_md)
                    inserted = True
                    break
            if not inserted:
                lines.insert(0, badge_md)
            readme = "\n".join(lines)
        else:
            readme = replaced

    # 2) Replace __VERSION__ tokens everywhere
    readme = readme.replace("__VERSION__", version)

    # 3) Build and insert What's New block
    whats_new_block = "## 🆕 What’s New in " + version + "\n\n" + "\n".join(
        f"* {line}" for line in description_lines
    ) + "\n"

    if "<!--WHATS_NEW_START-->" in readme and "<!--WHATS_NEW_END-->" in readme:
        readme = re.sub(
            r'<!--WHATS_NEW_START-->.*?<!--WHATS_NEW_END-->',
            f'<!--WHATS_NEW_START-->\n{whats_new_block}<!--WHATS_NEW_END-->',
            readme,
            flags=re.DOTALL
        )
    else:
        # Fallback: replace any existing What's New section, or append at end
        if re.search(r'^## 🆕 What’s New in ', readme, flags=re.MULTILINE):
            readme = re.sub(r'## 🆕 What’s New in .*?(?=\n##|\Z)', whats_new_block, readme, flags=re.DOTALL)
        else:
            readme = readme.rstrip() + "\n\n" + whats_new_block

    file_path.write_text(readme, encoding="utf-8")
    print(f"✔️ Updated README.md → {file_path}")

def update_changelog(file_path: Path, version: str, sections: dict[str, list[str]]):
    if not file_path.exists():
        print(f"⚠️  Skipping (missing): {file_path}")
        return

    text = clean(file_path.read_text(encoding="utf-8"))

    changelog_entry = [f"## [{version}]"]
    for header, lines in sections.items():
        if lines:
            changelog_entry.append(f"\n### {header}")
            changelog_entry.extend(f"* {line}" for line in lines)

    changelog_block = "\n".join(changelog_entry) + "\n\n---\n\n"

    # Inject after <!--CHANGELOG_START-->
    if "<!--CHANGELOG_START-->" in text:
        text = re.sub(
            r"(<!--CHANGELOG_START-->\n)",
            r"\1" + changelog_block,
            text,
            count=1
        )
    else:
        text = changelog_block + text

    file_path.write_text(text, encoding="utf-8")
    print(f"✔️ Updated CHANGELOG.md → {file_path}")

# === Main ===================================================================

def main():
    data = load_version_data(ROOT / "version.yaml")
    version = data["version"]
    badge = data.get("badge", {"label": "version", "value": version, "color": "purple"})
    description = data.get("description", [])
    whats_new = data.get("whats_new", [])
    improvements = data.get("improvements", [])
    fixes = data.get("fixes", [])
    
    sections = {
        "What's New": whats_new,
        "Improvements": improvements,
        "Fixes": fixes,
    }

    for p in VERSION_FILES:
        update_version_py(p, version)

    for p in PYPROJECT_FILES:
        update_pyproject(p, version)

    for p in README_FILES:
        update_readme(p, version, badge, description)
        
    for p in CHANGELOG_FILES:
        update_changelog(p, version, sections)  # Function to be created

    print(f"\n🎉 Bump complete → v{version}")

if __name__ == "__main__":
    main()
