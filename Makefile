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
	@echo "$(COLOR_OK)  docker-build                  Build Docker image (single-arch, host CPU)$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docker-build-multiarch        Build & push image to registry (requires IMAGE=<uri>; opt PLATFORMS=linux/amd64)$(COLOR_NONE)"
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
	@echo "$(COLOR_OK)  docs-install-deps             Install documentation dependencies$(COLOR_NONE)"
	@echo "$(COLOR_OK)  docs-github                   Build docs and copy to docs/ for GitHub Pages$(COLOR_NONE)"
	@echo "$(COLOR_OK)  generate-docs                 Refresh auto-managed Markdown regions from the live tool inventory$(COLOR_NONE)"
	@echo "$(COLOR_OK)  check-docs                    Fail if any auto-managed Markdown region is stale (CI guardrail)$(COLOR_NONE)"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

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

# Multi-arch build, pushed straight to the IMAGE registry.
#
# Why a separate target: `docker build` on Apple Silicon defaults to arm64.
# Pushing an arm64-only image to ECR breaks ECS Fargate (which is amd64 by
# default) with `exec /usr/local/bin/python: exec format error`. The CI
# pipeline (.github/workflows/docker-build-push.yml) does this via
# `docker/build-push-action@v6`; this target is the local-machine
# equivalent so developers don't need to memorise the buildx incantation
# when they push to ECR, ACR, GAR, etc.
#
# Usage:
#   make docker-build-multiarch IMAGE=<your-registry-uri>:<tag>
# Example (ECR, defaults to amd64 + arm64):
#   make docker-build-multiarch \
#     IMAGE=123456789012.dkr.ecr.us-east-1.amazonaws.com/zscaler/zscaler-mcp-server:latest
# Example (dev — amd64 only, fewer ECR rows):
#   make docker-build-multiarch IMAGE=... PLATFORMS=linux/amd64
#
# Notes:
#  - PLATFORMS defaults to `linux/amd64,linux/arm64`. Override it to push
#    a subset (e.g. only `linux/amd64` for an ECS-only dev deploy).
#  - We pass `--provenance=false --sbom=false` to suppress the in-toto
#    attestation manifests buildx injects by default. Those attestations
#    show up in ECR as "unknown/unknown" entries with 0-byte size and
#    are useful for AWS Marketplace / SLSA compliance but pure noise for
#    a personal-ECR dev push. CI keeps them on; this target leaves them
#    off so the ECR repo stays at 1 manifest list + 1 image per platform
#    instead of 2 extra "unknown" rows.
#  - `--push` is required: buildx cannot load a multi-platform manifest
#    list into the local Docker engine (engine is single-arch).
PLATFORMS ?= linux/amd64,linux/arm64

docker-build-multiarch:
	@if [ -z "$(IMAGE)" ]; then \
		echo "$(COLOR_WARNING)ERROR: IMAGE is required.$(COLOR_NONE)"; \
		echo "Example: make docker-build-multiarch IMAGE=<account>.dkr.ecr.<region>.amazonaws.com/zscaler/zscaler-mcp-server:latest"; \
		exit 1; \
	fi
	@echo "$(COLOR_WARNING)Building $(PLATFORMS) → $(IMAGE)$(COLOR_NONE)"
	@# Ensure a buildx builder exists (idempotent; no-op when it already does).
	@$(DOCKER) buildx inspect zmcp-multiarch >/dev/null 2>&1 || \
		$(DOCKER) buildx create --name zmcp-multiarch --driver docker-container --use
	@$(DOCKER) buildx use zmcp-multiarch >/dev/null
	$(DOCKER) buildx build \
		--platform $(PLATFORMS) \
		--provenance=false \
		--sbom=false \
		--pull \
		--push \
		--build-arg VERSION=$(VERSION) \
		-t $(IMAGE) .
	@echo "$(COLOR_OK)Pushed to $(IMAGE) ($(PLATFORMS))$(COLOR_NONE)"
	@echo "$(COLOR_OK)Verify:$(COLOR_NONE) docker buildx imagetools inspect $(IMAGE)"

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
#
# The Sphinx portal (docsrc/) was retired in favour of the Docusaurus
# portal at docs-site/. Use the `docs-site-*` targets below to work
# with the new portal. For auto-generated content regions inside
# `docs/guides/*.md` and `README.md`, see `generate-docs` /
# `check-docs` further down.

# Tool-inventory documentation (separate from Sphinx — Sphinx renders
# Markdown into HTML; these targets keep the underlying Markdown in
# sync with the live tool inventory).
generate-docs:
	@echo "$(COLOR_WARNING)Refreshing auto-managed Markdown regions...$(COLOR_NONE)"
	python -m zscaler_mcp.server --generate-docs

check-docs:
	@echo "$(COLOR_WARNING)Checking auto-managed Markdown regions are in sync with live tool inventory...$(COLOR_NONE)"
	@python -m zscaler_mcp.server --check-docs

sync-integration-docs:
	@echo "$(COLOR_WARNING)Mirroring integrations/*/README.md into docs-site/...$(COLOR_NONE)"
	@python docs-site/scripts/sync_integrations_to_docs.py

