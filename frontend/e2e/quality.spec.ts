import AxeBuilder from "@axe-core/playwright";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { test, expect, installMockApi, SCREEN_ROUTES, waitForPageReady } from "./support";

const darkAccessibilityIds = new Set(SCREEN_ROUTES.map((screen) => screen.id));

for (const screen of SCREEN_ROUTES) {
  test("axe WCAG 2.1 A/AA: " + screen.id + " light", async ({ page }, testInfo) => {
    test.setTimeout(60000);
    await installMockApi(page, screen.role);
    await page.addInitScript(() => window.localStorage.setItem("rk-theme", "light"));
    await page.goto(screen.path);
    await waitForPageReady(page);

    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    await testInfo.attach("axe-violations.json", {
      body: Buffer.from(JSON.stringify(result.violations, null, 2)),
      contentType: "application/json",
    });
    const severe = result.violations.filter((item) => item.impact === "critical" || item.impact === "serious");
    expect(
      severe.map((item) => ({ id: item.id, impact: item.impact, description: item.description, nodes: item.nodes.length })),
      "Critical/serious accessibility violations on " + screen.path,
    ).toEqual([]);
  });

  if (darkAccessibilityIds.has(screen.id)) {
    test("axe WCAG 2.1 A/AA: " + screen.id + " dark", async ({ page }, testInfo) => {
      test.setTimeout(60000);
      await installMockApi(page, screen.role);
      await page.addInitScript(() => window.localStorage.setItem("rk-theme", "dark"));
      await page.goto(screen.path);
      await waitForPageReady(page);

      const result = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();

      await testInfo.attach("axe-violations-dark.json", {
        body: Buffer.from(JSON.stringify(result.violations, null, 2)),
        contentType: "application/json",
      });
      const severe = result.violations.filter((item) => item.impact === "critical" || item.impact === "serious");
      expect(
        severe.map((item) => ({ id: item.id, impact: item.impact, description: item.description, nodes: item.nodes.length })),
        "Critical/serious dark-theme accessibility violations on " + screen.path,
      ).toEqual([]);
    });
  }
}

