const CerebrasStrategy = require('../../../src/strategies/cerebras-strategy');
const axios = require('axios');

jest.mock('axios');

describe('CerebrasStrategy', () => {
  let strategy;
  const mockConfig = {
    apiKey: 'test-api-key',
    apiUrl: 'https://api.cerebras.ai/v1'
  };

  beforeEach(() => {
    strategy = new CerebrasStrategy(mockConfig);
    jest.clearAllMocks();
  });

  describe('Request Formatting', () => {
    test('should format request correctly for Anthropic API compatibility', async () => {
      const mockResponse = {
        status: 200,
        data: {
          id: 'msg_123',
          object: 'message',
          created: 1234567890,
          model: 'qwen3-coder',
          choices: [{
            message: {
              role: 'assistant',
              content: 'Hello, World!'
            },
            finish_reason: 'stop'
          }]
        }
      };

      axios.post.mockResolvedValue(mockResponse);

      const messages = [
        { role: 'user', content: 'Write a hello world function' }
      ];
      
      const options = { max_tokens: 100, temperature: 0.7 };
      
      await strategy.executeRequest(messages, options);

      expect(axios.post).toHaveBeenCalledWith(
        'https://api.cerebras.ai/v1/chat/completions',
        {
          model: 'qwen3-coder',
          messages: messages,
          max_tokens: 100,
          temperature: 0.7
        },
        {
          headers: {
            'Authorization': 'Bearer test-api-key',
            'Content-Type': 'application/json'
          }
        }
      );
    });

    test('should transform response to Anthropic format', async () => {
      const mockResponse = {
        status: 200,
        data: {
          id: 'msg_123',
          object: 'chat.completion',
          created: 1234567890,
          model: 'qwen3-coder',
          choices: [{
            message: {
              role: 'assistant',
              content: 'Hello, World!'
            },
            finish_reason: 'stop'
          }],
          usage: {
            prompt_tokens: 10,
            completion_tokens: 5,
            total_tokens: 15
          }
        }
      };

      axios.post.mockResolvedValue(mockResponse);

      const messages = [{ role: 'user', content: 'Hello' }];
      const result = await strategy.executeRequest(messages, {});

      expect(result).toEqual({
        id: 'msg_123',
        type: 'message',
        role: 'assistant',
        content: [{ type: 'text', text: 'Hello, World!' }],
        model: 'qwen3-coder',
        stop_reason: 'end_turn',
        stop_sequence: null,
        usage: {
          input_tokens: 10,
          output_tokens: 5
        }
      });
    });
  });

  describe('Error Handling', () => {
    test('should provide clear error message for API key issues', async () => {
      const errorResponse = {
        response: {
          status: 401,
          data: { error: 'Invalid API key' }
        }
      };

      axios.post.mockRejectedValue(errorResponse);

      const messages = [{ role: 'user', content: 'Hello' }];
      
      await expect(strategy.executeRequest(messages, {}))
        .rejects.toThrow('Cerebras API authentication failed: Invalid API key. Please check your API key configuration.');
    });

    test('should provide clear error message for rate limiting', async () => {
      const errorResponse = {
        response: {
          status: 429,
          data: { error: 'Rate limit exceeded' }
        }
      };

      axios.post.mockRejectedValue(errorResponse);

      const messages = [{ role: 'user', content: 'Hello' }];
      
      await expect(strategy.executeRequest(messages, {}))
        .rejects.toThrow('Cerebras API rate limit exceeded. Please try again later or consider using a self-hosted backend.');
    });

    test('should provide recommendations for alternative backends on failure', async () => {
      const errorResponse = {
        response: {
          status: 503,
          data: { error: 'Service unavailable' }
        }
      };

      axios.post.mockRejectedValue(errorResponse);

      const messages = [{ role: 'user', content: 'Hello' }];
      
      try {
        await strategy.executeRequest(messages, {});
      } catch (error) {
        expect(error.message).toContain('Cerebras API service unavailable');
        expect(error.recommendations).toEqual([
          'Try switching to self-hosted backend: llm-proxy switch self-hosted',
          'Check Cerebras status page for service issues',
          'Consider using vast-ai or runpod backends for reliability'
        ]);
      }
    });

    test('should handle network errors gracefully', async () => {
      const networkError = new Error('Network Error');
      networkError.code = 'ECONNREFUSED';

      axios.post.mockRejectedValue(networkError);

      const messages = [{ role: 'user', content: 'Hello' }];
      
      await expect(strategy.executeRequest(messages, {}))
        .rejects.toThrow('Cannot connect to Cerebras API. Please check your internet connection.');
    });

    test('should never expose API keys in error messages', async () => {
      const errorResponse = {
        response: {
          status: 500,
          data: { error: 'Internal server error' }
        }
      };

      axios.post.mockRejectedValue(errorResponse);

      const messages = [{ role: 'user', content: 'Hello' }];
      
      try {
        await strategy.executeRequest(messages, {});
      } catch (error) {
        expect(error.message).not.toContain('test-api-key');
        expect(error.message).not.toContain(mockConfig.apiKey);
      }
    });
  });

  describe('Configuration Validation', () => {
    test('should validate required configuration', () => {
      expect(() => new CerebrasStrategy({}))
        .toThrow('Cerebras strategy requires apiKey');
      
      expect(() => new CerebrasStrategy({ apiKey: '' }))
        .toThrow('Cerebras strategy requires apiKey');
      
      expect(() => new CerebrasStrategy({ apiKey: 'valid-key' }))
        .not.toThrow();
    });
  });
});