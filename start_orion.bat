@echo off
REM ==========================================
REM Orion Startup Script (venv version)
REM ==========================================

REM --- Set Core Paths ---
set TGWUI_DIR=C:\Orion\text-generation-webui
set PYTHON=%TGWUI_DIR%\venv-orion\Scripts\python.exe
set MODEL_NAME=openhermes-2.5-mistral-7b.Q5_K_M.gguf
set MODEL_PATH=%TGWUI_DIR%\user_data\models\%MODEL_NAME%

REM --- Network/Gradio hardening ---
set NO_PROXY=127.0.0.1,localhost
set no_proxy=127.0.0.1,localhost
set GRADIO_BROWSER=none

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

REM --- Toggle share link if local still fails (0=local, 1=share) ---
IF "%ORION_SHARE%"=="" set ORION_SHARE=0

echo [INFO] Launching Orion...
echo [INFO] Embedding model: %ORION_EMBED_MODEL%
echo [INFO] Model file: %MODEL_NAME%
REM echo [INFO] Extensions: orion_ltm
echo [INFO] Bind: 127.0.0.1:7860 (NO_PROXY=%NO_PROXY%)

REM --- Build common args (NO QUOTES; paths have no spaces) ---
set COMMON_ARGS=--model-dir %TGWUI_DIR%\user_data\models --model %MODEL_NAME% --loader llama --extensions orion_ltm --listen --listen-host 127.0.0.1 --listen-port 7860

REM Optional: inspect the final args
echo [DEBUG] python server.py %COMMON_ARGS%

if "%ORION_SHARE%"=="1" (
  echo [INFO] Using Gradio share link (ORION_SHARE=1)
  call "%PYTHON%" server.py %COMMON_ARGS% --share
) else (
  call "%PYTHON%" server.py %COMMON_ARGS%
)

pause
