import { expect, test } from '@playwright/test'

// The API is mocked, so this test needs no backend.
test('home page shows the backend status', async ({ page }) => {
  await page.route('**/api/health', (route) =>
    route.fulfill({
      json: {
        status: 'ok',
        environment: 'test',
        database: { connected: true },
        providers: [],
      },
    }),
  )
  await page.goto('/')
  await expect(page.getByText('Backend: ok')).toBeVisible()
})
