@echo off
REM ============================
REM Orion Startup Script (venv version)
REM ============================

REM Set paths
set "TGWUI_DIR=C:\Orion\text-generation-webui"
set PYTHON=%TGWUI_DIR%\venv-orion\Scripts\python.exe
set ORION_EMBED_MODEL=all-mpnet-base-v2
set "MODEL_NAME=openhermes-2.5-mistral-7b.Q5_K_M.gguf"
set "MODEL_PATH=%TGWUI_DIR%\user_data\models\%MODEL_NAME%"

REM Activate venv-orion environment
CALL "%TGWUI_DIR%\venv-orion\Scripts\activate.bat"

REM Check model exists before launching
IF NOT EXIST "%MODEL_PATH%" (
    echo [ERROR] Model file not found at:
    echo %MODEL_PATH%
    pause
    exit /b 1
)

echo [INFO] Embedding model set to: %ORION_EMBED_MODEL%

REM Launch TGWUI with Orion LTM extension and model autoload
call "%PYTHON%" server.py ^
 --model-dir "%TGWUI_DIR%\user_data\models" ^
 --model "%MODEL_NAME%" ^
 --loader llama ^
 --extensions orion_ltm

pause
