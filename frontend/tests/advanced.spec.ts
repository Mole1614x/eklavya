import { expect, test } from "@playwright/test";

const identity = process.env.UAT_ADMIN_IDENTITY ?? "uat_admin@example.com";
const password = process.env.UAT_ADMIN_PASSWORD ?? "UatAdminPass123!";

test("Phase 17 assessment, Data Lab, expression, and multi-tool journeys", async ({ page }) => {
  await page.goto("/auth");
  await page.getByLabel("Email or username").fill(identity);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin$/);

  const me = await (await page.request.get("/api/auth/me")).json();
  const suffix = Date.now().toString(36);
  const created = await page.request.post("/api/advanced/admin/assessments", { data: {
    title: `Phase 17 Journey ${suffix}`, description: "Browser-verified timed assessment", instructions: "Answer before expiry.",
    assessment_type: "MIXED", duration_minutes: 15,
    opens_at: new Date(Date.now() - 60_000).toISOString(), closes_at: new Date(Date.now() + 3_600_000).toISOString(),
    max_attempts: 1, penalty_percent: 0, release_results: true, status: "PUBLISHED", access_scope: "ALL",
    questions: [{ problem_slug: "parity-check", points: 100 }], assigned_user_ids: [], assigned_group_ids: [],
  } });
  expect(created.status()).toBe(201);

  await page.goto("/assessments");
  await page
    .getByRole("article")
    .filter({ hasText: `Phase 17 Journey ${suffix}` })
    .getByRole("button", { name: "Start or resume" })
    .click();
  await page.getByLabel("Your assessment answer").fill("Odd");
  await page.getByRole("button", { name: "Save answer" }).click();
  await expect(page.getByRole("status").last()).toContainText("Answer saved");
  await page.getByRole("button", { name: "Submit assessment" }).click();
  await expect(page.getByText("100 / 100")).toBeVisible();

  await page.goto("/data-cleaning-lab");
  const datasetTitle = `Scores ${suffix}`;
  await page.getByLabel("Dataset title").fill(datasetTitle);
  await page.getByLabel("CSV, XLSX, JSON, or Parquet").setInputFiles({
    name: "scores.csv", mimeType: "text/csv", buffer: Buffer.from("name,score\nAnu,10\nAnu,10\nDev,12\n"),
  });
  await page.getByRole("button", { name: "Upload and profile" }).click();
  await expect(page.getByRole("status")).toContainText("Dataset uploaded");
  await expect(page.getByText(datasetTitle, { exact: true }).last()).toBeVisible();

  await page.goto("/excel-practice");
  await page.getByRole("button", { name: "Validate and submit" }).click();
  await expect(page.getByText("Accepted", { exact: true })).toBeVisible();

  await page.goto("/tableau-practice");
  await page.getByRole("button", { name: "Validate and submit" }).click();
  await expect(page.getByText("Accepted", { exact: true })).toBeVisible();

  await page.goto("/multi-tool-challenges");
  await expect(page.getByRole("button", { name: "Submit approach" })).toBeEnabled();
  await page.getByRole("button", { name: "Submit approach" }).click();
  await expect(page.getByRole("status")).toContainText("passed");

  await page.goto("/linux-practice");
  await expect(page.getByRole("heading", { name: "Disposable Linux sandbox" })).toBeVisible();
});
