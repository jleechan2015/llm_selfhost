const fs = require('fs-extra');
const path = require('path');
const os = require('os');

class ConfigLoader {
  constructor(homeDir = null) {
    this.homeDir = homeDir || os.homedir();
    this.globalConfigPath = path.join(this.homeDir, '.llm-proxy', 'config.json');
  }

  getGlobalConfigPath() {
    return this.globalConfigPath;
  }

  async load(workspaceDir = process.cwd()) {
    let config = {};
    let hasExplicitConfig = false;

    // 1. Start with empty config
    
    // 2. Load global config if exists
    try {
      if (await fs.pathExists(this.globalConfigPath)) {
        const globalConfig = await fs.readJson(this.globalConfigPath);
        config = this.mergeConfigs(config, globalConfig);
        hasExplicitConfig = true;
      }
    } catch (error) {
      console.warn(`Warning: Could not load global config: ${error.message}`);
    }

    // 3. Load project config if exists (highest precedence)
    const projectConfigPath = path.join(workspaceDir, '.llmrc.json');
    try {
      if (await fs.pathExists(projectConfigPath)) {
        const projectConfig = await fs.readJson(projectConfigPath);
        config = this.mergeConfigs(config, projectConfig);
        hasExplicitConfig = true;
      }
    } catch (error) {
      console.warn(`Warning: Could not load project config: ${error.message}`);
    }

    // 4. Override with environment variables
    if (process.env.LLM_BACKEND_CONFIG) {
      try {
        const envConfig = JSON.parse(process.env.LLM_BACKEND_CONFIG);
        config = this.mergeConfigs(config, envConfig);
        hasExplicitConfig = true;
      } catch (error) {
        console.warn(`Warning: Invalid LLM_BACKEND_CONFIG environment variable: ${error.message}`);
      }
    }

    // 5. Fall back to default config if no explicit config found
    if (!hasExplicitConfig) {
      const defaultConfig = this.getDefaultConfig();
      config = { ...defaultConfig };
    } else {
      // Merge with defaults for missing backends only
      const defaultConfig = this.getDefaultConfig();
      if (!config.backends) config.backends = {};
      // Only add default backends that don't exist in config
      Object.keys(defaultConfig.backends).forEach(backendName => {
        if (!config.backends[backendName]) {
          config.backends[backendName] = defaultConfig.backends[backendName];
        }
      });
      // Set default port if not specified
      if (!config.port) {
        config.port = defaultConfig.port;
      }
    }

    // 6. Validate final config
    this.validateConfig(config);

    return config;
  }

  async save(config, configPath) {
    await fs.ensureDir(path.dirname(configPath));
    await fs.writeJson(configPath, config, { spaces: 2 });
    
    // Set restrictive permissions for files containing secrets
    if (this.configContainsSecrets(config)) {
      await fs.chmod(configPath, 0o600);
    }
  }

  mergeConfigs(base, override) {
    const merged = { ...base };
    
    // Override all properties from override
    Object.keys(override).forEach(key => {
      if (key === 'backends') {
        // Deep merge backends
        merged.backends = { ...merged.backends, ...override.backends };
      } else {
        // Override other properties
        merged[key] = override[key];
      }
    });

    return merged;
  }

  validateConfig(config) {
    // Check required top-level fields
    if (!config.backend) {
      throw new Error('Missing required field: backend');
    }

    if (!config.backends || typeof config.backends !== 'object') {
      throw new Error('Missing required field: backends');
    }

    // Validate active backend exists
    if (!config.backends[config.backend]) {
      throw new Error(`Backend "${config.backend}" not found in backends configuration`);
    }

    // Validate active backend configuration only
    this.validateBackend(config.backend, config.backends[config.backend]);
  }

  validateBackend(name, backend) {
    if (!backend.type) {
      throw new Error(`Backend "${name}" missing required field: type`);
    }

    switch (backend.type) {
      case 'cerebras':
        if (!backend.apiKey) {
          throw new Error(`Backend "${name}" missing required field: apiKey`);
        }
        break;
      case 'self-hosted':
        if (!backend.url) {
          throw new Error(`Backend "${name}" missing required field: url`);
        }
        break;
      default:
        throw new Error(`Backend "${name}" has invalid type: ${backend.type}`);
    }
  }

  configContainsSecrets(config) {
    if (!config.backends) return false;
    
    return Object.values(config.backends).some(backend => 
      backend.apiKey || backend.password || backend.token
    );
  }

  getDefaultConfig() {
    return {
      backend: 'self-hosted',
      port: 'auto',
      backends: {
        'cerebras': {
          type: 'cerebras',
          apiKey: 'YOUR_CEREBRAS_API_KEY',
          apiUrl: 'https://api.cerebras.ai/v1'
        },
        'self-hosted': {
          type: 'self-hosted',
          url: 'http://localhost:8000',
          description: 'Local Python proxy (simple_api_proxy.py)'
        },
        'vast-ai': {
          type: 'self-hosted',
          url: 'http://vast-instance:8000',
          description: 'Vast.ai instance with Redis caching'
        },
        'runpod': {
          type: 'self-hosted',
          url: 'http://runpod-instance:8000',
          description: 'RunPod instance with persistent storage'
        }
      }
    };
  }
}

module.exports = ConfigLoader;