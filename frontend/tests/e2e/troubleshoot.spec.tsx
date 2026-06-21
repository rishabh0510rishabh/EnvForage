/**
 * E2E tests for the AI Troubleshoot page.
 *
 * These tests use Playwright to verify the full troubleshoot flow:
 *   1. Page loads and renders key UI elements.
 *   2. "Load Sample Data" prefills the form correctly.
 *   3. Validation rejects empty / invalid JSON input.
 *   4. A successful analysis renders result cards.
 *
 * Run with:  npx playwright test tests/e2e/troubleshoot.spec.tsx
 */

import { test, expect } from "@playwright/test";

// ── Helpers ───────────────────────────────────────────────────────────────────

const BASE_URL = process.env.TEST_BASE_URL ?? "http://localhost:3000";
const TROUBLESHOOT_URL = `${BASE_URL}/troubleshoot`;

/** Minimal valid diagnostic JSON that the backend accepts. */
const MINIMAL_DIAGNOSTIC = JSON.stringify({
  agent_version: "2.0.0",
  os: { name: "Ubuntu 22.04", version: "22.04", architecture: "x86_64", wsl_version: null },
  cpu: { brand: "Intel Core i9", cores: 8, threads: 16 },
  ram: { total_gb: 32, available_gb: 16 },
  gpus: [{ name: "NVIDIA RTX 4090", vram_gb: 24, driver_version: "535.129", index: 0 }],
  cuda: { version: "12.1", toolkit_path: "/usr/local/cuda", cudnn_version: "8.7", nccl_version: null },
  python_installations: [],
  active_python: { version: "3.11.4", path: "/usr/bin/python3", is_venv: false, venv_path: null, pip_version: "23.2" },
});

// ── Page Load ─────────────────────────────────────────────────────────────────

test.describe("Troubleshoot Page — Initial Load", () => {
  test("should display the page heading", async ({ page }) => {
    await page.goto(TROUBLESHOOT_URL);
    await expect(page.getByRole("heading", { name: /AI Troubleshoot/i })).toBeVisible();
  });

  test("should show the diagnostic textarea", async ({ page }) => {
    await page.goto(TROUBLESHOOT_URL);
    await expect(page.locator("textarea")).toBeVisible();
  });

  test("should show the 'Run AI Analysis' button disabled when textarea is empty", async ({ page }) => {
    await page.goto(TROUBLESHOOT_URL);
    const btn = page.getByRole("button", { name: /Run AI Analysis/i });
    await expect(btn).toBeDisabled();
  });

  test("should show the profile selector with default option", async ({ page }) => {
    await page.goto(TROUBLESHOOT_URL);
    const select = page.locator("select");
    await expect(select).toHaveValue("pytorch-cuda");
  });
});

// ── Load Sample Data ──────────────────────────────────────────────────────────

test.describe("Troubleshoot Page — Sample Data Prefill", () => {
  test("should prefill textarea when 'Load Sample Data' is clicked", async ({ page }) => {
    await page.goto(TROUBLESHOOT_URL);
    await page.getByRole("button", { name: /Load Sample Data/i }).click();
    const textarea = page.locator("textarea");
    const value = await textarea.inputValue();
    expect(value).toContain('"agent_version"');
    expect(value).toContain('"os"');
    expect(value).toContain('"gpus"');
  });

  test("should enable the 'Run AI Analysis' button after prefill", async ({ page }) => {
    await page.goto(TROUBLESHOOT_URL);
    await page.getByRole("button", { name: /Load Sample Data/i }).click();
    await expect(page.getByRole("button", { name: /Run AI Analysis/i })).toBeEnabled();
  });
});

// ── Input Validation ──────────────────────────────────────────────────────────

test.describe("Troubleshoot Page — Input Validation", () => {
  test("should show an error for invalid JSON", async ({ page }) => {
    await page.goto(TROUBLESHOOT_URL);
    await page.locator("textarea").fill("this is not json {{{");
    await page.getByRole("button", { name: /Run AI Analysis/i }).click();
    // The error message should appear (exact text may vary)
    await expect(page.locator("text=/Invalid JSON|Unexpected token/i")).toBeVisible({ timeout: 3000 });
  });

  test("should show an error when os/cpu fields are missing", async ({ page }) => {
    await page.goto(TROUBLESHOOT_URL);
    await page.locator("textarea").fill('{"agent_version": "2.0.0"}');
    await page.getByRole("button", { name: /Run AI Analysis/i }).click();
    await expect(page.locator("text=/Missing required fields/i")).toBeVisible({ timeout: 3000 });
  });
});

// ── Full Analysis Flow (requires running backend) ─────────────────────────────

test.describe("Troubleshoot Page — Full Analysis Flow", () => {
  // Skip if the backend is not available in CI
  test.skip(
    process.env.SKIP_BACKEND_TESTS === "true",
    "Backend not available in this environment",
  );

  test("should display analysis results after successful submission", async ({ page }) => {
    await page.goto(TROUBLESHOOT_URL);
    await page.locator("textarea").fill(MINIMAL_DIAGNOSTIC);
    await page.getByRole("button", { name: /Run AI Analysis/i }).click();

    // Results section should appear (may take a few seconds for streaming to complete)
    await expect(
      page.getByRole("heading", { name: /Analysis Results/i }),
    ).toBeVisible({ timeout: 30_000 });
  });

  test("should show a 'New Analysis' button in the results view", async ({ page }) => {
    await page.goto(TROUBLESHOOT_URL);
    await page.locator("textarea").fill(MINIMAL_DIAGNOSTIC);
    await page.getByRole("button", { name: /Run AI Analysis/i }).click();
    await page.getByRole("heading", { name: /Analysis Results/i }).waitFor({ timeout: 30_000 });

    await expect(page.getByRole("button", { name: /New Analysis/i })).toBeVisible();
  });

  test("should return to the form when 'New Analysis' is clicked", async ({ page }) => {
    await page.goto(TROUBLESHOOT_URL);
    await page.locator("textarea").fill(MINIMAL_DIAGNOSTIC);
    await page.getByRole("button", { name: /Run AI Analysis/i }).click();
    await page.getByRole("heading", { name: /Analysis Results/i }).waitFor({ timeout: 30_000 });

    await page.getByRole("button", { name: /New Analysis/i }).click();
    await expect(page.getByRole("button", { name: /Run AI Analysis/i })).toBeVisible();
  });
});
