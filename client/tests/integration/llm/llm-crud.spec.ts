import { test, expect } from "@playwright/test";
import { loginAs } from "../../utils/auth";
import { getProviderConfigs, logAvailableCredentials, type ProviderConfigs } from "../../utils/providerConfig";

// Model constants are now imported through the shared provider config utility

// These flows exercise real backend endpoints; ensure backend is started with test-mode credentials
// and that provider packages are installed.

// Get provider configurations using shared utility
let PROVIDER_CONFIGS: ProviderConfigs;

// Initialize provider configs before tests
test.beforeAll(async () => {
  PROVIDER_CONFIGS = await getProviderConfigs();
  logAvailableCredentials(PROVIDER_CONFIGS);
});

// Helper function to test any provider
async function testProviderIntegration(
  page: any,
  providerKey: keyof typeof PROVIDER_CONFIGS
) {
  const config = PROVIDER_CONFIGS[providerKey];

  try {
    // Check if credentials are available
    if (!config.hasCredentials) {
      console.warn(`Skipping ${config.name} test - no credentials available`);
      return;
    }

    console.log(`Testing ${config.name} integration...`);

  // Increase timeout for this complex test
  test.setTimeout(120000); // 2 minutes

  // Open a page that shows the EnhancedLLMModelSelector with settings enabled
  await page.goto("/tools/new");

  // Open the model selector dropdown (prefer visible test id)
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(150);

  // Wait for the LLM context to load and try both approaches
  await page.waitForTimeout(1000); // Give time for context to load

  // First, try the "Add Integration" button approach
  const addIntegrationButton = page.getByRole('button', { name: /add integration/i }).first();
  const isAddButtonVisible = await addIntegrationButton.isVisible({ timeout: 5000 });

  if (isAddButtonVisible) {
    // No integrations exist - click "Add Integration" button
    console.log('  No integrations found, clicking Add Integration button');
    await addIntegrationButton.click();
  } else {
    // Try dropdown approach - but if it fails, fall back to Add Integration
    console.log('  Trying dropdown approach for Manage Integrations');
    let dropdownWorked = false;

    try {
      const triggers = page.getByTestId('llm-model-trigger');
      let clicked = false;
      const count = await triggers.count();
      for (let i = 0; i < count; i++) {
        const trigger = triggers.nth(i);
        if (await trigger.isVisible({ timeout: 3000 })) {
          await trigger.scrollIntoViewIfNeeded();
          await trigger.click({ timeout: 3000 });
          clicked = true;
          break;
        }
      }
      if (!clicked) {
        const fallback = page.getByRole('button', { name: /select model|model|llm/i }).first();
        await fallback.scrollIntoViewIfNeeded();
        await fallback.click({ timeout: 5000 });
      }

      // Check if dropdown opened successfully
      await page.waitForTimeout(500);
      const allMenuItems = page.getByRole('menuitem');
      const menuItemCount = await allMenuItems.count();
      console.log(`  Found ${menuItemCount} menu items in dropdown`);

      if (menuItemCount > 0) {
        // Dropdown worked - look for Manage Integrations
        const manageItem = page.getByRole('menuitem', { name: /manage integrations/i }).first();
        const manageVisible = await manageItem.isVisible({ timeout: 3000 });
        if (manageVisible) {
          await manageItem.click();
          dropdownWorked = true;
        }
      }
    } catch (error) {
      console.log('  Dropdown approach failed:', error);
    }

    // If dropdown didn't work, fall back to Add Integration button
    if (!dropdownWorked) {
      console.log('  Dropdown failed, falling back to Add Integration button');

      // The Add Integration button is inside the dropdown content, so we need to check if dropdown is open
      // Look for the button using the test ID we added
      const fallbackButton = page.getByTestId('add-integration-button');
      const fallbackVisible = await fallbackButton.isVisible({ timeout: 3000 });
      if (fallbackVisible) {
        console.log('  Found Add Integration button, clicking...');
        await fallbackButton.click();
      } else {
        // If button is not visible, the dropdown might not be open or there might be a different state
        console.log('  Add Integration button not visible, checking dropdown state...');

        // Try to look for any button with "Add Integration" text as fallback
        const textButton = page.getByRole('button', { name: /add integration/i }).first();
        const textButtonVisible = await textButton.isVisible({ timeout: 3000 });
        if (textButtonVisible) {
          console.log('  Found Add Integration button by text, clicking...');
          await textButton.click();
        } else {
          throw new Error('Neither dropdown nor Add Integration button approach worked');
        }
      }
    }
  }

  // Wait for dialog to open
  await expect(page.getByRole('dialog')).toBeVisible();

  // Click on the provider tab
  await page.getByRole('tab', { name: config.tabName }).click();

  // Wait for the provider card content to be visible
  await expect(page.locator('div.font-semibold.tracking-tight').getByText(config.name)).toBeVisible();

  // Fill API key for all providers (now using consistent structure)
  const input = page.locator(`input[id="${config.inputId}"]`);
  await input.fill(config.apiKey!);

  // Select a preferred model if available (use default model first, then try others)
  const modelsToTry = [config.defaultModel, ...config.preferredModels];

  const modelSelect = page.locator('select').first();
  if (await modelSelect.isVisible({ timeout: 5000 })) {
    const options = await modelSelect.locator('option').all();
    for (const model of modelsToTry) {
      for (const option of options) {
        const text = await option.textContent();
        const value = await option.getAttribute('value');
        if ((text && text.includes(model)) || (value && value === model)) {
          await modelSelect.selectOption(value || '');
          console.log(`    Selected model: ${text || value}`);
          return; // Exit once we've selected a model
        }
      }
    }
  } else {
    // Try to find model dropdown/combobox
    const modelDropdown = page.getByRole('combobox').or(page.getByRole('button')).filter({ hasText: /model|select/i }).first();
    if (await modelDropdown.isVisible({ timeout: 5000 })) {
      await modelDropdown.click();
      // Wait for dropdown to open and select preferred model option
      for (const model of modelsToTry) {
        const modelOption = page.getByRole('option').filter({ hasText: new RegExp(model.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i') }).first();
        if (await modelOption.isVisible({ timeout: 2000 })) {
          await modelOption.click();
          console.log(`    Selected model: ${model}`);
          return; // Exit once we've selected a model
        }
      }
    }
  }

  // Skip API key testing in CRUD test - this is covered by multi-provider test
  // For CRUD test, we just need to save the integration without validation
  console.log(`Skipping API validation for ${config.name} - focusing on CRUD operations`);

  // Save integration immediately (new UI saves per provider immediately)
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();

  // With the new immediate saving UI, we need to click the Save button in the provider card
  // This will save immediately and show a success toast
  const saveButton = dialog.getByRole('button', { name: /^(save|update)$/i }).first();
  if (await saveButton.isVisible({ timeout: 5000 })) {
    await saveButton.click();
    console.log(`  ✓ ${config.name} integration saved immediately`);
    
    // Wait for save to complete (success toast or UI update)
    await page.waitForTimeout(2000);
  } else {
    console.log(`  ⚠ Save button not visible, checking for existing integration`);
  }

  // Close dialog with OK button (no longer saves, just closes)
  const okButton = page.getByTestId('llm-dialog-ok');
  await expect(okButton).toBeVisible({ timeout: 5000 });
  await okButton.click();

  // Wait for dialog to close, then reopen to verify
  await page.waitForTimeout(1000);

  // Reopen the dialog to verify the integration was saved
  await page.goto("/tools/new");
  await page.waitForTimeout(1000);

  // Open the dialog again to check for delete button - now there should be integrations
  console.log(`  Reopening dialog to verify ${config.name} integration was saved...`);
  const triggers2 = page.getByTestId('llm-model-trigger');
  const trigger2 = triggers2.first();
  if (await trigger2.isVisible({ timeout: 5000 })) {
    await trigger2.click();
    // Now there should be integrations, so look for "Manage Integrations"
    const manageItem = page.getByRole('menuitem', { name: /manage integrations/i }).first();
    if (await manageItem.isVisible({ timeout: 3000 })) {
      await manageItem.click();
    } else {
      console.log('  Manage Integrations not found, trying fallback...');
      // Fallback: close dropdown and try again
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
      await trigger2.click();
      await page.waitForTimeout(500);
      const manageItem2 = page.getByRole('menuitem', { name: /manage integrations/i }).first();
      if (await manageItem2.isVisible({ timeout: 3000 })) {
        await manageItem2.click();
      }
    }
  }

  // Wait for dialog and select the provider tab
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 10000 });
  console.log(`  Dialog opened, selecting ${config.tabName} tab...`);
  await page.getByRole('tab', { name: config.tabName }).click();

  // Verify the integration was saved by checking if delete button appears
  const saveDeleteButton = page.getByTestId('llm-delete-integration').first();
  await expect(saveDeleteButton).toBeVisible({ timeout: 10000 });
  console.log(`  ✓ ${config.name} integration saved and delete button visible`);

  // Delete the integration directly since dialog is still open
  const deleteButton = page.getByTestId('llm-delete-integration').first();
  await expect(deleteButton).toBeVisible({ timeout: 10000 });
  await deleteButton.click();

  // Confirm deletion in the confirmation dialog
  await page.getByRole('button', { name: /^delete$/i }).click();

  // Wait for deletion to complete and verify delete button disappears
  await expect(deleteButton).not.toBeVisible({ timeout: 10000 });
  console.log(`  ✓ ${config.name} integration successfully deleted`);

  // Close the dialog using the OK button
  await page.waitForTimeout(300);
  const closeDialog = page.getByRole('dialog');
  if (await closeDialog.isVisible({ timeout: 3000 })) {
    const okButton = page.getByTestId('llm-dialog-ok');
    if (await okButton.isVisible({ timeout: 3000 })) {
      await okButton.click();
    } else {
      // Fallback to other close methods
      const closeButton = closeDialog.getByRole('button', { name: /close|ok|×/i }).first();
      if (await closeButton.isVisible({ timeout: 3000 })) {
        await closeButton.click();
      } else {
        await page.keyboard.press('Escape');
      }
    }
  }

  // Verify provider is no longer listed in dropdown
  const triggers3 = page.getByTestId('llm-model-trigger');
  let verified = false;
  const count3 = await triggers3.count();
  for (let i = 0; i < count3; i++) {
    const t3 = triggers3.nth(i);
    if (await t3.isVisible({ timeout: 3000 })) {
      await t3.scrollIntoViewIfNeeded();
      await t3.click({ timeout: 3000 });
      verified = true;
      break;
    }
  }

    if (verified) {
      // Verify provider badge is no longer present
      const deletedBadge = page.getByRole('menuitem').filter({ hasText: config.badge }).first();
      await expect(deletedBadge).not.toBeVisible({ timeout: 5000 });
      console.log(`✓ ${config.name} integration successfully deleted`);
    }
    
  } catch (error) {
    console.log(`❌ ${config.name} CRUD integration test failed: ${error}`);
    throw new Error(`CRUD integration test failed for ${config.name}: ${error}`);
  }
}

test.describe("LLM Integrations - CRUD", () => {
  test.beforeEach(async ({ page }) => {
    // Simple deterministic login for all LLM CRUD tests
    // Note: The ADMIN user (admin@admin.com) is configured to not have pre-populated
    // LLM integrations, ensuring a clean test state for CRUD operations
    await loginAs(page, "ADMIN");
  });

  // Test all providers in a single comprehensive test
  test("integration lifecycle (create, save, delete) @regression", async ({ page }) => {
    test.setTimeout(300000); // 5 minutes for all providers

    const errors: string[] = [];
    
    try {
      for (const [providerKey, config] of Object.entries(PROVIDER_CONFIGS)) {
        if (config.hasCredentials) {
          try {
            console.log(`\n=== Testing ${config.name} Provider CRUD ===`);
            await testProviderIntegration(page, providerKey as keyof typeof PROVIDER_CONFIGS);
            console.log(`✓ ${config.name} CRUD test completed successfully`);
          } catch (error) {
            const errorMsg = `${config.name} CRUD test failed: ${error}`;
            console.log(`✗ ${errorMsg}`);
            errors.push(errorMsg);
          }
        } else {
          console.log(`\n=== Skipping ${config.name} Provider (no credentials) ===`);
        }
      }
      
      // If any provider CRUD tests failed, fail the entire test
      if (errors.length > 0) {
        const failureMessage = `CRUD integration tests failed for ${errors.length} provider(s):\n${errors.join('\n')}`;
        console.log(`\n❌ ${failureMessage}`);
        throw new Error(failureMessage);
      }
      
      console.log('\n✅ All provider CRUD integration tests completed successfully');
      
    } catch (error) {
      console.log(`\n❌ CRUD integration test failed: ${error}`);
      throw error; // Re-throw to ensure test fails
    }
  });
});

