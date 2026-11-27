import { resolve } from "node:path";
import { test, expect, installMockApi, SCREEN_ROUTES, STUDENT_PATHS, ADMIN_PATHS, saveScreenshot, waitForPageReady } from "./support";

const viewportTargets = [
  { width: 1440, height: 900, label: "desktop" },
  { width: 1024, height: 768, label: "laptop" },
  { width: 820, height: 1180, label: "tablet-820" },
  { width: 768, height: 1024, label: "tablet-768" },
  { width: 390, height: 844, label: "mobile" },
  { width: 320, height: 800, label: "small-mobile" },
];

for (const screen of SCREEN_ROUTES) {
  for (const theme of ["light", "dark"] as const) {
    test("visual route: " + screen.id + " / " + theme, async ({ page }) => {
      test.setTimeout(60000);
      const api = await installMockApi(page, screen.role);
      await page.addInitScript((savedTheme: string) => {
        window.localStorage.setItem("rk-theme", savedTheme);
      }, theme);
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto(screen.path);
      await waitForPageReady(page);
      await expect(page.locator("h1").first()).toBeVisible();

      const activeTheme = await page.evaluate(() => document.documentElement.dataset.theme || "light");
      expect(activeTheme).toBe(theme);

      const screenshot = resolve(
        "test-results/screenshots/baseline",
        screen.group,
        screen.id,
        screen.id + "-1440-" + theme + ".png",
      );
      await saveScreenshot(page, screenshot);
      expect(api.unmatched, "Unmapped API requests on " + screen.path).toEqual([]);
    });
  }
}

test("responsive layout: every protected route at all six target viewports", async ({ page }) => {
  test.setTimeout(8 * 60 * 1000);
  for (const viewport of viewportTargets) {
    for (const [role, routeScreens] of [
      ["Student", STUDENT_PATHS],
      ["Staff Sekretariat", ADMIN_PATHS],
    ] as const) {
      await page.unroute("**/api/v1/**");
      const api = await installMockApi(page, role);
      for (const screen of routeScreens) {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await page.goto(screen.path);
        await waitForPageReady(page);

        const metrics = await page.evaluate(() => {
          const main = document.querySelector("main.main-content");
          const nav = document.querySelector(".mobile-nav-shell");
          const links = Array.from(document.querySelectorAll(".mobile-nav-shell a"));
          return {
            viewportWidth: window.innerWidth,
            documentWidth: document.documentElement.scrollWidth,
            bodyWidth: document.body.scrollWidth,
            mainWidth: main ? (main as HTMLElement).scrollWidth : 0,
            mobileNavDisplay: nav ? getComputedStyle(nav).display : "missing",
            mobileNavHeight: nav ? (nav as HTMLElement).getBoundingClientRect().height : 0,
            mobileLinkHeights: links.map((item) => (item as HTMLElement).getBoundingClientRect().height),
            mobileLabels: links.map((item) => (item.textContent || "").trim()),
          };
        });

        expect(
          metrics.documentWidth,
          screen.path + " document horizontal overflow at " + viewport.width,
        ).toBeLessThanOrEqual(metrics.viewportWidth + 1);
        expect(
          metrics.bodyWidth,
          screen.path + " body horizontal overflow at " + viewport.width,
        ).toBeLessThanOrEqual(metrics.viewportWidth + 1);
        expect(metrics.mainWidth).toBeLessThanOrEqual(metrics.viewportWidth + 1);

        if (viewport.width <= 1180) {
          expect(metrics.mobileNavDisplay, "Mobile navigation hidden at " + viewport.width).not.toBe("none");
          expect(metrics.mobileNavHeight).toBeGreaterThan(0);
          expect(Math.min(...metrics.mobileLinkHeights)).toBeGreaterThanOrEqual(44);
          if (role === "Staff Sekretariat") {
            expect(metrics.mobileLabels.some((label) => label.includes("Jadwal"))).toBe(true);
            expect(metrics.mobileLabels.some((label) => label.includes("Impor"))).toBe(true);
          }
        } else {
          expect(metrics.mobileNavDisplay).toBe("none");
        }

        const responsiveScreenshot = resolve(
          "test-results/screenshots/final/responsive",
          role === "Student" ? "student" : "admin",
          screen.id,
          screen.id + "-" + viewport.width + "-light.png",
        );
        await saveScreenshot(page, responsiveScreenshot);
      }
      expect(api.unmatched, "Unmapped mock API requests for " + role + " at " + viewport.width).toEqual([]);
    }

    await page.unroute("**/api/v1/**");
    const publicApi = await installMockApi(page, null);
    for (const screen of SCREEN_ROUTES.filter((item) => item.group === "auth")) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(screen.path);
      await waitForPageReady(page);
      const publicMetrics = await page.evaluate(() => ({
        viewportWidth: window.innerWidth,
        documentWidth: document.documentElement.scrollWidth,
        bodyWidth: document.body.scrollWidth,
      }));
      expect(publicMetrics.documentWidth, screen.path + " document overflow at " + viewport.width)
        .toBeLessThanOrEqual(publicMetrics.viewportWidth + 1);
      expect(publicMetrics.bodyWidth, screen.path + " body overflow at " + viewport.width)
        .toBeLessThanOrEqual(publicMetrics.viewportWidth + 1);
      await saveScreenshot(page, resolve(
        "test-results/screenshots/final/responsive/auth",
        screen.id,
        screen.id + "-" + viewport.width + "-light.png",
      ));
    }
    expect(publicApi.unmatched, "Unmapped public mock API requests at " + viewport.width).toEqual([]);
  }
});

test("theme: toggling persists across navigation and public auth uses stored theme", async ({ page }) => {
  await installMockApi(page, "Student");
  await page.goto("/student/dashboard");
  await waitForPageReady(page);

  const themeButton = page.getByRole("button", { name: "Aktifkan mode gelap" });
  await themeButton.click();
  await expect.poll(() => page.evaluate(() => document.documentElement.dataset.theme)).toBe("dark");
  await expect(page.getByRole("button", { name: "Aktifkan mode terang" })).toBeVisible();

  await page.getByRole("link", { name: "Rooms", exact: true }).click();
  await waitForPageReady(page);
  await expect.poll(() => page.evaluate(() => document.documentElement.dataset.theme)).toBe("dark");

  await page.goto("/login");
  await waitForPageReady(page);
  await expect.poll(() => page.evaluate(() => document.documentElement.dataset.theme)).toBe("dark");
  const authTheme = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement);
    const panel = document.querySelector(".auth-panel");
    const tokenProbe = document.createElement("span");
    tokenProbe.style.backgroundColor = "var(--surface-card)";
    document.body.append(tokenProbe);
    const result = {
      colorScheme: root.colorScheme,
      background: panel ? getComputedStyle(panel).backgroundColor : "missing",
      expectedBackground: getComputedStyle(tokenProbe).backgroundColor,
    };
    tokenProbe.remove();
    return result;
  });
  expect(authTheme.colorScheme).toBe("dark");
  expect(authTheme.background).toBe(authTheme.expectedBackground);
});
