#!/usr/bin/env node

const { Command } = require('commander');
const chalk = require('chalk');
const ProxyServer = require('../src/proxy-server');
const ConfigLoader = require('../src/config-loader');
const BackendFactory = require('../src/backend-factory');
const path = require('path');
const fs = require('fs-extra');

const program = new Command();

program
  .name('llm-proxy')
  .description('Multi-LLM proxy server for Claude CLI')
  .version('1.0.0');

program
  .command('start')
  .description('Start the proxy server')
  .option('-p, --port <port>', 'Port to run on (or "auto" for auto-selection)', 'auto')
  .option('-w, --workspace <path>', 'Workspace directory for config', process.cwd())
  .action(async (options) => {
    try {
      console.log(chalk.blue('🚀 Starting Multi-LLM Proxy Server...'));
      
      const configLoader = new ConfigLoader();
      const server = new ProxyServer(configLoader);
      
      const { port, url } = await server.start(options.workspace);
      
      console.log(chalk.green('✅ Proxy server started successfully!'));
      console.log(chalk.cyan(`📍 Server URL: ${url}`));
      console.log(chalk.cyan(`🔧 Backend: ${server.getCurrentBackend()}`));
      console.log('');
      console.log(chalk.yellow('To use with Claude CLI, run:'));
      console.log(chalk.white(`export ANTHROPIC_BASE_URL="${url}"`));
      console.log(chalk.white('claude "Write a Python function"'));
      console.log('');
      console.log(chalk.gray('Press Ctrl+C to stop the server'));
      
      // Handle graceful shutdown
      process.on('SIGINT', async () => {
        console.log(chalk.yellow('\n🛑 Shutting down proxy server...'));
        await server.stop();
        console.log(chalk.green('✅ Server stopped'));
        process.exit(0);
      });
      
    } catch (error) {
      console.error(chalk.red('❌ Failed to start proxy server:'));
      console.error(chalk.red(error.message));
      if (error.recommendations) {
        console.log(chalk.yellow('\n💡 Recommendations:'));
        error.recommendations.forEach(rec => {
          console.log(chalk.yellow(`  • ${rec}`));
        });
      }
      process.exit(1);
    }
  });

program
  .command('setup')
  .description('Generate configuration files')
  .option('-w, --workspace <path>', 'Workspace directory for config', process.cwd())
  .action(async (options) => {
    try {
      console.log(chalk.blue('🔧 Setting up configuration...'));
      
      const configLoader = new ConfigLoader();
      const defaultConfig = configLoader.getDefaultConfig();
      
      const configPath = path.join(options.workspace, '.llmrc.json');
      
      if (await fs.pathExists(configPath)) {
        console.log(chalk.yellow('⚠️  Configuration file already exists at:'));
        console.log(chalk.gray(configPath));
        console.log(chalk.yellow('To regenerate, delete the existing file first.'));
        return;
      }
      
      await fs.writeJson(configPath, defaultConfig, { spaces: 2 });
      await fs.chmod(configPath, 0o600); // Secure permissions
      
      console.log(chalk.green('✅ Configuration created at:'));
      console.log(chalk.cyan(configPath));
      console.log('');
      console.log(chalk.yellow('📝 Next steps:'));
      console.log(chalk.white('1. Edit the configuration file to add your API keys'));
      console.log(chalk.white('2. Run: llm-proxy start'));
      console.log(chalk.white('3. Set ANTHROPIC_BASE_URL to use with Claude CLI'));
      
    } catch (error) {
      console.error(chalk.red('❌ Failed to create configuration:'));
      console.error(chalk.red(error.message));
      process.exit(1);
    }
  });

program
  .command('status')
  .description('Show server and backend status')
  .option('-w, --workspace <path>', 'Workspace directory for config', process.cwd())
  .action(async (options) => {
    try {
      console.log(chalk.blue('📊 Proxy Server Status'));
      console.log('');
      
      const configLoader = new ConfigLoader();
      const config = await configLoader.load(options.workspace);
      
      console.log(chalk.cyan('Configuration:'));
      console.log(chalk.white(`  Active Backend: ${config.backend}`));
      console.log(chalk.white(`  Port: ${config.port}`));
      console.log('');
      
      console.log(chalk.cyan('Available Backends:'));
      Object.entries(config.backends).forEach(([name, backend]) => {
        const isActive = name === config.backend;
        const prefix = isActive ? chalk.green('  ✓') : chalk.gray('  •');
        const nameColor = isActive ? chalk.green : chalk.white;
        console.log(`${prefix} ${nameColor(name)}: ${backend.type}`);
        
        if (backend.url) {
          console.log(chalk.gray(`    URL: ${backend.url}`));
        }
        if (backend.description) {
          console.log(chalk.gray(`    ${backend.description}`));
        }
      });
      
      // Try to check backend health
      console.log('');
      console.log(chalk.cyan('Backend Health:'));
      try {
        const activeBackend = config.backends[config.backend];
        const strategy = BackendFactory.createStrategy(activeBackend);
        
        if (typeof strategy.checkHealth === 'function') {
          const health = await strategy.checkHealth();
          if (health.status === 'healthy') {
            console.log(chalk.green('  ✅ Backend is healthy'));
          } else {
            console.log(chalk.red('  ❌ Backend is unhealthy'));
            if (health.error) {
              console.log(chalk.red(`     Error: ${health.error}`));
            }
          }
        } else {
          console.log(chalk.yellow('  ⚠️  Health check not available for this backend'));
        }
      } catch (error) {
        console.log(chalk.red('  ❌ Cannot check backend health'));
        console.log(chalk.red(`     ${error.message}`));
      }
      
    } catch (error) {
      console.error(chalk.red('❌ Failed to get status:'));
      console.error(chalk.red(error.message));
      process.exit(1);
    }
  });

