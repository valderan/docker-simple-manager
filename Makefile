.PHONY: help install lint format typecheck test build-linux build-macos dist-clean

help:
	@echo "Available targets: install lint format typecheck test build-linux build-macos dist-clean"

install:
	uv pip install -e ".[dev]"

lint: install
	uv run black --check src tests
	uv run flake8 src tests

format:
	uv run black src tests

typecheck: install
	uv run mypy src

test: install
	uv run python -m pytest

run:
	uv run docker-simple-manager 

build-linux:
	DSM_BINARY_NAME=dsm DSM_DIST_NAME=dsm-linux \
	uv run --extra dev pyinstaller --clean -y pyinstaller.spec

build-macos:
	@if [ "$$(uname)" != "Darwin" ]; then \
		echo "build-macos можно запускать только на macOS (Darwin)"; \
		exit 1; \
	fi
	DSM_BINARY_NAME=dsm DSM_DIST_NAME=dist-macos \
	uv run --extra dev pyinstaller --clean -y pyinstaller.spec

dist-clean:
	rm -rf build dist
