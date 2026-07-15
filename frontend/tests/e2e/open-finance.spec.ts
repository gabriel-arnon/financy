import { expect, test, type Page } from "@playwright/test";

const item = {
  id: "of-item-1",
  user_id: "owner-user",
  provider: "pluggy",
  external_item_id: "pluggy-item-1",
  connector_name: "Meu Pluggy",
  institution_name: "Banco Teste",
  status: "active",
  consent_expires_at: null,
  last_sync_at: "2026-07-15T12:00:00Z",
  last_successful_sync_at: "2026-07-15T12:00:00Z",
  last_error: null,
  metadata: {},
  created_at: "2026-07-15T11:00:00Z",
  updated_at: null
};

const run = {
  id: "run-1",
  user_id: "owner-user",
  provider: "pluggy",
  external_item_id: "pluggy-item-1",
  status: "success",
  started_at: "2026-07-15T12:00:00Z",
  finished_at: "2026-07-15T12:00:02Z",
  duration_ms: 2000,
  accounts_created: 1,
  accounts_updated: 0,
  cards_created: 0,
  cards_updated: 0,
  transactions_created: 3,
  transactions_updated: 1,
  transactions_ignored: 0,
  error_message: null,
  metadata: {
    accounts_found: 2,
    transactions_found: 4,
    item_execution_status: "SUCCESS",
    transactions_ignored_reasons: {},
    transaction_account_errors: []
  }
};

async function mockOpenFinanceApi(page: Page) {
  await page.route("**/open-finance/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ enabled: true, owner_only: true, configured: true, provider: "pluggy" })
    });
  });
  await page.route("**/open-finance/items", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...item, external_item_id: "new-item" }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([item]) });
  });
  await page.route("**/open-finance/sync-runs", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([run]) });
  });
  await page.route("**/open-finance/sync", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ run, items: [item] }) });
  });
  await page.route("**/open-finance/items/*/sync", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ run, items: [item] }) });
  });
}

test("open finance page renders owner operations", async ({ page }) => {
  await mockOpenFinanceApi(page);

  await page.goto("/open-finance");

  await expect(page.getByRole("heading", { name: "Open Finance" })).toBeVisible();
  await expect(page.getByText("Banco Teste")).toBeVisible();
  await expect(page.getByText("3 novas, 1 atualizadas, 0 ignoradas")).toBeVisible();
  await expect(page.getByText("Pluggy: 2 contas, 4 transacoes, execucao SUCCESS")).toBeVisible();
  await expect(page.getByRole("button", { name: "Conectar banco" })).toBeVisible();

  await page.getByRole("button", { name: "Sincronizar tudo" }).click();
  await expect(page.getByText("Sincronizacao Open Finance concluida.")).toBeVisible();

  await page.getByText("Adicionar item manualmente").click();
  await page.getByLabel("Item ID Pluggy").fill("new-item");
  await page.getByRole("button", { name: "Adicionar" }).click();
  await expect(page.getByText("Conexao Open Finance adicionada.")).toBeVisible();
});

test("open finance page handles disabled state", async ({ page }) => {
  await page.route("**/open-finance/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ enabled: false, owner_only: true, configured: false, provider: "pluggy" })
    });
  });

  await page.goto("/open-finance");

  await expect(page.getByRole("heading", { name: "Open Finance" })).toBeVisible();
  await expect(page.getByText("Feature desabilitada ou restrita ao owner.")).toBeVisible();
});
