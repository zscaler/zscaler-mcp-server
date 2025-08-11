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
	@echo "$(COLOR_OK)Zscaler MCP Server$(COLOR_NONE) version $(COLOR_WARNING)$(VERSION)$(COLOR_NONE)"
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
	@echo "$(COLOR_WARNING)development$(COLOR_NONE)"
	@echo "$(COLOR_OK)  check-format                  Check code format/style with black$(COLOR_NONE)"
	@echo "$(COLOR_OK)  format                        Reformat code with black$(COLOR_NONE)"
	@echo "$(COLOR_OK)  lint                          Check style with flake8 for all packages$(COLOR_NONE)"
	@echo "$(COLOR_OK)  lint:zcc                      Check style with flake8 for zcc packages$(COLOR_NONE)"
	@echo "$(COLOR_OK)  lint:zdx                      Check style with flake8 for zdx packages$(COLOR_NONE)"
	@echo "$(COLOR_OK)  lint:zpa                      Check style with flake8 for zpa packages$(COLOR_NONE)"
	@echo "$(COLOR_OK)  lint:zia                      Check style with flake8 for zia packages$(COLOR_NONE)"
	@echo "$(COLOR_OK)  coverage                      Check code coverage quickly with the default Python$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)test$(COLOR_NONE)"
	@echo "$(COLOR_OK)  test:all                      Run all tests$(COLOR_NONE)"
	@echo "$(COLOR_OK)  test:integration:zcc          Run only zcc integration tests$(COLOR_NONE)"
	@echo "$(COLOR_OK)  test:integration:zdx          Run only zdx integration tests$(COLOR_NONE)"
	@echo "$(COLOR_OK)  test:integration:zia          Run only zia integration tests$(COLOR_NONE)"
	@echo "$(COLOR_OK)  test:integration:zpa          Run only zpa integration tests$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)build$(COLOR_NONE)"
	@echo "$(COLOR_OK)  build:dist                    Build the distribution for publishing$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)publish$(COLOR_NONE)"
	@echo "$(COLOR_OK)  publish:test                  Publish distribution to testpypi (Will ask for credentials)$(COLOR_NONE)"
	@echo "$(COLOR_OK)  publish:prod                  Publish distribution to pypi (Will ask for credentials)$(COLOR_NONE)"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-docs:
	rm -fr docs/_build/

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

# Runtime-only dependencies
sync-deps:
	poetry export -f requirements.txt --without-hashes > requirements.txt

# Dev dependencies for contributors/CI
sync-dev-deps:
	poetry export -f requirements.txt --without-hashes --with dev > requirements-dev.txt

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

.PHONY: reqs
reqs:       ## Recreate the requirements.txt file
	poetry export -f requirements.txt --output requirements.txt --only=main --without-hashes

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

.PHONY: clean-pyc clean-build docs clean docker-clean docker-build docker-rebuild
