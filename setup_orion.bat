@echo off
SETLOCAL ENABLEEXTENSIONS

echo.
echo [Orion Installer] Setting up your environment...
echo.

:: Create venv if not exists
if not exist venv-orion (
    python -m venv venv-orion
)

:: Install dependencies
venv-orion\Scripts\pip install --upgrade pip
venv-orion\Scripts\pip install -r requirements.txt

:: === Pre-download embedding model for Orion LTM ===
echo.
echo [Orion Installer] Pre-downloading embedding model (all-MiniLM-L6-v2)...
venv-orion\Scripts\python.exe -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

:: Set environment variables
setx ORION_CHROMA_DB "C:\Orion\text-generation-webui\user_data\chroma_db"
setx ORION_PERSONA_COLLECTION "orion_persona"
setx ORION_LTM_COLLECTION "orion_episodic_sent_ltm"
setx ORION_EMBED_MODEL "user_data/models/embeddings/all-MiniLM-L6-v2"

echo.
echo [✅] Environment variables have been set.
echo [ℹ️] You may need to restart your terminal or system for changes to take effect.
pause
