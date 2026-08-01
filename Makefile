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
	@echo "$(COLOR_OK)  docker-run                    Run Docker container (stdio, no auth)$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docker-run-http               Run Docker container (HTTP, with auth)$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docker-stop                   Stop the running HTTP container$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docker-generate-auth-token    Generate auth token for MCP clients$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docker-save                   Export Docker image to tarball$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docker-clean                  Clean Docker images and containers$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)documentation$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docs-build                    Build Sphinx documentation$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docs-clean                    Clean documentation build artifacts$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docs-install-deps             Install pinned documentation dependencies$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docs-update-deps              Refresh docsrc/requirements.txt from requirements.in$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docs-check-deps               Verify docsrc/requirements.txt is in sync with requirements.in (CI)$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docs-github                   Build docs and copy to docs/ for GitHub Pages$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)generated docs + bundle$(COLOR_NONE)"
	@echo "$(COLOR_OK)  generate-docs                 Regenerate auto-docs + MCPB manifest from the tool inventory$(COLOR_NONE)"
	@echo "$(COLOR_OK)  check-docs                    Verify auto-docs + MCPB manifest are in sync (CI)$(COLOR_NONE)"
	@echo "$(COLOR_OK)  build-mcpb                    Build the cross-platform .mcpb (Claude Desktop) bundle$(COLOR_NONE)"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

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

.PHONY: upgrade-sdk
upgrade-sdk:  ## Upgrade all deps to latest incl. zscaler-sdk-python, refreshing uv.lock + requirements.txt
	@echo "$(COLOR_WARNING)Upgrading uv.lock (all packages, fresh index)...$(COLOR_NONE)"
	uv lock --upgrade --refresh
	@echo "$(COLOR_WARNING)Regenerating requirements.txt from the latest resolution...$(COLOR_NONE)"
	uv pip compile pyproject.toml --output-file requirements.txt --upgrade
	@echo "$(COLOR_OK)uv.lock + requirements.txt refreshed to latest.$(COLOR_NONE)"
	@echo "$(COLOR_OK)(pyproject.toml is intentionally unpinned so PyPI/uvx installs always resolve latest.)$(COLOR_NONE)"
	@echo "$(COLOR_OK)zscaler-sdk-python now at: $$(grep -E '^zscaler-sdk-python==' requirements.txt)$(COLOR_NONE)"

.PHONY: upgrade-sdk-only
upgrade-sdk-only:  ## Bump ONLY zscaler-sdk-python to latest (minimal-churn uv.lock + requirements.txt)
	@echo "$(COLOR_WARNING)Upgrading only zscaler-sdk-python to latest (fresh index)...$(COLOR_NONE)"
	uv lock --upgrade-package zscaler-sdk-python --refresh-package zscaler-sdk-python
	uv pip compile pyproject.toml --output-file requirements.txt --upgrade-package zscaler-sdk-python
	@echo "$(COLOR_OK)zscaler-sdk-python now at: $$(grep -E '^zscaler-sdk-python==' requirements.txt)$(COLOR_NONE)"

# Official MCP conformance suite (server mode). Boots the server over
# streamable-http, points the PINNED runner at it for the PUBLISHED 2025-11-25
# baseline, and gates on .github/conformance-baseline.yml. Mirrors the CI job in
# .github/workflows/mcp-conformance.yml so you can reproduce it locally. Needs
# node/npx on PATH. Override CONFORMANCE_PORT if 8123 is taken.
CONFORMANCE_PORT ?= 8123
CONFORMANCE_RUNNER ?= @modelcontextprotocol/conformance@0.1.16
CONFORMANCE_SPEC_VERSION ?= 2025-11-25
.PHONY: conformance
conformance:  ## Run the official MCP conformance suite against a local server
	@echo "$(COLOR_WARNING)Starting server on 127.0.0.1:$(CONFORMANCE_PORT)...$(COLOR_NONE)"
	@ZSCALER_MCP_AUTH_ENABLED=false \
	  ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER=true \
	  ZSCALER_MCP_PID_FILE=/tmp/zscaler-mcp-conformance.pid \
	  uv run zscaler-mcp --transport streamable-http --host 127.0.0.1 --port $(CONFORMANCE_PORT) \
	  > /tmp/mcp-conformance-server.log 2>&1 & echo $$! > /tmp/mcp-conformance.pid
	@for _ in $$(seq 1 30); do \
	  curl -sf http://127.0.0.1:$(CONFORMANCE_PORT)/health >/dev/null && break; sleep 1; done
	@echo "$(COLOR_WARNING)Running conformance suite ($(CONFORMANCE_SPEC_VERSION))...$(COLOR_NONE)"
	@npx --yes $(CONFORMANCE_RUNNER) server \
	  --url http://127.0.0.1:$(CONFORMANCE_PORT)/mcp \
	  --suite active --spec-version $(CONFORMANCE_SPEC_VERSION) \
	  --expected-failures .github/conformance-baseline.yml; \
	  status=$$?; kill $$(cat /tmp/mcp-conformance.pid) 2>/dev/null || true; exit $$status

