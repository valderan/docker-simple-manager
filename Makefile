.PHONY: help install lint format typecheck test build-linux build-macos package-deb dist-clean

help:
	@echo "Available targets: install lint format typecheck test build-linux build-macos package-deb dist-clean"

install:
	uv pip install -e ".[dev]"

VERSION := $(shell python3 -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")

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

DEB_BUILD_DIR := build/deb/docker-simple-manager
DEB_INSTALL_PREFIX := $(DEB_BUILD_DIR)/opt/docker-simple-manager
DEB_BIN_DIR := $(DEB_BUILD_DIR)/usr/bin
DEB_DESKTOP_DIR := $(DEB_BUILD_DIR)/usr/share/applications
DEB_ICON_DIR := $(DEB_BUILD_DIR)/usr/share/pixmaps
DEB_DEBIAN_DIR := $(DEB_BUILD_DIR)/DEBIAN

package-deb: build-linux
	rm -rf $(DEB_BUILD_DIR)
	mkdir -p $(DEB_INSTALL_PREFIX) $(DEB_BIN_DIR) $(DEB_DESKTOP_DIR) $(DEB_ICON_DIR) $(DEB_DEBIAN_DIR)
	cp -R dist/dsm-linux/. $(DEB_INSTALL_PREFIX)/
	chmod +x $(DEB_INSTALL_PREFIX)/dsm
	cp packaging/usr/bin/docker-simple-manager $(DEB_BIN_DIR)/docker-simple-manager
	chmod +x $(DEB_BIN_DIR)/docker-simple-manager
	sed 's/@VERSION@/$(VERSION)/g' packaging/debian/control > $(DEB_DEBIAN_DIR)/control
	cp packaging/docker-simple-manager.desktop $(DEB_DESKTOP_DIR)/docker-simple-manager.desktop
	cp logo-dsm.png $(DEB_ICON_DIR)/docker-simple-manager.png
	dpkg-deb --build $(DEB_BUILD_DIR) dist/docker-simple-manager_$(VERSION)_amd64.deb

dist-clean:
	rm -rf build dist
