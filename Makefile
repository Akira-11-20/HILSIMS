.PHONY: run build up down logs clean status help

# デフォルトターゲット
help:
	@echo "HiLSim-3 Makefile Commands:"
	@echo ""
	@echo "Simulation:"
	@echo "  run          - Build and run simulation with timestamped logs"
	@echo "  build        - Build Docker images"
	@echo "  up           - Start containers (without build)"
	@echo "  down         - Stop and remove containers"
	@echo "  logs         - Show container logs"
	@echo "  status       - Show container status"
	@echo "  clean        - Stop containers and remove images"
	@echo "  clean-logs   - Remove all log directories"
	@echo ""
	@echo "Analysis:"
	@echo "  analyze      - Run RTT analysis with plots"
	@echo "  analyze-stats - Run RTT analysis (stats only)"
	@echo "  plot-rtt     - Create RTT timeline plot"
	@echo ""
	@echo "Development:"
	@echo "  install      - Install Python dependencies with uv"
	@echo "  setup-dev    - Setup development environment with pre-commit"
	@echo "  lint         - Run linting and type checking"
	@echo "  format       - Format code with black and ruff"
	@echo "  test         - Run tests"
	@echo "  pre-commit   - Run pre-commit hooks on all files"

# タイムスタンプを生成してシミュレーション実行
run:
	@LOG_TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	echo "Starting HiLSim-3 with log timestamp: $$LOG_TIMESTAMP"; \
	echo "Logs will be saved to: ./logs/$$LOG_TIMESTAMP/"; \
	export LOG_TIMESTAMP=$$LOG_TIMESTAMP; \
	export UID=$$(id -u); \
	export GID=$$(id -g); \
	docker compose up --build; \
	echo "Simulation completed. Check logs in: ./logs/$$LOG_TIMESTAMP/"

# バックグラウンド実行
run-bg:
	@LOG_TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	echo "Starting HiLSim-3 in background with log timestamp: $$LOG_TIMESTAMP"; \
	echo "Logs will be saved to: ./logs/$$LOG_TIMESTAMP/"; \
	export LOG_TIMESTAMP=$$LOG_TIMESTAMP; \
	export UID=$$(id -u); \
	export GID=$$(id -g); \
	docker compose up --build -d; \
	echo "Simulation started in background. Log timestamp: $$LOG_TIMESTAMP"

# イメージをビルド
build:
	docker compose build

# コンテナ起動（ビルドなし）
up:
	docker compose up

# コンテナ停止・削除
down:
	docker compose down

# ログ表示
logs:
	docker compose logs

# simのログのみ
logs-sim:
	docker logs rt_sim

# actのログのみ
logs-act:
	docker logs rt_act

# コンテナ状態確認
status:
	docker compose ps

# 完全クリーンアップ（コンテナ停止・イメージ削除）
clean:
	docker compose down --rmi all --volumes --remove-orphans

# ログディレクトリをクリーンアップ
clean-logs:
	@echo "Removing all log directories..."
	rm -rf logs/*/
	@echo "Log directories cleaned."

# 最新のログディレクトリを表示
show-latest-logs:
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

# 設定確認
config:
	@echo "Current configuration:"
	@echo "  TOTAL_STEPS: $${TOTAL_STEPS:-10000}"
	@echo "  STEP_MS: $${STEP_MS:-10}"
	@echo "  REPLY_TIMEOUT_MS: $${REPLY_TIMEOUT_MS:-2}"
	@echo "  NETWORK_DELAY_MS: $${NETWORK_DELAY_MS:-1}"

# RTT解析
analyze:
	uv run python analysis/analyze_rtt.py

# RTT解析（プロットなし）
analyze-stats:
	uv run python analysis/analyze_rtt.py --no-plot

# RTTタイムラインプロット
plot-rtt:
	uv run python analysis/plot_rtt_timeline.py

# 依存関係インストール
install:
	uv sync

# 開発環境セットアップ
setup-dev: install
	uv run pre-commit install

# リント・フォーマット
lint:
	uv run ruff check .
	uv run black --check .
	uv run mypy .

# フォーマット適用
format:
	uv run ruff check --fix .
	uv run black .

# テスト実行
test:
	uv run pytest

# pre-commit実行
pre-commit:
	uv run pre-commit run --all-files