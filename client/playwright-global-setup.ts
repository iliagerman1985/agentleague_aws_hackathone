import { execSync } from 'child_process';
import { existsSync } from 'fs';

/**
 * Global setup for VS Code Playwright extension
 * Ensures test servers are running before tests execute
 */

// Function to check if servers are running
function areServersRunning(): boolean {
  try {
    execSync('curl -s http://localhost:9997/health', { stdio: 'ignore' });
    execSync('curl -s http://localhost:5889', { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

// Function to stop any existing servers with retry logic
function stopExistingServers(): void {
  console.log('🛑 Stopping any existing test servers...');

  const maxRetries = 3;
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      // Use full path to just and set environment
      const justPath = '/usr/local/bin/just';
      execSync(`${justPath} stop-test-servers`, {
        stdio: 'pipe', // Use pipe to capture output
        env: { ...process.env, PATH: process.env.PATH + ':/usr/local/bin' }
      });

      console.log('✅ Existing servers stopped');
      return; // Success, exit the retry loop

    } catch (error) {
      console.log(`ℹ️  Stop attempt ${attempt}/${maxRetries} failed (this is normal if no servers were running)`);

      if (attempt === maxRetries) {
        // Force kill any processes on the test ports as a last resort
        try {
          console.log('🔨 Force killing any processes on test ports...');
          execSync('pkill -f "uvicorn.*:9997" || true', { stdio: 'pipe' });
          execSync('pkill -f "vite.*5889" || true', { stdio: 'pipe' });
          execSync('lsof -ti:9997 | xargs kill -9 2>/dev/null || true', { stdio: 'pipe' });
          execSync('lsof -ti:5889 | xargs kill -9 2>/dev/null || true', { stdio: 'pipe' });
          console.log('✅ Force kill completed');
        } catch (forceKillError) {
          console.log('ℹ️  Force kill failed or no processes to kill');
        }
      }

      // Wait a bit before retrying
      if (attempt < maxRetries) {
        execSync('sleep 2');
      }
    }
  }
}

// Function to start servers with retry logic
function startServers(): void {
  console.log('🚀 Starting test servers for VS Code Playwright extension...');

  const maxRetries = 2;
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      // Use full path to just and set environment
      const justPath = '/usr/local/bin/just';
      console.log(`📡 Server start attempt ${attempt}/${maxRetries}...`);
      console.log(`🔍 Current directory: ${process.cwd()}`);
      console.log(`🔍 Just path: ${justPath}`);
      console.log(`🔍 PATH: ${process.env.PATH}`);

      // Test if just command exists
      try {
        execSync(`${justPath} --version`, { stdio: 'pipe' });
        console.log('✅ Just command is accessible');
      } catch (error) {
        console.log('❌ Just command is not accessible:', error.message);
        throw new Error('Just command not found');
      }

      // Test if justfile exists
      if (!existsSync('./justfile')) {
        throw new Error('justfile not found in current directory');
      }
      console.log('✅ justfile found');

      execSync(`${justPath} start-test-servers`, {
        stdio: 'inherit',
        env: { ...process.env, PATH: process.env.PATH + ':/usr/local/bin' },
        timeout: 120000, // 2 minute timeout
        cwd: process.cwd() // Explicitly set working directory
      });

      console.log('✅ Test servers started successfully');
      return; // Success, exit the retry loop

    } catch (error) {
      console.error(`❌ Server start attempt ${attempt}/${maxRetries} failed:`, error.message);

      if (attempt === maxRetries) {
        console.error('❌ All server start attempts failed');
        console.error('Make sure just is installed and test servers can be started');
        throw error;
      }

      // Wait before retrying
      console.log('⏳ Waiting before retry...');
      execSync('sleep 5');
    }
  }
}

async function globalSetup() {
  // Set environment variables
  process.env.PLAYWRIGHT_BASE_URL = 'http://localhost:5889';
  process.env.USE_MEMORY_DB = 'true';

  console.log('🔧 VS Code Playwright Global Setup Starting...');
  console.log('Current working directory:', process.cwd());

  // Fix working directory issue - VS Code extension might start from root
  const expectedProjectRoot = '/workspaces/agentleague';
  if (process.cwd() !== expectedProjectRoot) {
    console.log(`🔧 Changing working directory from ${process.cwd()} to ${expectedProjectRoot}`);
    try {
      process.chdir(expectedProjectRoot);
      console.log('✅ Working directory changed successfully');
    } catch (error) {
      console.error('❌ Failed to change working directory:', error.message);
      throw new Error(`Cannot change to project root directory: ${expectedProjectRoot}`);
    }
  }

  // Note: Removed lock mechanism for VS Code extension as it was causing issues
  // The VS Code config uses 1 worker so conflicts should be minimal

  // Always stop existing servers first to avoid conflicts
  stopExistingServers();

  // Wait a moment for cleanup
  await new Promise(resolve => setTimeout(resolve, 2000));

  // Start fresh servers (this includes database setup)
  startServers();

  // Wait a bit for servers to be fully ready
  await new Promise(resolve => setTimeout(resolve, 5000));

  // Verify servers are now running
  if (!areServersRunning()) {
    throw new Error('Failed to start test servers');
  }

  // Additional verification: check if we can reach the backend health endpoint
  try {
    execSync('curl -s http://localhost:9997/health', { stdio: 'ignore' });
    console.log('✅ Backend health check passed');
  } catch (error) {
    console.error('❌ Backend health check failed');
    throw new Error('Backend is not responding to health checks');
  }

  // Verify test database has users (simple check)
  try {
    // Check if test database file exists (we're already in project root)
    if (existsSync('./test_database.db')) {
      console.log('✅ Test database file exists');
    } else {
      console.log('⚠️  Test database file not found at ./test_database.db');
    }
  } catch (error) {
    console.log('⚠️  Could not verify test database:', error.message);
  }

  console.log('✅ Test environment ready for VS Code Playwright extension');

  // Note: We don't remove the lock file here because tests are about to run
  // The lock file will be cleaned up when the test process exits or by the next test session
}

export default globalSetup;
