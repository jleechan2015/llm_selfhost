const axios = require('axios');

class SelfHostedStrategy {
  constructor(config) {
    this.validateConfig(config);
    this.url = config.url;
    this.description = config.description || 'Self-hosted proxy';
  }

  validateConfig(config) {
    if (!config.url || config.url.trim() === '') {
      throw new Error('Self-hosted strategy requires url');
    }

    // Validate URL format
    try {
      new URL(config.url);
    } catch (error) {
      throw new Error('Invalid URL format');
    }
  }

  async executeRequest(messages, options = {}) {
    try {
      const requestData = {
        messages: messages,
        max_tokens: options.max_tokens,
        temperature: options.temperature,
        model: options.model
      };

      // Remove undefined values
      Object.keys(requestData).forEach(key => {
        if (requestData[key] === undefined) {
          delete requestData[key];
        }
      });

      const response = await axios.post(
        `${this.url}/v1/messages`,
        requestData,
        {
          headers: {
            'Content-Type': 'application/json'
          },
          timeout: 30000 // 30 second timeout for model inference
        }
      );

      // Return the response as-is since it should already be in Anthropic format
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async checkHealth() {
    try {
      const response = await axios.get(`${this.url}/health`, { timeout: 5000 });
      return {
        ...response.data,
        endpoint: this.url
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        error: 'Cannot connect to proxy',
        endpoint: this.url
      };
    }
  }

  handleError(error) {
    const safeError = new Error();

    if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
      safeError.message = `Cannot connect to self-hosted proxy at ${this.url}. Please ensure the proxy is running.`;
      safeError.recommendations = [
        'Check if the Python proxy is running: python3 simple_api_proxy.py',
        'Verify the proxy URL in your configuration',
        'Try switching to Cerebras backend: llm-proxy switch cerebras',
        'Check proxy logs for error details'
      ];
    } else if (error.code === 'ECONNABORTED' || (error.message && error.message.includes('timeout'))) {
      safeError.message = 'Self-hosted proxy request timed out. The model may be loading or overloaded.';
      safeError.recommendations = [
        'Wait for the model to finish loading',
        'Check if the GPU has sufficient memory',
        'Try switching to Cerebras backend: llm-proxy switch cerebras',
        'Restart the Python proxy if it appears stuck'
      ];
    } else if (error.response) {
      const status = error.response.status;
      const errorData = error.response.data;
      const errorMessage = errorData.error || errorData.detail || 'Unknown error';

      // Detect specific Ollama errors
      if (errorMessage && (errorMessage.includes('not found') || (errorMessage.includes('model') && errorMessage.includes('not')))) {
        safeError.message = `Model not loaded on self-hosted proxy: ${errorMessage}`;
        safeError.recommendations = [
          'Run: ollama pull qwen3-coder',
          'Check available models: ollama list',
          'Verify model name in configuration',
          'Try switching to Cerebras backend: llm-proxy switch cerebras'
        ];
      } else {
        safeError.message = `Self-hosted proxy error (${status}): ${errorMessage}`;
        safeError.recommendations = [
          'Check proxy logs for detailed error information',
          'Verify the proxy is running correctly',
          'Try switching to Cerebras backend: llm-proxy switch cerebras'
        ];
      }
    } else {
      safeError.message = `Self-hosted proxy request failed: ${error.message || 'Unknown error'}`;
      safeError.recommendations = [
        'Check your network connection',
        'Verify the proxy URL is correct',
        'Try switching to Cerebras backend: llm-proxy switch cerebras'
      ];
    }

    return safeError;
  }
}

module.exports = SelfHostedStrategy;