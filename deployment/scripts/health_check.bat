@echo off
REM Comprehensive System Health Check Script
REM Author: System Architecture Team
REM Date: 2025-08-12

setlocal enabledelayedexpansion

echo.
echo 🏥 AI-Powered Multi-Domain News Crawler - Health Check
echo =====================================================
echo.

set "HEALTHY_COUNT=0"
set "TOTAL_SERVICES=4"
set "CRITICAL_FAILURE=0"

REM Check if docker-compose.yml exists
if not exist "docker-compose.yml" (
    echo ❌ ERROR: docker-compose.yml not found
    echo    Please run from deployment directory
    exit /b 1
)

echo 📊 Story 1.1 - Database Schema Foundation
echo ------------------------------------------

REM PostgreSQL Health Check
docker ps --filter "name=crawler_postgres" --format "{{.Status}}" | findstr "Up" >nul 2>&1
if %errorlevel%==0 (
    echo ✅ PostgreSQL Container: Running
    
    REM Test database connection
    docker exec crawler_postgres pg_isready -U crawler_user -d crawler_db >nul 2>&1
    if %errorlevel%==0 (
        echo ✅ PostgreSQL Connection: Healthy
        set /a HEALTHY_COUNT+=1
    ) else (
        echo ❌ PostgreSQL Connection: Failed
        set "CRITICAL_FAILURE=1"
    )
) else (
    echo ❌ PostgreSQL Container: Down
    set "CRITICAL_FAILURE=1"
)

echo.
echo 🤖 Story 1.2 - GWEN-3 Model Deployment  
echo ----------------------------------------

REM Ollama Health Check
docker ps --filter "name=crawler_ollama" --format "{{.Status}}" | findstr "Up" >nul 2>&1
if %errorlevel%==0 (
    echo ✅ Ollama Container: Running
    
    REM Test Ollama API
    curl -s -f "http://localhost:11434/api/tags" >nul 2>&1
    if %errorlevel%==0 (
        echo ✅ Ollama API: Responding
        
        REM Check if qwen2.5:3b model exists
        docker exec crawler_ollama ollama list | findstr "qwen2.5:3b" >nul 2>&1
        if %errorlevel%==0 (
            echo ✅ GWEN-3 Model (qwen2.5:3b): Available
            set /a HEALTHY_COUNT+=1
        ) else (
            echo ⚠️  GWEN-3 Model: Not downloaded
            echo    Run: docker exec crawler_ollama ollama pull qwen2.5:3b
        )
    ) else (
        echo ❌ Ollama API: Not responding
        set "CRITICAL_FAILURE=1"
    )
) else (
    echo ❌ Ollama Container: Down
    set "CRITICAL_FAILURE=1"
)

echo.
echo 🔧 Story 1.3 - Domain Analysis Worker
echo -------------------------------------

REM Redis Health Check
docker ps --filter "name=crawler_redis" --format "{{.Status}}" | findstr "Up" >nul 2>&1
if %errorlevel%==0 (
    echo ✅ Redis Container: Running
    
    REM Test Redis connection
    docker exec crawler_redis redis-cli ping | findstr "PONG" >nul 2>&1
    if %errorlevel%==0 (
        echo ✅ Redis Connection: Healthy
        set /a HEALTHY_COUNT+=1
    ) else (
        echo ❌ Redis Connection: Failed
        set "CRITICAL_FAILURE=1"
    )
) else (
    echo ❌ Redis Container: Down
    set "CRITICAL_FAILURE=1"
)

REM Analysis Worker Health Check
docker ps --filter "name=crawler_analysis_worker" --format "{{.Status}}" | findstr "Up" >nul 2>&1
if %errorlevel%==0 (
    echo ✅ Analysis Worker Container: Running
    
    REM Test Analysis Worker API
    curl -s -f "http://localhost:8082/health" >nul 2>&1
    if %errorlevel%==0 (
        echo ✅ Analysis Worker API: Healthy
        set /a HEALTHY_COUNT+=1
    ) else (
        echo ❌ Analysis Worker API: Not responding
        set "CRITICAL_FAILURE=1"
    )
) else (
    echo ❌ Analysis Worker Container: Down
    set "CRITICAL_FAILURE=1"
)

echo.
echo 🌐 Service Endpoints
echo -------------------
echo 📊 Analysis Worker API: http://localhost:8082/health
echo 🤖 Ollama Model API: http://localhost:11434/api/tags
echo 📊 pgAdmin (optional): http://localhost:8080
echo 🔄 Redis Commander (dev): http://localhost:8081

echo.
echo 📋 System Status Summary
echo =======================

if %HEALTHY_COUNT% equ %TOTAL_SERVICES% (
    if %CRITICAL_FAILURE% equ 0 (
        echo 🎉 ALL SYSTEMS HEALTHY (%HEALTHY_COUNT%/%TOTAL_SERVICES%)
        echo    Vietnamese content analysis system is ready!
        echo.
        echo 🧪 Test the system:
        echo    curl -X POST "http://localhost:8082/trigger/5ca6f1b9-ee1a-4df7-89d7-e3a3d04e4faf"
        exit /b 0
    )
)

if %HEALTHY_COUNT% gtr 0 (
    echo ⚠️  PARTIAL SYSTEM HEALTH (%HEALTHY_COUNT%/%TOTAL_SERVICES%)
    echo    Some services are healthy but system is degraded
) else (
    echo 💥 SYSTEM DOWN (0/%TOTAL_SERVICES%)
    echo    Critical failure - no services responding
)

echo.
echo 🔧 Troubleshooting Steps:
echo 1. deploy.bat stop
echo 2. deploy.bat start  
echo 3. Wait 2-3 minutes for services to initialize
echo 4. deploy.bat health
echo.
echo 📋 Detailed logs: deploy.bat logs
echo 📋 Individual service logs: docker-compose logs [service-name]

exit /b 1