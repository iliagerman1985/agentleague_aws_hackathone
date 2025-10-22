import { test, expect } from "@playwright/test";
import { loginAs } from "../../utils/auth";
import { getProviderConfigs, logAvailableCredentials, type ProviderConfigs } from "../../utils/providerConfig";

// Multi-provider LLM integration tests
// Tests all available providers with real API calls
// Uses shared provider configuration for consistency

// Get provider configurations using shared utility
let PROVIDER_CONFIGS: ProviderConfigs;

// Initialize provider configs before tests
test.beforeAll(async () => {
  PROVIDER_CONFIGS = await getProviderConfigs();
  console.log('\n=== Multi-Provider Test Configuration ===');
  logAvailableCredentials(PROVIDER_CONFIGS);
});

// Helper function to test API key validation for a provider
async function testProviderAPIKey(
  page: any,
  providerKey: keyof typeof PROVIDER_CONFIGS,
  testInvalidKey: boolean = false
) {
  const config = PROVIDER_CONFIGS[providerKey];
  
  try {
    if (!config.apiKey && !testInvalidKey) {
      console.warn(`Skipping ${config.name} API key test - no API key available`);
      return;
    }

    console.log(`Testing ${config.name} API key validation...`);

  // Navigate to tools page
  await page.goto("/tools/new");
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(150);

  // Open model selector
  const trigger = page.getByTestId('llm-model-trigger').first();
  await trigger.click();

  // Try to open manage integrations, fall back to add integration if no integrations exist
  let dropdownWorked = false;
  try {
    const manageItem = page.getByRole('menuitem', { name: /manage integrations/i }).first();
    if (await manageItem.isVisible({ timeout: 3000 })) {
      await manageItem.click();
      dropdownWorked = true;
    }
  } catch (error) {
    console.log('Manage integrations not found, trying Add Integration...');
  }

  // If dropdown didn't work, fall back to Add Integration button
  if (!dropdownWorked) {
    const addButton = page.getByTestId('add-integration-button');
    if (await addButton.isVisible({ timeout: 3000 })) {
      await addButton.click();
    } else {
      throw new Error('Neither Manage Integrations nor Add Integration button found');
    }
  }

  // Wait for dialog and select provider tab
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('tab', { name: config.tabName }).click();
  await expect(page.locator('div.font-semibold.tracking-tight').getByText(config.name)).toBeVisible();

  // Test with invalid key first if requested
  if (testInvalidKey) {
    console.log(`  Testing invalid API key for ${config.name}...`);
    const input = page.locator(`input[id="${config.inputId}"]`);
    await input.fill('invalid-key-12345');
    
    // Click test button
    await page.getByRole('button', { name: /^test$/i }).click();
    
    // Should see failure result
    const failedContainer = page.locator('.bg-red-50');
    await expect(failedContainer).toBeVisible({ timeout: 120000 });
    console.log(`  ✓ Invalid key correctly rejected for ${config.name}`);
    
    // Clear the invalid key
    await input.clear();
  }

  // Test with valid key
  if (config.apiKey) {
    console.log(`  Testing valid API key for ${config.name}...`);
    const input = page.locator(`input[id="${config.inputId}"]`);
    await input.fill(config.apiKey);
    
    // Select preferred model if available
    await selectPreferredModel(page, config);
    
    // Click test button
    await page.getByRole('button', { name: /^test$/i }).click();
    
    // Wait for result
    const successContainer = page.locator('.bg-green-50');
    const failedContainer = page.locator('.bg-red-50');
    await expect(successContainer.or(failedContainer)).toBeVisible({ timeout: 120000 });
    
    const isSuccess = await successContainer.isVisible({ timeout: 1000 });
    console.log(`  ✓ Valid key test result for ${config.name}: ${isSuccess ? 'SUCCESS' : 'FAILURE'}`);
    
    if (!isSuccess) {
      const errorText = await failedContainer.textContent() || 'Unknown error';
      console.log(`    Error details: ${errorText}`);
      // FAIL THE TEST when API key validation fails
      throw new Error(`API key test failed for ${config.name}: ${errorText}`);
    }
  }

    // Close dialog using OK button (new UI pattern)
    const okButton = page.getByTestId('llm-dialog-ok');
    if (await okButton.isVisible({ timeout: 3000 })) {
      await okButton.click();
    } else {
      // Fallback to escape if OK button not found
      await page.keyboard.press('Escape');
    }
    await page.waitForTimeout(500);
    
  } catch (error) {
    console.log(`❌ ${config.name} API key test failed with error: ${error}`);
    throw new Error(`API key test failed for ${config.name}: ${error}`);
  }
}

