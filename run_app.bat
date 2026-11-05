@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo Add your API keys to the .env file, then run run_app.bat again.
echo Starting VibeCast. Open the local URL shown below.
streamlit run app.py
pause
