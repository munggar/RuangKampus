import { resolve } from "node:path";
import { test, expect, installMockApi, STUDENT_PATHS, saveScreenshot, waitForPageReady } from "./support";

test("Stage 4 student visual matrix", async ({ page }) => {
  test.setTimeout(10 * 60 * 1000);
  const viewports = [
    { width: 1440, height: 900, label: "desktop" },
    { width: 768, height: 1024, label: "tablet" },
    { width: 430, height: 932, label: "mobile-430" },
    { width: 390, height: 844, label: "mobile-390" },
    { width: 360, height: 800, label: "mobile-360" },
  ];

  const api = await installMockApi(page, "Student");
  await page.addInitScript(() => {
    const saved = sessionStorage.getItem("stage-4-theme");
    if (saved === "light" || saved === "dark") localStorage.setItem("rk-theme", saved);
  });
  await page.goto("/login");

  for (const viewport of viewports) {
    for (const theme of ["light", "dark"] as const) {
      await page.evaluate((value) => sessionStorage.setItem("stage-4-theme", value), theme);
      for (const screen of STUDENT_PATHS) {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await page.goto(screen.path);
        await waitForPageReady(page);
        await expect(page.locator("h1").first(), `Missing heading at ${screen.path}`).toBeVisible();

        const metrics = await page.evaluate(() => ({
          viewport: window.innerWidth,
          document: document.documentElement.scrollWidth,
          body: document.body.scrollWidth,
          theme: document.documentElement.dataset.theme || "light",
          mobileNav: document.querySelector(".mobile-nav-shell") ? getComputedStyle(document.querySelector(".mobile-nav-shell")!).display : "missing",
        }));
        expect(metrics.document, `${screen.path} document overflow at ${viewport.width}`).toBeLessThanOrEqual(metrics.viewport + 1);
        expect(metrics.body, `${screen.path} body overflow at ${viewport.width}`).toBeLessThanOrEqual(metrics.viewport + 1);
        expect(metrics.theme, `${screen.path} theme`).toBe(theme);
        if (viewport.width <= 768) expect(metrics.mobileNav, `${screen.path} mobile navigation`).not.toBe("none");

        await saveScreenshot(page, resolve(
          "test-results/stage-4",
          screen.id,
          `${viewport.label}-${viewport.width}-${theme}.png`,
        ));
      }
    }
  }
  expect(api.unmatched, "Unmapped student API requests in visual matrix").toEqual([]);
});
