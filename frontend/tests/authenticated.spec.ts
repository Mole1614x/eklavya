import { expect, test } from "@playwright/test";

test("authenticated session rotates across BFF routes and protects profile data", async ({ page, context }) => {
  const suffix = Date.now().toString(36);
  const displayName = `Integration Archer ${suffix}`;

  await page.goto("/auth");
  await page.getByRole("tab", { name: "Create account" }).click();
  await page.getByLabel("Display name").fill(displayName);
  await page.getByLabel("Username").fill(`archer_${suffix}`);
  await page.getByLabel("Email").fill(`archer_${suffix}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("StrongPass123");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  const accountMenuButton = page.getByRole("button", { name: "Account menu" });
  await expect(accountMenuButton).toBeVisible();
  await accountMenuButton.click();
  const accountOptions = page.getByRole("navigation", { name: "Account options" });
  await expect(accountMenuButton).toHaveAttribute("aria-expanded", "true");
  await expect(accountOptions.getByRole("link", { name: "My Profile" })).toBeVisible();
  await expect(accountOptions.getByRole("button", { name: "Log out" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(accountMenuButton).toHaveAttribute("aria-expanded", "false");
  await expect(accountOptions).toHaveCount(0);
  await accountMenuButton.click();
  await accountOptions.getByRole("link", { name: "My Profile" }).click();
  await expect(page).toHaveURL(/\/profile$/);
  await expect(page.getByRole("heading", { name: displayName })).toBeVisible();
  await expect(page.locator('[data-profile-design="studio-glass-v2"]')).toBeVisible();
  await expect(page.locator(".lp-hero")).toBeVisible();
  await expect(page.locator(".lp-stat")).toHaveCount(4);
  await expect(page.getByRole("heading", { name: "Submission activity" })).toBeVisible();
  await expect(page.locator(".lp-heatmap .lp-day")).toHaveCount(371);
  const profileGrid = page.locator(".lp-profile-layout");
  await expect(profileGrid).toHaveCSS("display", "grid");
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".lp-hero")).toBeVisible();
  await expect(page.locator(".lp-activity")).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 900 });

  const csrfAttempt = await page.request.patch("/api/auth/me", {
    headers: { Origin: "https://attacker.example", "Sec-Fetch-Site": "cross-site" },
    data: { bio: "cross-site mutation" },
  });
  expect(csrfAttempt.status()).toBe(403);
  expect(await csrfAttempt.json()).toEqual({ detail: "Cross-site request rejected" });

  // Simulate access-token expiry while retaining the HttpOnly refresh session.
  await context.clearCookies({ name: "eklavya_access" });
  const submission = await page.request.post("/api/submissions/problem/parity-check", {
    data: { language: "python", source_code: "n = int(input())\nprint('Even' if n % 2 == 0 else 'Odd')", mode: "SUBMIT" },
  });
  expect(submission.status()).toBe(202);
  const created = await submission.json();
  expect(created).not.toHaveProperty("source_code");
  expect(["QUEUED", "SYSTEM_ERROR"]).toContain(created.status);
  expect((await context.cookies()).some((cookie) => cookie.name === "eklavya_access")).toBe(true);

  await page.reload();
  await expect(page.getByRole("heading", { name: displayName })).toBeVisible();
  await page.getByRole("button", { name: "Edit profile" }).click();
  await page.getByLabel("Bio").fill("Verified integration journey");
  await page.getByRole("button", { name: "Save profile" }).click();
  await expect(page.getByRole("status")).toContainText("Profile saved.");

  await page.goto("/admin");
  const restricted = page.getByRole("heading", { name: "Administration unavailable" }).locator("..");
  await expect(restricted).toBeVisible();
  await expect(restricted).toContainText("restricted to administrators");
  await page.goto("/profile");

  await accountMenuButton.click();
  await expect(accountOptions.getByRole("button", { name: "Log out" })).toBeVisible();
  await accountOptions.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/auth$/);
  await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();
  await page.goto("/profile");
  await expect(page).toHaveURL(/\/auth$/);
});
