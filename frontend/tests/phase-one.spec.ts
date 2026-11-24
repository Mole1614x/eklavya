import { expect, test } from "@playwright/test";
import { community, modules } from "../lib/navigation";

test("navigation reaches every Phase 1 section", async ({ page }) => {
  await page.goto("/");
  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  await navigation.getByRole("link", { name: "Dashboard" }).click();
  await expect(page.getByRole("heading", { name: "Progress at a glance" })).toBeVisible();
  await expect(page.getByText("Sign in to see your verified skill analytics.")).toBeVisible();
  for (const module of [...modules, ...community]) {
    await navigation.getByRole("link", { name: module.label, exact: true }).click();
    await expect(page.getByRole("heading", { name: module.title, level: 1 })).toBeVisible();
  }
});

test("catalog filtering opens a working Monaco editor and honest statuses", async ({ page }) => {
  await page.goto("/problems");
  await expect(page.getByRole("heading", { name: "122 problems" })).toBeVisible();
  await page.getByRole("searchbox").fill("Star Staircase");
  await page.getByLabel("Category").selectOption("foundations");
  await page.getByLabel("Difficulty").selectOption("Beginner");
  await page.getByLabel("Topic").selectOption("Patterns");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page.getByRole("heading", { name: "1 problem" })).toBeVisible();
  const localLoader = page.waitForResponse((response) => new URL(response.url()).pathname === "/monaco/vs/loader.js");
  await page.getByRole("link", { name: /Star Staircase/ }).click();
  expect((await localLoader).ok()).toBe(true);
  await expect(page.getByRole("heading", { name: "Star Staircase", level: 1 })).toBeVisible();
  await expect(page.locator(".monaco-editor")).toBeVisible({ timeout: 15000 });
  await expect(page.locator(".monaco-editor .view-lines")).toContainText("#include");
  await page.getByLabel("Language").selectOption("python");
  await expect(page.locator(".monaco-editor .view-lines")).toContainText("input()");
  const editor = page.locator(".monaco-editor");
  await editor.click();
  await page.keyboard.press("Control+End");
  await page.keyboard.type("# My draft");
  await page.getByLabel("Language").selectOption("c");
  await expect(page.locator(".monaco-editor .view-lines")).toContainText("#include");
  await page.getByLabel("Language").selectOption("python");
  await expect(page.locator(".monaco-editor .view-lines")).toContainText("My draft");
  await page.getByRole("button", { name: "Run" }).click();
  await expect(page.getByRole("status")).toContainText("Sign in to run or submit solutions.");
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByRole("status")).toContainText("Sign in to run or submit solutions.");
});

test("mobile menu and missing problem recovery", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const result = await page.goto("/problems/does-not-exist");
  expect(result?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "Page unavailable" })).toBeVisible();
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("link", { name: "Statistics", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Reason from evidence" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Toggle navigation" })).toHaveAttribute("aria-expanded", "false");
});

test("statistics answers and data expression have distinct workspaces", async ({ page }) => {
  await page.goto("/problems/sample-variance");
  await expect(page.getByText("Numerical", { exact: true })).toBeVisible();
  await page.getByLabel("Draft answer").fill("4");
  await page.goto("/problems/independent-events");
  await expect(page.getByText("Multiple choice", { exact: true })).toBeVisible();
  const answer = page.getByRole("radio", { name: "P(A) × P(B)" });
  await answer.check();
  await expect(answer).toBeChecked();
  await page.goto("/problems/filter-students");
  await expect(page.getByText("Expression", { exact: true })).toBeVisible();
  await expect(page.locator(".monaco-editor")).toBeVisible();
});
