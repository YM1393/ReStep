import { test, expect } from '@playwright/test';

test.describe('Test / Video Upload Flow', () => {
  test('landing page shows test type badges (10MWT, TUG, BBS)', async ({ page }) => {
    await page.goto('/');
    // The landing page has test type badges in the hero section
    await expect(page.getByText('10MWT').first()).toBeVisible();
    await expect(page.getByText('TUG').first()).toBeVisible();
    await expect(page.getByText('BBS').first()).toBeVisible();
  });

  test('unauthenticated user cannot access upload page', async ({ page }) => {
    // Try to go to a patient test page directly without logging in
    await page.goto('/patients/some-id/test');
    // Should redirect to landing page
    await expect(page).toHaveURL('/');
  });

  test('non-existent patient test page redirects to root', async ({ page }) => {
    // Without login, navigating to a test page should redirect
    await page.goto('/patients/nonexistent/test');
    await page.waitForTimeout(1000);
    // Should end up at the landing page (not logged in)
    await expect(page).toHaveURL('/');
  });
});
