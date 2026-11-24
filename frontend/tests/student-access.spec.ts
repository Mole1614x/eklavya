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
