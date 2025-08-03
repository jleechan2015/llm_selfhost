const BackendFactory = require('../../src/backend-factory');
const CerebrasStrategy = require('../../src/strategies/cerebras-strategy');
const SelfHostedStrategy = require('../../src/strategies/self-hosted-strategy');

describe('BackendFactory', () => {
  describe('Strategy Creation', () => {
    test('should create CerebrasStrategy for cerebras backend type', () => {
      const config = {
        type: 'cerebras',
        apiKey: 'test-key',
        apiUrl: 'https://api.cerebras.ai/v1'
      };

      const strategy = BackendFactory.createStrategy(config);
      
      expect(strategy).toBeInstanceOf(CerebrasStrategy);
    });

    test('should create SelfHostedStrategy for self-hosted backend type', () => {
      const config = {
        type: 'self-hosted',
        url: 'http://localhost:8000',
        description: 'Local proxy'
      };

      const strategy = BackendFactory.createStrategy(config);
      
      expect(strategy).toBeInstanceOf(SelfHostedStrategy);
    });

    test('should throw error for unknown backend type', () => {
      const config = {
        type: 'unknown-backend',
        someOption: 'value'
      };

      expect(() => BackendFactory.createStrategy(config))
        .toThrow('Unknown backend type: unknown-backend');
    });

    test('should throw error for missing backend type', () => {
      const config = {
        apiKey: 'test-key'
      };

      expect(() => BackendFactory.createStrategy(config))
        .toThrow('Backend configuration missing required field: type');
    });
  });

  describe('Supported Backend Types', () => {
    test('should return list of supported backend types', () => {
      const supportedTypes = BackendFactory.getSupportedTypes();
      
      expect(supportedTypes).toEqual(['cerebras', 'self-hosted']);
    });

    test('should check if backend type is supported', () => {
      expect(BackendFactory.isSupported('cerebras')).toBe(true);
      expect(BackendFactory.isSupported('self-hosted')).toBe(true);
      expect(BackendFactory.isSupported('unknown')).toBe(false);
      expect(BackendFactory.isSupported('')).toBe(false);
      expect(BackendFactory.isSupported(null)).toBe(false);
    });
  });

  describe('Configuration Validation', () => {
    test('should validate configuration before creating strategy', () => {
      const invalidConfig = {
        type: 'cerebras'
        // Missing apiKey
      };

      expect(() => BackendFactory.createStrategy(invalidConfig))
        .toThrow('Cerebras strategy requires apiKey');
    });

    test('should pass through validation from strategy constructors', () => {
      const invalidConfig = {
        type: 'self-hosted',
        url: 'invalid-url'
      };

      expect(() => BackendFactory.createStrategy(invalidConfig))
        .toThrow('Invalid URL format');
    });
  });

  describe('Error Handling', () => {
    test('should provide helpful error messages', () => {
      try {
        BackendFactory.createStrategy({ type: 'nonexistent' });
      } catch (error) {
        expect(error.message).toContain('Unknown backend type: nonexistent');
        expect(error.supportedTypes).toEqual(['cerebras', 'self-hosted']);
      }
    });
  });
});