# Same suite against the 2026-07-28 revision — the one this server actually
# negotiates. Deliberately NOT wired into CI: the runner that knows those
# scenarios is alpha-only, and gating on a prerelease turns upstream scenario
# churn into red builds here. `make conformance` (published revision, pinned
# stable runner) stays the gate; this is the maintainer's check on the newer
# revision. Fold it into the gate once the 0.2.x runner reaches GA.
CONFORMANCE_NEXT_PORT ?= 8124
CONFORMANCE_NEXT_RUNNER ?= @modelcontextprotocol/conformance@0.2.0-alpha.10
CONFORMANCE_NEXT_SPEC_VERSION ?= 2026-07-28
.PHONY: conformance-next
conformance-next:  ## Run the MCP conformance suite against the 2026-07-28 revision (alpha runner)
	@echo "$(COLOR_WARNING)Starting server on 127.0.0.1:$(CONFORMANCE_NEXT_PORT)...$(COLOR_NONE)"
	@ZSCALER_MCP_AUTH_ENABLED=false \
	  ZSCALER_MCP_DISABLE_ENTITLEMENT_FILTER=true \
	  ZSCALER_MCP_PID_FILE=/tmp/zscaler-mcp-conformance-next.pid \
	  uv run zscaler-mcp --transport streamable-http --host 127.0.0.1 --port $(CONFORMANCE_NEXT_PORT) \
	  > /tmp/mcp-conformance-next-server.log 2>&1 & echo $$! > /tmp/mcp-conformance-next.pid
	@for _ in $$(seq 1 30); do \
	  curl -sf http://127.0.0.1:$(CONFORMANCE_NEXT_PORT)/health >/dev/null && break; sleep 1; done
	@echo "$(COLOR_WARNING)Running conformance suite ($(CONFORMANCE_NEXT_SPEC_VERSION), alpha runner)...$(COLOR_NONE)"
	@npx --yes $(CONFORMANCE_NEXT_RUNNER) server \
	  --url http://127.0.0.1:$(CONFORMANCE_NEXT_PORT)/mcp \
	  --suite active --spec-version $(CONFORMANCE_NEXT_SPEC_VERSION) \
	  --expected-failures .github/conformance-baseline-next.yml; \
	  status=$$?; kill $$(cat /tmp/mcp-conformance-next.pid) 2>/dev/null || true; exit $$status

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

docker-run-http:
	@echo "$(COLOR_WARNING)Starting MCP server with HTTP transport + auth...$(COLOR_NONE)"
	$(DOCKER) run -d --restart=unless-stopped --name $(BINARY_NAME) \
		-p 8000:8000 --env-file .env $(BINARY_NAME):$(VERSION) \
		--transport streamable-http --host 0.0.0.0 --port 8000
	@echo "$(COLOR_OK)Server running at http://localhost:8000/mcp$(COLOR_NONE)"
	@echo "$(COLOR_OK)Run 'make docker-generate-auth-token' to get client config$(COLOR_NONE)"

docker-stop:
	-$(DOCKER) stop $(BINARY_NAME) 2>/dev/null
	-$(DOCKER) rm $(BINARY_NAME) 2>/dev/null
	@echo "$(COLOR_OK)Container stopped$(COLOR_NONE)"

docker-generate-auth-token:
	@$(DOCKER) run --rm --env-file .env $(BINARY_NAME):$(VERSION) --generate-auth-token

docker-save:
	@echo "$(COLOR_WARNING)Exporting Docker image to tarball...$(COLOR_NONE)"
	$(DOCKER) save $(BINARY_NAME):$(VERSION) -o $(BINARY_NAME)-$(VERSION).tar
	@echo "$(COLOR_OK)Docker image exported to $(BINARY_NAME)-$(VERSION).tar$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)File size:$(COLOR_NONE) $$(du -h $(BINARY_NAME)-$(VERSION).tar | cut -f1)"

