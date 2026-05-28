.. _contributing:

Contributing
============

.. warning::

   **Preview release — external contributions paused.**

   The Zscaler MCP Server is currently in **preview** and we are **not accepting external pull requests at this time**. The codebase, public APIs, and toolset shape are still stabilising, and merging outside contributions before the surface settles would create churn for early adopters and reviewers alike.

   If you would like to report a bug, request a feature, or share feedback during the preview, please open an issue on `GitHub Issues <https://github.com/zscaler/zscaler-mcp-server/issues>`__ or start a thread in `GitHub Discussions <https://github.com/zscaler/zscaler-mcp-server/discussions>`__. We read every one.

   This page is kept up to date so that, when the project moves to general availability, contributors will already have the development workflow documented. The instructions below also apply to internal Zscaler engineers working on the server today.

See the full `CONTRIBUTING.md <https://github.com/zscaler/zscaler-mcp-server/blob/master/CONTRIBUTING.md>`__ on GitHub for the canonical guide.

Getting started
---------------

.. code-block:: bash

   git clone https://github.com/zscaler/zscaler-mcp-server.git
   cd zscaler-mcp-server

   # Create .venv and install dependencies
   uv sync --all-extras

   # Activate the venv
   source .venv/bin/activate

Conventional Commits
--------------------

This project uses `Conventional Commits <https://www.conventionalcommits.org/>`__ for automated releases and semantic versioning. Format your commit messages as:

.. code-block:: text

   feat(zia): add support for new URL filtering rule type
   fix(zpa): handle empty server group response
   docs(deployment): update Azure AKS preview limitations

Common types: ``feat``, ``fix``, ``docs``, ``chore``, ``test``, ``refactor``, ``perf``, ``ci``.

Running tests
-------------

.. code-block:: bash

   # Unit + integration tests
   pytest tests/ --ignore=tests/e2e -v

   # End-to-end tests (requires Zscaler credentials)
   pytest --run-e2e tests/e2e/

   # E2E with verbose output (note: -s required to see output)
   pytest --run-e2e -v -s tests/e2e/

Lint
----

.. code-block:: bash

   ruff check .
   ruff format .

Adding a new tool
-----------------

1. Create the tool module in ``zscaler_mcp/tools/{service}/``
2. Add the tool definition to the service class in ``services.py``
3. Import the tool function in the service class's ``register_tools`` method
4. Run ``make generate-docs`` to refresh the auto-generated docs
5. Commit using Conventional Commits (``feat({service}): add {tool_name}``)

See :doc:`building-from-source` for the full dev environment setup.

Code of conduct
---------------

Please read our `Code of Conduct <https://github.com/zscaler/zscaler-mcp-server/blob/master/CODE_OF_CONDUCT.md>`__ before contributing.
