import { expect, test, type Page } from "@playwright/test";

const categories = [
  { id: "cat-food", name: "Alimentacao", type: "expense", status: "active" },
  { id: "cat-subscriptions", name: "Assinaturas", type: "expense", status: "active" },
  { id: "cat-income", name: "Salario", type: "income", status: "active" }
];

const accounts = [
  {
    id: "acc-1",
    user_id: "dev-user",
    name: "Conta Corrente",
    institution: "Banco Teste",
    agency: null,
    account_number: null,
    type: "checking",
    balance: "1250.00",
    status: "active",
    created_at: "2026-06-01T00:00:00Z"
  }
];

const cards = [
  {
    id: "card-1",
    user_id: "dev-user",
    account_id: "acc-1",
    name: "Cartao Principal",
    institution: "Banco Teste",
    brand: "Visa",
    last_digits: "1234",
    limit_amount: "5000.00",
    closing_day: 25,
    due_day: 5,
    status: "active",
    created_at: "2026-06-01T00:00:00Z"
  }
];

function transaction(index: number) {
  return {
    id: `tx-${index}`,
    user_id: "dev-user",
    account_id: index % 2 === 0 ? "acc-1" : null,
    card_id: index % 2 === 0 ? null : "card-1",
    card_statement_id: index % 2 === 0 ? null : "statement-1",
    transaction_date: `2026-07-${String((index % 25) + 1).padStart(2, "0")}`,
    description: index === 1 ? "OPENAI ASSINATURA" : `TRANSACAO TESTE ${index}`,
    original_description: index === 1 ? "OPENAI ASSINATURA ORIGINAL" : `TRANSACAO TESTE ${index}`,
    normalized_description: index === 1 ? "openai assinatura" : `transacao teste ${index}`,
    amount: String(10 + index),
    type: index === 3 ? "income" : "expense",
    category_id: index === 2 ? null : index === 1 ? "cat-subscriptions" : index === 3 ? "cat-income" : "cat-food",
    source_file_id: null,
    installment_current: null,
    installment_total: null,
    status: index === 4 ? "pending" : "confirmed",
    created_at: `2026-07-${String((index % 25) + 1).padStart(2, "0")}T12:00:00Z`
  };
}

const transactions = Array.from({ length: 30 }, (_, index) => transaction(index + 1));

async function mockCoreApi(page: Page) {
  let attachments = [] as Array<{
    id: string;
    owner_user_id: string;
    transaction_id: string;
    file_id: string;
    status: string;
    created_at: string;
    deleted_at: string | null;
    file: {
      id: string;
      owner_user_id: string;
      original_filename: string;
      declared_mime_type: string;
      detected_mime_type: string;
      size_bytes: number;
      sha256_hash: string;
      source: string;
      status: string;
      scan_status: string;
      metadata: Record<string, unknown>;
      created_at: string;
      deleted_at: string | null;
    };
  }>;
  await page.route("**/transactions/*/attachments", async (route) => {
    if (route.request().method() === "POST") {
      const payload = route.request().postDataJSON() as { file_id: string };
      const attachment = {
        id: "attachment-1",
        owner_user_id: "dev-user",
        transaction_id: "tx-1",
        file_id: payload.file_id,
        status: "active",
        created_at: "2026-07-01T00:00:00Z",
        deleted_at: null,
        file: {
          id: payload.file_id,
          owner_user_id: "dev-user",
          original_filename: "comprovante.png",
          declared_mime_type: "image/png",
          detected_mime_type: "image/png",
          size_bytes: 1280,
          sha256_hash: "a".repeat(64),
          source: "transaction_attachment",
          status: "available",
          scan_status: "skipped",
          metadata: {},
          created_at: "2026-07-01T00:00:00Z",
          deleted_at: null
        }
      };
      attachments = [attachment];
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(attachment) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(attachments) });
  });
  await page.route("**/transactions/*/attachments/*", async (route) => {
    attachments = [];
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "deleted" }) });
  });
  await page.route("**/files/upload?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "file-1",
        owner_user_id: "dev-user",
        original_filename: "comprovante.png",
        declared_mime_type: "image/png",
        detected_mime_type: "image/png",
        size_bytes: 1280,
        sha256_hash: "a".repeat(64),
        source: "transaction_attachment",
        status: "available",
        scan_status: "skipped",
        metadata: {},
        created_at: "2026-07-01T00:00:00Z",
        deleted_at: null
      })
    });
  });
  await page.route("**/files/*/signed-url", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ file_id: "file-1", url: "https://example.test/comprovante.png", expires_at: "2026-07-01T00:05:00Z" })
    });
  });
  await page.route("**/transactions", async (route) => {
    if (route.request().resourceType() === "document") {
      await route.fallback();
      return;
    }
    if (route.request().method() === "DELETE") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "deleted" }) });
      return;
    }
    if (route.request().method() === "POST") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...transaction(99), id: "tx-created" }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(transactions) });
  });
  await page.route("**/transactions/**", async (route) => {
    if (route.request().url().includes("/attachments")) {
      await route.fallback();
      return;
    }
    if (route.request().resourceType() === "document") {
      await route.fallback();
      return;
    }
    if (route.request().method() === "DELETE") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "deleted" }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(transactions[0]) });
  });
  await page.route("**/categories", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(categories) });
  });
  await page.route("**/accounts", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(accounts) });
  });
  await page.route("**/cards", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(cards) });
  });
  await page.route("**/classification-rules", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });
}

