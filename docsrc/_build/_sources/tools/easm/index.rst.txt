Zscaler External Attack Surface Management (EASM) Tools
========================================================

The Zscaler External Attack Surface Management (EASM) tools provide **read-only** functionality for monitoring your organization's external attack surface, including findings, lookalike domains, and organization management.

.. note::
   EASM tools do not require ``ZSCALER_CUSTOMER_ID``. Only ``ZSCALER_CLIENT_ID``, ``ZSCALER_CLIENT_SECRET``, and ``ZSCALER_VANITY_DOMAIN`` are required.

Available Tools
---------------

.. list-table:: EASM Tools
   :header-rows: 1
   :widths: 30 70

   * - Tool Name
     - Description
   * - ``zeasm_list_organizations``
     - List all EASM organizations configured for the tenant
   * - ``zeasm_list_findings``
     - List all findings for an organization's internet-facing assets
   * - ``zeasm_get_finding_details``
     - Get detailed information for a specific finding
   * - ``zeasm_get_finding_evidence``
     - Get scan evidence attributed to a specific finding
   * - ``zeasm_get_finding_scan_output``
     - Get complete scan output for a specific finding
   * - ``zeasm_list_lookalike_domains``
     - List all lookalike domains detected for an organization
   * - ``zeasm_get_lookalike_domain``
     - Get details for a specific lookalike domain

Tool Details
------------

Organizations
~~~~~~~~~~~~~

zeasm_list_organizations
^^^^^^^^^^^^^^^^^^^^^^^^

List all organizations configured for a tenant in the EASM Admin Portal.

**Parameters:**

:param service: The service to use (default: "zeasm")
:type service: str

**Returns:**

- Dictionary containing:
  - ``results``: List of organization objects
  - ``total_results``: Total number of organizations

**Example:**

.. code-block:: python

   # List all EASM organizations
   orgs = zeasm_list_organizations()
   print(f"Total: {orgs['total_results']}")
   for org in orgs['results']:
       print(f"  {org['id']}: {org['name']}")

Findings
~~~~~~~~

zeasm_list_findings
^^^^^^^^^^^^^^^^^^^

List all findings identified and tracked for an organization's internet-facing assets.

**Parameters:**

:param org_id: The unique identifier for the organization
:type org_id: str
:param service: The service to use (default: "zeasm")
:type service: str

**Returns:**

- Dictionary containing:
  - ``results``: List of finding objects
  - ``total_results``: Total number of findings

**Example:**

.. code-block:: python

   # List all findings for an organization
   findings = zeasm_list_findings(org_id="3f61a446-1a0d-11f0-94e8-8a5f4d45e80c")
   print(f"Total: {findings['total_results']}")
   for finding in findings['results']:
       print(f"  {finding['id']}: {finding['category']}")

zeasm_get_finding_details
^^^^^^^^^^^^^^^^^^^^^^^^^

Get detailed information for a specific EASM finding by ID.

**Parameters:**

:param org_id: The unique identifier for the organization
:type org_id: str
:param finding_id: The unique identifier for the finding
:type finding_id: str
:param service: The service to use (default: "zeasm")
:type service: str

**Returns:**

- Dictionary containing finding details

**Example:**

.. code-block:: python

   # Get details for a specific finding
   details = zeasm_get_finding_details(
       org_id="3f61a446-1a0d-11f0-94e8-8a5f4d45e80c",
       finding_id="8abfc6a2b3058cb75de44c4c65ca4641"
   )
   print(details)

zeasm_get_finding_evidence
^^^^^^^^^^^^^^^^^^^^^^^^^^

Get scan evidence attributed to a specific EASM finding. This is a subset of the scan output.

**Parameters:**

:param org_id: The unique identifier for the organization
:type org_id: str
:param finding_id: The unique identifier for the finding
:type finding_id: str
:param service: The service to use (default: "zeasm")
:type service: str

**Returns:**

