const CerebrasStrategy = require('./strategies/cerebras-strategy');
const SelfHostedStrategy = require('./strategies/self-hosted-strategy');

class BackendFactory {
  static createStrategy(config) {
    if (!config || !config.type) {
      throw new Error('Backend configuration missing required field: type');
    }

    switch (config.type) {
      case 'cerebras':
        return new CerebrasStrategy(config);
      case 'self-hosted':
        return new SelfHostedStrategy(config);
      default:
        const error = new Error(`Unknown backend type: ${config.type}`);
        error.supportedTypes = this.getSupportedTypes();
        throw error;
    }
  }

  static getSupportedTypes() {
    return ['cerebras', 'self-hosted'];
  }

  static isSupported(type) {
    return this.getSupportedTypes().includes(type);
  }
}

module.exports = BackendFactory;