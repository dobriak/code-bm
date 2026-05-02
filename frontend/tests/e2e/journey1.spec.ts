import { test, expect } from "@playwright/test";

test.describe("User Journey 1: Library workflow", () => {
  test("scan library, search, build playlist, submit to queue", async ({ page }) => {
    await page.goto("/admin/login");

    await page.getByLabel("Email").fill("admin@raidio.local");
    await page.getByLabel("Password").fill("admin");
    await page.getByRole("button", { name: "Login" }).click();

    await expect(page).toHaveURL("/admin");

    await page.getByRole("button", { name: "Scan Library" }).click();
    await page.waitForTimeout(2000);

    const progressBar = page.locator(".progress-fill");
    await expect(progressBar).toBeVisible();

    await page.goto("/browse");

    const searchInput = page.locator(".search-box input");
    await searchInput.fill("beatles");
    await page.waitForTimeout(500);

    const trackRows = page.locator(".track-row");
    const count = await trackRows.count();
    expect(count).toBeGreaterThan(0);

    await page.goto("/create");

    const firstTrack = page.locator(".creator-left-pane .track-row").first();
    await firstTrack.click();

    const playlistName = page.locator('input[placeholder="Playlist name (required)"]');
    await playlistName.fill("Test Playlist");

    const sendBtn = page.locator(".send-btn");
    await sendBtn.click();

    await page.waitForTimeout(1000);
  });
});
