import { expect, test } from "@playwright/test";

test("Minimal Glass dashboard preserves desktop reference geometry", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto("/dashboard");
  const header = page.locator(".studio-header");
  const sidebar = page.locator(".sidebar");
  const dashboard = page.locator(".studio-dashboard");
  const mainColumn = page.locator(".studio-main-col");
  const rightColumn = page.locator(".studio-right-col");
  await expect(page.getByRole("heading", { name: "Continue your learning journey" })).toBeVisible();
  await expect(header).toBeVisible();
  await expect(sidebar).toBeVisible();
  await expect(page.locator(".studio-stat")).toHaveCount(4);
  await expect(page.locator(".studio-path")).toHaveCount(4);
  const [h, s, d, m, r] = await Promise.all(
    [header, sidebar, dashboard, mainColumn, rightColumn].map(locator => locator.boundingBox())
  );
  expect(h && s && d && m && r).toBeTruthy();
  if (!h || !s || !d || !m || !r) return;
  expect(h.y).toBe(0);
  expect(h.height).toBeGreaterThanOrEqual(60);
  expect(s.x).toBe(0);
  expect(s.width).toBeGreaterThanOrEqual(215);
  expect(d.x).toBeGreaterThanOrEqual(s.width);
  expect(r.x).toBeGreaterThan(m.x + m.width);
  expect(m.width).toBeGreaterThan(r.width);
  expect(Math.abs(m.y - r.y)).toBeLessThan(3);
});

test("Minimal Glass dashboard keeps an accessible mobile navigation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Continue your learning journey" })).toBeVisible();
  const toggle = page.getByRole("button", { name: "Toggle navigation" });
  await expect(toggle).toBeVisible();
  await toggle.click();
  const nav = page.getByRole("navigation", { name: "Main navigation" });
  await expect(nav).toBeVisible();
  await expect(nav.getByRole("link", { name: "Practice", exact: true })).toBeVisible();
  await nav.getByRole("link", { name: "Practice", exact: true }).click();
  await expect(page).toHaveURL(/\/problems$/);
});


test("primary destinations appear only in glass top navigation on desktop", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await page.goto("/dashboard");
  const header = page.locator(".studio-header");
  const sidebar = page.locator(".sidebar");
  for (const name of ["Dashboard", "Practice", "Learn", "Assessments", "Career Paths", "Community"]) {
    await expect(header.getByRole("link", { name, exact: true })).toHaveCount(1);
    await expect(sidebar.getByRole("link", { name, exact: true })).toHaveCount(0);
  }
  await expect(sidebar.getByRole("link", { name: "Progress insights" })).toBeVisible();
  await expect(sidebar.getByRole("link", { name: "Foundations" })).toBeVisible();
  // A transparent layered surface, border and highlight are the stable glass
  // fallback. Some CI Chromium builds disable backdrop-filter rendering.
  await expect(header).toHaveCSS("background-image", /linear-gradient/);
  await expect(header).toHaveCSS("box-shadow", /rgba/);
  const style = await header.evaluate(element => {
    const computed = getComputedStyle(element);
    return { backdrop: computed.backdropFilter, border: computed.borderBottomColor };
  });
  expect(style.border).not.toBe("rgba(0, 0, 0, 0)");
  // The authored backdrop blur remains enabled where browsers support it.
  expect(style.backdrop === "none" || style.backdrop.includes("blur")).toBe(true);
});


test("auth page has a focused glass layout without the workspace shell", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/auth");
  await expect(page.locator(".auth-experience")).toBeVisible();
  await expect(page.locator(".studio-header")).toHaveCount(0);
  await expect(page.locator(".sidebar")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: /One challenge at a time/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Welcome back." })).toBeVisible();
  await expect(page.locator(".auth-showcase")).toBeVisible();
  const story = await page.locator(".auth-story").boundingBox();
  const card = await page.locator(".auth-access-card").boundingBox();
  expect(story && card).toBeTruthy();
  if (story && card) expect(card.x).toBeGreaterThan(story.x + story.width);

  const password = page.getByLabel("Password", { exact: true });
  await expect(password).toHaveAttribute("type", "password");
  await page.getByRole("button", { name: "Show password" }).click();
  await expect(password).toHaveAttribute("type", "text");
  await page.getByRole("button", { name: "Hide password" }).click();
  await expect(password).toHaveAttribute("type", "password");

  await page.getByRole("tab", { name: "Create account" }).click();
  await expect(page.getByLabel("Display name")).toBeVisible();
  await expect(page.getByLabel("Username", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Start your journey." })).toBeVisible();
  await page.getByRole("tab", { name: "Sign in" }).click();
  await expect(page.getByLabel("Email or username")).toBeVisible();
  await expect(page.getByLabel("Display name")).toHaveCount(0);
});

test("auth page keeps form readable and operable at mobile width", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/auth");
  await expect(page.getByRole("heading", { name: "Welcome back." })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in to workspace" })).toBeVisible();
  await expect(page.locator(".auth-showcase")).toBeHidden();
  const viewport = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(viewport).toBeLessThanOrEqual(390);
  await page.getByRole("tab", { name: "Create account" }).click();
  await expect(page.getByRole("button", { name: "Create account" })).toBeVisible();
});
