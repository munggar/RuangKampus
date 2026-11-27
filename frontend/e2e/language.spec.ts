import { expect, test } from "@playwright/test";

test("global language switch translates auth UI and persists after reload", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Selamat datang kembali" })).toBeVisible();

  await page.locator(".language-switch button").nth(1).click();
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await expect(page.getByPlaceholder("Enter your student ID")).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();

  await page.locator(".language-switch button").nth(0).click();
  await expect(page.getByRole("heading", { name: "Selamat datang kembali" })).toBeVisible();
  await expect(page.getByPlaceholder("Masukkan NIM Anda")).toBeVisible();
});