program
  .command('switch <backend>')
  .description('Switch to a different backend')
  .option('-w, --workspace <path>', 'Workspace directory for config', process.cwd())
  .action(async (backend, options) => {
    try {
      console.log(chalk.blue(`🔄 Switching to backend: ${backend}`));
      
      const configLoader = new ConfigLoader();
      const config = await configLoader.load(options.workspace);
      
      if (!config.backends[backend]) {
        console.error(chalk.red(`❌ Backend "${backend}" not found in configuration`));
        console.log(chalk.yellow('Available backends:'));
        Object.keys(config.backends).forEach(name => {
          console.log(chalk.white(`  • ${name}`));
        });
        process.exit(1);
      }
      
      // Update config
      config.backend = backend;
      
      const configPath = path.join(options.workspace, '.llmrc.json');
      await configLoader.save(config, configPath);
      
      console.log(chalk.green(`✅ Switched to backend: ${backend}`));
      console.log(chalk.yellow('💡 Restart the proxy server to apply changes:'));
      console.log(chalk.white('llm-proxy start'));
      
    } catch (error) {
      console.error(chalk.red('❌ Failed to switch backend:'));
      console.error(chalk.red(error.message));
      process.exit(1);
    }
  });

program
  .command('recommend')
  .description('Get backend recommendations')
  .option('-w, --workspace <path>', 'Workspace directory for config', process.cwd())
  .action(async (options) => {
    try {
      console.log(chalk.blue('💡 Backend Recommendations'));
      console.log('');
      
      const configLoader = new ConfigLoader();
      const config = await configLoader.load(options.workspace);
      
      console.log(chalk.cyan('When to use each backend:'));
      console.log('');
      
      console.log(chalk.green('🏢 Cerebras (SaaS):'));
      console.log(chalk.white('  • Best for: Reliability and performance'));
      console.log(chalk.white('  • Use when: Claude CLI rate limits you'));
      console.log(chalk.white('  • Switch: llm-proxy switch cerebras'));
      console.log('');
      
      console.log(chalk.green('🏠 Self-hosted:'));
      console.log(chalk.white('  • Best for: Cost savings and privacy'));
      console.log(chalk.white('  • Use when: High volume usage'));
      console.log(chalk.white('  • Switch: llm-proxy switch self-hosted'));
      console.log('');
      
      console.log(chalk.green('☁️  Vast.ai:'));
      console.log(chalk.white('  • Best for: Cost optimization'));
      console.log(chalk.white('  • Use when: Budget is primary concern'));
      console.log(chalk.white('  • Switch: llm-proxy switch vast-ai'));
      console.log('');
      
      console.log(chalk.green('🚀 RunPod:'));
      console.log(chalk.white('  • Best for: Stability and persistence'));
      console.log(chalk.white('  • Use when: Reliability is critical'));
      console.log(chalk.white('  • Switch: llm-proxy switch runpod'));
      console.log('');
      
      // Current backend recommendation
      const currentBackend = config.backends[config.backend];
      if (currentBackend.type === 'cerebras') {
        console.log(chalk.yellow('💰 Cost tip: Switch to self-hosted for high volume usage'));
      } else {
        console.log(chalk.yellow('⚡ Performance tip: Switch to Cerebras for guaranteed uptime'));
      }
      
    } catch (error) {
      console.error(chalk.red('❌ Failed to get recommendations:'));
      console.error(chalk.red(error.message));
      process.exit(1);
    }
  });

// Handle unknown commands
program.on('command:*', () => {
  console.error(chalk.red('❌ Invalid command'));
  console.log(chalk.yellow('Available commands:'));
  console.log(chalk.white('  start    - Start the proxy server'));
  console.log(chalk.white('  setup    - Generate configuration files'));
  console.log(chalk.white('  status   - Show server and backend status'));
  console.log(chalk.white('  switch   - Switch to a different backend'));
  console.log(chalk.white('  recommend - Get backend recommendations'));
  process.exit(1);
});

program.parse(process.argv);