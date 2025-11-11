@echo off
REM ReSpeaker CLI Wrapper for Windows
REM Quick launcher for common commands

setlocal enabledelayedexpansion

if "%1"=="" (
    echo.
    echo ============================================================
    echo   ReSpeaker Sound Detection Service - Quick Launcher
    echo ============================================================
    echo.
    echo Usage: respeaker.bat [command]
    echo.
    echo Commands:
    echo   start         - Khoi dong service va monitor
    echo   status        - Xem trang thai hien tai
    echo   stats         - Xem thong ke
    echo   test-vad      - Test VAD/DOA
    echo   test-audio    - Test audio classification
    echo   test-led      - Test LED
    echo   record        - Ghi am vao file
    echo   api           - Chay REST API
    echo   help          - Xem tat ca commands
    echo.
    echo Examples:
    echo   respeaker.bat start
    echo   respeaker.bat status
    echo   respeaker.bat stats
    echo.
    exit /b 0
)

if "%1"=="start" (
    python cli.py start --monitor
    exit /b %errorlevel%
)

if "%1"=="status" (
    python cli.py status
    exit /b %errorlevel%
)

if "%1"=="stats" (
    python cli.py stats --duration 30
    exit /b %errorlevel%
)

if "%1"=="test-vad" (
    python cli.py test-vad --duration 20
    exit /b %errorlevel%
)

if "%1"=="test-audio" (
    python cli.py test-audio --duration 20
    exit /b %errorlevel%
)

if "%1"=="test-led" (
    python cli.py test-led --demo
    exit /b %errorlevel%
)

if "%1"=="record" (
    if "%2"=="" (
        set filename=recording.wav
    ) else (
        set filename=%2
    )
    python cli.py record !filename! --duration 5
    exit /b %errorlevel%
)

if "%1"=="api" (
    python api.py
    exit /b %errorlevel%
)

if "%1"=="help" (
    python cli.py --help
    exit /b %errorlevel%
)

REM Default: forward all arguments to cli.py
python cli.py %*
exit /b %errorlevel%