# Documentation targets
docs-build:
	cd docsrc && python -m sphinx -b html . _build

docs-clean:
	rm -fr docsrc/_build/

docs-install-deps:
	cd docsrc && uv pip install -r requirements.txt

# Target Python for the docs lockfile. Pinned to the project's minimum
# supported interpreter (requires-python = ">=3.11") so resolution is
# identical on every machine and in CI, regardless of which interpreter
# happens to run `uv`. Newer Sphinx releases that require >=3.12 are
# correctly excluded here.
DOCS_PYTHON ?= 3.11

# Refresh docsrc/requirements.txt from docsrc/requirements.in with the
# latest compatible versions for DOCS_PYTHON. Run this whenever
# requirements.in changes or you want to pull in upstream releases.
docs-update-deps:
	@echo "$(COLOR_WARNING)Refreshing docsrc/requirements.txt from requirements.in (Python $(DOCS_PYTHON))...$(COLOR_NONE)"
	uv pip compile docsrc/requirements.in --upgrade \
		--python-version $(DOCS_PYTHON) \
		--custom-compile-command "make docs-update-deps" \
		--output-file docsrc/requirements.txt
	@echo "$(COLOR_OK)Lockfile refreshed. Commit docsrc/requirements.txt.$(COLOR_NONE)"

# CI guard: re-resolve from requirements.in while *preferring the
# committed pins* (no --upgrade), then diff. This fails only on genuine
# drift -- a new constraint added to requirements.in without recompiling,
# or a pin that no longer satisfies its constraint. It does NOT fail just
# because a newer upstream release exists (that is what docs-update-deps
# is for). Seeding the scratch file with the committed lockfile lets uv
# keep the existing pins when they are still valid.
docs-check-deps:
	@echo "$(COLOR_WARNING)Checking docsrc/requirements.txt is in sync with requirements.in (Python $(DOCS_PYTHON))...$(COLOR_NONE)"
	@tmpfile=$$(mktemp); \
	cp docsrc/requirements.txt "$$tmpfile"; \
	uv pip compile docsrc/requirements.in \
		--python-version $(DOCS_PYTHON) \
		--custom-compile-command "make docs-update-deps" \
		--output-file "$$tmpfile" --quiet; \
	if ! diff -u docsrc/requirements.txt "$$tmpfile" > /dev/null; then \
		echo "$(COLOR_ERROR)docsrc/requirements.txt is stale. Run 'make docs-update-deps' and commit the result.$(COLOR_NONE)"; \
		diff -u docsrc/requirements.txt "$$tmpfile" || true; \
		rm -f "$$tmpfile"; \
		exit 1; \
	fi; \
	rm -f "$$tmpfile"; \
	echo "$(COLOR_OK)docsrc/requirements.txt is up to date.$(COLOR_NONE)"

docs-github:
	cd docsrc && python -m sphinx -b html . _build && cp -a _build/. ../docs

# ---------------------------------------------------------------------------
# Auto-generated docs + MCPB (Claude Desktop) bundle
# ---------------------------------------------------------------------------

# Regenerate every auto-generated region (supported-tools, README service
# summary, toolset catalog) AND the MCPB manifest at
# integrations/anthropic/manifest.json. Run after adding/renaming/removing
# a tool, then commit the result.
generate-docs:
	uv run python -m zscaler_mcp.server --generate-docs

# CI guard: exit non-zero if any auto-generated file (including the MCPB
# manifest) is out of sync with the live tool inventory.
check-docs:
	uv run python -m zscaler_mcp.server --check-docs

# Build the cross-platform (uv-runtime) .mcpb bundle for the Claude Desktop
# Directory. Validates the manifest is in sync + server.type == uv, copies
# the canonical integrations/anthropic/manifest.json to the pack root,
# packs, and emits dist/zscaler-mcp-server-<version>.mcpb.
build-mcpb:
	uv run python scripts/build_mcpb.py

.PHONY: clean-pyc clean-build docs clean docker-clean docker-build docker-rebuild docker-run docker-run-http docker-stop docker-generate-auth-token docker-save docs-build docs-clean docs-install-deps docs-update-deps docs-check-deps docs-github generate-docs check-docs build-mcpb