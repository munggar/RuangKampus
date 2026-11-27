import { resolve } from "node:path";
import { test, expect, installMockApi, ADMIN_PATHS, saveScreenshot, waitForPageReady } from "./support";

test("Stage 3 admin visual matrix", async ({ page }) => {
  test.setTimeout(8 * 60 * 1000);
  const targets = [
    { width: 1440, height: 900, label: "desktop", themes: ["light", "dark"] },
    { width: 1280, height: 800, label: "laptop", themes: ["light"] },
    { width: 768, height: 1024, label: "tablet", themes: ["light"] },
    { width: 390, height: 844, label: "mobile", themes: ["light"] },
    { width: 360, height: 800, label: "small-mobile", themes: ["light"] },
  ];
  for (const target of targets) {
    for (const theme of target.themes) {
      await page.unroute("**/api/v1/**");
      const api = await installMockApi(page, "Staff Sekretariat");
      await page.addInitScript((savedTheme: string) => localStorage.setItem("rk-theme", savedTheme), theme);
      for (const screen of ADMIN_PATHS) {
        await page.setViewportSize({ width: target.width, height: target.height });
        await page.goto(screen.path);
        await waitForPageReady(page);
        await expect(page.locator("h1").first()).toBeVisible();
        const metrics = await page.evaluate(() => ({
          width: window.innerWidth,
          documentWidth: document.documentElement.scrollWidth,
          theme: document.documentElement.dataset.theme || "light",
        }));
        expect(metrics.documentWidth, `${screen.path} overflow ${target.width}`).toBeLessThanOrEqual(metrics.width + 1);
        expect(metrics.theme).toBe(theme);
        await saveScreenshot(page, resolve("test-results/stage-3", screen.id, `${target.label}-${target.width}-${theme}.png`));
      }
      expect(api.unmatched, `Unmapped API requests at ${target.width}/${theme}`).toEqual([]);
    }
  }
});
