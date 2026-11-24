import { expect, test } from "@playwright/test";

const tiers: Record<string, number> = { Beginner: 0, Easy: 1, Medium: 2, Hard: 3 };

test("catalog lists numbered questions in ascending difficulty and across pages", async ({ page }) => {
  await page.goto("/problems");
  const rows = page.locator(".problem-list li");
  await expect(rows).toHaveCount(50);
  await expect(rows.first().locator(".problem-index")).toHaveText("001");
  await expect(rows.last().locator(".problem-index")).toHaveText("050");
  const difficulties = await rows.locator(".difficulty").allTextContents();
  expect(difficulties.map(level => tiers[level])).toEqual(
    difficulties.map(level => tiers[level]).sort((a, b) => a - b)
  );
  await expect(page.locator(".problem-list .problem-solved-tick")).toHaveCount(0);

  await page.getByRole("navigation", { name: "Catalog pagination" }).getByRole("link", { name: "Next" }).click();
  await expect(page.locator(".problem-list li").first().locator(".problem-index")).toHaveText("051");
  await page.locator(".problem-list li a").first().click();
  await expect(page.getByRole("navigation", { name: "Question navigation", exact: true })).toContainText("Question 51 of");
});

test("difficulty filter and numbering agree for individual practice tracks", async ({ page }) => {
  await page.goto("/problems?category=foundations&difficulty=Medium");
  const rows = page.locator(".problem-list li");
  const total = await rows.count();
  expect(total).toBeGreaterThan(0);
  await expect(rows.first().locator(".problem-index")).toHaveText("001");
  const badges = await rows.locator(".difficulty").allTextContents();
  expect(badges.every(level => level === "Medium")).toBe(true);
});

test("question numbers and difficulty labels are readable on narrow screens", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/problems");
  const row = page.locator(".problem-list li").first();
  await expect(row.locator(".problem-index")).toBeVisible();
  await expect(row.locator(".difficulty")).toBeVisible();
});
