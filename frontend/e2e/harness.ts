
// --- Automated E2E Testing Harness (Playwright) ---
import { test as base, expect, Page } from '@playwright/test';
import { setupMockBackend, teardownMockBackend } from './mockServer';

// Define custom fixture types
type E2EFixtures = {
    authenticatedPage: Page;
    mockBackend: any;
};

// Extend base test with custom fixtures
export const test = base.extend<E2EFixtures>({
    // Start a mock backend before tests
    mockBackend: [async ({}, use) => {
        const server = await setupMockBackend({ port: 8080 });
        console.log('Mock backend started on port 8080');
        
        await use(server);
        
        await teardownMockBackend(server);
        console.log('Mock backend stopped');
    }, { scope: 'worker', auto: true }],

    // Provide a pre-authenticated page state
    authenticatedPage: async ({ page }, use) => {
        // Intercept network requests to route to mock server
        await page.route('**/api/v1/**', async route => {
            const request = route.request();
            const url = new URL(request.url());
            url.port = '8080';
            
            const response = await page.request.fetch(url.toString(), {
                method: request.method(),
                headers: request.headers(),
                data: request.postData() || undefined,
            });
            await route.fulfill({ response });
        });

        // Set Auth Cookies/LocalStorage
        await page.context().addInitScript(() => {
            window.localStorage.setItem('user-preferences', JSON.stringify({ theme: 'dark' }));
        });
        await page.context().addCookies([{
            name: 'auth_token',
            value: 'mock_jwt_token_for_e2e_testing',
            domain: 'localhost',
            path: '/',
        }]);

        // Navigate to home and ensure auth state resolves
        await page.goto('/');
        await expect(page.locator('text=Dashboard')).toBeVisible();

        // Pass the authenticated page to the test
        await use(page);
    },
});

export { expect };

/*
Example Test File (e2e/dashboard.spec.ts):
----------------------------------------
import { test, expect } from './harness';

test('Dashboard loads critical metrics', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('[data-testid="metric-card-cpu"]')).toBeVisible();
    await authenticatedPage.click('text=Run Diagnostic');
    await expect(authenticatedPage.locator('.spinner')).toBeVisible();
});
*/

// Mock server placeholder for type correctness
async function setupMockBackend(config: any) { return { config }; }
async function teardownMockBackend(server: any) { return true; }
