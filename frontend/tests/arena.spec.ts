import { expect, test } from "@playwright/test";

test("Arena lists the seeded contest and protects registration", async ({ page }) => {
  await page.goto("/arena");
  await expect(page.getByRole("heading", { name: "Compete in the Arena", level: 1 })).toBeVisible();
  await expect(page.getByText("UPCOMING")).toBeVisible();
  await page.getByRole("link", { name: "View contest" }).click();
  await expect(page.getByText("STARTS IN")).toBeVisible();
  await expect(page.getByText("Problems unlock when the contest begins.")).toBeVisible();
  await page.getByRole("button", { name: "Register" }).click();
  await expect(page.getByRole("status")).toContainText("Authentication required");
});
