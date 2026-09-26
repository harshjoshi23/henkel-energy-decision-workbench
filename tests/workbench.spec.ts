import { test, expect, Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
const work = (page: Page) => page.locator("main > div:not([hidden])");
async function run(page: Page, preset: string) {
  await work(page).getByRole("button", { name: preset, exact: true }).click();
  await work(page).getByRole("checkbox").check();
  const reply = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/calculate") && r.request().method() === "POST",
  );
  await work(page).getByRole("button", { name: "Calculate scenario" }).click();
  const response = await reply;
  expect(response.status()).toBe(200);
  return await response.json();
}
async function exported(page: Page, type: "JSON" | "Markdown") {
  const pending = page.waitForEvent("download");
  await work(page)
    .getByRole("button", { name: `Export ${type}` })
    .click();
  const file = await pending;
  return readFile((await file.path())!, "utf8");
}
for (const c of [
  {
    candidate: "C03",
    preset: "Base switch",
    value: "6.00",
    raw: "6",
    choice: "Alternative B",
  },
  {
    candidate: "C03",
    preset: "Higher power price",
    value: "-22.00",
    raw: "-22",
    choice: "Retain baseline A",
  },
  {
    candidate: "C03",
    preset: "Limited flexibility",
    value: "-1.50",
    raw: "-1.5",
    choice: "Retain baseline A",
  },
  {
    candidate: "C03",
    preset: "Infeasible switch",
    value: "Not admissible",
    raw: null,
    choice: "Retain baseline A",
  },
  {
    candidate: "C01",
    preset: "Residual improvement",
    value: "0.34",
    raw: "0.34",
    choice: "Alternative B",
  },
  {
    candidate: "C01",
    preset: "Cost exceeds benefit",
    value: "-0.11",
    raw: "-0.11",
    choice: "Retain baseline A",
  },
  {
    candidate: "C01",
    preset: "Break-even cost",
    value: "0.00",
    raw: "0",
    choice: "Retain baseline A",
  },
]) {
  test(`API / UI / JSON / Markdown parity: ${c.preset}`, async ({ page }) => {
    await page.goto("/");
    if (c.candidate === "C01")
      await page.getByRole("button", { name: "Residual dryer C01" }).click();
    const data = await run(page, c.preset);
    await expect(work(page).getByTestId("per-tonne")).toHaveText(c.value);
    await expect(work(page).getByTestId("choice")).toHaveText(c.choice);
    expect(data.snapshot.metrics.per_tonne).toBe(c.raw);
    expect(JSON.parse(await exported(page, "JSON"))).toEqual(data.snapshot);
    expect(await exported(page, "Markdown")).toBe(data.markdown);
    expect(data.markdown).toContain(data.snapshot.id);
    if (c.raw && c.raw.startsWith("-"))
      await expect(work(page).getByTestId("policy-value")).toHaveText("0.00");
  });
}
test("empty, input validation, stale result and reapproval", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    work(page).getByText("No result has been calculated"),
  ).toBeVisible();
  await expect(
    work(page).getByRole("button", { name: "Calculate scenario" }),
  ).toBeDisabled();
  await run(page, "Base switch");
  await work(page).getByLabel("Electricity price", { exact: true }).fill("120");
  await expect(work(page).getByRole("checkbox")).not.toBeChecked();
  await expect(
    work(page).getByText("Inputs changed — recalculate"),
  ).toBeVisible();
  await expect(
    work(page).getByRole("button", { name: "Export JSON" }),
  ).toBeDisabled();
  await work(page)
    .getByLabel("Matching product output", { exact: true })
    .fill("0");
  await work(page).getByRole("checkbox").check();
  await work(page).getByRole("button", { name: "Calculate scenario" }).click();
  expect(
    await work(page)
      .getByLabel("Matching product output", { exact: true })
      .evaluate((el: HTMLInputElement) => el.validity.valid),
  ).toBe(false);
  await work(page).getByRole("button", { name: "Clear inputs" }).click();
  await expect(
    work(page).getByRole("button", { name: "Export JSON" }),
  ).toBeDisabled();
});
test("API failure is visible and preserves inputs", async ({ page }) => {
  await page.goto("/");
  await page.route("**/api/calculate", (r) =>
    r.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ error: "Service unavailable" }),
    }),
  );
  await work(page)
    .getByRole("button", { name: "Base switch", exact: true })
    .click();
  await work(page).getByRole("checkbox").check();
  await work(page).getByRole("button", { name: "Calculate scenario" }).click();
  await expect(work(page).getByRole("alert")).toContainText(
    "Service unavailable",
  );
  await expect(
    work(page).getByLabel("Fuel price", { exact: true }),
  ).toHaveValue("40");
  await expect(
    work(page).getByText("No result has been calculated"),
  ).toBeVisible();
});
test("in-flight response cannot replace an edited revision", async ({
  page,
}) => {
  await page.goto("/");
  let release: () => void = () => {};
  const barrier = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/calculate", async (route) => {
    const result = await route.fetch();
    await barrier;
    await route.fulfill({ response: result });
  });
  await work(page)
    .getByRole("button", { name: "Base switch", exact: true })
    .click();
  await work(page).getByRole("checkbox").check();
  await work(page).getByRole("button", { name: "Calculate scenario" }).click();
  await expect(work(page).getByRole("status")).toContainText(
    "Validating inputs",
  );
  await work(page).getByLabel("Fuel price", { exact: true }).fill("70");
  release();
  await expect(
    work(page).getByText("No result has been calculated"),
  ).toBeVisible();
  await expect(work(page).getByRole("checkbox")).not.toBeChecked();
});
test("evidence, diagrams, live checks and mobile layout", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));
  await page.goto("/");
  await page.getByRole("button", { name: "Evidence & choices" }).click();
  await expect(page.locator("main")).toContainText("R64");
  const links = await page
    .locator('main a[href^="http"]')
    .evaluateAll((els) => els.map((e) => e.getAttribute("href")));
  expect(links.length).toBeGreaterThan(3);
  expect(links.every((x) => !x?.includes("oc.rizm"))).toBe(true);
  await page.getByRole("button", { name: "How it works" }).click();
  for (const image of await page.locator("main img").all())
    expect(
      await image.evaluate(
        (el: HTMLImageElement) => el.complete && el.naturalWidth > 0,
      ),
    ).toBe(true);
  await page
    .getByRole("button", { name: "Verification Execute actual checks" })
    .click();
  await expect(page.getByText("Not run in this view yet.")).toBeVisible();
  await page.getByRole("button", { name: "Run verification checks" }).click();
  await expect(
    page.getByText("adapter-c03-base", { exact: true }),
  ).toBeVisible();
  expect(
    await page.locator("main table tbody tr").count(),
  ).toBeGreaterThanOrEqual(44);
  await expect(page.locator("main table")).not.toContainText("failed");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Coupled utilities C03" }).click();
  await run(page, "Base switch");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "test-results/mobile.png", fullPage: true });
  expect(errors).toEqual([]);
});
test("negative prices and changed product denominator stay authoritative", async ({
  page,
}) => {
  await page.goto("/");
  await work(page)
    .getByRole("button", { name: "Base switch", exact: true })
    .click();
  await work(page)
    .getByLabel("Matching product output", { exact: true })
    .fill("40");
  await work(page).getByLabel("Electricity price", { exact: true }).fill("-10");
  await work(page).getByRole("checkbox").check();
  const reply = page.waitForResponse((r) => r.url().endsWith("/api/calculate"));
  await work(page).getByRole("button", { name: "Calculate scenario" }).click();
  const data = await (await reply).json();
  expect(data.snapshot.metrics.per_tonne).toBe("11.75");
  await expect(work(page).getByTestId("per-tonne")).toHaveText("11.75");
  expect(JSON.parse(await exported(page, "JSON"))).toEqual(data.snapshot);
});
