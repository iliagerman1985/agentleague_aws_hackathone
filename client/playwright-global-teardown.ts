import { existsSync, unlinkSync } from 'fs';

/**
 * Global teardown for VS Code Playwright extension
 * Cleans up the test session lock file
 */

async function globalTeardown() {
  console.log('🧹 VS Code Playwright Global Teardown...');

  // Clean up lock file
  const lockFile = '/workspaces/agentleague/.playwright-test-lock';

  try {
    if (existsSync(lockFile)) {
      unlinkSync(lockFile);
      console.log('🔓 Test session lock released');
    }
  } catch (error) {
    console.log('⚠️  Could not remove lock file:', error.message);
  }

  console.log('✅ Global teardown complete');
}

export default globalTeardown;
