import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers/auth';

test.describe('Admin Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('admin dashboard page loads and shows statistics', async ({ page }) => {
    await page.goto('/admin/dashboard');
    // Wait for the dashboard heading
    await expect(page.getByText('병원 통계 대시보드')).toBeVisible({ timeout: 10000 });
    // Should show summary cards - use exact match to avoid ambiguity
    await expect(page.getByText('전체 환자', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('총 검사', { exact: true })).toBeVisible();
    await expect(page.getByText('이번 주', { exact: true })).toBeVisible();
    await expect(page.getByText('이번 달', { exact: true })).toBeVisible();
  });

  test('therapist management page loads', async ({ page }) => {
    await page.goto('/admin/therapists');
    // The page should load without error
    await page.waitForTimeout(2000);
    // Check that we are still on the therapists page (not redirected)
    await expect(page).toHaveURL('/admin/therapists');
  });

  test('export buttons exist on admin dashboard', async ({ page }) => {
    await page.goto('/admin/dashboard');
    await expect(page.getByText('병원 통계 대시보드')).toBeVisible({ timeout: 10000 });

    // Check for the export section
    await expect(page.getByText('데이터 내보내기 / 백업')).toBeVisible();
    await expect(page.getByText('환자 목록 CSV')).toBeVisible();
    await expect(page.getByText('검사 결과 CSV')).toBeVisible();
    await expect(page.getByText('DB 백업')).toBeVisible();
  });

  test('admin can navigate to therapist management from dashboard', async ({ page }) => {
    // Use first() to avoid strict mode violation (two "치료사 관리" links exist)
    const therapistLink = page.getByText('치료사 관리').first();
    await expect(therapistLink).toBeVisible();
    await therapistLink.click();
    await expect(page).toHaveURL('/admin/therapists');
  });
});