// Helper function to select preferred model - this function is not used in API validation
// since the new model selector is integrated into the dropdown, not the provider dialog
async function selectPreferredModel(_page: any, config: any) {
  try {
    console.log(`⚠️ Model selection is not needed for API key validation - models are selected in the main dropdown, not provider dialog`);
    // For API key validation, we don't need to select a specific model
    // The provider dialog will use a default model for testing
    return;
  } catch (error) {
    console.log(`❌ Model selection failed for ${config.name}: ${error}`);
    throw new Error(`Failed to select model for ${config.name}: ${error}`);
  }
}

test.describe("LLM Multi-Provider Integration Tests", () => {
  test.beforeEach(async ({ page }) => {
    // Use USER instead of ADMIN to get pre-populated integrations
    // ADMIN user has no integrations for CRUD testing
    await loginAs(page, "USER");
  });

  test("validate API keys for all providers @regression", async ({ page }) => {
    test.setTimeout(180000); // 3 minutes
    
    const errors: string[] = [];
    
    try {
      for (const [providerKey, config] of Object.entries(PROVIDER_CONFIGS)) {
        if (config.apiKey) {
          try {
            console.log(`\n=== Testing API Key for ${config.name} ===`);
            await testProviderAPIKey(page, providerKey as keyof typeof PROVIDER_CONFIGS, true);
            console.log(`✓ ${config.name} API key validation completed successfully`);
          } catch (error) {
            const errorMsg = `${config.name} API key test failed: ${error}`;
            console.log(`✗ ${errorMsg}`);
            errors.push(errorMsg);
          }
        } else {
          console.log(`Skipping ${config.name} - no API key configured`);
        }
      }
      
      // If any provider tests failed, fail the entire test
      if (errors.length > 0) {
        const failureMessage = `API key validation failed for ${errors.length} provider(s):\n${errors.join('\n')}`;
        console.log(`\n❌ ${failureMessage}`);
        throw new Error(failureMessage);
      }
      
      console.log('\n✅ All configured provider API keys validated successfully');
      
    } catch (error) {
      console.log(`\n❌ API key validation test failed: ${error}`);
      throw error; // Re-throw to ensure test fails
    }
  });

  // Individual provider tests removed to avoid duplication
  // All providers are tested in the comprehensive tests above

  test("compare UI response times for model selection @regression", async ({ page }) => {
    test.setTimeout(300000); // 5 minutes
    
    const results: Array<{provider: string, latency: number, success: boolean}> = [];
    
    try {
      // Navigate to tools page once for all measurements
      await page.goto("/tools/new");
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(150);
      
      for (const [, config] of Object.entries(PROVIDER_CONFIGS)) {
        if (!config.apiKey) continue;
        
        console.log(`\n=== Measuring ${config.name} UI Response Time ===`);
        
        try {
          const startTime = Date.now();
          
          // Measure time to open LLM model selector dropdown
          const trigger = page.getByTestId('llm-model-trigger').first();
          await trigger.click();
          
          // Wait for dropdown to fully load with models (UI element - shorter timeout)
          await expect(page.getByPlaceholder('Search models...')).toBeVisible({ timeout: 10000 });
          
          // Use search box to find provider models (more reliable than scrolling)
          const searchBox = page.getByPlaceholder('Search models...');
          await searchBox.fill(config.name.toLowerCase());
          await page.waitForTimeout(500); // Wait for search results to filter
          
          // Look for provider models after search filtering
          const providerModels = page.getByRole('menuitem').filter({ hasText: config.badge });
          await expect(providerModels.first()).toBeVisible({ timeout: 5000 });
          
          console.log(`  ✓ Found ${config.name} models using search`);
          
          const endTime = Date.now();
          const uiLatency = endTime - startTime;
          
          // Close dropdown for next iteration
          await page.keyboard.press('Escape');
          await page.waitForTimeout(500);
          
          results.push({
            provider: config.name,
            latency: uiLatency,
            success: true
          });
          
          console.log(`  ✓ ${config.name} UI response: ${uiLatency}ms`);
          
        } catch (error) {
          console.log(`  ✗ ${config.name} UI measurement failed: ${error}`);
          results.push({
            provider: config.name,
            latency: -1,
            success: false
          });
          throw new Error(`UI performance test failed for ${config.name}: ${error}`);
        }
      }
      
      // Log performance comparison results
      console.log('\n=== UI Response Time Comparison ===');
      const successfulResults = results.filter(r => r.success);
      successfulResults.sort((a, b) => a.latency - b.latency);
      successfulResults.forEach((result, index) => {
        console.log(`${index + 1}. ${result.provider}: ${result.latency}ms`);
      });
      
      // Verify we have meaningful results
      if (successfulResults.length === 0) {
        throw new Error("No successful UI measurements recorded");
      }
      
    } catch (error) {
      console.log(`\n❌ Performance test failed with error: ${error}`);
      throw error; // Re-throw to fail the test
    }
  });
});
