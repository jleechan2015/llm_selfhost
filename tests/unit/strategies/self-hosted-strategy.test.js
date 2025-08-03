const SelfHostedStrategy = require('../../../src/strategies/self-hosted-strategy');
const axios = require('axios');

jest.mock('axios');

describe('SelfHostedStrategy', () => {
  let strategy;
  const mockConfig = {
    url: 'http://localhost:8000',
    description: 'Local Python proxy'
  };

  beforeEach(() => {
    strategy = new SelfHostedStrategy(mockConfig);
    jest.clearAllMocks();
  });

  describe('Request Proxying', () => {
    test('should proxy request to self-hosted endpoint correctly', async () => {
      const mockResponse = {
        status: 200,
        data: {
          id: 'msg_123',
          type: 'message',
          role: 'assistant',
          content: [{ type: 'text', text: 'Hello from self-hosted!' }],
          model: 'qwen3-coder',
          stop_reason: 'end_turn',
          usage: { input_tokens: 10, output_tokens: 5 }
        }
      };

      axios.post.mockResolvedValue(mockResponse);

      const messages = [
        { role: 'user', content: 'Write a hello world function' }
      ];
      
      const options = { max_tokens: 100, temperature: 0.7 };
      
      const result = await strategy.executeRequest(messages, options);

      expect(axios.post).toHaveBeenCalledWith(
        'http://localhost:8000/v1/messages',
        {
          messages: messages,
          max_tokens: 100,
          temperature: 0.7
        },
        {
          headers: {
            'Content-Type': 'application/json'
          },
          timeout: 30000
        }
      );

      expect(result).toEqual(mockResponse.data);
    });

    test('should pass through model parameter if specified', async () => {
      const mockResponse = {
        status: 200,
        data: {
          id: 'msg_123',
          type: 'message',
          role: 'assistant',
          content: [{ type: 'text', text: 'Response' }]
        }
      };

      axios.post.mockResolvedValue(mockResponse);

      const messages = [{ role: 'user', content: 'Hello' }];
      const options = { model: 'qwen3-coder', max_tokens: 50 };
      
      await strategy.executeRequest(messages, options);

      expect(axios.post).toHaveBeenCalledWith(
        'http://localhost:8000/v1/messages',
        {
          messages: messages,
          model: 'qwen3-coder',
          max_tokens: 50
        },
        expect.any(Object)
      );
    });
  });

  describe('Error Handling', () => {
    test('should provide clear error message when self-hosted proxy is down', async () => {
      const networkError = new Error('Network Error');
      networkError.code = 'ECONNREFUSED';

      axios.post.mockRejectedValue(networkError);

      const messages = [{ role: 'user', content: 'Hello' }];
      
      await expect(strategy.executeRequest(messages, {}))
        .rejects.toThrow('Cannot connect to self-hosted proxy at http://localhost:8000. Please ensure the proxy is running.');
    });

    test('should provide recommendations when self-hosted proxy fails', async () => {
      const networkError = new Error('Network Error');
      networkError.code = 'ECONNREFUSED';

      axios.post.mockRejectedValue(networkError);

      const messages = [{ role: 'user', content: 'Hello' }];
      
      try {
        await strategy.executeRequest(messages, {});
      } catch (error) {
        expect(error.recommendations).toEqual([
          'Check if the Python proxy is running: python3 simple_api_proxy.py',
          'Verify the proxy URL in your configuration',
          'Try switching to Cerebras backend: llm-proxy switch cerebras',
          'Check proxy logs for error details'
        ]);
      }
    });

    test('should handle proxy timeout errors', async () => {
      const timeoutError = new Error('timeout of 30000ms exceeded');
      timeoutError.code = 'ECONNABORTED';

      axios.post.mockRejectedValue(timeoutError);

      const messages = [{ role: 'user', content: 'Hello' }];
      
      await expect(strategy.executeRequest(messages, {}))
        .rejects.toThrow('Self-hosted proxy request timed out. The model may be loading or overloaded.');
    });

    test('should handle proxy HTTP errors', async () => {
      const errorResponse = {
        response: {
          status: 500,
          data: { error: 'Internal Server Error' }
        }
      };

      axios.post.mockRejectedValue(errorResponse);

      const messages = [{ role: 'user', content: 'Hello' }];
      
      await expect(strategy.executeRequest(messages, {}))
        .rejects.toThrow('Self-hosted proxy error (500): Internal Server Error');
    });

    test('should detect when Ollama model is not loaded', async () => {
      const errorResponse = {
        response: {
          status: 500,
          data: { error: 'model "qwen3-coder" not found' }
        }
      };

      axios.post.mockRejectedValue(errorResponse);

      const messages = [{ role: 'user', content: 'Hello' }];
      
      try {
        await strategy.executeRequest(messages, {});
      } catch (error) {
        expect(error.message).toContain('Model not loaded');
        expect(error.recommendations).toContain('Run: ollama pull qwen3-coder');
      }
    });
  });

  describe('Health Checking', () => {
    test('should check proxy health and cache status', async () => {
      const healthResponse = {
        status: 200,
        data: {
          status: 'healthy',
          components: {
            ollama: 'healthy',
            redis: 'healthy'
          },
          model: 'qwen3-coder'
        }
      };

      axios.get.mockResolvedValue(healthResponse);

      const health = await strategy.checkHealth();

      expect(axios.get).toHaveBeenCalledWith(
        'http://localhost:8000/health',
        { timeout: 5000 }
      );

      expect(health).toEqual({
        status: 'healthy',
        components: {
          ollama: 'healthy',
          redis: 'healthy'
        },
        model: 'qwen3-coder',
        endpoint: 'http://localhost:8000'
      });
    });

    test('should handle health check failures gracefully', async () => {
      const networkError = new Error('Network Error');
      axios.get.mockRejectedValue(networkError);

      const health = await strategy.checkHealth();

      expect(health).toEqual({
        status: 'unhealthy',
        error: 'Cannot connect to proxy',
        endpoint: 'http://localhost:8000'
      });
    });
  });

  describe('Configuration Validation', () => {
    test('should validate required configuration', () => {
      expect(() => new SelfHostedStrategy({}))
        .toThrow('Self-hosted strategy requires url');
      
      expect(() => new SelfHostedStrategy({ url: '' }))
        .toThrow('Self-hosted strategy requires url');
      
      expect(() => new SelfHostedStrategy({ url: 'http://localhost:8000' }))
        .not.toThrow();
    });

    test('should validate URL format', () => {
      expect(() => new SelfHostedStrategy({ url: 'invalid-url' }))
        .toThrow('Invalid URL format');
      
      expect(() => new SelfHostedStrategy({ url: 'http://valid-url.com' }))
        .not.toThrow();
    });
  });
});