async function gotoTransactions(page: Page, path = "/transactions") {
  await mockCoreApi(page);
  await page.goto(path);
  await page.waitForLoadState("networkidle");
}

test("opens the transaction drawer from a table row and from the edit action", async ({ page }) => {
  await gotoTransactions(page);

  await page.locator("tbody tr").first().click();
  const drawer = page.locator("aside");
  await expect(page.getByRole("heading", { name: "Detalhes do lançamento" })).toBeVisible();
  await expect(drawer.getByLabel("Descrição")).toBeVisible();
  await expect(drawer.getByLabel("Categoria")).toBeVisible();
  await expect(drawer.getByLabel("Data")).toBeVisible();
  await expect(drawer.getByLabel("Tipo")).toBeVisible();
  await expect(drawer.getByLabel("Origem")).toBeVisible();
  await expect(drawer.getByLabel("Valor")).toBeVisible();
  await expect(drawer.getByLabel("Pendente")).toBeVisible();

  await drawer.getByRole("button", { name: "Fechar" }).first().click();
  await page.getByRole("button", { name: "Editar transação" }).first().click();
  await expect(page.getByRole("heading", { name: "Detalhes do lançamento" })).toBeVisible();
});

test("allows editing supported drawer fields", async ({ page }) => {
  await gotoTransactions(page);

  await page.locator("tbody tr").first().click();
  const drawer = page.locator("aside");
  await drawer.getByLabel("Descrição").fill("DESCRICAO TESTE E2E");
  await expect(drawer.getByLabel("Descrição")).toHaveValue("DESCRICAO TESTE E2E");
  await expect(drawer.getByLabel("Categoria")).toBeEnabled();
  await expect(drawer.getByLabel("Data")).toBeEnabled();
  await expect(drawer.getByLabel("Tipo")).toBeEnabled();
  await expect(drawer.getByLabel("Origem")).toBeEnabled();
  await expect(drawer.getByLabel("Valor")).toBeEnabled();
  await expect(drawer.getByLabel("Pendente")).toBeEnabled();
});

test("asks for visual confirmation before deleting from the row and drawer", async ({ page }) => {
  await gotoTransactions(page);

  await page.locator("tbody tr").first().getByRole("button", { name: "Excluir transação" }).click();
  await expect(page.getByRole("heading", { name: "Excluir transação" })).toBeVisible();
  await expect(page.getByText("Esta ação não pode ser desfeita.")).toBeVisible();
  await page.getByRole("button", { name: "Cancelar" }).click();

  await page.locator("tbody tr").first().click();
  await page.locator("aside").getByRole("button", { name: "Excluir transação" }).click();
  await expect(page.getByRole("heading", { name: "Excluir transação" })).toBeVisible();
  await page.getByRole("button", { name: "Cancelar" }).click();
});

