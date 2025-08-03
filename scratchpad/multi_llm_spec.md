---

# **Design Documentation: Multi-LLM Proxy Server**

This document contains the complete product and engineering plans for creating a standalone, npm-installable proxy service that provides configurable multi-LLM backend routing for any repository using Claude CLI.

---

# **Part 1: Product Specification**

## **Table of Contents**

1. [Executive Summary](https://www.google.com/search?q=%23executive-summary)
2. [Goals & Objectives](https://www.google.com/search?q=%23goals--objectives)
3. [User Stories](https://www.google.com/search?q=%23user-stories)
4. [Feature Requirements](https://www.google.com/search?q=%23feature-requirements)
5. [UI/UX Requirements](https://www.google.com/search?q=%23uiux-requirements)
6. [Success Criteria](https://www.google.com/search?q=%23success-criteria)
7. [Metrics & KPIs](https://www.google.com/search?q=%23metrics--kpis)

## **Executive Summary**

This project creates a standalone proxy service installable via npm that provides multi-LLM backend routing for any repository using Claude CLI. Users can install the proxy globally (`npm install -g @jleechan/llm-proxy-server`) and configure any project to route Claude CLI requests through multiple LLM providers. The primary value is providing universal flexibility, cost control, and performance optimization by enabling managed services like Cerebras or cost-effective, self-hosted solutions on Vast.ai and RunPod with enterprise-grade caching. Success is defined by seamless installation, configuration portability across repositories, and reliable multi-backend routing.

## **Goals & Objectives**

### **Primary Goals**

* **Business Goal:** Reduce operational and development costs by up to 80% by shifting high-volume, repetitive tasks from premium SaaS LLMs to cached, self-hosted endpoints.
* **User Goal:** Empower users to select the optimal LLM backend based on their specific needs for performance (SaaS), cost (Vast.ai), or reliability (RunPod).
* **User Goal:** Enable access to specialized models like Qwen3-Coder that may not be available through the default provider.
* **Developer Goal:** Provide a universal, installable solution that works across any repository without modifying Claude CLI itself.

### **Secondary Goals**

* **Resilience:** Create a system that can failover to an alternative backend if the primary provider is down.
* **Developer Experience:** Establish a modular architecture that allows new LLM providers to be added with minimal code changes.
* **Portability:** Enable consistent LLM backend configuration across multiple repositories and development environments.

## **User Stories**

1. **As a developer seeking simplicity**, I want to install and configure the proxy to use a Cerebras Qwen3-Coder endpoint, so that I can leverage a fully managed, high-performance service with zero setup overhead.
   * **Acceptance Criteria:**
     * \[ \] `npm install -g @jleechan/llm-proxy-server` installs successfully
     * \[ \] The proxy accepts a configuration pointing to the Cerebras API URL and an API key
     * \[ \] Claude CLI commands successfully route through the proxy and return responses from Cerebras
2. **As a power user focused on cost optimization**, I want to configure the proxy to use a self-hosted Qwen3-Coder on Vast.ai with Redis Enterprise caching, so that I can dramatically reduce token costs for repeated queries.
   * **Acceptance Criteria:**
     * \[ \] The proxy accepts a configuration pointing to a self-hosted endpoint URL
     * \[ \] Claude CLI commands successfully route to the Vast.ai endpoint
     * \[ \] A second, identical command is served from the Redis cache, confirmed by logging
3. **As a developer prioritizing stability**, I want to configure the proxy to use a self-hosted Qwen3-Coder on RunPod with persistent storage, so that my self-hosted endpoint has higher uptime and my models persist across restarts.
   * **Acceptance Criteria:**
     * \[ \] The proxy accepts a configuration pointing to a self-hosted RunPod URL
     * \[ \] Claude CLI commands successfully route to the RunPod endpoint
     * \[ \] The RunPod instance can be stopped and restarted without needing to re-download the LLM
4. **As a developer working across multiple repositories**, I want to install the proxy once globally and use it in any project, so that I can maintain consistent LLM backend configuration across all my codebases.
   * **Acceptance Criteria:**
     * \[ \] Global installation works: `npm install -g @jleechan/llm-proxy-server`
     * \[ \] Any repository can use `export ANTHROPIC_BASE_URL=http://localhost:8000`
     * \[ \] Configuration is portable across projects via config files

## **Feature Requirements**

### **Functional Requirements**

1. **NPM Distribution:** The proxy must be installable via `npm install -g @jleechan/llm-proxy-server` and provide a CLI interface.
2. **Configurable Backend:** The proxy must support configuration methods (environment variables, config files) to specify the active LLM backend.
3. **Request Routing:** The proxy server must intercept Claude CLI API requests and route them to the appropriate provider's endpoint.
4. **Authentication Handling:** The system must manage different authentication schemes (API keys for Cerebras, dummy keys for self-hosted proxies).
5. **Provider Support:** The initial implementation must support three providers: Cerebras (SaaS), Vast.ai (self-hosted), and RunPod (self-hosted).
6. **Multi-Repository Support:** The proxy must work with any repository using Claude CLI by setting `ANTHROPIC_BASE_URL`.

### **Non-Functional Requirements**

1. **Performance:** The overhead introduced by the routing logic should be negligible (\<50ms). End-to-end latency for self-hosted options should be under 3 seconds for a p95 response time.
2. **Security:** All secrets (API keys) must be handled securely and never logged or exposed in error messages.
3. **Usability:** Switching between backends should be achievable by changing a single configuration variable.

## **UI/UX Requirements**

This is a backend proxy service with a CLI interface for management. The proxy provides these command-line interactions:

- **Installation**: `npm install -g @jleechan/llm-proxy-server`
- **Startup**: `llm-proxy start [--config path/to/config.json]`
- **Configuration**: `llm-proxy setup` (generates config templates)
- **Status**: `llm-proxy status` (shows running backends and health)

The user experience is defined by simple installation, intuitive configuration, and seamless integration with existing Claude CLI workflows.

## **Success Criteria**

* **Feature Complete Checklist:**
  * \[ \] NPM package installs globally and provides `llm-proxy` CLI command
  * \[ \] Proxy successfully routes requests using the Cerebras backend
  * \[ \] Proxy successfully routes requests using the Vast.ai + Redis backend
  * \[ \] Proxy successfully routes requests using the RunPod backend
  * \[ \] Configuration is loaded correctly from files and environment variables
  * \[ \] Multiple repositories can use the same proxy instance simultaneously
* **User Acceptance Tests:**
  * \[ \] A user can install the proxy globally and start it in under 2 minutes
  * \[ \] A user can configure any repository to use the proxy with a single environment variable
  * \[ \] A user can switch backends by editing a config file without restarting Claude CLI

## **Metrics & KPIs**

* **Adoption Rate:** Track the percentage of users who configure a non-default backend.
* **Performance:** Monitor average latency, p95 latency, and error rate for each supported backend.
* **Cost Savings:** Calculate the estimated monthly cost savings for users utilizing the self-hosted options versus the default SaaS provider based on usage volume.
* **Distribution Metrics:** Track npm download count, installation success rate, and global vs local installs.

## **Distribution & Package Management**

### **NPM Package Details**
- **Package Name**: `@jleechan/llm-proxy-server`
- **Installation**: `npm install -g @jleechan/llm-proxy-server`
- **CLI Commands**:
  - `llm-proxy start [--config path/to/config.json] [--port 8000]`
  - `llm-proxy setup` (generates config templates)
  - `llm-proxy status` (shows running backends and health)
  - `llm-proxy stop` (gracefully shutdown)

### **Configuration Management**
- **Global Config**: `~/.llm-proxy/config.json` (user-wide defaults)
- **Project Config**: `.llmrc.json` or `llm.config.js` (repository-specific)
- **Environment Variables**: `LLM_BACKEND_CONFIG`, `LLM_PROXY_PORT`

### **Integration Pattern**
```bash
# One-time setup
npm install -g @jleechan/llm-proxy-server
llm-proxy setup

# Per-repository usage
export ANTHROPIC_BASE_URL="http://localhost:8000"
claude "Write a Python function"  # Routes through proxy
```

### **Multi-Repository Support**
- Single proxy instance serves multiple repositories simultaneously
- Each repository uses `ANTHROPIC_BASE_URL=http://localhost:8000`
- Configuration changes apply to all connected repositories
- No per-repository installation required

---

---

# **Part 2: Engineering Design**

## **Table of Contents**

1. [Engineering Goals](https://www.google.com/search?q=%23engineering-goals)
2. [Engineering Tenets](https://www.google.com/search?q=%23engineering-tenets)
3. [Technical Overview](https://www.google.com/search?q=%23technical-overview)
4. [System Design](https://www.google.com/search?q=%23system-design)
5. [Implementation Plan](https://www.google.com/search?q=%23implementation-plan)
6. [Testing Strategy](https://www.google.com/search?q=%23testing-strategy)
7. [Risk Assessment](https://www.google.com/search?q=%23risk-assessment)
8. [Decision Records](https://www.google.com/search?q=%23decision-records)
9. [Rollout Plan](https://www.google.com/search?q=%23rollout-plan)
10. [Monitoring & Success Metrics](https://www.google.com/search?q=%23monitoring--success-metrics)
11. [Automation Hooks](https://www.google.com/search?q=%23automation-hooks)

## **Engineering Goals**

### **Primary Engineering Goals**

1. **Modularity:** Implement a "Strategy" design pattern for the API client, allowing new LLM providers to be added by creating a single new class, with zero changes to the core CLI logic.
2. **Reliability:** Achieve a \>99.9% successful API translation rate for the self-hosted LiteLLM proxy for all valid requests.
3. **Performance:** Ensure the self-hosted proxy adds less than 100ms of overhead to any request.

### **Secondary Engineering Goals**

* **Maintainability:** Refactor the existing API client to be more abstract and easier to test.
* **Developer Productivity:** Provide a clear, documented process for developers to add and test new LLM backends.

## **Engineering Tenets**

### **Core Principles**

1. **Simplicity**: The method for a user to switch between backends must be a single, simple configuration change.
2. **Reliability First**: The default recommendation for self-hosting will be RunPod with persistent storage due to its higher intrinsic reliability over a pure marketplace solution.
3. **Testability**: All backend client implementations must be unit-testable with mocked dependencies. An integration test suite will validate against live endpoints.
4. **Observability**: The chosen backend and the result of the API call (success, failure, latency) must be logged for debugging and performance monitoring.

## **Technical Overview**

The core of this project is a standalone Node.js proxy server that implements the BackendStrategy pattern for multi-LLM routing. The proxy server is distributed as an npm package and runs independently of Claude CLI. A configuration loader reads settings from files or environment variables defining the active backend and credentials. A factory instantiates the correct concrete strategy (e.g., CerebrasStrategy, SelfHostedProxyStrategy). The self-hosted backends (Vast.ai, RunPod) both use the SelfHostedProxyStrategy, configured to point to the appropriate URL. This leverages the existing Python-based Ollama + FastAPI proxy architecture from this repository.

## **System Design**

### **Component Architecture**

```
graph TD
    subgraph "Any Repository"
        A[Claude CLI] --> B[ANTHROPIC_BASE_URL=localhost:8000]
    end
    
    subgraph "NPM Global Package: @jleechan/llm-proxy-server"
        B --> C[Proxy Server :8000]
        C --> D{Config Loader}
        D --> E[Backend Factory]
        E --> F{BackendStrategy Interface}
    end

    F --> G[CerebrasStrategy]
    F --> H[SelfHostedProxyStrategy]

    subgraph "External Services"
        G --> I((Cerebras API))
        H --> J[Python FastAPI Proxy on Vast.ai/RunPod]
        J --> K[Ollama w/ Qwen3-Coder]
        J --> L((Redis Enterprise API))
    end
```

### **Deployment Architecture**
```
npm install -g → llm-proxy start → Any Repository (ANTHROPIC_BASE_URL) → Multi-Backend Router → LLM Services
```

### **API Design**

The proxy server exposes Anthropic API-compatible endpoints that Claude CLI expects:

- **POST /v1/messages** - Message completion (routes to configured backend)
- **GET /v1/models** - List available models (aggregated from backends)
- **GET /health** - Proxy health and backend status

The BackendStrategy interface defines a standard method `executeRequest(prompt, options)`, and each implementation translates this to the specific format required by its target (Cerebras, self-hosted proxy, etc.).

### **Database Design**

The caching mechanism for self-hosted solutions will be managed by Redis Enterprise, interfaced via the LiteLLM proxy. LiteLLM has built-in support for Redis caching, so no custom database schema or logic is required. We only need to provide LiteLLM with the Redis endpoint credentials.

## **Implementation Plan**

### **AI-Assisted Timeline (Claude Code CLI)**

#### **Phase 1: NPM Package Infrastructure (20 min - 3 agents parallel)**

* **Agent 1 (Package Setup):** Creates Node.js package structure with CLI interface, package.json, and npm publish workflow.
* **Agent 2 (Config System):** Implements config loading from files (`~/.llm-proxy/config.json`, `.llmrc.json`) and environment variables.
* **Agent 3 (Core Server):** Creates Express.js/Fastify server with Anthropic API-compatible endpoints (`/v1/messages`, `/v1/models`, `/health`).

#### **Phase 2: Strategy Implementation (20 min - 2 agents parallel)**

* **Agent 4 (SaaS Strategy):** Implements CerebrasStrategy class with API key authentication and request formatting.
* **Agent 5 (Self-Hosted Strategy):** Implements SelfHostedProxyStrategy that connects to existing Python FastAPI proxies (this repo's architecture).

#### **Phase 3: CLI & Testing (20 min - 2 agents parallel)**

* **Agent 6 (CLI Commands):** Implements `llm-proxy start/stop/status/setup` commands with proper process management.
* **Agent 7 (Testing):** Creates unit tests for strategies and integration tests against live endpoints, plus npm install/uninstall tests.

**Total Estimated Time: 60 minutes**

### **Leveraging Existing Architecture**

This Node.js proxy will integrate with the existing Python-based infrastructure in this repository:

- **Reuse Python Proxies**: The `SelfHostedProxyStrategy` will connect to existing `simple_api_proxy.py` and `api_proxy.py` servers
- **Leverage Install Scripts**: Use existing `install.sh` and `startup_llm.sh` for vast.ai deployment
- **Maintain Compatibility**: Preserve all existing Anthropic API compatibility and Redis caching functionality
- **Hybrid Architecture**: Node.js for distribution/routing, Python for LLM inference and caching

**Migration Path**: Current Python proxy users can install the npm package and point it to their existing proxy URLs with zero changes to their backend infrastructure.

## **Testing Strategy**

### **Unit Tests (/tdd)**

* Test the configuration loader with various valid and invalid config files.
* Test that the Backend Factory produces the correct strategy object based on the config.
* Test each BackendStrategy implementation with a mocked httpx client to ensure correct request headers, body, and URL are generated.

### **Integration Tests**

* A separate test suite will be created that reads a special test configuration (e.g., secrets.ci.json).
* This suite will contain "live fire" tests that make actual API calls to provisioned test endpoints for Cerebras, Vast.ai, and RunPod.
* These tests will be run nightly and on every merge to the main branch to detect provider API changes or regressions.

## **Risk Assessment**

### **Technical Risks**

* **High Risk**: **Self-Hosted Endpoint Instability.** Vast.ai instances can be unreliable. **Mitigation**: Strongly recommend RunPod Secure Cloud with persistent storage as the primary self-hosting option. Implement connection timeouts and retries in the SelfHostedProxyStrategy.
* **Medium Risk**: **Provider API Divergence.** Cerebras and the OpenAI-compatible API from LiteLLM may change. **Mitigation**: The nightly integration test suite will immediately detect breaking changes. The BackendStrategy pattern isolates the impact of any change to a single class.
* **Low Risk**: **Credential Leakage.** **Mitigation**: Enforce the use of environment variables for all secrets and ensure no secrets are ever logged.

## **Decision Records**

### **Architecture Decisions**

**\*\*Decision\*\***: Use the Strategy Design Pattern for backend communication.
**\*\*Date\*\***: 2025-08-03
**\*\*Context\*\***: The CLI needs to support multiple, swappable API backends with different authentication and request formats.
**\*\*Options\*\***: 1\) A large \`if/else\` block in the API client. 2\) The Strategy Pattern.
**\*\*Rationale\*\***: The Strategy Pattern is vastly more modular, scalable, and testable. Adding a new provider requires adding one new file, not modifying a complex conditional block.
**\*\*Consequences\*\***: Slightly more initial setup work to define the interface and factory.

**\*\*Decision\*\***: Use LiteLLM as the standard proxy for all self-hosted models.
**\*\*Date\*\***: 2025-08-03
**\*\*Context\*\***: We need a way to make self-hosted Ollama models compatible with clients expecting a standard API format.
**\*\*Options\*\***: 1\) Build a custom Flask/FastAPI proxy. 2\) Use LiteLLM.
**\*\*Rationale\*\***: LiteLLM is a production-ready, open-source tool specifically designed for this purpose. It supports caching, multiple backends, and a standard OpenAI-compatible API out of the box, saving significant development time.
**\*\*Consequences\*\***: Adds a dependency on the LiteLLM project.

## **Rollout Plan**

1. **Phase 1 (Internal Release):** The feature will be merged but disabled by default. It can be enabled by setting an environment variable ENABLE\_MULTI\_BACKEND=true.
2. **Phase 2 (Power-User Beta):** Document the new feature in advanced documentation and invite power users to test it. Gather feedback on the setup process for self-hosted options.
3. **Phase 3 (General Availability):** Once stable, enable the feature by default and update the main user documentation.

## **Monitoring & Success Metrics**

* **Logging:** The CLI will log which backend strategy is being used for each command invocation.
* **Performance Monitoring:** The CLI will log the end-to-end latency of each API call. This data can be optionally collected from users to build performance dashboards.
* **Error Tracking:** All API failures, connection errors, or timeouts will be logged with context, including which backend was used.

## **Automation Hooks**

### **CI/CD Integration**

* A GitHub Actions workflow will trigger on every Pull Request.
* **Unit Tests:** The workflow will run the full unit test suite.
* **Integration Tests:** For PRs merged to main, the workflow will run the integration test suite against live, sandboxed endpoints. A failure will trigger an alert.
* **Security:** A secret scanning tool will be run to ensure no credentials have been accidentally committed.