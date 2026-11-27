import { resolve } from "node:path";
import { test, expect, installMockApi, SCREEN_ROUTES, saveScreenshot, waitForPageReady } from "./support";

test("Stage 5 final route matrix across roles, themes, and representative viewports", async ({ page }) => {
  test.setTimeout(10 * 60 * 1000);
  const targets = [
    { width: 1440, height: 900, label: "desktop-1440" },
    { width: 1280, height: 800, label: "laptop-1280" },
    { width: 768, height: 1024, label: "tablet-768" },
    { width: 390, height: 844, label: "mobile-390" },
  ];
  const themes = ["light", "dark"] as const;

  for (const screen of SCREEN_ROUTES) {
    for (const target of targets) {
      for (const theme of themes) {
        await page.unroute("**/api/v1/**");
        const api = await installMockApi(page, screen.role);
        await page.setViewportSize({ width: target.width, height: target.height });
        await page.goto("/login");
        await page.evaluate((savedTheme) => localStorage.setItem("rk-theme", savedTheme), theme);
        await page.goto(screen.path);
        await waitForPageReady(page);
        await expect(page.locator("h1").first(), `Missing heading at ${screen.path}`).toBeVisible();

        const metrics = await page.evaluate(() => ({
          width: window.innerWidth,
          documentWidth: document.documentElement.scrollWidth,
          bodyWidth: document.body.scrollWidth,
          theme: document.documentElement.dataset.theme || "light",
          mobileNav: document.querySelector(".mobile-nav-shell")
            ? getComputedStyle(document.querySelector(".mobile-nav-shell")!).display
            : "missing",
        }));
        expect(metrics.documentWidth, `${screen.path} document overflow at ${target.width}`).toBeLessThanOrEqual(metrics.width + 1);
        expect(metrics.bodyWidth, `${screen.path} body overflow at ${target.width}`).toBeLessThanOrEqual(metrics.width + 1);
        expect(metrics.theme, `${screen.path} theme`).toBe(theme);
        if (screen.role && target.width <= 768) expect(metrics.mobileNav).not.toBe("none");

        await saveScreenshot(page, resolve(
          "test-results/stage-5",
          screen.group,
          screen.id,
          `${target.label}-${theme}.png`,
        ));
        expect(api.unmatched, `Unmapped API requests at ${screen.path}/${theme}/${target.width}`).toEqual([]);
      }
    }
  }
});
