#!/usr/bin/env bash
# Start the investor chat. First run: creates .venv and installs the requirements.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements-app.txt
fi
exec .venv/bin/python -m streamlit run src/app/streamlit_app.py
