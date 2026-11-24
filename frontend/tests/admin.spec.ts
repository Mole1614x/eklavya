import { expect, test } from "@playwright/test";

const identity = process.env.UAT_ADMIN_IDENTITY ?? "uat_admin@example.com";
const password = process.env.UAT_ADMIN_PASSWORD ?? "UatAdminPass123!";

test("administrator creates, publishes, and reviews through the real BFF", async ({ page }) => {
  await page.goto("/auth");
  await page.getByLabel("Email or username").fill(identity);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin$/);

  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Admin control center" })).toBeVisible();
  await page.getByRole("tab", { name: "Problems" }).click();

  const title = "Release Readiness Sum";
  const editor = page.locator("form.admin-editor").filter({ has: page.getByRole("heading", { name: "Create or replace a problem" }) });
  await editor.getByLabel("Unique slug").fill("uat-release-readiness-sum");
  await editor.getByLabel("Validated definition").fill(JSON.stringify({
    title,
    category: "foundations",
    difficulty: "Easy",
    format: "CODE",
    topic: "Release readiness",
    tags: ["uat"],
    description: "Read two integers and print their sum.",
    constraints: ["Input contains two integers."],
    examples: [{ input: "1 2\n", output: "3\n" }],
    choices: [],
    status: "DRAFT",
    starters: [{ language: "python", code: "a, b = map(int, input().split())\n" }],
    test_cases: [
      { input_data: "1 2\n", expected_output: "3\n", is_hidden: false, position: 0 },
      { input_data: "-2 5\n", expected_output: "3\n", is_hidden: true, position: 1 },
    ],
    evaluator: null,
  }, null, 2));
  await editor.getByRole("button", { name: "Save changes" }).click();
  await expect(editor.getByRole("status")).toContainText("Saved and audited.");

  let row = page.getByRole("row").filter({ hasText: title });
  await row.getByRole("button", { name: "Publish" }).click();
  await expect(page.locator(".admin-notice")).toContainText("Problem status updated.");
  row = page.getByRole("row").filter({ hasText: title });
  await expect(row).toContainText("PUBLISHED");

  await page.getByRole("tab", { name: "Contests" }).click();
  await page.getByRole("button", { name: "Review" }).first().click();
  await expect(page.getByRole("heading", { name: /review$/ })).toBeVisible();
  await expect(page.getByText(/Submissions \(\d+\)/)).toBeVisible();

  await page.getByRole("tab", { name: "Problems" }).click();
  row = page.getByRole("row").filter({ hasText: title });
  await row.getByRole("button", { name: "Archive" }).click();
  await expect(page.locator(".admin-notice")).toContainText("Problem archived.");
});
