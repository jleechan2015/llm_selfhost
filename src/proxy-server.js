const fastify = require('fastify');
const findFreePort = require('find-free-port');
const ConfigLoader = require('./config-loader');
const BackendFactory = require('./backend-factory');

class ProxyServer {
  constructor(configLoader = null) {
    this.configLoader = configLoader || new ConfigLoader();
    this.app = null;
    this.config = null;
    this.currentStrategy = null;
    this.server = null;
  }

  async initialize(workspaceDir = process.cwd()) {
    // Load configuration
    this.config = await this.configLoader.load(workspaceDir);
    
    // Create Fastify app
    this.app = fastify({
      logger: process.env.NODE_ENV !== 'test'
    });

    // Register routes
    this.registerRoutes();

    // Initialize backend strategy
    await this.initializeBackend();

    return this.app;
  }

  registerRoutes() {
    // Health check endpoints
    this.app.get('/', async (request, reply) => {
      return {
        service: 'Multi-LLM Proxy Server',
        status: 'running',
        backend: this.config.backend,
        version: '1.0.0',
        timestamp: new Date().toISOString()
      };
    });

    this.app.get('/health', async (request, reply) => {
      const health = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        backend: this.config.backend,
        port: this.server ? this.server.address()?.port : null
      };

      // Check backend health if supported
      if (this.currentStrategy && typeof this.currentStrategy.checkHealth === 'function') {
        try {
          const backendHealth = await this.currentStrategy.checkHealth();
          health.backendHealth = backendHealth;
        } catch (error) {
          health.backendHealth = { status: 'unhealthy', error: error.message };
          health.status = 'degraded';
        }
      }

      return health;
    });

    // Anthropic API compatible endpoints
    this.app.get('/v1/models', async (request, reply) => {
      return {
        object: 'list',
        data: [
          {
            id: 'qwen3-coder',
            object: 'model',
            created: Math.floor(Date.now() / 1000),
            owned_by: 'llm-proxy',
            type: 'text'
          }
        ]
      };
    });

    this.app.post('/v1/messages', async (request, reply) => {
      try {
        const { messages, max_tokens, temperature, model } = request.body;

        if (!messages || !Array.isArray(messages) || messages.length === 0) {
          reply.code(400);
          return { error: 'Messages field is required and must be a non-empty array' };
        }

        const options = {
          max_tokens,
          temperature,
          model: model || 'qwen3-coder'
        };

        const result = await this.currentStrategy.executeRequest(messages, options);
        return result;
      } catch (error) {
        this.app.log.error('Request failed:', error);
        
        reply.code(500);
        return {
          error: error.message,
          recommendations: error.recommendations || [
            'Check backend configuration',
            'Try switching to a different backend'
          ]
        };
      }
    });
  }

  async initializeBackend() {
    const backendConfig = this.config.backends[this.config.backend];
    if (!backendConfig) {
      throw new Error(`Backend "${this.config.backend}" not found in configuration`);
    }

    this.currentStrategy = BackendFactory.createStrategy(backendConfig);
  }

  async start(workspaceDir = process.cwd()) {
    if (!this.app) {
      await this.initialize(workspaceDir);
    }

    let port = this.config.port;
    
    // Handle automatic port selection
    if (port === 'auto' || port === 0) {
      const freePorts = await findFreePort(8000, 8100);
      port = freePorts[0];
    }

    this.server = await this.app.listen({
      port: port,
      host: '0.0.0.0'
    });

    return {
      port: this.server.address().port,
      url: `http://localhost:${this.server.address().port}`
    };
  }

  async stop() {
    if (this.server) {
      await this.app.close();
      this.server = null;
    }
  }

  async reloadConfig(workspaceDir = process.cwd()) {
    this.config = await this.configLoader.load(workspaceDir);
    await this.initializeBackend();
  }

  getConfig() {
    return this.config;
  }

  getCurrentBackend() {
    return this.config?.backend;
  }

  getBackendStrategy() {
    return this.currentStrategy;
  }
}

module.exports = ProxyServer;