COLOR_OK=\\x1b[0;32m
COLOR_NONE=\x1b[0m
COLOR_ERROR=\x1b[31;01m
COLOR_WARNING=\x1b[33;01m
COLOR_ZSCALER=\x1B[34;01m

VERSION=$(shell grep -E -o '(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?' ./zscaler/__init__.py)

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
	@echo "$(COLOR_OK)  lint:zcon                     Check style with flake8 for zcon packages$(COLOR_NONE)"
	@echo "$(COLOR_OK)  lint:zdx                      Check style with flake8 for zdx packages$(COLOR_NONE)"
	@echo "$(COLOR_OK)  lint:zpa                      Check style with flake8 for zpa packages$(COLOR_NONE)"
	@echo "$(COLOR_OK)  lint:zia                      Check style with flake8 for zia packages$(COLOR_NONE)"
	@echo "$(COLOR_OK)  coverage                      Check code coverage quickly with the default Python$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)test$(COLOR_NONE)"
	@echo "$(COLOR_OK)  test:all                      Run all tests$(COLOR_NONE)"
	@echo "$(COLOR_OK)  test:integration:zcc          Run only zcc integration tests$(COLOR_NONE)"
	@echo "$(COLOR_OK)  test:integration:zcon         Run only zcon integration tests$(COLOR_NONE)"
	@echo "$(COLOR_OK)  test:integration:zdx          Run only zdx integration tests$(COLOR_NONE)"
	@echo "$(COLOR_OK)  test:integration:zia          Run only zia integration tests$(COLOR_NONE)"
	@echo "$(COLOR_OK)  test:integration:zpa          Run only zpa integration tests$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)build$(COLOR_NONE)"
	@echo "$(COLOR_OK)  build:dist                    Build the distribution for publishing$(COLOR_NONE)"
	@echo "$(COLOR_WARNING)publish$(COLOR_NONE)"
	@echo "$(COLOR_OK)  publish:test                  Publish distribution to testpypi (Will ask for credentials)$(COLOR_NONE)"
	@echo "$(COLOR_OK)  publish:prod                  Publish distribution to pypi (Will ask for credentials)$(COLOR_NONE)"

clean: clean-build clean-pyc clean-test clean-docsrc

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

clean-docsrc:
	rm -fr docsrc/_build/

docs: clean-docsrc
	$(MAKE) -C docsrc html
	open docsrc/_build/html/index.html

lint:
	flake8 zscaler --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	flake8 zscaler --count --select=E9,F63,F7,F82 --show-source --statistics

lint\:zcc:
	flake8 zscaler/zcc --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	flake8 zscaler/zcc --count --select=E9,F63,F7,F82 --show-source --statistics

lint\:zcon:
	flake8 zscaler/zcon --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	flake8 zscaler/zcon --count --select=E9,F63,F7,F82 --show-source --statistics

lint\:zdx:
	flake8 zscaler/zdx --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	flake8 zscaler/zdx --count --select=E9,F63,F7,F82 --show-source --statistics

lint\:zpa:
	flake8 zscaler/zpa --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	flake8 zscaler/zpa --count --select=E9,F63,F7,F82 --show-source --statistics

lint\:zia:
	flake8 zscaler/zia --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	flake8 zscaler/zia --count --select=E9,F63,F7,F82 --show-source --statistics

format:
	black .

check-format:
	black --check --diff .

test\:integration\:zcc:
	@echo "$(COLOR_ZSCALER)Running zcc integration tests...$(COLOR_NONE)"
	pytest tests/integration/zcc --disable-warnings

test\:integration\:zcon:
	@echo "$(COLOR_ZSCALER)Running zcon integration tests...$(COLOR_NONE)"
	pytest tests/integration/zcon --disable-warnings

test\:integration\:zdx:
	@echo "$(COLOR_ZSCALER)Running zdx integration tests...$(COLOR_NONE)"
	pytest tests/integration/zdx --disable-warnings

test\:integration\:zpa:
	@echo "$(COLOR_ZSCALER)Running zpa integration tests...$(COLOR_NONE)"
	pytest tests/integration/zpa --disable-warnings

test\:integration\:zia:
	@echo "$(COLOR_ZSCALER)Running zia integration tests...$(COLOR_NONE)"
	pytest tests/integration/zia --disable-warnings

test-simple:
	pytest --disable-warnings

coverage:
	pytest --cov=zscaler --cov-report xml --cov-report term

coverage\:zcc:
	pytest tests/integration/zcc -v --cov=zscaler/zcc --cov-report xml --cov-report term

coverage\:zcon:
	pytest tests/integration/zcon -v --cov=zscaler/zcon --cov-report xml --cov-report term

coverage\:zdx:
	pytest tests/integration/zdx -v --cov=zscaler/zdx --cov-report xml --cov-report term

coverage\:zia:
	pytest tests/integration/zia --cov=zscaler/zia --cov-report xml --cov-report term

coverage\:zpa:
	pytest tests/integration/zpa --cov=zscaler/zpa --cov-report xml --cov-report term

sweep\:zia:
	@echo "$(COLOR_WARNING)WARNING: This will destroy infrastructure. Use only in development accounts.$(COLOR_NONE)"
	ZIA_SDK_TEST_SWEEP=true python tests/integration/zia/sweep/run_sweep.py --sweep

sweep\:zpa:
	@echo "$(COLOR_WARNING)WARNING: This will destroy infrastructure. Use only in development accounts.$(COLOR_NONE)"
	ZPA_SDK_TEST_SWEEP=true python tests/integration/zpa/sweep/run_sweep.py --sweep


build\:dist:
	python3 setup.py sdist bdist_wheel
	pip3 install dist/zscaler-sdk-python-${VERSION}.tar.gz
	ls -l dist

publish\:test:
	python3 -m twine upload --repository testpypi dist/*

publish\:prod:
	python3 -m twine upload dist/*

# Runtime-only dependencies
sync-deps:
	poetry export -f requirements.txt --without-hashes > requirements.txt

# Dev dependencies for contributors/CI
sync-dev-deps:
	poetry export -f requirements.txt --without-hashes --with dev > requirements-dev.txt


local-setup:
ifeq ($(wildcard ~/.local/bin/poetry),)
	@echo "installing poetry"
	curl -sSL https://install.python-poetry.org | python3 -
else
	@echo "poetry installation found"
endif
	~/.local/bin/poetry install

.PHONY: clean-pyc clean-build docs clean
