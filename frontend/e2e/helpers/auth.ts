import { type Page, expect } from '@playwright/test';

/**
 * Login as the default admin account (admin / admin).
 * After login the page should redirect to the dashboard ("/").
 */
export async function loginAsAdmin(page: Page) {
  // Navigate to login and clear stale auth state, then reload to get a clean form
  await page.goto('/login');
  await page.evaluate(() => {
    localStorage.clear();
  });
  await page.goto('/login');
  await expect(page.getByLabel('아이디')).toBeVisible({ timeout: 10000 });

  await page.getByLabel('아이디').fill('admin');
  await page.getByLabel('비밀번호').fill('admin');
  await page.getByRole('button', { name: '로그인' }).click();

  // Wait for dashboard to render - use a generous timeout
  await expect(page.getByText('환자 목록')).toBeVisible({ timeout: 20000 });
}

/**
 * Register a new therapist account and return the credentials.
 * Does NOT log in -- the therapist still needs admin approval.
 */
export async function registerTherapist(
  page: Page,
  opts: { username: string; password: string; name: string },
) {
  await page.goto('/register');
  await page.getByLabel('이름').fill(opts.name);
  await page.getByLabel('아이디').fill(opts.username);
  await page.getByLabel('비밀번호', { exact: true }).fill(opts.password);
  await page.getByLabel('비밀번호 확인').fill(opts.password);
  await page.getByRole('button', { name: '회원가입' }).click();

  // Wait for the success screen
  await expect(page.getByText('회원가입 완료')).toBeVisible({ timeout: 10000 });
}

/**
 * Login as a specific user (therapist or admin).
 */
export async function loginAs(
  page: Page,
  username: string,
  password: string,
) {
  await page.goto('/login');
  await expect(page.getByLabel('아이디')).toBeVisible({ timeout: 10000 });
  await page.getByLabel('아이디').fill(username);
  await page.getByLabel('비밀번호').fill(password);
  await page.getByRole('button', { name: '로그인' }).click();
}

/**
 * Ensure a clean logged-out state for tests that check landing/public pages.
 */
export async function ensureLoggedOut(page: Page) {
  await page.goto('/login');
  await page.evaluate(() => {
    localStorage.clear();
  });
}
