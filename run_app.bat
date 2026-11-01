@echo off
rem Start the investor chat. First run: creates .venv and installs the requirements.
cd /d "%~dp0"
if not exist .venv (
  py -m venv .venv || python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\python -m pip install -r requirements-app.txt
)
.venv\Scripts\python -m streamlit run src\app\streamlit_app.py
