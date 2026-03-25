@echo off
color 0E
title Gold Tier AI Employee - Setup

echo.
echo ============================================================
echo        GOLD TIER AI EMPLOYEE - SETUP WIZARD
echo ============================================================
echo.
echo Welcome! This will set up your AI Employee in a few steps.
echo.
pause

:: Step 1 - Check Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python not found!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
echo       Python found!

:: Step 2 - Install dependencies
echo.
echo [2/5] Installing required packages...
pip install -r requirements.txt -q
echo       Packages installed!

:: Step 3 - Collect user credentials
echo.
echo ============================================================
echo  [3/5] ENTER YOUR ACCOUNT DETAILS
echo ============================================================
echo.

set /p FACEBOOK_TOKEN=Enter your Facebook Access Token:
set /p FACEBOOK_PAGE=Enter your Facebook Page ID:
set /p INSTAGRAM_TOKEN=Enter your Instagram Access Token:
set /p INSTAGRAM_ID=Enter your Instagram Business Account ID:
set /p TWITTER_KEY=Enter your Twitter API Key:
set /p TWITTER_SECRET=Enter your Twitter API Secret:
set /p TWITTER_ACCESS=Enter your Twitter Access Token:
set /p TWITTER_ACCESS_SECRET=Enter your Twitter Access Token Secret:
set /p LINKEDIN_TOKEN=Enter your LinkedIn Access Token:
set /p ANTHROPIC_KEY=Enter your Claude AI API Key:

:: Step 4 - Write .env file
echo.
echo [4/5] Saving your configuration...

(
echo # Gold Tier AI Employee - Configuration
echo ANTHROPIC_API_KEY=%ANTHROPIC_KEY%
echo CLAUDE_MODEL=claude-sonnet-4-20250514
echo.
echo # Odoo
echo ODOO_URL=http://localhost:8069
echo ODOO_DATABASE=gold
echo ODOO_USERNAME=admin
echo ODOO_PASSWORD=admin123
echo ODOO_TIMEOUT=30
echo.
echo # Facebook
echo FACEBOOK_APP_ID=
echo FACEBOOK_APP_SECRET=
echo FACEBOOK_ACCESS_TOKEN=%FACEBOOK_TOKEN%
echo FACEBOOK_PAGE_ID=%FACEBOOK_PAGE%
echo.
echo # Instagram
echo INSTAGRAM_ACCESS_TOKEN=%INSTAGRAM_TOKEN%
echo INSTAGRAM_BUSINESS_ACCOUNT_ID=%INSTAGRAM_ID%
echo.
echo # Twitter
echo TWITTER_API_KEY=%TWITTER_KEY%
echo TWITTER_API_SECRET=%TWITTER_SECRET%
echo TWITTER_ACCESS_TOKEN=%TWITTER_ACCESS%
echo TWITTER_ACCESS_TOKEN_SECRET=%TWITTER_ACCESS_SECRET%
echo TWITTER_BEARER_TOKEN=
echo.
echo # LinkedIn
echo LINKEDIN_CLIENT_ID=
echo LINKEDIN_CLIENT_SECRET=
echo LINKEDIN_ACCESS_TOKEN=%LINKEDIN_TOKEN%
echo LINKEDIN_ORGANIZATION_ID=
echo.
echo # Settings
echo AUDIT_DAY=sunday
echo AUDIT_HOUR=9
echo AUDIT_RETENTION_DAYS=90
echo CEO_BRIEFING_ENABLED=true
echo GOLD_LOG_LEVEL=INFO
) > config\.env

echo       Configuration saved!

:: Step 5 - Done
echo.
echo ============================================================
echo  [5/5] SETUP COMPLETE!
echo ============================================================
echo.
echo  Your Gold Tier AI Employee is ready to run!
echo.
echo  To START your AI Employee:
echo     python main.py
echo.
echo  To TEST your connections:
echo     python test_connections.py
echo.
echo ============================================================
echo.
pause
