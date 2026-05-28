.. _integration-vscode:

VS Code + GitHub Copilot
========================

GitHub Copilot in VS Code supports MCP servers via **Agent Mode**.

Install and configure
---------------------

1. Open VS Code and ensure GitHub Copilot is installed
2. Switch Copilot to **Agent Mode** (via the gear menu in Copilot Chat)
3. Add the Zscaler MCP Server to your MCP configuration:

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "uvx",
         "args": ["--env-file", "/path/to/.env", "zscaler-mcp-server"]
       }
     }
   }

4. Refresh the tools list in Copilot Chat
5. Prompt the agent

With service selection
----------------------

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "uvx",
         "args": [
           "--env-file", "/path/to/.env",
           "zscaler-mcp-server",
           "--services", "zia,zpa"
         ]
       }
     }
   }

With Docker
-----------

.. code-block:: json

   {
     "mcpServers": {
       "zscaler-mcp-server": {
         "command": "docker",
         "args": [
           "run", "-i", "--rm",
           "--env-file", "/full/path/to/.env",
           "zscaler/zscaler-mcp-server:latest"
         ]
       }
     }
   }

Try prompts
-----------

- *"Create a ZPA segment group named DevServices"*
- *"List my ZIA URL categories"*
- *"Show the experience score for my Toronto office in ZDX"*

Learn more about Agent Mode in the `VS Code Copilot documentation <https://code.visualstudio.com/docs/copilot/chat/chat-agent-mode>`__.

Resources
---------

- :doc:`../../skills/index`
- :doc:`../../guides/troubleshooting`
