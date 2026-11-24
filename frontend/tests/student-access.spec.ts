import { expect, test } from "@playwright/test";

const identity = process.env.UAT_ADMIN_IDENTITY ?? "uat_admin@example.com";
const password = process.env.UAT_ADMIN_PASSWORD ?? "UatAdminPass123!";

test("admin student-access picker toggles scope and hides selection for ALL", async ({ page }) => {
  await page.goto("/auth");
  await page.getByLabel("Email or username").fill(identity);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Admin control center" })).toBeVisible();
  await page.getByRole("tab", { name: "Assessment Management" }).click();
  await expect(page.getByText("Who can access this content?")).toBeVisible();
  await page.getByRole("radio", { name: /All Students/ }).check();
  await expect(page.getByText("All eligible students will have access")).toBeVisible();
  await expect(page.getByLabel("Search registered learners")).toHaveCount(0);
  await page.getByRole("radio", { name: /Selected Students Only/ }).check();
  await expect(page.getByLabel("Search registered learners")).toBeVisible();
  await expect(page.getByText("Select at least one student before publishing")).toBeVisible();
});


test("admin can create a published assessment available immediately to all students", async ({ page }) => {
  await page.goto("/auth");
  await page.getByLabel("Email or username").fill(identity);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await page.getByRole("tab", { name: "Assessment Management" }).click();
  const form = page.locator("form.assessment-create-form");
  const title = `Immediate Practice ${Date.now().toString(36)}`;
  await form.getByLabel("Assessment title").fill(title);
  await form.getByLabel("Question bank problem").selectOption("parity-check");
  await form.getByRole("button", { name: "Add question" }).click();
  await form.getByLabel("Publish immediately after creating").check();
  await form.getByRole("button", { name: "Create and publish assessment" }).click();
  await expect(form.getByRole("status")).toContainText("Assessment published successfully.");
  const record = page.locator(".assessment-record").filter({ hasText: title });
  await expect(record).toBeVisible();
  await expect(record.locator(".assessment-window-badge")).toHaveText("AVAILABLE");
  await expect(record).toContainText("All eligible students");
});


test("Content Studio checks existing questions and blocks duplicate publication", async ({ page }) => {
  await page.goto("/auth");
  await page.getByLabel("Email or username").fill(identity);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await page.getByRole("tab", { name: "Problems / Question Management" }).click();
  const editor = page.locator("form.admin-editor").first();
  await editor.getByLabel("Unique slug").fill("duplicate-parity-new");
  await editor.getByLabel("Title").fill("Parity Check");
  await editor.getByRole("button", { name: "Check for duplicates" }).click();
  await expect(editor.getByText("Potential existing questions")).toBeVisible();
  await expect(editor.locator(".duplicate-matches")).toContainText("parity-check");
  await editor.getByRole("button", { name: "Save changes" }).click();
  await expect(editor.getByRole("status")).toContainText("Existing question found");
  await expect(page.locator("tr").filter({ hasText: "duplicate-parity-new" })).toHaveCount(0);
});