test("loads transactions in batches of 25 and keeps summaries on all filtered rows", async ({ page }) => {
  await gotoTransactions(page);

  const summaryTotal = Number(await page.getByText("Total transações").locator("xpath=..").locator("p").nth(1).innerText());
  const initialRows = await page.locator("tbody tr").count();
  expect(initialRows).toBe(Math.min(25, summaryTotal));

  await expect(page.getByRole("button", { name: "Carregar mais" })).toBeVisible();
  await page.getByRole("button", { name: "Carregar mais" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(30);

  await page.getByPlaceholder("Buscar descrição").fill("zzzz-sem-resultado-e2e");
  await expect(page.getByText("Nenhuma transação encontrada.")).toBeVisible();
});

test("sorts by date, description and amount without changing the filtered total", async ({ page }) => {
  await gotoTransactions(page);

  const summaryTotal = await page.getByText("Total transações").locator("xpath=..").locator("p").nth(1).innerText();

  await page.getByRole("button", { name: "Data" }).click();
  await page.getByRole("button", { name: "Descrição" }).click();
  await page.getByRole("button", { name: "Valor" }).click();

  await expect(page.getByText("Total transações").locator("xpath=..").locator("p").nth(1)).toHaveText(summaryTotal);
  await expect(page.locator("tbody tr").first()).toBeVisible();
});

test("supports selecting visible transactions for batch actions", async ({ page }) => {
  await gotoTransactions(page);

  await expect(page.getByText(/transações selecionadas/)).toBeHidden();
  await page.locator("tbody input[type='checkbox']").first().check();
  await expect(page.getByText("1 transações selecionadas")).toBeVisible();
  await expect(page.getByRole("button", { name: "Alterar categoria" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Criar regras" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Excluir selecionadas" })).toBeEnabled();

  await page.getByRole("button", { name: "Excluir selecionadas" }).click();
  await expect(page.getByRole("heading", { name: "Excluir transações selecionadas" })).toBeVisible();
  await page.getByRole("button", { name: "Cancelar" }).click();

  await page.getByRole("button", { name: "Limpar seleção" }).click();
  await expect(page.getByText(/transações selecionadas/)).toBeHidden();
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
  await expect(drawer.getByLabel("Origem")).toBeVisible();
  await expect(drawer.getByLabel("Valor")).toBeVisible();
  await expect(drawer.getByLabel("Pendente")).toBeVisible();

  await drawer.getByLabel("Descrição").fill("");
  await drawer.getByLabel("Valor").fill("");
  await page.getByRole("button", { name: "Criar transação" }).click();
  await expect(page.getByText("Informe data, descrição e valor para criar a transação.")).toBeVisible();
});

test("supports transaction attachment upload open and removal", async ({ page }) => {
  await gotoTransactions(page);

  await page.locator("tbody tr").first().click();
  const drawer = page.locator("aside");
  await expect(drawer.getByText("Nenhum comprovante anexado.")).toBeVisible();

  await drawer.locator("input[type='file']").setInputFiles({
    name: "comprovante.png",
    mimeType: "image/png",
    buffer: Buffer.from([0x89, 0x50, 0x4e, 0x47])
  });

  await expect(drawer.getByText("comprovante.png")).toBeVisible();
  const popupPromise = page.waitForEvent("popup");
  const signedUrlRequest = page.waitForRequest(/\/files\/file-1\/signed-url/);
  await drawer.getByRole("button", { name: "Abrir comprovante" }).click();
  await signedUrlRequest;
  const popup = await popupPromise;
  await popup.close();

  await drawer.getByRole("button", { name: "Remover comprovante" }).click();
  await expect(drawer.getByText("Nenhum comprovante anexado.")).toBeVisible();
});

test("opens manual transaction drawer from create query params", async ({ page }) => {
  await gotoTransactions(page, "/transactions?create=income");

  const drawer = page.locator("aside");
  await expect(page.getByRole("heading", { name: "Criar lançamento manual" })).toBeVisible();
  await expect(drawer.getByLabel("Tipo")).toHaveValue("income");

  await drawer.getByLabel("Fechar", { exact: true }).click();
  await gotoTransactions(page, "/transactions?create=expense");
  await expect(page.getByRole("heading", { name: "Criar lançamento manual" })).toBeVisible();
  await expect(page.locator("aside").getByLabel("Tipo")).toHaveValue("expense");
});

test("supports keyboard access and escape close for the transaction drawer", async ({ page }) => {
  await gotoTransactions(page);

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

test("hydrates filters from transaction query params", async ({ page }) => {
  await gotoTransactions(page, "/transactions?q=openai&type=expense&category_id=cat-subscriptions&start_date=2026-07-01&end_date=2026-07-31");

  await expect(page.getByPlaceholder("Buscar descrição")).toHaveValue("openai");
  await expect(page.getByLabel("Tipo")).toHaveValue("expense");
  await expect(page.getByLabel("Categoria")).toHaveValue("cat-subscriptions");
  await expect(page.getByLabel("Data inicial")).toHaveValue("2026-07-01");
  await expect(page.getByLabel("Data final")).toHaveValue("2026-07-31");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(page.locator("tbody tr").first()).toContainText("OPENAI ASSINATURA");
});

test("keeps filters empty when transactions route has no query params", async ({ page }) => {
  await gotoTransactions(page);

  await expect(page.getByPlaceholder("Buscar descrição")).toHaveValue("");
  await expect(page.getByLabel("Tipo")).toHaveValue("all");
  await expect(page.getByLabel("Categoria")).toHaveValue("all");
  await expect(page.getByLabel("Data inicial")).toHaveValue("");
  await expect(page.getByLabel("Data final")).toHaveValue("");
});
