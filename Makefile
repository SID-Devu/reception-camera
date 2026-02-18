CFLAGS = -Wall -Wextra -O2
PYTHON = python3
PIP = pip3

.PHONY: all install run clean

all: install

install:
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

run:
	$(PYTHON) src/main.py

clean:
	find . -type d -name '__pycache__' -exec rm -r {} +
	find . -type f -name '*.pyc' -exec rm -f {} +