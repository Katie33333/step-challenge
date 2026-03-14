PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
STREAMLIT := $(VENV)/bin/streamlit

.PHONY: setup run

setup:
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(PIP) install -r requirements.txt

run: setup
	$(STREAMLIT) run app.py