- Dictionary containing evidence object with ``content`` and ``source_type``

**Example:**

.. code-block:: python

   # Get evidence for a finding
   evidence = zeasm_get_finding_evidence(
       org_id="3f61a446-1a0d-11f0-94e8-8a5f4d45e80c",
       finding_id="8abfc6a2b3058cb75de44c4c65ca4641"
   )
   print(evidence['content'])

zeasm_get_finding_scan_output
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get complete scan output for a specific EASM finding.

**Parameters:**

:param org_id: The unique identifier for the organization
:type org_id: str
:param finding_id: The unique identifier for the finding
:type finding_id: str
:param service: The service to use (default: "zeasm")
:type service: str

**Returns:**

- Dictionary containing scan output object with ``content`` and ``source_type``

**Example:**

.. code-block:: python

   # Get scan output for a finding
   scan_output = zeasm_get_finding_scan_output(
       org_id="3f61a446-1a0d-11f0-94e8-8a5f4d45e80c",
       finding_id="8abfc6a2b3058cb75de44c4c65ca4641"
   )
   print(scan_output['content'])

Lookalike Domains
~~~~~~~~~~~~~~~~~

zeasm_list_lookalike_domains
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

List all lookalike domains detected for an organization's assets.

**Parameters:**

:param org_id: The unique identifier for the organization
:type org_id: str
:param service: The service to use (default: "zeasm")
:type service: str

**Returns:**

- Dictionary containing:
  - ``results``: List of lookalike domain objects
  - ``total_results``: Total number of lookalike domains

**Example:**

.. code-block:: python

   # List all lookalike domains for an organization
   domains = zeasm_list_lookalike_domains(org_id="3f61a446-1a0d-11f0-94e8-8a5f4d45e80c")
   print(f"Total: {domains['total_results']}")
   for domain in domains['results']:
       print(f"  {domain['domain_name']}")

zeasm_get_lookalike_domain
^^^^^^^^^^^^^^^^^^^^^^^^^^

Get details for a specific lookalike domain by domain name.

**Parameters:**

:param org_id: The unique identifier for the organization
:type org_id: str
:param lookalike_raw: The lookalike domain name (e.g., "example-domain.com")
:type lookalike_raw: str
:param service: The service to use (default: "zeasm")
:type service: str

**Returns:**

- Dictionary containing lookalike domain details

**Example:**

.. code-block:: python

   # Get details for a specific lookalike domain
   details = zeasm_get_lookalike_domain(
       org_id="3f61a446-1a0d-11f0-94e8-8a5f4d45e80c",
       lookalike_raw="assuredartners.com"
   )
   print(details)

Authentication
--------------

EASM tools support OneAPI authentication only (legacy authentication is not supported):

**OneAPI Authentication:**

- Uses OAuth2 client credentials
- Requires the following environment variables:

  * ``ZSCALER_CLIENT_ID``
  * ``ZSCALER_CLIENT_SECRET``
  * ``ZSCALER_VANITY_DOMAIN``

.. note::
   Unlike other Zscaler services, EASM does **not** require ``ZSCALER_CUSTOMER_ID``.

Common Use Cases
----------------

1. **Attack Surface Monitoring**: List and review findings across your organization's internet-facing assets
2. **Vulnerability Assessment**: Get detailed information about specific security findings
3. **Brand Protection**: Monitor and track lookalike domains that may be used for phishing
4. **Evidence Collection**: Retrieve scan evidence and outputs for security investigations
5. **Multi-Organization Management**: Manage EASM across multiple organizations in a tenant

Error Handling
--------------

All EASM tools include comprehensive error handling:

- **Authentication errors**: Invalid credentials or expired tokens
- **Permission errors**: Insufficient privileges for the requested operation
- **Validation errors**: Invalid parameters or malformed requests
- **Not Found errors**: Organization, finding, or domain not found

For detailed error information, check the tool response for error messages and status codes.

