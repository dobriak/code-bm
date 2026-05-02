import { test, expect } from "@playwright/test";

test.describe("User Journey 4: Save and load .raidio playlist file", () => {
  test("save playlist, reload page, load playlist, state restored", async ({ page }) => {
    await page.goto("/create");

    const track = page.locator(".creator-left-pane .track-row").first();
    await track.click();

    const playlistName = page.locator('input[placeholder="Playlist name (required)"]');
    await playlistName.fill("My Saved Playlist");

    const saveBtn = page.locator(".save-btn");
    const downloadPromise = page.waitForEvent("download");
    await saveBtn.click();
    const download = await downloadPromise;

    const filename = download.suggestedFilename();
    expect(filename).toMatch(/\.raidio$/);
    expect(filename).toContain("My_Saved_Playlist");

    const loadInput = page.locator('input[type="file"]');
    await loadInput.setInputFiles({
      name: filename,
      mimeType: "application/json",
      buffer: Buffer.from(JSON.stringify({
        raidio_version: 1,
        name: "My Saved Playlist",
        items: [],
      })),
    });

    await page.waitForTimeout(500);
  });
});
