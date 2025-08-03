const fs = require('fs-extra');
const path = require('path');
const os = require('os');
const ConfigLoader = require('../../src/config-loader');

describe('ConfigLoader', () => {
  let tempDir;
  let originalHome;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'llm-proxy-test-'));
    originalHome = process.env.HOME;
    process.env.HOME = tempDir;
  });

  afterEach(() => {
    fs.removeSync(tempDir);
    process.env.HOME = originalHome;
  });

  describe('Configuration Precedence', () => {
    test('should load project .llmrc.json over global config', async () => {
      // Create global config
      const globalConfig = {
        backend: 'global-backend',
        backends: {
          'global-backend': { type: 'cerebras', apiKey: 'global-key' }
        }
      };
      await fs.ensureDir(path.join(tempDir, '.llm-proxy'));
      await fs.writeJson(path.join(tempDir, '.llm-proxy', 'config.json'), globalConfig);

      // Create project config
      const projectDir = path.join(tempDir, 'project');
      await fs.ensureDir(projectDir);
      const projectConfig = {
        backend: 'project-backend',
        backends: {
          'project-backend': { type: 'self-hosted', url: 'http://localhost:8000' }
        }
      };
      await fs.writeJson(path.join(projectDir, '.llmrc.json'), projectConfig);

      const loader = new ConfigLoader(tempDir);
      const config = await loader.load(projectDir);

      expect(config.backend).toBe('project-backend');
      expect(config.backends['project-backend'].type).toBe('self-hosted');
    });

    test('should fall back to global config when no project config exists', async () => {
      const globalConfig = {
        backend: 'cerebras',
        backends: {
          'cerebras': { type: 'cerebras', apiKey: 'test-key' }
        }
      };
      await fs.ensureDir(path.join(tempDir, '.llm-proxy'));
      await fs.writeJson(path.join(tempDir, '.llm-proxy', 'config.json'), globalConfig);

      const projectDir = path.join(tempDir, 'project');
      await fs.ensureDir(projectDir);

      const loader = new ConfigLoader(tempDir);
      const config = await loader.load(projectDir);

      expect(config.backend).toBe('cerebras');
      expect(config.backends['cerebras'].type).toBe('cerebras');
    });

    test('should override with environment variables', async () => {
      const globalConfig = {
        backend: 'cerebras',
        backends: {
          'cerebras': { type: 'cerebras', apiKey: 'test-key' }
        }
      };
      await fs.ensureDir(path.join(tempDir, '.llm-proxy'));
      await fs.writeJson(path.join(tempDir, '.llm-proxy', 'config.json'), globalConfig);

      process.env.LLM_BACKEND_CONFIG = JSON.stringify({
        backend: 'env-backend',
        backends: {
          'env-backend': { type: 'self-hosted', url: 'http://env:8000' }
        }
      });

      const loader = new ConfigLoader(tempDir);
      const config = await loader.load(tempDir);

      expect(config.backend).toBe('env-backend');
      expect(config.backends['env-backend'].url).toBe('http://env:8000');

      delete process.env.LLM_BACKEND_CONFIG;
    });
  });

  describe('Validation', () => {
    test('should validate required fields', async () => {
      const invalidConfig = {
        // Missing backend field
        backends: {
          'test': { type: 'cerebras' } // Missing apiKey
        }
      };
      
      const projectDir = path.join(tempDir, 'project');
      await fs.ensureDir(projectDir);
      await fs.writeJson(path.join(projectDir, '.llmrc.json'), invalidConfig);

      const loader = new ConfigLoader(tempDir);
      
      await expect(loader.load(projectDir)).rejects.toThrow('Missing required field: backend');
    });

    test('should validate backend configuration', async () => {
      const invalidConfig = {
        backend: 'test',
        backends: {
          'test': { 
            type: 'cerebras'
            // Missing apiKey for cerebras backend
          }
        }
      };
      
      const projectDir = path.join(tempDir, 'project');
      await fs.ensureDir(projectDir);
      await fs.writeJson(path.join(projectDir, '.llmrc.json'), invalidConfig);

      const loader = new ConfigLoader(tempDir);
      
      await expect(loader.load(projectDir)).rejects.toThrow('Backend "test" missing required field: apiKey');
    });
  });

  describe('File Permissions', () => {
    test('should set 600 permissions on config files with secrets', async () => {
      const configWithSecrets = {
        backend: 'cerebras',
        backends: {
          'cerebras': { type: 'cerebras', apiKey: 'secret-key' }
        }
      };

      const loader = new ConfigLoader(tempDir);
      const configPath = path.join(tempDir, '.llm-proxy', 'config.json');
      
      await loader.save(configWithSecrets, configPath);

      const stats = await fs.stat(configPath);
      const permissions = (stats.mode & parseInt('777', 8)).toString(8);
      expect(permissions).toBe('600');
    });
  });

  describe('Default Configuration', () => {
    test('should generate valid default configuration', () => {
      const loader = new ConfigLoader(tempDir);
      const defaultConfig = loader.getDefaultConfig();

      expect(defaultConfig).toHaveProperty('backend');
      expect(defaultConfig).toHaveProperty('backends');
      expect(defaultConfig.backends).toHaveProperty('cerebras');
      expect(defaultConfig.backends).toHaveProperty('self-hosted');
      expect(defaultConfig.backends.cerebras.type).toBe('cerebras');
      expect(defaultConfig.backends['self-hosted'].type).toBe('self-hosted');
    });
  });
});