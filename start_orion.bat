@echo off
REM ==========================================
REM Orion Startup Script (venv version)
REM ==========================================

:: Set working directory to Orion root
cd /d C:\Orion\text-generation-webui
:: Enable logging for LTM injections
set ORION_LTM_DEBUG=1
:: Optional: force embedding model consistency
set ORION_EMBED_MODEL=sentence-transformers/all-mpnet-base-v2

REM --- Set Core Paths ---
set "TGWUI_DIR=C:\Orion\text-generation-webui"
set "PYTHON=%TGWUI_DIR%\venv-orion\Scripts\python.exe"
set "MODEL_NAME=openhermes-2.5-mistral-7b.Q5_K_M.gguf"
set "MODEL_PATH=%TGWUI_DIR%\user_data\models\%MODEL_NAME%"

REM --- Activate venv ---
CALL "%TGWUI_DIR%\venv-orion\Scripts\activate.bat"

REM --- Check model existence ---
IF NOT EXIST "%MODEL_PATH%" (
    echo [ERROR] Model not found:
    echo   %MODEL_PATH%
    pause
    exit /b 1
)

REM --- Orion LTM Environment Variables ---
set ORION_EMBED_MODEL=all-mpnet-base-v2
set ORION_LTM_DEBUG=1
set ORION_LTM_TOPK_PERSONA=5
set ORION_LTM_TOPK_EPISODIC=10

REM --- Optional: Set prompt template ---
REM Override instruction template if needed (e.g., chatml, alpaca, etc.)
REM You can set this via --chat-template if supported, or ensure your prompt format matches
REM For now, rely on script.py using <|im_start|> blocks

echo [INFO] Launching Orion...
echo [INFO] Embedding model: %ORION_EMBED_MODEL%
echo [INFO] Model file: %MODEL_NAME%
echo [INFO] Extensions: orion_ltm

REM --- Launch TGWUI with Orion LTM extension ---
call "%PYTHON%" server.py ^
 --model-dir "%TGWUI_DIR%\user_data\models" ^
 --model "%MODEL_NAME%" ^
 --loader llama ^
 --extensions orion_ltm ^
 --listen

REM --- Start Orion autonomous ingestion loop in a new window ---
start "OrionIngest" cmd /k "%PYTHON% -m cli.orion_ingest_loop"

pause