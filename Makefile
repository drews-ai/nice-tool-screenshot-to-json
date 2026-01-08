# Interface Inventory System - Makefile
# Run `make install` to set up the project

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: install clean run help

# Default target
help:
	@echo "Usage:"
	@echo "  make install  - Create venv and install dependencies"
	@echo "  make run      - Run the server"
	@echo "  make clean    - Remove venv"

# Create venv and install all dependencies
install: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install openai
	@echo ""
	@echo "✓ Installation complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and add your API keys"
	@echo "  2. Run: make run"
	@echo ""
	@touch $(VENV)/bin/activate

# Run the server
run: $(VENV)/bin/activate
	$(PYTHON) -c "from config import get_config; print('Config OK')"
	@echo "Server would start here (add your entry point)"

# Clean up
clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned"
