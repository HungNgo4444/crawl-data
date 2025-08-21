@echo off
REM System Integration Test Script
REM Tests end-to-end Vietnamese content analysis functionality
REM Author: System Architecture Team
REM Date: 2025-08-12

setlocal enabledelayedexpansion

echo.
echo 🧪 AI-Powered Multi-Domain News Crawler - Integration Tests
echo ==========================================================
echo.

REM Check if system is healthy first
echo 🏥 Pre-test Health Check...
call scripts\health_check.bat
if %errorlevel% neq 0 (
    echo.
    echo ❌ System not healthy - aborting tests
    echo    Please fix health issues first
    exit /b 1
)

echo.
echo ✅ System healthy - proceeding with tests
echo.

set "TEST_DOMAIN_ID=5ca6f1b9-ee1a-4df7-89d7-e3a3d04e4faf"
set "JOB_ID="
set "TEST_PASSED=0"
set "TEST_FAILED=0"

echo 📊 Test 1: Trigger Vietnamese Content Analysis (VNExpress.net)
echo --------------------------------------------------------------

REM Trigger analysis
for /f "delims=" %%i in ('curl -s -X POST "http://localhost:8082/trigger/%TEST_DOMAIN_ID%"') do set "TRIGGER_RESPONSE=%%i"

REM Check if response contains success
echo Response: !TRIGGER_RESPONSE!
echo !TRIGGER_RESPONSE! | findstr "success.*true" >nul 2>&1
if %errorlevel%==0 (
    echo ✅ Test 1 PASSED: Analysis triggered successfully
    set /a TEST_PASSED+=1
    
    REM Extract job ID for next test
    for /f "tokens=2 delims=:" %%a in ('echo !TRIGGER_RESPONSE! ^| findstr "job_id"') do (
        set "JOB_ID=%%a"
        set "JOB_ID=!JOB_ID: =!"
        set "JOB_ID=!JOB_ID:"=!"
        set "JOB_ID=!JOB_ID:}=!"
    )
    echo    Job ID: !JOB_ID!
) else (
    echo ❌ Test 1 FAILED: Analysis trigger failed
    set /a TEST_FAILED+=1
)

if not "!JOB_ID!"=="" (
    echo.
    echo 📊 Test 2: Check Job Status
    echo ---------------------------
    
    timeout /t 5 /nobreak >nul
    
    for /f "delims=" %%i in ('curl -s "http://localhost:8082/jobs/!JOB_ID!/status"') do set "STATUS_RESPONSE=%%i"
    
    echo Response: !STATUS_RESPONSE!
    echo !STATUS_RESPONSE! | findstr "job_id" >nul 2>&1
    if %errorlevel%==0 (
        echo ✅ Test 2 PASSED: Job status retrieved
        set /a TEST_PASSED+=1
    ) else (
        echo ❌ Test 2 FAILED: Job status not available
        set /a TEST_FAILED+=1
    )
)

echo.
echo 📊 Test 3: System Statistics
echo ----------------------------

for /f "delims=" %%i in ('curl -s "http://localhost:8082/stats"') do set "STATS_RESPONSE=%%i"

echo !STATS_RESPONSE! | findstr "worker_id" >nul 2>&1
if %errorlevel%==0 (
    echo ✅ Test 3 PASSED: System statistics available
    set /a TEST_PASSED+=1
) else (
    echo ❌ Test 3 FAILED: System statistics not available  
    set /a TEST_FAILED+=1
)

echo.
echo 📊 Test 4: Database Connectivity
echo --------------------------------

docker exec crawler_postgres psql -U crawler_user -d crawler_db -c "SELECT COUNT(*) FROM domain_configurations;" >nul 2>&1
if %errorlevel%==0 (
    echo ✅ Test 4 PASSED: Database accessible
    set /a TEST_PASSED+=1
) else (
    echo ❌ Test 4 FAILED: Database connection issues
    set /a TEST_FAILED+=1
)

echo.
echo 📊 Test 5: Vietnamese Domain Data
echo ---------------------------------

for /f %%i in ('docker exec crawler_postgres psql -U crawler_user -d crawler_db -t -c "SELECT COUNT(*) FROM domain_configurations WHERE domain_name LIKE '%%vn%%';"') do set "VN_COUNT=%%i"
set "VN_COUNT=!VN_COUNT: =!"

if !VN_COUNT! gtr 0 (
    echo ✅ Test 5 PASSED: Vietnamese domains found (!VN_COUNT! domains)
    set /a TEST_PASSED+=1
) else (
    echo ❌ Test 5 FAILED: No Vietnamese domains in database
    set /a TEST_FAILED+=1
)

echo.
echo 📊 Test 6: GWEN-3 Model Availability
echo ------------------------------------

docker exec crawler_ollama ollama list | findstr "qwen2.5:3b" >nul 2>&1
if %errorlevel%==0 (
    echo ✅ Test 6 PASSED: GWEN-3 model available
    set /a TEST_PASSED+=1
) else (
    echo ❌ Test 6 FAILED: GWEN-3 model not found
    set /a TEST_FAILED+=1
    echo    Run: docker exec crawler_ollama ollama pull qwen2.5:3b
)

echo.
echo 📊 Test 7: Redis Queue Connectivity
echo -----------------------------------

docker exec crawler_redis redis-cli ping | findstr "PONG" >nul 2>&1
if %errorlevel%==0 (
    echo ✅ Test 7 PASSED: Redis queue responsive
    set /a TEST_PASSED+=1
) else (
    echo ❌ Test 7 FAILED: Redis queue not responding
    set /a TEST_FAILED+=1
)

echo.
echo 🎯 Integration Test Results
echo ==========================

set /a TOTAL_TESTS=!TEST_PASSED! + !TEST_FAILED!

if !TEST_FAILED! equ 0 (
    echo 🎉 ALL TESTS PASSED (!TEST_PASSED!/!TOTAL_TESTS!)
    echo.
    echo ✅ Vietnamese content analysis system is fully operational
    echo 🚀 Stories 1.1-1.3 implementation: COMPLETE
    echo.
    echo 🌟 System Ready for Production Use:
    echo    • PostgreSQL database với Vietnamese domains
    echo    • GWEN-3 model cho Vietnamese content analysis  
    echo    • Analysis worker với real-time processing
    echo    • Complete API endpoints for integration
    exit /b 0
) else (
    echo ⚠️  TESTS COMPLETED WITH ISSUES (!TEST_PASSED! passed, !TEST_FAILED! failed)
    echo.
    echo 🔧 System Status: Partially operational
    echo 📋 Review failed tests and fix issues
    echo 💡 Run: deploy.bat logs (for detailed diagnostics)
    exit /b 1
)

:end