// Using Fastify's built-in testing with inject
const ProxyServer = require('../../src/proxy-server');
const ConfigLoader = require('../../src/config-loader');
const fs = require('fs-extra');
const path = require('path');
const os = require('os');

// Mock the strategies
jest.mock('../../src/strategies/cerebras-strategy');
jest.mock('../../src/strategies/self-hosted-strategy');

const CerebrasStrategy = require('../../src/strategies/cerebras-strategy');
const SelfHostedStrategy = require('../../src/strategies/self-hosted-strategy');

describe('ProxyServer Integration', () => {
  let server;
  let app;
  let tempDir;

  const mockCerebrasResponse = {
    id: 'msg_123',
    type: 'message',
    role: 'assistant',
    content: [{ type: 'text', text: 'Hello from Cerebras!' }],
    model: 'qwen3-coder',
    stop_reason: 'end_turn',
    usage: { input_tokens: 5, output_tokens: 3 }
  };

  beforeEach(async () => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'proxy-server-test-'));
    
    // Create test config
    const testConfig = {
      backend: 'cerebras',
      port: 0, // Use random available port
      backends: {
        'cerebras': {
          type: 'cerebras',
          apiKey: 'test-key'
        },
        'self-hosted': {
          type: 'self-hosted',
          url: 'http://localhost:8000'
        }
      }
    };

    await fs.writeJson(path.join(tempDir, '.llmrc.json'), testConfig);

    // Mock strategy implementations
    CerebrasStrategy.mockImplementation(() => ({
      executeRequest: jest.fn().mockResolvedValue(mockCerebrasResponse)
    }));

    SelfHostedStrategy.mockImplementation(() => ({
      executeRequest: jest.fn().mockResolvedValue(mockCerebrasResponse),
      checkHealth: jest.fn().mockResolvedValue({ status: 'healthy' })
    }));

    const configLoader = new ConfigLoader(tempDir);
    server = new ProxyServer(configLoader);
    await server.initialize(tempDir);
    app = server.app;
  });

  afterEach(async () => {
    if (server) {
      await server.stop();
    }
    if (tempDir) {
      fs.removeSync(tempDir);
    }
    jest.clearAllMocks();
  });

  describe('Health Endpoints', () => {
    test('GET / should return service status', async () => {
      const response = await app.inject({
        method: 'GET',
        url: '/'
      });
      
      expect(response.statusCode).toBe(200);
      const body = JSON.parse(response.payload);
      expect(body).toMatchObject({
        service: 'Multi-LLM Proxy Server',
        status: 'running',
        backend: 'cerebras'
      });
    });

    test('GET /health should return detailed health status', async () => {
      const response = await app.inject({
        method: 'GET',
        url: '/health'
      });
      
      expect(response.statusCode).toBe(200);
      const body = JSON.parse(response.payload);
      expect(body).toHaveProperty('status');
      expect(body).toHaveProperty('timestamp');
      expect(body).toHaveProperty('backend');
    });
  });

  describe('Model Endpoints', () => {
    test('GET /v1/models should return available models', async () => {
      const response = await app.inject({
        method: 'GET',
        url: '/v1/models'
      });
      
      expect(response.statusCode).toBe(200);
      const body = JSON.parse(response.payload);
      expect(body).toMatchObject({
        object: 'list',
        data: expect.arrayContaining([
          expect.objectContaining({
            id: expect.any(String),
            object: 'model',
            owned_by: 'llm-proxy'
          })
        ])
      });
    });
  });

  describe('Message Completion', () => {
    test('POST /v1/messages should route request to active backend', async () => {
      const requestBody = {
        messages: [
          { role: 'user', content: 'Hello, world!' }
        ],
        max_tokens: 100
      };

      const response = await app.inject({
        method: 'POST',
        url: '/v1/messages',
        payload: requestBody
      });

      expect(response.statusCode).toBe(200);
      const body = JSON.parse(response.payload);
      expect(body).toEqual(mockCerebrasResponse);
      
      // Verify the strategy was created (the response confirms it worked)
      expect(CerebrasStrategy).toHaveBeenCalled();
    });

    test('should handle missing messages field', async () => {
      const response = await app.inject({
        method: 'POST',
        url: '/v1/messages',
        payload: {}
      });

      expect(response.statusCode).toBe(400);
      const body = JSON.parse(response.payload);
      expect(body).toMatchObject({
        error: 'Messages field is required and must be a non-empty array'
      });
    });

    test('should handle backend strategy errors gracefully', async () => {
      const mockError = new Error('Backend failed');
      mockError.recommendations = ['Try switching backends'];
      
      CerebrasStrategy.mockImplementation(() => ({
        executeRequest: jest.fn().mockRejectedValue(mockError)
      }));

      const configLoader = new ConfigLoader(tempDir);
      const errorServer = new ProxyServer(configLoader);
      await errorServer.initialize(tempDir);
      const errorApp = errorServer.app;

      const response = await errorApp.inject({
        method: 'POST',
        url: '/v1/messages',
        payload: {
          messages: [{ role: 'user', content: 'Hello' }]
        }
      });

      expect(response.statusCode).toBe(500);
      const body = JSON.parse(response.payload);
      expect(body).toMatchObject({
        error: 'Backend failed',
        recommendations: ['Try switching backends']
      });

      await errorServer.stop();
    });
  });

  describe('Backend Switching', () => {
    test('should switch backends when configuration changes', async () => {
      // Initial request should use cerebras
      await app.inject({
        method: 'POST',
        url: '/v1/messages',
        payload: { messages: [{ role: 'user', content: 'Hello' }] }
      });

      expect(CerebrasStrategy).toHaveBeenCalled();

      // Update config to use self-hosted
      const newConfig = {
        backend: 'self-hosted',
        backends: {
          'cerebras': { type: 'cerebras', apiKey: 'test-key' },
          'self-hosted': { type: 'self-hosted', url: 'http://localhost:8000' }
        }
      };

      await fs.writeJson(path.join(tempDir, '.llmrc.json'), newConfig);
      
      // Reload configuration
      await server.reloadConfig();

      // Next request should use self-hosted
      await app.inject({
        method: 'POST',
        url: '/v1/messages',
        payload: { messages: [{ role: 'user', content: 'Hello again' }] }
      });

      expect(SelfHostedStrategy).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    test('should provide helpful error messages for configuration issues', async () => {
      // Write invalid config
      await fs.writeJson(path.join(tempDir, '.llmrc.json'), {
        backend: 'nonexistent'
      });

      try {
        const configLoader = new ConfigLoader(tempDir);
        const errorServer = new ProxyServer(configLoader);
        await errorServer.initialize(tempDir);
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.message).toContain('nonexistent');
      }
    });
  });
});