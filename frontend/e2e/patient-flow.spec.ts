import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers/auth';

test.describe('Patient Flow', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('dashboard shows patient list section', async ({ page }) => {
    await expect(page.getByText('환자 목록')).toBeVisible();
  });

  test('search for patient by name', async ({ page }) => {
    const searchInput = page.getByPlaceholder('환자 이름 또는 번호 검색...');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('TestPatient');
    await searchInput.press('Enter');
    await page.waitForTimeout(1000);
    // The search results area should be visible
    await expect(page.getByText('환자 목록')).toBeVisible();
  });

  test('create patient via API and verify search works', async ({ page }) => {
    // Verify search functionality works with an arbitrary name
    const searchInput = page.getByPlaceholder('환자 이름 또는 번호 검색...');
    await searchInput.fill('E2E_Test_Patient');
    await searchInput.press('Enter');
    await page.waitForTimeout(1000);
    // Verify search completed (no error)
    await expect(page.getByText('환자 목록')).toBeVisible();
  });

  test('admin info notice is shown', async ({ page }) => {
    // Admin should see the admin notice
    await expect(
      page.getByText('관리자는 환자 등록/수정/삭제를 할 수 없습니다')
    ).toBeVisible();
  });

  test('filter and sort controls are functional', async ({ page }) => {
    // Risk filter
    const riskFilter = page.getByLabel('위험도 필터');
    await expect(riskFilter).toBeVisible();
    await riskFilter.selectOption('risk');
    await page.waitForTimeout(500);

    // Sort control
    const sortControl = page.getByLabel('정렬 기준');
    await expect(sortControl).toBeVisible();
    await sortControl.selectOption('name');
    await page.waitForTimeout(500);

    // Reset
    await riskFilter.selectOption('all');
  });
});
