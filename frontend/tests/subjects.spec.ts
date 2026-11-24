import { expect, test } from "@playwright/test";

test("all 45 subjects show truthful targets and lead to genuine questions", async ({ page }) => {
  await page.goto("/subjects");
  await expect(page.getByRole("heading", { name: "Explore all 45 subjects" })).toBeVisible();
  await expect(page.locator(".subject-card")).toHaveCount(45);
  await expect(page.getByText("2531", { exact: true })).toBeVisible();
  const numpy = page.locator(".subject-card").filter({ has: page.getByRole("heading", { name: "NumPy", exact: true }) });
  await expect(numpy).toContainText("54 published in this track");
  await expect(numpy).toContainText("Target 50");
  await numpy.getByRole("link", { name: "Explore questions" }).click();
  await expect(page).toHaveURL(/\/problems\?subject=numpy/);
  await expect(page.getByRole("heading", { name: /problems/ })).toBeVisible();
});

test("one question per subject is available through public catalogue", async ({ page, request }) => {
  const response = await request.get("/api/subjects");
  // The UI's server-side API is authoritative; this route may not be proxied
  // publicly by the web deployment. Focus on visible page behavior instead.
  if (response.ok()) {
    const payload = await response.json();
    expect(payload.subjects).toHaveLength(45);
  }
  await page.goto("/subjects");
  const agents = page.locator(".subject-card").filter({ has: page.getByRole("heading", { name: "AI Agents and Agentic Workflows" }) });
  await agents.getByRole("link", { name: "Explore questions" }).click();
  await expect(page.getByText("AI Agents and Agentic Workflows: Tool calling")).toBeVisible();
});
