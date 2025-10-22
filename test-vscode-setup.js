#!/usr/bin/env node

// Simple script to test if the VS Code Playwright setup works
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('🧪 Testing VS Code Playwright Extension Setup');
console.log('='.repeat(50));

// Check if required files exist
const requiredFiles = [
    'playwright.config.ts',
    'client/playwright.vscode.config.ts',
    '.vscode/extensions.json',
    '.vscode/settings.json'
];

console.log('📁 Checking required files...');
for (const file of requiredFiles) {
    if (fs.existsSync(file)) {
        console.log(`✅ ${file}`);
    } else {
        console.log(`❌ ${file} - MISSING`);
    }
}

console.log('\n🔍 Testing Playwright config discovery...');
try {
    // Test if Playwright can find and load the config
    const result = execSync('cd client && npx playwright test --list', { encoding: 'utf8' });
    if (result.includes('tests/integration')) {
        console.log('✅ Playwright can discover tests using the VS Code config');
    } else {
        console.log('⚠️  Playwright config loaded but no tests found');
    }
} catch (error) {
    console.log('❌ Error loading Playwright config:', error.message);
}

console.log('\n📋 Next steps:');
console.log('1. Reload VS Code window (Ctrl+Shift+P → "Developer: Reload Window")');
console.log('2. Open the Test Explorer panel (View → Test)');
console.log('3. The extension should now automatically start servers when running tests');
console.log('4. Click the play button next to any test to run it');

console.log('\n🛠️  If tests don\'t appear:');
console.log('- Make sure the Playwright extension is installed');
console.log('- Check that you\'re in the correct workspace folder');
console.log('- Try running "just start-test-servers" manually first');
