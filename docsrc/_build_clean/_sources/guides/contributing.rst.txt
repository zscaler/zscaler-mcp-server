.. _contributing-guide:

Contributing Guide
==================

Getting Started for Contributors
--------------------------------

We welcome contributions to the Zscaler Integrations MCP Server! This guide will help you get started with contributing to the project.

Prerequisites
-------------

- Python 3.11, 3.12, or 3.13
- Git
- Basic understanding of the Model Context Protocol (MCP)
- Familiarity with Zscaler services

Development Setup
-----------------

1. Fork the repository on GitHub
2. Clone your fork locally:

.. code-block:: bash

   git clone https://github.com/your-username/zscaler-mcp-server.git
   cd zscaler-mcp-server

3. Create a virtual environment:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

4. Install dependencies:

.. code-block:: bash

   pip install -r requirements.txt

5. Install development dependencies:

.. code-block:: bash

   pip install -r requirements-dev.txt

Commit Message Format
---------------------

This project uses `Conventional Commits <https://www.conventionalcommits.org/>`__ for automated releases and semantic versioning.

Format: ``<type>[optional scope]: <description>``

Types:
- ``feat``: A new feature
- ``fix``: A bug fix
- ``docs``: Documentation only changes
- ``style``: Changes that do not affect the meaning of the code
- ``refactor``: A code change that neither fixes a bug nor adds a feature
- ``test``: Adding missing tests or correcting existing tests
- ``chore``: Changes to the build process or auxiliary tools

Examples:
- ``feat(zcc): add list_trusted_networks tool``
- ``fix(zia): resolve authentication timeout issue``
- ``docs: update installation instructions``

Pull Request Process
--------------------

1. Create a feature branch from ``main``
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation as needed
6. Submit a pull request with a clear description

Testing
-------

Run the test suite:

.. code-block:: bash

   pytest tests/

Run specific test categories:

.. code-block:: bash

   pytest tests/e2e/  # End-to-end tests
   pytest tests/unit/ # Unit tests

Code Style
----------

We follow Python best practices and use:

- Black for code formatting
- isort for import sorting
- flake8 for linting
- mypy for type checking

Run formatting and linting:

.. code-block:: bash

   black .
   isort .
   flake8
   mypy

Documentation
-------------

When adding new tools or features:

1. Update the tool's docstring with examples
2. Add the tool to the appropriate service in ``services.py``
3. Update the README.md with the new tool
4. Update the Sphinx documentation

Questions?
----------

If you have questions about contributing, please:

1. Check existing GitHub issues
2. Create a new issue with the "question" label
3. Join our community discussions

Thank you for contributing to the Zscaler Integrations MCP Server!
