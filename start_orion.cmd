@echo off
setlocal enableextensions enabledelayedexpansion

REM ====== CONFIG ======
set "TGWUI_DIR=C:\Orion\text-generation-webui"
set "VENV=%TGWUI_DIR%\venv-orion"
set "PYTHON=%VENV%\Scripts\python.exe"

REM Model under user_data\models\<folder>\<file>.gguf
set "MODEL_FOLDER=openhermes-2.5-mistral-7b"
set "MODEL_FILE=openhermes-2.5-mistral-7b.Q5_K_M.gguf"
set "MODEL_DIR=%TGWUI_DIR%\user_data\models"
set "MODEL_PATH=%MODEL_DIR%\%MODEL_FOLDER%\%MODEL_FILE%"

REM Mode: GPU or CPU (type: start_orion.cmd GPU   or   start_orion.cmd CPU)
set "MODE=%~1"
if /I "%MODE%"=="" set "MODE=GPU"

REM RAG / Chroma
set "ORION_EMBED_MODEL=sentence-transformers/all-mpnet-base-v2"
set "CHROMA_TELEMETRY_IMPLEMENTATION=none"
set "ORION_LTM_DEBUG=0"
set "ORION_LTM_TOPK_PERSONA=5"
set "ORION_LTM_TOPK_EPISODIC=10"

REM Noise filter
set "PYTHONWARNINGS=ignore::PendingDeprecationWarning"

REM Optional auth (set empty to disable)
set "GRADIO_AUTH="

echo [Orion] Activating venv...
call "%VENV%\Scripts\activate.bat" || (echo [ERROR] venv missing & pause & exit /b 1)

echo [Orion] Checking model path...
if not exist "%MODEL_PATH%" (
  echo [ERROR] Model not found:
  echo   "%MODEL_PATH%"
  echo Tip: Place the file at:
  echo   %MODEL_DIR%\%MODEL_FOLDER%\%MODEL_FILE%
  pause & exit /b 1
)

REM ==============================
REM  Orion: Launch TGWUI Server
REM ==============================
echo [INFO] Mode: %MODE%
echo [INFO] Model: %MODEL_FOLDER%\%MODEL_FILE%
echo [INFO] Embeddings: %ORION_EMBED_MODEL%

REM --- Build common arguments safely ---
set COMMON_ARGS=--listen
set COMMON_ARGS=%COMMON_ARGS% --listen-host 127.0.0.1
set COMMON_ARGS=%COMMON_ARGS% --listen-port 7862
set COMMON_ARGS=%COMMON_ARGS% --loader llama.cpp
set "MODEL_PATH=%MODEL_DIR%\%MODEL_FOLDER%\%MODEL_FILE%"
set "COMMON_ARGS=%COMMON_ARGS% --model-dir "%MODEL_DIR%""
set "COMMON_ARGS=%COMMON_ARGS% --model "%MODEL_PATH%""
set COMMON_ARGS=%COMMON_ARGS% --ctx-size 4096
set COMMON_ARGS=%COMMON_ARGS% --threads 8
set COMMON_ARGS=%COMMON_ARGS% --batch-size 256
set COMMON_ARGS=%COMMON_ARGS% --extensions orion_ltm
set COMMON_ARGS=%COMMON_ARGS% --old-colors

if not "%GRADIO_AUTH%"=="" (
  set COMMON_ARGS=%COMMON_ARGS% --gradio-auth %GRADIO_AUTH%
)

REM --- CPU vs GPU mode ---
if /I "%MODE%"=="CPU" (
  echo [INFO] Launching CPU safe profile...
  
  REM echo [DEBUG] Final launch command:
  REM echo %PYTHON% "%TGWUI_DIR%\server.py" %COMMON_ARGS% --gpu-layers 33
  REM pause
  
  "%PYTHON%" "%TGWUI_DIR%\server.py" %COMMON_ARGS% --gpu-layers 0 --no-mmap
) else (
  echo [INFO] Launching GPU fast profile...
  
  REM echo [DEBUG] Final launch command:
  REM echo %PYTHON% "%TGWUI_DIR%\server.py" %COMMON_ARGS% --gpu-layers 33
  REM pause
  
  "%PYTHON%" "%TGWUI_DIR%\server.py" %COMMON_ARGS% --gpu-layers 33
)

REM --- Error handling ---
if errorlevel 1 (
  echo [ERROR] Orion server failed to launch.
  pause
  exit /b 1
)