test("keyboard: skip link, main landmark, account dropdown and Escape handling", async ({ page }) => {
  await installMockApi(page, "Student");
  await page.goto("/student/dashboard");
  await waitForPageReady(page);

  await page.keyboard.press("Tab");
  await expect(page.locator(".skip-link")).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();

  const accountTrigger = page.locator(".account-trigger");
  await accountTrigger.click();
  await expect(accountTrigger).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("menuitem", { name: "Keluar" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(accountTrigger).toHaveAttribute("aria-expanded", "false");
  await expect(accountTrigger).toBeFocused();
});

test("keyboard: approval dialog traps focus and restores it after Escape", async ({ page }) => {
  await installMockApi(page, "Staff Sekretariat");
  await page.goto("/admin/reservations");
  await waitForPageReady(page);

  const approveTrigger = page.getByRole("button", { name: "Setujui", exact: true }).first();
  await approveTrigger.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const closeButton = dialog.getByRole("button", { name: "Tutup dialog" });
  await expect(closeButton).toBeFocused();

  await page.keyboard.press("Shift+Tab");
  await expect(dialog.getByRole("button", { name: "Setujui permohonan" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(approveTrigger).toBeFocused();
});

test("reduced motion preference is respected by the application styles", async ({ page }) => {
  await installMockApi(page, "Student");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/student/dashboard");
  await waitForPageReady(page);
  const preference = await page.evaluate(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  expect(preference).toBe(true);

  const transitionDuration = await page.locator(".nav-link").first().evaluate((element) =>
    getComputedStyle(element).transitionDuration,
  );
  expect(Number.parseFloat(transitionDuration)).toBeLessThanOrEqual(0.00001);
});

test("performance: records navigation, paint, layout shift, long task and asset metrics", async ({ page }, testInfo) => {
  await page.addInitScript(() => {
    type ObservedEntry = PerformanceEntry & { value?: number; hadRecentInput?: boolean };
    type WindowWithMetrics = Window & {
      __rkPerformanceEntries?: Array<{
        entryType: string;
        startTime: number;
        duration: number;
        value?: number;
        hadRecentInput?: boolean;
      }>;
    };
    const target = window as WindowWithMetrics;
    target.__rkPerformanceEntries = [];
    for (const entryType of ["layout-shift", "longtask", "largest-contentful-paint"]) {
      try {
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            const observed = entry as ObservedEntry;
            target.__rkPerformanceEntries?.push({
              entryType: observed.entryType,
              startTime: observed.startTime,
              duration: observed.duration,
              ...(typeof observed.value === "number" ? { value: observed.value } : {}),
              ...(typeof observed.hadRecentInput === "boolean" ? { hadRecentInput: observed.hadRecentInput } : {}),
            });
          }
        });
        observer.observe({ type: entryType, buffered: true });
      } catch {
        // Unsupported entry types are reported as unavailable in the metrics below.
      }
    }
  });

  await installMockApi(page, "Student");
  await page.goto("/student/dashboard");
  await waitForPageReady(page);

  const metrics = await page.evaluate(() => {
    type ObservedEntry = {
      entryType: string;
      startTime: number;
      duration: number;
      value?: number;
      hadRecentInput?: boolean;
    };
    const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
    const paints = performance.getEntriesByType("paint").map((item) => ({
      name: item.name,
      startTimeMs: Math.round(item.startTime * 100) / 100,
    }));
    const resources = performance.getEntriesByType("resource") as PerformanceResourceTiming[];
    const scripts = resources.filter((item) => item.initiatorType === "script");
    const styles = resources.filter((item) => item.initiatorType === "link" || item.name.endsWith(".css"));
    const images = Array.from(document.images);
    const observed = (window as typeof window & { __rkPerformanceEntries?: ObservedEntry[] }).__rkPerformanceEntries || [];
    const shifts = observed.filter((item) => item.entryType === "layout-shift" && !item.hadRecentInput);
    const longTasks = observed.filter((item) => item.entryType === "longtask");
    const largestPaint = observed.filter((item) => item.entryType === "largest-contentful-paint")
      .reduce<number | null>((latest, item) => latest === null || item.startTime > latest ? item.startTime : latest, null);
    const totalBytes = (items: PerformanceResourceTiming[]) =>
      items.reduce((sum, item) => sum + (item.transferSize || item.encodedBodySize || 0), 0);
    const round = (value: number) => Math.round(value * 100) / 100;

    return {
      capturedAt: new Date().toISOString(),
      route: window.location.pathname,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      documentReadyState: document.readyState,
      navigation: nav ? {
        responseStartMs: round(nav.responseStart),
        domInteractiveMs: round(nav.domInteractive),
        domContentLoadedMs: round(nav.domContentLoadedEventEnd),
        loadEventEndMs: round(nav.loadEventEnd),
        transferSizeBytes: nav.transferSize,
      } : null,
      paint: {
        entries: paints,
        largestContentfulPaintMs: largestPaint === null ? null : round(largestPaint),
      },
      layout: {
        layoutShiftCount: shifts.length,
        cumulativeLayoutShiftEstimate: round(shifts.reduce((sum, item) => sum + (item.value || 0), 0)),
      },
      longTasks: {
        count: longTasks.length,
        totalDurationMs: round(longTasks.reduce((sum, item) => sum + item.duration, 0)),
        maxDurationMs: round(longTasks.reduce((maximum, item) => Math.max(maximum, item.duration), 0)),
      },
      images: {
        count: images.length,
        loaded: images.filter((image) => image.complete && image.naturalWidth > 0).length,
        broken: images.filter((image) => image.complete && image.naturalWidth === 0).length,
        pending: images.filter((image) => !image.complete).length,
      },
      resources: {
        count: resources.length,
        scriptCount: scripts.length,
        styleCount: styles.length,
        imageResourceCount: resources.filter((item) => item.initiatorType === "img").length,
        scriptTransferBytes: totalBytes(scripts),
        styleTransferBytes: totalBytes(styles),
        totalTransferBytes: totalBytes(resources),
      },
    };
  });

  const outputPath = resolve("test-results/diagnostics/performance.json");
  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, JSON.stringify(metrics, null, 2), "utf8");
  await testInfo.attach("performance-metrics.json", {
    body: Buffer.from(JSON.stringify(metrics, null, 2)),
    contentType: "application/json",
  });

  expect(metrics.documentReadyState).toBe("complete");
  expect(metrics.navigation?.loadEventEndMs || 0).toBeGreaterThan(0);
  expect(metrics.navigation?.loadEventEndMs || 0).toBeLessThan(30000);
  expect(metrics.resources.scriptTransferBytes).toBeLessThan(8 * 1024 * 1024);
  expect(metrics.images.broken).toBe(0);
});