check-integration-docs:
	@echo "$(COLOR_WARNING)Checking docs-site integration mirror is up to date...$(COLOR_NONE)"
	@python docs-site/scripts/sync_integrations_to_docs.py --check

# Skills index — derived from skills/*/*/SKILL.md frontmatter.
# Update whenever a skill is added, removed, or has its frontmatter
# `name` / `description` changed. The generator only rewrites the
# target file when content actually changes, so it is safe to run
# unconditionally.
generate-skills-docs:
	@echo "$(COLOR_WARNING)Generating docs-site/docs/guides/skills.md from SKILL.md frontmatter...$(COLOR_NONE)"
	@python docs-site/scripts/generate_skills_index.py

check-skills-docs:
	@echo "$(COLOR_WARNING)Checking docs-site skills index is up to date...$(COLOR_NONE)"
	@python docs-site/scripts/generate_skills_index.py --check

# Docusaurus portal (docs-site/) — separate from the older Sphinx
# targets above. Use these when working on the public docs site that
# ships to GitHub Pages.
#
#   docs-site-install  — one-time `npm install` (creates node_modules/).
#                        Auto-invoked by docs-site-start when missing.
#   docs-site-start    — local dev server on http://localhost:3000/
#                        with hot reload. Browser opens automatically.
#                        Override the port with PORT=4000 etc.
#   docs-site-build    — production build to docs-site/build/ — the
#                        same output GitHub Pages serves.
docs-site-install:
	@command -v npm >/dev/null 2>&1 || { \
		echo "ERROR: npm not found. Install Node.js (>= 18) to use the Docusaurus targets."; \
		exit 1; \
	}
	@echo "$(COLOR_WARNING)Installing docs-site dependencies (this may take a minute)...$(COLOR_NONE)"
	@cd docs-site && npm install

docs-site-start:
	@command -v npm >/dev/null 2>&1 || { \
		echo "ERROR: npm not found. Install Node.js (>= 18) to use the Docusaurus targets."; \
		exit 1; \
	}
	@[ -d docs-site/node_modules ] || $(MAKE) docs-site-install
	@echo "$(COLOR_OK)Starting Docusaurus dev server on http://localhost:$(if $(PORT),$(PORT),3000)/zscaler-mcp-server/...$(COLOR_NONE)"
	@cd docs-site && npm run start $(if $(PORT),-- --port $(PORT))

docs-site-build:
	@command -v npm >/dev/null 2>&1 || { \
		echo "ERROR: npm not found. Install Node.js (>= 18) to use the Docusaurus targets."; \
		exit 1; \
	}
	@[ -d docs-site/node_modules ] || $(MAKE) docs-site-install
	@echo "$(COLOR_WARNING)Building Docusaurus production bundle to docs-site/build/...$(COLOR_NONE)"
	@cd docs-site && npm run build

# MCPB bundle (Claude Desktop Directory)
#
# Builds the `.mcpb` archive you upload to Anthropic's submission form.
# The manifest at the repo root is auto-generated by `make generate-docs`
# (whole-file target — see `zscaler_mcp/common/mcpb.py`), so this target
# refreshes it first to guarantee the bundled tool list and version match
# the live inventory.
#
# The Anthropic `mcpb pack` CLI always writes `zscaler-mcp-server.mcpb`
# (filename derived from `name` in manifest.json — no version suffix). We
# rename it to `zscaler-mcp-server-<VERSION>.mcpb` so the artifact name on
# disk matches the version you're submitting.
build-mcpb: generate-docs
	@echo "$(COLOR_WARNING)Packing MCPB bundle for Claude Desktop...$(COLOR_NONE)"
	@command -v npx >/dev/null 2>&1 || { \
		echo "ERROR: npx not found. Install Node.js (>= 18) to build the .mcpb bundle."; \
		exit 1; \
	}
	@find . -maxdepth 1 -name "*.mcpb" -delete 2>/dev/null || true
	@npx --yes @anthropic-ai/mcpb@latest pack . || exit 1
	@VERSION=$$(python -c "from zscaler_mcp import __version__; print(__version__)"); \
		mv zscaler-mcp-server.mcpb "zscaler-mcp-server-$$VERSION.mcpb"; \
		echo "$(COLOR_OK)Bundle ready:$(COLOR_NONE)"; \
		ls -lh "zscaler-mcp-server-$$VERSION.mcpb"

# Inspect an already-built .mcpb. Usage:
#   make info-mcpb FILE=zscaler-mcp-server-0.12.2.mcpb
info-mcpb:
	@[ -n "$(FILE)" ] || { echo "Usage: make info-mcpb FILE=<bundle.mcpb>"; exit 1; }
	@npx --yes @anthropic-ai/mcpb@latest info "$(FILE)"

.PHONY: clean-pyc clean-build clean docker-clean docker-build docker-build-multiarch docker-rebuild docker-run docker-run-http docker-stop docker-generate-auth-token docker-save docs-site-install docs-site-start docs-site-build generate-docs check-docs sync-integration-docs check-integration-docs generate-skills-docs check-skills-docs build-mcpb info-mcpb
