const axios = require('axios');

class CerebrasStrategy {
  constructor(config) {
    this.validateConfig(config);
    this.apiKey = config.apiKey;
    this.apiUrl = config.apiUrl || 'https://api.cerebras.ai/v1';
  }

  validateConfig(config) {
    if (!config.apiKey || config.apiKey.trim() === '') {
      throw new Error('Cerebras strategy requires apiKey');
    }
  }

  async executeRequest(messages, options = {}) {
    try {
      const requestData = {
        model: options.model || 'qwen-3-coder-480b',
        messages: messages,
        max_tokens: options.max_tokens,
        temperature: options.temperature
      };

      // Remove undefined values
      Object.keys(requestData).forEach(key => {
        if (requestData[key] === undefined) {
          delete requestData[key];
        }
      });

      const response = await axios.post(
        `${this.apiUrl}/chat/completions`,
        requestData,
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
          }
        }
      );

      return this.transformResponse(response.data);
    } catch (error) {
      throw this.handleError(error);
    }
  }

  transformResponse(cerebrasResponse) {
    const choice = cerebrasResponse.choices[0];
    
    return {
      id: cerebrasResponse.id,
      type: 'message',
      role: 'assistant',
      content: [{ type: 'text', text: choice.message.content }],
      model: cerebrasResponse.model,
      stop_reason: choice.finish_reason === 'stop' ? 'end_turn' : choice.finish_reason,
      stop_sequence: null,
      usage: {
        input_tokens: cerebrasResponse.usage?.prompt_tokens || 0,
        output_tokens: cerebrasResponse.usage?.completion_tokens || 0
      }
    };
  }

  handleError(error) {
    // Never expose API keys in error messages
    const safeError = new Error();

    if (error.response) {
      const status = error.response.status;
      const errorData = error.response.data;

      switch (status) {
        case 401:
          safeError.message = `Cerebras API authentication failed: ${errorData.error || 'Invalid credentials'}. Please check your API key configuration.`;
          break;
        case 429:
          safeError.message = 'Cerebras API rate limit exceeded. Please try again later or consider using a self-hosted backend.';
          safeError.recommendations = [
            'Wait before retrying the request',
            'Switch to self-hosted backend: llm-proxy switch self-hosted',
            'Consider upgrading your Cerebras plan'
          ];
          break;
        case 503:
          safeError.message = 'Cerebras API service unavailable. The service may be experiencing issues.';
          safeError.recommendations = [
            'Try switching to self-hosted backend: llm-proxy switch self-hosted',
            'Check Cerebras status page for service issues',
            'Consider using vast-ai or runpod backends for reliability'
          ];
          break;
        default:
          safeError.message = `Cerebras API error (${status}): ${errorData.error || 'Unknown error'}`;
          safeError.recommendations = [
            'Check Cerebras API documentation',
            'Try switching to self-hosted backend: llm-proxy switch self-hosted'
          ];
      }
    } else if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
      safeError.message = 'Cannot connect to Cerebras API. Please check your internet connection.';
      safeError.recommendations = [
        'Check your internet connection',
        'Verify DNS resolution',
        'Try switching to self-hosted backend: llm-proxy switch self-hosted'
      ];
    } else {
      safeError.message = `Cerebras API request failed: ${error.message}`;
      safeError.recommendations = [
        'Try switching to self-hosted backend: llm-proxy switch self-hosted'
      ];
    }

    return safeError;
  }
}

module.exports = CerebrasStrategy;