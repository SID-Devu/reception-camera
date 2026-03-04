PYTHON = python3
PIP = pip3
VENV = .venv
VENV_PYTHON = $(VENV)/bin/python
VENV_PIP = $(VENV)/bin/pip

.PHONY: all install install-dev run setup setup-rb5 deploy-rb5 validate test clean help

all: install

help:
	@echo "Reception Greeter – Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  install       Install production deps into venv"
	@echo "  install-dev   Install dev deps into venv"
	@echo "  run           Run the application"
	@echo "  setup         Full auto-setup (all platforms)"
	@echo "  setup-rb5     Run RB5 board-level configuration"
	@echo "  deploy-rb5    Deploy to RB5 via ADB"
	@echo "  validate      Run post-setup health check"
	@echo "  test          Run test suite"
	@echo "  clean         Remove caches and build artifacts"

$(VENV):
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip setuptools wheel

install: $(VENV)
	$(VENV_PIP) install -r requirements.txt

install-dev: install
	$(VENV_PIP) install -r requirements-dev.txt

run:
	$(VENV_PYTHON) app/main.py

setup:
	sudo bash setup.sh

setup-rb5:
	sudo bash scripts/setup_rb5.sh

deploy-rb5:
	bash scripts/deploy_rb5.sh

validate:
	bash scripts/validate.sh

test:
	$(VENV_PYTHON) -m pytest tests/ -v

clean:
	find . -type d -name '__pycache__' -exec rm -r {} +
	find . -type f -name '*.pyc' -exec rm -f {} +
	rm -rf .pytest_cache .mypy_cache htmlcov *.egg-info