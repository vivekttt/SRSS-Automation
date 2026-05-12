@echo off
echo 🚀 Creating Local Environment (using Python 3.12)...

:: This forces the use of Python 3.12 specifically
py -3.12 -m venv venv

if %errorlevel% neq 0 (
    echo ❌ ERROR: Python 3.12 not found! 
    echo Please install it from python.org or the Microsoft Store.
    pause
    exit /b
)

echo 📥 Installing Dependencies...
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo ✅ Setup Complete using Python 3.12.
pause