import { expect, test } from "@playwright/test";

test("question Previous and Next follow the filtered catalog order", async ({ page }) => {
  await page.goto("/problems?category=foundations");
  const links = page.locator(".problem-list li a");
  const firstHref = await links.nth(0).getAttribute("href");
  const secondHref = await links.nth(1).getAttribute("href");
  expect(firstHref).toContain("category=foundations");
  expect(secondHref).toContain("category=foundations");

  await links.first().click();
  const nav = page.getByRole("navigation", { name: "Question navigation", exact: true });
  await expect(nav).toBeVisible();
  await expect(nav.getByRole("button", { name: "Previous" })).toBeDisabled();
  await expect(nav.getByRole("link", { name: "Next" })).toHaveAttribute("href", secondHref!);
  await expect(nav).toContainText("Question 1 of");
  await nav.getByRole("link", { name: "Next" }).click();
  await expect(page).toHaveURL(new URL(secondHref!, page.url()).href);

  const nextNav = page.getByRole("navigation", { name: "Question navigation", exact: true });
  await expect(nextNav.getByRole("link", { name: "Previous" })).toHaveAttribute("href", firstHref!);
  await nextNav.getByRole("link", { name: "Previous" }).click();
  await expect(page).toHaveURL(new URL(firstHref!, page.url()).href);
});

test("single search match disables both buttons and restores filtered catalog", async ({ page }) => {
  await page.goto("/problems?q=Star%20Staircase&category=foundations&difficulty=Beginner");
  await expect(page.getByRole("heading", { name: "1 problem" })).toBeVisible();
  await page.locator(".problem-list li a").first().click();
  const nav = page.getByRole("navigation", { name: "Question navigation", exact: true });
  await expect(nav.getByRole("button", { name: "Previous" })).toBeDisabled();
  await expect(nav.getByRole("button", { name: "Next" })).toBeDisabled();
  await expect(nav).toContainText("Question 1 of 1");
  await page.getByRole("link", { name: "Problem Catalog" }).click();
  await expect(page).toHaveURL(/\/problems\?/);
  await expect(page.getByRole("heading", { name: "1 problem" })).toBeVisible();
});

test("question navigation stays accessible on mobile but not in contest flow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/problems/parity-check");
  const nav = page.getByRole("navigation", { name: "Question navigation", exact: true });
  await expect(nav).toBeVisible();
  await expect(nav.getByRole("link", { name: "Next" })).toBeVisible();
  await page.goto("/problems/parity-check?contest=example");
  await expect(page.getByRole("link", { name: "Back to contest" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Question navigation", exact: true })).toHaveCount(0);
});
