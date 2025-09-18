Server API
==========

The main MCP server implementation and configuration.

.. automodule:: zscaler_mcp.server
   :members:
   :undoc-members:
   :show-inheritance:

Server Configuration
--------------------

The server can be configured using environment variables or command-line arguments.

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Server Configuration Environment Variables
   :header-rows: 1
   :widths: 25 25 50

   * - Variable
     - Default
     - Description
   * - ``ZSCALER_MCP_SERVICES``
     - All services
     - Comma-separated list of services to enable
   * - ``ZSCALER_MCP_TRANSPORT``
     - ``stdio``
     - Transport method (stdio, sse, streamable-http)
   * - ``ZSCALER_MCP_DEBUG``
     - ``false``
     - Enable debug logging
   * - ``ZSCALER_MCP_HOST``
     - ``127.0.0.1``
     - Host for HTTP transports
   * - ``ZSCALER_MCP_PORT``
     - ``8000``
     - Port for HTTP transports

Command Line Arguments
~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Server Command Line Arguments
   :header-rows: 1
   :widths: 25 25 50

   * - Argument
     - Default
     - Description
   * - ``--services``
     - All services
     - Comma-separated list of services to enable
   * - ``--transport``
     - ``stdio``
     - Transport method (stdio, sse, streamable-http)
   * - ``--debug``
     - ``false``
     - Enable debug logging
   * - ``--host``
     - ``127.0.0.1``
     - Host for HTTP transports
   * - ``--port``
     - ``8000``
     - Port for HTTP transports

Transport Methods
-----------------

The server supports three transport methods:

Stdio Transport
~~~~~~~~~~~~~~~

Default transport method using standard input/output for communication.

.. code-block:: python

   from zscaler_mcp.server import main
   main()

SSE Transport
~~~~~~~~~~~~~

Server-Sent Events transport for web-based clients.

.. code-block:: python

   from zscaler_mcp.server import main
   main(transport="sse", host="0.0.0.0", port=8000)

Streamable HTTP Transport
~~~~~~~~~~~~~~~~~~~~~~~~~

HTTP-based transport with streaming support.

.. code-block:: python

   from zscaler_mcp.server import main
   main(transport="streamable-http", host="0.0.0.0", port=8000)
