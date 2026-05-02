import { test, expect } from "@playwright/test";

test.describe("User Journey 3: Admin settings and jingle drop", () => {
  test("admin login, change settings, trigger jingle drop", async ({ page }) => {
    await page.goto("/admin/login");

    await page.getByLabel("Email").fill("admin@raidio.local");
    await page.getByLabel("Password").fill("admin");
    await page.getByRole("button", { name: "Login" }).click();

    await page.goto("/admin/settings");

    const crossfadeCheckbox = page.locator('input[name="crossfade_enabled"]');
    if (await crossfadeCheckbox.isVisible()) {
      await crossfadeCheckbox.check();
    }

    const saveBtn = page.locator('button[type="submit"]');
    await saveBtn.click();

    await page.waitForTimeout(500);

    const savedMsg = page.locator("text=Saved!");
    await expect(savedMsg).toBeVisible();

    await page.goto("/admin/queue");

    const jingleSection = page.locator(".insert-jingle");
    await expect(jingleSection).toBeVisible();
  });
});
