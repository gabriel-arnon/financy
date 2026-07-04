import { expect, test, type Page } from "@playwright/test";

async function gotoTransactions(page: Page) {
  await page.goto("/transactions");
  await page.waitForLoadState("networkidle");
}

async function hasTransactions(page: Page) {
  return !(await page.getByText("Nenhuma transação encontrada.").isVisible().catch(() => false));
}

test("opens the transaction drawer from a table row and from the edit action", async ({ page }) => {
  await gotoTransactions(page);
  test.skip(!(await hasTransactions(page)), "transactions data is not available in this environment");

  await page.locator("tbody tr").first().click();
  const drawer = page.locator("aside");
  await expect(page.getByRole("heading", { name: "Detalhes do lançamento" })).toBeVisible();
  await expect(drawer.getByLabel("Descrição")).toBeVisible();
  await expect(drawer.getByLabel("Categoria")).toBeVisible();
  await expect(drawer.getByLabel("Data")).toBeVisible();
  await expect(drawer.getByLabel("Tipo")).toBeVisible();
  await expect(drawer.getByLabel("Conta")).toBeVisible();
  await expect(drawer.getByLabel("Cartão")).toBeVisible();
  await expect(drawer.getByLabel("Valor")).toBeVisible();
  await expect(drawer.getByLabel("Status")).toBeVisible();

  await drawer.getByRole("button", { name: "Fechar" }).first().click();
  await page.getByRole("button", { name: "Editar transação" }).first().click();
  await expect(page.getByRole("heading", { name: "Detalhes do lançamento" })).toBeVisible();
});

test("allows editing supported drawer fields only", async ({ page }) => {
  await gotoTransactions(page);
  test.skip(!(await hasTransactions(page)), "transactions data is not available in this environment");

  await page.locator("tbody tr").first().click();
  const drawer = page.locator("aside");
  const description = drawer.getByLabel("Descrição");
  await description.fill("DESCRIÇÃO TESTE E2E");
  await expect(description).toHaveValue("DESCRIÇÃO TESTE E2E");
  await expect(drawer.getByLabel("Categoria")).toBeEnabled();

  for (const label of ["Data", "Tipo", "Conta", "Cartão", "Valor", "Status"]) {
    await expect(drawer.getByLabel(label)).toHaveAttribute("readonly", "");
  }
});

test("asks for visual confirmation before deleting from the row and drawer", async ({ page }) => {
  await gotoTransactions(page);
  test.skip(!(await hasTransactions(page)), "transactions data is not available in this environment");

  await page.getByRole("button", { name: "Excluir transação" }).first().click();
  await expect(page.getByRole("heading", { name: "Excluir transação" })).toBeVisible();
  await expect(page.getByText("Esta ação não pode ser desfeita.")).toBeVisible();
  await page.getByRole("button", { name: "Cancelar" }).click();

  await page.locator("tbody tr").first().click();
  await page.getByRole("button", { name: "Excluir transação" }).last().click();
  await expect(page.getByRole("heading", { name: "Excluir transação" })).toBeVisible();
  await page.getByRole("button", { name: "Cancelar" }).click();
});

test("loads transactions in batches of 25 and keeps summaries on all filtered rows", async ({ page }) => {
  await gotoTransactions(page);
  test.skip(!(await hasTransactions(page)), "transactions data is not available in this environment");

  const summaryTotal = Number(await page.getByText("Total transações").locator("xpath=..").locator("p").nth(1).innerText());
  const initialRows = await page.locator("tbody tr").count();
  expect(initialRows).toBe(Math.min(25, summaryTotal));

  const loadMore = page.getByRole("button", { name: "Carregar mais" });
  if (summaryTotal > 25) {
    await expect(loadMore).toBeVisible();
    await loadMore.click();
    await expect(page.locator("tbody tr")).toHaveCount(Math.min(50, summaryTotal));
  } else {
    await expect(page.getByText("Todas as transações foram carregadas.")).toBeVisible();
  }

  await page.getByPlaceholder("Buscar descrição").fill("zzzz-sem-resultado-e2e");
  await expect(page.getByText("Nenhuma transação encontrada.")).toBeVisible();
});

