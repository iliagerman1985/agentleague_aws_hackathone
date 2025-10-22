import { test, expect } from "@playwright/test";
import { loginAs } from "../../utils/auth";
import { getProviderConfigs, type ProviderConfigs } from "../../utils/providerConfig";

// Get provider configurations using shared utility
let PROVIDER_CONFIGS: ProviderConfigs;

// Initialize provider configs before tests
test.beforeAll(async () => {
  PROVIDER_CONFIGS = await getProviderConfigs();
});

// Assumes at least one integration exists or will be created during run.

 test.describe("LLM Model Selection", () => {
  test.beforeEach(async ({ page }) => {
    // Use USER instead of ADMIN to get pre-populated integrations
    // ADMIN user has no integrations for CRUD testing
    await loginAs(page, "USER");
    // Ensure we are on a page that renders the LLM model selector
    try {
      await page.goto('/tools');
    } catch {}
  });

  test("shows CTA when no integrations, then reflects selection after create @regression", async ({ page }) => {
    try {
      console.log('\n=== Starting LLM Model Selection Test ===');
      
      await page.goto("/tools/new");

      // Helper: find the first VISIBLE LLM trigger (desktop layout also exists in DOM but is hidden on mobile)
      const getVisibleTrigger = async () => {
        const candidates = page.getByTestId('llm-model-trigger');
        const count = await candidates.count();
        for (let i = 0; i < count; i++) {
          const t = candidates.nth(i);
          if (await t.isVisible({ timeout: 1000 })) return t;
        }
        return undefined;
      };

      // Open the LLM model dropdown (prefer visible test id)
      const openDropdown = async () => {
        try {
          await page.waitForLoadState('domcontentloaded');
          await page.waitForTimeout(150);

          // If already open (search input visible), do nothing
          const searchInput = page.getByPlaceholder('Search models...');
          if (await searchInput.isVisible({ timeout: 1000 })) return;

          // Try visible test id (on mobile the hidden desktop instance also exists in DOM)
          const trigger = await getVisibleTrigger();
          if (trigger) {
            await trigger.scrollIntoViewIfNeeded().catch(() => {});
            await trigger.click({ timeout: 3000 }).catch(async () => {
              await trigger.click({ force: true });
            });
            await expect(searchInput).toBeVisible({ timeout: 15000 });
            return;
          }

          // Fallback to role/text
          const candidate = page.getByRole('button').filter({ hasText: /select a model|select model|llm model/i }).first();
          if (await candidate.count() > 0) {
            await candidate.scrollIntoViewIfNeeded().catch(() => {});
            await candidate.click({ timeout: 3000 }).catch(async () => {
              await candidate.click({ force: true });
            });
            await expect(searchInput).toBeVisible({ timeout: 15000 });
            return;
          }

          // As a last resort on mobile, tap where the trigger usually is
          await page.mouse.move(50, 140);
          await page.mouse.down();
          await page.mouse.up();
          if (await searchInput.isVisible({ timeout: 1000 })) return;

          throw new Error('Could not find LLM model dropdown trigger');
        } catch (error) {
          throw new Error(`Failed to open dropdown: ${error}`);
        }
      };

      console.log('Opening LLM model dropdown...');
      await openDropdown();

      // If empty, CTA should be visible
      const addCta = page.getByRole('button', { name: /add integration/i });
      if (await addCta.isVisible()) {
        console.log('No integrations found, creating OpenAI integration...');
        await addCta.click();

        // Wait for dialog to open
        await expect(page.getByRole('dialog')).toBeVisible();

        // The dialog now uses tabs - click on the OpenAI tab
        await page.getByRole('tab', { name: /openai/i }).click();

        // Wait for the OpenAI provider card content to be visible (use the card title, not the tab)
        await expect(page.locator('div.font-semibold').getByText('OpenAI')).toBeVisible();

        // Create OpenAI with the API key from shared config
        const openaiKey = PROVIDER_CONFIGS.openai.apiKey || 'sk-dummy';
        await page.locator('#openai-api-key').fill(openaiKey);
        await page.getByRole('button', { name: /^(save|update)$/i }).click();

        // Dialog now auto-closes after successful save
        await expect(page.getByRole('dialog')).toBeHidden({ timeout: 20000 });
        console.log('✓ OpenAI integration created successfully');
      } else {
        console.log('Integrations already exist, proceeding to model selection...');
        // If already has integrations, close dialog if opened
        const cancel = page.getByRole('button', { name: /^cancel$/i });
        if (await cancel.isVisible()) {
          await cancel.click();
        }
      }

      // Select any available model from dropdown list
      console.log('Selecting a model from dropdown...');
      await openDropdown();

      // Wait for enhanced selector dropdown to be ready (search input visible)
      await expect(page.getByPlaceholder('Search models...')).toBeVisible({ timeout: 20000 });

      // Pick the first visible model option
      const anyModel = page.getByRole('menuitem').first();
      await anyModel.waitFor({ state: 'visible', timeout: 15000 });
      await anyModel.click();

      // Selector button should no longer show the placeholder text
      const triggerAfter = page.getByTestId('llm-model-trigger').first();
      await expect(triggerAfter).not.toContainText(/select a model/i);
      
      console.log('✅ LLM model selection test completed successfully');
      
    } catch (error) {
      console.log(`\n❌ LLM model selection test failed: ${error}`);
      throw error; // Re-throw to ensure test fails
    }
  });
});

