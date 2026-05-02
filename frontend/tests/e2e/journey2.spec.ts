import { test, expect } from "@playwright/test";

test.describe("User Journey 2: Multi-user round-robin", () => {
  test("two browsers submit playlists and verify round-robin order", async ({ browser }) => {
    const context1 = await browser.newContext({ storageState: undefined });
    const context2 = await browser.newContext({ storageState: undefined });

    const page1 = await context1.newPage();
    const page2 = await context2.newPage();

    await page1.goto("/create");
    await page2.goto("/create");

    const track1 = page1.locator(".creator-left-pane .track-row").first();
    await track1.click();

    const playlistName1 = page1.locator('input[placeholder="Playlist name (required)"]');
    await playlistName1.fill("Playlist A");

    await page1.locator(".send-btn").click();

    await track1.click();
    const playlistName2 = page2.locator('input[placeholder="Playlist name (required)"]');
    await playlistName2.fill("Playlist B");
    await page2.locator(".send-btn").click();

    await page1.waitForTimeout(500);

    const res = await page1.request.get("/api/v1/admin/queue");
    const queue = await res.json();

    const positions = queue.queue?.map((i: { position: number }) => i.position) ?? [];
    expect(positions.length).toBeGreaterThanOrEqual(2);

    const sorted = [...positions].sort();
    expect(positions).toEqual(sorted);

    await context1.close();
    await context2.close();
  });
});
