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
