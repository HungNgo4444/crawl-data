@echo off
REM Clean Deployment Commands for AI-Powered Multi-Domain News Crawler
REM Stories 1.1-1.3 Complete Container System
REM Author: System Architecture
REM Date: 2025-08-12

if "%1"=="" (
    echo ❌ Error: Missing command
    goto :help
)

if "%1"=="help" goto :help
if "%1"=="start" goto :start  
if "%1"=="stop" goto :stop
if "%1"=="health" goto :health
if "%1"=="logs" goto :logs
if "%1"=="clean" goto :clean
if "%1"=="setup-db" goto :setup-db

echo ❌ Unknown command: %1
goto :help

:help
echo.
echo 🚀 AI-Powered Multi-Domain News Crawler - Deployment System
echo ===========================================================
echo.
echo Stories 1.1-1.3 Production Ready:
echo   Story 1.1: Database Schema Foundation ✅
echo   Story 1.2: GWEN-3 Model Deployment ✅
echo   Story 1.3: Domain Analysis Worker ✅
echo.
echo Available commands:
echo   help       - Show this help menu
echo   start      - Start complete containerized system
echo   stop       - Stop all containers
echo   health     - Check all service health status  
echo   logs       - Show recent logs from all services
echo   setup-db   - Setup database with Vietnamese domains
echo   clean      - Clean up containers and volumes
echo.
echo Usage: deploy.bat [command]
echo Example: deploy.bat start
echo.
goto :end

:start
echo 🚀 Starting Complete AI Crawler System...
echo.
docker-compose -f docker-compose.yml up -d
echo 📊 Starting pgAdmin for database management...
docker-compose -f docker-compose.yml --profile admin up -d pgadmin
echo ✅ System started with pgAdmin!
timeout /t 10 /nobreak > nul
goto :health

:stop
echo 🛑 Stopping complete AI crawler system...
docker-compose -f docker-compose.yml down
echo ✅ All services stopped
goto :end

:health
call scripts\health_check.bat
goto :end

:setup-db
echo 🗄️ Setting up database with Vietnamese news domains...
docker-compose -f docker-compose.yml exec postgres psql -U crawler_user -d crawler_db -f /docker-entrypoint-initdb.d/01-init.sql
echo ✅ Database setup completed
goto :end

:logs
echo 📋 System Logs:
echo ==============
docker-compose -f docker-compose.yml logs --tail=10
goto :end

:clean
echo 🧹 Cleaning up system...
docker-compose -f docker-compose.yml down -v --remove-orphans
docker system prune -f
echo ✅ Cleanup completed
goto :end

:end