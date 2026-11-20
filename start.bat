@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo  EKLAVYA - Learn. Practice. Master.
echo  Starting the local web application...
echo.

where docker >nul 2>&1
if errorlevel 1 goto :docker_missing

docker compose version >nul 2>&1
if errorlevel 1 goto :compose_missing

docker info >nul 2>&1
if errorlevel 1 goto :docker_stopped

if not exist ".env" (
    if not exist ".env.example" goto :env_missing
    copy /Y ".env.example" ".env" >nul
    echo Created .env from .env.example.
)

set "WEB_PORT=3000"
set "API_PORT=8000"
if defined FRONTEND_PORT set "WEB_PORT=%FRONTEND_PORT%"
if defined BACKEND_PORT set "API_PORT=%BACKEND_PORT%"
for /F "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /I "%%A"=="FRONTEND_PORT" set "WEB_PORT=%%B"
    if /I "%%A"=="BACKEND_PORT" set "API_PORT=%%B"
)

if /I "%~1"=="judge" goto :start_judge
if /I "%~1"=="--judge" goto :start_judge

echo Starting PostgreSQL, Redis, API, and web frontend...
docker compose up --build -d --wait --wait-timeout 180 db redis migrate backend frontend
if errorlevel 1 goto :start_failed
goto :ready

:start_judge
echo Starting the complete platform, including judge workers...
echo The scientific, Spark, and AI images may take several minutes to build.
docker compose --profile judge up --build -d --wait --wait-timeout 300
if errorlevel 1 goto :start_failed

:ready
echo.
echo EKLAVYA is ready at http://localhost:%WEB_PORT%
echo API health: http://localhost:%API_PORT%/api/v1/health/ready
echo.
start "" "http://localhost:%WEB_PORT%"
exit /b 0

:docker_missing
echo ERROR: Docker was not found. Install Docker Desktop, then run this file again.
goto :failed

:compose_missing
echo ERROR: Docker Compose v2 is unavailable. Update Docker Desktop and try again.
goto :failed

:docker_stopped
echo ERROR: Docker Desktop is not running. Start it, wait until it is ready, and try again.
goto :failed

:env_missing
echo ERROR: .env.example is missing, so the local environment cannot be initialized.
goto :failed

:start_failed
echo.
echo ERROR: EKLAVYA did not start successfully.
echo Run "docker compose logs --no-color" from this folder for details.

:failed
echo.
pause
exit /b 1
