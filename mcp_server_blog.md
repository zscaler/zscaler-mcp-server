# Zscaler MCP Server: Bringing Unified Security Automation to Your AI Agents

It feels like everywhere you look, people are talking about the Model Context Protocol (MCP)—the new standard for connecting AI agents and applications to real-world tools and APIs. MCP is quickly becoming the bridge that lets large language models (LLMs) and coding assistants do more than just answer questions: it lets them take action, automate workflows, and interact with your environment in powerful new ways.

But until now, most MCP servers have been limited to local, developer-focused setups. What if you could bring the full power of Zscaler's security cloud ZCC, ZDX, ZIA, and ZPA right to your favorite AI agent, with a single, unified, open-source server? That's exactly what we've built.

Today, we're excited to announce the preview version of **Zscaler MCP Server**, an open-source solution that brings the full power of Zscaler's security platform directly to your AI agents and automation workflows. Whether you're using Claude Desktop, Cursor, VS Code with Copilot, or any other MCP-compatible client, you can now manage your entire Zscaler environment through natural language conversations and automated workflows.

---

## »Zscaler's vision for MCP servers

At Zscaler, we view Model Context Protocol (MCP) servers as an essential bridge connecting enterprise security infrastructure with the rapidly evolving AI landscape. By leveraging standardized protocols like MCP, we can create secure, traceable interactions between AI agents and security systems, ensuring that security automation relies on trustworthy, up-to-date data and robust enterprise security policies — rather than just probabilistic assumptions.

As AI capabilities continue to advance, enterprises will increasingly expect these intelligent agents to perform critical security operations such as threat mitigation, policy management, or automated incident response. These operations, however, must be executed within a framework that enterprises can rely on and that upholds the zero-trust security principles essential to modern organizations. This is precisely where the Zscaler MCP Server plays its role: It empowers security professionals, developers, and platform teams to engage with Zscaler's integrated security platform through natural language and AI-driven interactions, enabling them to complete security tasks efficiently while maintaining security, compliance, and full auditability.

The Zscaler MCP Server maintains LLM neutrality, giving organizations the flexibility to leverage their existing AI investments and preferred LLMs, while security practitioners can choose the tools that best suit their workflow. Whether integrating with Claude, GPT, or any other MCP-compatible AI solution, the server delivers a uniform, secure gateway to your Zscaler environment.









 

## »What is the Zscaler MCP Server?

The Zscaler MCP Server is a Python-based, open-source application that exposes Zscaler's core services through a unified, MCP-compliant API. It's designed to be the missing link between your AI-powered agents and the full suite of Zscaler APIs, enabling seamless integration between your security infrastructure and modern AI workflows.



**Why is this a big deal?**  
With the Zscaler MCP Server, you can:
- **Automate security operations**: Across all Zscaler products from a single endpoint
- **Integrate with AI assistants**: To manage your environment using natural language
- **Orchestrate complex, cross-product workflows**: No more juggling multiple APIs or dashboards
- **Choose your API framework**: The MCP server can be configured to use either the new Zscaler OneAPI framework or the legacy API framework, depending on your organization's requirements

