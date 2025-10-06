COLOR_OK=\\x1b[0;32m
COLOR_NONE=\x1b[0m
COLOR_ERROR=\x1b[31;01m
COLOR_WARNING=\x1b[33;01m
COLOR_ZSCALER=\x1B[34;01m

DOCKER        ?= docker
BINARY_NAME   ?= zscaler-mcp-server
VERSION       ?= latest


help:
	@echo "$(COLOR_ZSCALER)"
	@echo "  ______              _           "
	@echo " |___  /             | |          "
	@echo "    / / ___  ___ __ _| | ___ _ __ "
	@echo "   / / / __|/ __/ _\` | |/ _ \ '__|"
	@echo "  / /__\__ \ (_| (_| | |  __/ |   "
	@echo " /_____|___/\___\__,_|_|\___|_|   "
	@echo "                                  "
	@echo "                                  "
	@echo "$(COLOR_NONE)"
	@echo "$(COLOR_OK)Zscaler Integrations MCP Server$(COLOR_NONE) version $(COLOR_WARNING)$(VERSION)$(COLOR_NONE)"
	@echo ""
	@echo "$(COLOR_WARNING)Usage:$(COLOR_NONE)"
	@echo "$(COLOR_OK)  make [command]$(COLOR_NONE)"
	@echo ""
	@echo "$(COLOR_WARNING)Available commands:$(COLOR_NONE)"
	@echo "$(COLOR_OK)  help$(COLOR_NONE)           Show this help message"
	@echo "$(COLOR_WARNING)clean$(COLOR_NONE)"
	@echo "$(COLOR_OK)  clean                  	Remove all build, test, coverage and Python artifacts$(COLOR_NONE)"
	@echo "$(COLOR_OK)  clean-build                   Remove build artifacts$(COLOR_NONE)"
	@echo "$(COLOR_OK)  clean-pyc                     Remove Python file artifacts$(COLOR_NONE)"
	@echo "$(COLOR_OK)  clean-test                    Remove test and coverage artifacts$(COLOR_NONE)"
	@echo "$(COLOR_OK)  clean-docs                    Remove documentation build artifacts$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)dependencies$(COLOR_NONE)"
	@echo "$(COLOR_OK)  sync-deps                     Install dependencies from uv.lock$(COLOR_NONE)"
	@echo "$(COLOR_OK)  sync-dev-deps                 Install dev dependencies from uv.lock$(COLOR_NONE)"
	@echo "$(COLOR_OK)  update-deps                   Update all dependencies (uv.lock, pyproject.toml)$(COLOR_NONE)"
	@echo "$(COLOR_OK)  update-lock                   Update uv.lock with latest compatible versions$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)install$(COLOR_NONE)"
	@echo "$(COLOR_OK)  install                       Install package$(COLOR_NONE)"
	@echo "$(COLOR_OK)  install-dev                   Install package in development mode$(COLOR_NONE)"
	@echo "$(COLOR_OK)  install-uv                    Install as uv tool$(COLOR_NONE)"
	@echo "$(COLOR_OK)  install-pip                   Install using pip$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)uv$(COLOR_NONE)"
	@echo "$(COLOR_OK)  clean-uv-cache                Clean uv cache and regenerate lock file$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)docker$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docker-build                  Build Docker image$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docker-rebuild                Clean and rebuild Docker image$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docker-run                    Run Docker container$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docker-clean                  Clean Docker images and containers$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)documentation$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docs-build                    Build Sphinx documentation$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docs-clean                    Clean documentation build artifacts$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docs-install-deps             Install documentation dependencies$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docs-github                   Build docs and copy to docs/ for GitHub Pages$(COLOR_NONE)"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-docsrc:
	echo "Wg!2161980" | sudo -S rm -fr docsrc/_build/

docs: clean-docsrc
	@echo "$(COLOR_WARNING)Building Sphinx documentation...$(COLOR_NONE)"
	cd docsrc && python -m sphinx -b html . _build
	@echo "$(COLOR_OK)Documentation built successfully! Opening in browser...$(COLOR_NONE)"
	open docsrc/_build/index.html

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache
	rm -fr .ruff_cache

# Runtime-only dependencies
sync-deps:
	uv sync --frozen --no-dev

# Dev dependencies for contributors/CI
sync-dev-deps:
	uv sync --frozen

install:
	uv pip install .

install-dev:
	uv pip install -e .

install-uv:
	uv tool install --local .

clean-uv-cache:
	rm -rf uv.lock
	uv cache clean
	uv lock

install-pip:
	pip install -e .


.PHONY: update-lock
update-lock:  ## Update uv.lock with latest compatible versions
	uv lock --upgrade

.PHONY: update-deps
update-deps:  ## Update all dependencies (uv.lock, pyproject.toml)
	@echo "$(COLOR_WARNING)Updating uv.lock with latest compatible versions...$(COLOR_NONE)"
	uv lock --upgrade
	@echo "$(COLOR_WARNING)Updating pyproject.toml with new version constraints...$(COLOR_NONE)"
	uv add --upgrade authlib cryptography fastapi huggingface-hub jiter langsmith openai posthog pydantic starlette zstandard
	@echo "$(COLOR_OK)All dependencies updated successfully!$(COLOR_NONE)"

docker-clean:
	-$(DOCKER) ps -a --filter "ancestor=$(BINARY_NAME):$(VERSION)" -q | xargs -r $(DOCKER) rm -f
	-$(DOCKER) rmi -f $(BINARY_NAME):$(VERSION) 2>/dev/null || true
	-$(DOCKER) image prune -f
	-$(DOCKER) builder prune -f

docker-build:
	$(DOCKER) build --pull --build-arg VERSION=$(VERSION) \
		-t $(BINARY_NAME):$(VERSION) .

docker-rebuild: docker-clean docker-build

docker-run:
	$(DOCKER) run -i --rm --env-file .env $(BINARY_NAME):$(VERSION)

# Documentation targets
docs-build:
	cd docsrc && python -m sphinx -b html . _build

docs-clean:
	rm -fr docsrc/_build/

docs-install-deps:
	cd docsrc && uv pip install -r requirements.txt

docs-github:
	cd docsrc && python -m sphinx -b html . _build && cp -a _build/. ../docs

.PHONY: clean-pyc clean-build docs clean docker-clean docker-build docker-rebuild docs-build docs-clean docs-install-deps docs-github
