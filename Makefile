.PHONY: run run-vehicle run-numeric build up down logs status clean config help

# デフォルトターゲット
help:
	@echo "HiLSim-3 Makefile Commands:"
	@echo ""
	@echo "Simulation:"
	@echo "  run          - Run simulation with current .env settings"
	@echo "  run-vehicle  - Run vehicle simulation"
	@echo "  run-numeric  - Run numeric simulation (basic communication test)"
	@echo "  config       - Show current configuration"
	@echo ""
	@echo "Control:"
	@echo "  build        - Build Docker images"
	@echo "  up           - Start containers (without build)"
	@echo "  down         - Stop containers"
	@echo "  clean        - Stop containers and remove images"
	@echo ""
	@echo "Monitoring:"
	@echo "  logs         - Show container logs"
	@echo "  logs-sim     - Show simulator logs only"
	@echo "  logs-hw      - Show hardware logs only"
	@echo "  status       - Show container status"
	@echo "  show-logs    - Show latest log files"
	@echo ""
	@echo "Development:"
	@echo "  install      - Install dependencies"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting"
	@echo "  format       - Format code"

# Main simulation command
run:
	@LOG_TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	echo "Starting HiLSim-3 with log timestamp: $$LOG_TIMESTAMP"; \
	echo "Configuration: SIM_TYPE=$${SIM_TYPE:-vehicle}, HW_TYPE=$${HW_TYPE:-vehicle}"; \
	echo "Logs will be saved to: ./logs/$$LOG_TIMESTAMP/"; \
	export LOG_TIMESTAMP=$$LOG_TIMESTAMP; \
	export UID=$$(id -u); \
	export GID=$$(id -g); \
	docker compose up --build; \
	echo "Simulation completed. Check logs in: ./logs/$$LOG_TIMESTAMP/"

# Vehicle simulation
run-vehicle:
	@LOG_TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	echo "Starting Vehicle Simulation with log timestamp: $$LOG_TIMESTAMP"; \
	export LOG_TIMESTAMP=$$LOG_TIMESTAMP; \
	export UID=$$(id -u); \
	export GID=$$(id -g); \
	export SIM_TYPE=vehicle; \
	export HW_TYPE=vehicle; \
	docker compose up --build; \
	echo "Vehicle simulation completed. Check logs in: ./logs/$$LOG_TIMESTAMP/"

# Numeric simulation (basic communication test)
run-numeric:
	@LOG_TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	echo "Starting Numeric Simulation (basic communication test) with log timestamp: $$LOG_TIMESTAMP"; \
	export LOG_TIMESTAMP=$$LOG_TIMESTAMP; \
	export UID=$$(id -u); \
	export GID=$$(id -g); \
	export SIM_TYPE=numeric; \
	export HW_TYPE=numeric; \
	docker compose up --build; \
	echo "Numeric simulation completed. Check logs in: ./logs/$$LOG_TIMESTAMP/"

# Container management
build:
	docker compose build

up:
	docker compose up

down:
	docker compose down

clean:
	docker compose down --rmi all --volumes --remove-orphans
	@echo "Cleaned up containers and images"

# Monitoring
logs:
	docker compose logs

logs-sim:
	docker logs hilsim_simulator

logs-hw:
	docker logs hilsim_hardware

status:
	docker compose ps

show-logs:
	@if [ -d "logs" ]; then \
		latest=$$(ls -1t logs/ | head -1); \
		if [ -n "$$latest" ]; then \
			echo "Latest log directory: logs/$$latest"; \
			echo "Files:"; \
			ls -la logs/$$latest/; \
		else \
			echo "No log directories found"; \
		fi; \
	else \
		echo "logs directory does not exist"; \
	fi

# Configuration
config:
	@echo "Current HiLSim-3 Configuration:"
	@echo "  SIM_TYPE: $${SIM_TYPE:-vehicle}"
	@echo "  HW_TYPE: $${HW_TYPE:-vehicle}"
	@echo "  TOTAL_STEPS: $${TOTAL_STEPS:-1000}"
	@echo "  STEP_MS: $${STEP_MS:-10}"
	@echo "  REPLY_TIMEOUT_MS: $${REPLY_TIMEOUT_MS:-2}"
	@echo "  NETWORK_DELAY_MS: $${NETWORK_DELAY_MS:-0}"
	@echo ""
	@echo "Available simulation types: numeric (basic test), vehicle"

# Development
install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run mypy .

format:
	uv run ruff check --fix .
	uv run black .