test("sorts by date, description and amount without changing the filtered total", async ({ page }) => {
  await gotoTransactions(page);
  test.skip(!(await hasTransactions(page)), "transactions data is not available in this environment");

  const summaryTotal = await page.getByText("Total transações").locator("xpath=..").locator("p").nth(1).innerText();

  await page.getByRole("button", { name: "Data" }).click();
  await page.getByRole("button", { name: "Descrição" }).click();
  await page.getByRole("button", { name: "Valor" }).click();

  await expect(page.getByText("Total transações").locator("xpath=..").locator("p").nth(1)).toHaveText(summaryTotal);
  await expect(page.locator("tbody tr").first()).toBeVisible();
});

test("supports selecting visible transactions for batch actions", async ({ page }) => {
  await gotoTransactions(page);
  test.skip(!(await hasTransactions(page)), "transactions data is not available in this environment");

  await expect(page.getByText("0 transações selecionadas")).toBeVisible();
  await page.locator("tbody input[type='checkbox']").first().check();
  await expect(page.getByText("1 transações selecionadas")).toBeVisible();
  await expect(page.getByRole("button", { name: "Alterar categoria" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Criar regras" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Excluir selecionadas" })).toBeEnabled();

  await page.getByRole("button", { name: "Excluir selecionadas" }).click();
  await expect(page.getByRole("heading", { name: "Excluir transações selecionadas" })).toBeVisible();
  await page.getByRole("button", { name: "Cancelar" }).click();

  await page.getByRole("button", { name: "Limpar seleção" }).click();
  await expect(page.getByText("0 transações selecionadas")).toBeVisible();
});

test("shows uncategorized shortcut and applies the category filter", async ({ page }) => {
  await gotoTransactions(page);

  await expect(page.getByRole("button", { name: /Transações sem categoria/ })).toBeVisible();
  await page.getByRole("button", { name: /Transações sem categoria/ }).click();
  await expect(page.getByLabel("Categoria")).toHaveValue("__none__");
});

test("opens manual transaction drawer and validates required fields", async ({ page }) => {
  await gotoTransactions(page);

  await page.getByRole("button", { name: "Nova transação" }).click();
  const drawer = page.locator("aside");
  await expect(page.getByRole("heading", { name: "Criar lançamento manual" })).toBeVisible();
  await expect(drawer.getByLabel("Data")).toBeVisible();
  await expect(drawer.getByLabel("Descrição")).toBeVisible();
  await expect(drawer.getByLabel("Tipo")).toBeVisible();
  await expect(drawer.getByLabel("Categoria")).toBeVisible();
  await expect(drawer.getByLabel("Conta")).toBeVisible();
  await expect(drawer.getByLabel("Cartão")).toBeVisible();
  await expect(drawer.getByLabel("Valor")).toBeVisible();
  await expect(drawer.getByLabel("Status")).toBeVisible();

  await drawer.getByLabel("Descrição").fill("");
  await drawer.getByLabel("Valor").fill("");
  await page.getByRole("button", { name: "Criar transação" }).click();
  await expect(page.getByText("Informe data, descrição e valor para criar a transação.")).toBeVisible();
});

test("supports keyboard access and escape close for the transaction drawer", async ({ page }) => {
  await gotoTransactions(page);
  test.skip(!(await hasTransactions(page)), "transactions data is not available in this environment");

  const firstRow = page.locator("tbody tr").first();
  await firstRow.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Detalhes do lançamento" })).toBeVisible();
  await expect(page.locator("aside").getByLabel("Descrição")).toBeFocused();

  await page.keyboard.press("Escape");
  await expect(page.getByRole("heading", { name: "Detalhes do lançamento" })).toBeHidden();
});

test("keeps the transaction drawer full width on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await gotoTransactions(page);

  await page.getByRole("button", { name: "Nova transação" }).click();
  const drawerBox = await page.getByRole("dialog", { name: "Criar lançamento manual" }).boundingBox();
  expect(drawerBox?.width).toBe(390);
});
