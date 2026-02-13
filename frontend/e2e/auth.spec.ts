import { test, expect } from '@playwright/test';
import { loginAsAdmin, registerTherapist, loginAs } from './helpers/auth';

test.describe('Authentication', () => {
  test('landing page shows hero section', async ({ browser, baseURL }) => {
    // Use a fresh context with no cookies/storage to guarantee logged-out state
    const context = await browser.newContext({ baseURL });
    const page = await context.newPage();
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // The hero section contains "임상 보행 분석" inside a span
    await expect(page.locator('span:has-text("임상 보행 분석")')).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('link', { name: '무료 체험 시작', exact: true })).toBeVisible();
    await context.close();
  });

  test('login page shows login form', async ({ browser, baseURL }) => {
    const context = await browser.newContext({ baseURL });
    const page = await context.newPage();
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: '로그인' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByLabel('아이디')).toBeVisible();
    await expect(page.getByLabel('비밀번호')).toBeVisible();
    await expect(page.getByRole('button', { name: '로그인' })).toBeVisible();
    await context.close();
  });

  test('register new therapist account', async ({ page }) => {
    const uniqueUser = `testtherapist_${Date.now()}`;
    await registerTherapist(page, {
      username: uniqueUser,
      password: 'test1234',
      name: 'Test Therapist',
    });
    await expect(page.getByText('회원가입 완료')).toBeVisible();
    await expect(page.getByText('관리자 승인 후')).toBeVisible();
  });

  // Place the admin login test BEFORE the invalid credentials test
  // to avoid any backend throttle effects
  test('login with valid admin credentials redirects to dashboard', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.getByText('환자 목록')).toBeVisible();
  });

  test('login with invalid credentials shows error', async ({ page }) => {
    await loginAs(page, 'nonexistent_user', 'wrongpassword');
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 5000 });
  });
});