**Key highlights:**
- **Unified API**: Access Zscaler Client Connector (ZCC), Digital Experience (ZDX), Internet Access (ZIA), and Private Access (ZPA) from one place
- **Dual API Framework Support**: Full compatibility with both the new Zscaler OneAPI framework and the legacy API framework
- **Open Source & Extensible**: Released on GitHub for the community to use, extend, and contribute to
- **Powered by the Official Zscaler Python SDK**: All functionality is built on top of the [zscaler-sdk-python](https://github.com/zscaler/zscaler-sdk-python), ensuring reliability, security, and full compatibility with Zscaler's APIs

---

## »Works Seamlessly With Your Favorite AI Agents

The Zscaler MCP Server is designed and tested to work with the most popular AI-powered agents and developer tools, including:

- **Claude Desktop** ([claude.ai](https://claude.ai/)): Interact with your Zscaler environment using natural language prompts. The server appears in Claude's tools list, enabling you to run queries like "List ZPA Segment Groups" or "List ZIA Rule Labels" directly from chat.

- **Cursor** ([cursor.so](https://cursor.so/)): Integrate the MCP server as a tool in Cursor's "Agent Mode" for code and security automation.

- **Visual Studio Code** ([VS Code](https://code.visualstudio.com/)): Use with GitHub Copilot's Agent Mode to automate Zscaler tasks from your code editor.

- **Other MCP-compatible clients**: The server is built to the MCP standard, so it can be integrated with any client that supports MCP.

Getting started is easy—just follow the configuration steps in the [README](./README.md) for your preferred agent.







## »Flexible Deployment: Docker or Local Install

You can run the Zscaler MCP Server however you like, and regardless of your deployment method, you have the flexibility to use either the new OneAPI authentication or the legacy API framework.

### 🐳 **Docker (Recommended for Most Users)**
- **Portability & Isolation**: Run the server in a container for a consistent, dependency-free experience
- **Quick Start**:
  1. Install Docker Desktop
  2. Create a `.env` file with your Zscaler credentials
  3. Build and run the container with `make docker-build`
  4. Configure your MCP client (Claude, Cursor, VS Code, etc.) to connect to the Dockerized server

### 🛠️ **Local Installation (For Developers & Contributors)**
- **Editable Source**: Clone the repo and install dependencies locally for rapid development and customization
- **Dev Mode**:
  1. Clone the repository
  2. Install dependencies with `uv pip install -e .` or `pip install -r requirements.txt`
  3. Start the server with your preferred MCP client

Both methods are fully documented in the [README](./README.md), including sample configuration files for each supported agent.

---

## »Enterprise-Ready: Amazon Bedrock AgentCore Integration

For organizations looking to deploy the Zscaler MCP Server in enterprise environments, we're excited to announce **native integration with Amazon Bedrock AgentCore**. This enterprise-grade deployment option brings the full power of Zscaler security automation to AWS's managed AI infrastructure, enabling seamless integration with your existing AWS workflows and security practices.

### 🏢 **Why Amazon Bedrock AgentCore?**

Amazon Bedrock AgentCore provides a fully managed, scalable platform for running AI agents in production environments. By deploying the Zscaler MCP Server on AgentCore, you get:

- **Enterprise Security**: Built-in AWS security features including IAM roles, VPC isolation, and CloudWatch monitoring
- **Scalability**: Automatic scaling based on demand with managed container orchestration
- **Compliance**: Enterprise-grade logging, monitoring, and audit capabilities
- **Integration**: Seamless integration with existing AWS services and workflows
- **Reliability**: AWS-managed infrastructure with high availability and fault tolerance

### 🚀 **Getting Started with AgentCore**

Deploying to Amazon Bedrock AgentCore is straightforward and follows AWS best practices:

1. **IAM Configuration**: Set up the required IAM roles and policies for AgentCore execution
2. **Network Configuration**: Configure VPC settings for secure API communication
3. **Environment Variables**: Configure your Zscaler API credentials securely
4. **Deployment**: Deploy via AWS CLI or the AWS Console

The complete deployment guide is available in our [Amazon Bedrock AgentCore documentation](./docs/deployment/amazon_bedrock_agentcore.md), including detailed IAM policies, network requirements, and step-by-step deployment instructions.

### 🔧 **Enterprise Features**

When deployed on Amazon Bedrock AgentCore, the Zscaler MCP Server includes:

- **Secure Credential Management**: Environment variables for Zscaler API credentials
- **Network Security**: VPC configuration with proper outbound access controls
- **Monitoring & Logging**: CloudWatch integration for comprehensive observability
- **IAM Integration**: Role-based access control with fine-grained permissions
- **Container Security**: ECR-based image distribution with vulnerability scanning

This enterprise deployment option makes the Zscaler MCP Server ready for production use in large organizations, providing the security, scalability, and compliance features that enterprise environments require.

---

## »Real-World Use Cases

The Zscaler MCP Server provides practical capabilities for managing Zscaler environments through AI agents. Here are the key use cases and capabilities:

### **Unified Security Management**
The MCP server enables centralized management across all Zscaler services (ZCC, ZDX, ZIA, ZPA) through a single interface. This allows security teams to:

- Query and manage policies across multiple Zscaler products
- Retrieve device information and enrollment status
- Access firewall rules, URL categories, and network configurations
- Manage user access and authentication settings

### **Natural Language Security Operations**
Connect AI agents like Claude Desktop to perform security tasks using conversational language. Common operations include:

- "List all devices enrolled in ZCC"
- "Show me ZIA firewall rules for our development team"
- "Retrieve ZPA application segments and access policies"
- "Get ZDX performance metrics for our critical applications"

### **Automated Reporting and Compliance**
Generate comprehensive reports and audit data across Zscaler services:

- Device enrollment and compliance status reports
- Firewall rule and policy configurations

- Network configuration and topology information

### **Cross-Product Workflow Automation**
Orchestrate workflows that span multiple Zscaler products without switching between different APIs or dashboards. This enables:

- Consistent policy management across ZIA and ZPA
- Unified device management and monitoring
- Coordinated access control and network security
- Integrated reporting and compliance workflows

---

## »Built on the Official Zscaler Python SDK

Every feature in the MCP server is powered by the [zscaler-sdk-python](https://github.com/zscaler/zscaler-sdk-python), Zscaler's official Python SDK. This ensures:

- **Full API Coverage**: Access the latest Zscaler features as soon as they're available
- **Security & Reliability**: Built and maintained by Zscaler, with best practices and robust error handling
- **Community Support**: Leverage the SDK's documentation, examples, and active community

---

## »Access and use of beta technology

The Zscaler MCP Server is currently in **beta** and is intended for development, testing, and evaluation purposes. While we encourage you to try it and provide feedback, use in production settings should be carefully evaluated based on your organization's requirements.

The outputs and recommendations provided by the MCP server are generated dynamically and may vary based on the query, model, and the connected Zscaler environment. Users should thoroughly review all outputs/recommendations to ensure they align with their organization's security best practices, compliance requirements, and operational procedures before implementation.

---

## »Get Involved

The Zscaler MCP Server is released in **beta** and we invite you to try it, provide feedback, and contribute. Whether you're a security engineer, developer, or AI enthusiast, your input will help us make Zscaler automation more powerful and accessible for everyone.

**Ready to get started?**
Visit the [GitHub repository](https://github.com/zscaler/zscaler-mcp-server) to download the MCP server, read the docs, and join the conversation!

**Further Reading & References:**
- [Enhancing Zscaler Management with Claude Desktop Integrations](https://www.zscaler.com/blogs/product-insights/enhancing-zscaler-management-claude-desktop-integrations)
- [zscaler-sdk-python (Official SDK)](https://github.com/zscaler/zscaler-sdk-python)
- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)

---

## »What's Next?

We're excited to see how the community uses the Zscaler MCP Server to build innovative security automation workflows. In future releases, we plan to add:

- Enhanced error handling and retry mechanisms
- Additional Zscaler service integrations
- Pre-built workflow templates for common security scenarios
- Integration with popular CI/CD platforms
- Advanced authentication and security features

Stay tuned for updates, and don't forget to star the repository and join our community discussions!

---

**Note**: The suggestions for architecture diagrams, GIFs, and enhanced use case examples you mentioned in your notes would indeed make this article even more impactful. Consider adding those visual elements to complement the enhanced text content.

