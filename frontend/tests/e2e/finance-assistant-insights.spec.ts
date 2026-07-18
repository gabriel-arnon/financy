import { expect, test, type Page } from "@playwright/test";

const initialCategories = [
  { id: "cat-subscriptions", name: "Assinaturas", type: "expense", status: "active" },
  { id: "cat-food", name: "Alimentacao", type: "expense", status: "active" }
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
    created_at: "2026-07-01T00:00:00Z"
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
    created_at: "2026-07-01T00:00:00Z"
  }
];

const transactions = [
  {
    id: "tx-openai",
    user_id: "dev-user",
    account_id: null,
    card_id: "card-1",
    card_statement_id: "statement-1",
    transaction_date: "2026-07-05",
    description: "OPENAI ASSINATURA",
    original_description: "OPENAI ASSINATURA",
    normalized_description: "openai assinatura",
    amount: "100.00",
    type: "expense",
    category_id: "cat-subscriptions",
    source_file_id: null,
    installment_current: null,
    installment_total: null,
    status: "confirmed",
    external_source: "open_finance",
    created_at: "2026-07-05T12:00:00Z"
  },
  {
    id: "tx-rename",
    user_id: "dev-user",
    account_id: "acc-1",
    card_id: null,
    card_statement_id: null,
    transaction_date: "2026-07-06",
    description: "MERCADO***TESTE",
    original_description: "MERCADO***TESTE",
    normalized_description: "mercado teste",
    amount: "42.00",
    type: "expense",
    category_id: "cat-food",
    source_file_id: null,
    installment_current: null,
    installment_total: null,
    status: "confirmed",
    external_source: null,
    created_at: "2026-07-06T12:00:00Z"
  }
];

function overview(ruleCreated: boolean) {
  return {
    summary: "Resumo legado mantido pela API.",
    insights: [
      { title: "Resultado do periodo", description: "Seu resultado esta em -142.00.", severity: "warning" }
    ],
    suggested_rules: ruleCreated
      ? []
      : [
          {
            keyword: "OPENAI",
            category_id: "cat-subscriptions",
            category_name: "Assinaturas",
            transaction_type: "expense",
            match_count: 3,
            reason: "Transacoes parecidas usam esta categoria."
          }
        ],
    suggested_categories: [
      {
        name: "Moradia",
        type: "expense",
        match_count: 4,
        sample_descriptions: ["ALUGUEL JULHO", "ALUGUEL AGOSTO"],
        reason: "Transacoes recorrentes ficaram em categoria generica."
      }
    ],
    category_suggestions: [],
    recurrence_suggestions: [],
    rename_suggestions: [
      {
        transaction_id: "tx-rename",
        current_description: "MERCADO***TESTE",
        suggested_description: "Mercado Teste",
        reason: "Descricao contem ruido."
      }
    ]
  };
}

async function mockFinanceApi(page: Page) {
  let ruleCreated = false;
  let categories = [...initialCategories];

  await page.route("**/transactions", async (route) => {
    if (route.request().resourceType() === "document") {
      await route.fallback();
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(transactions) });
  });
  await page.route("**/categories", async (route) => {
    if (route.request().method() === "POST") {
      const payload = JSON.parse(route.request().postData() ?? "{}");
      const category = {
        id: "cat-housing",
        name: payload.name,
        type: payload.type,
        status: payload.status,
        is_system: false
      };
      categories = [...categories.filter((item) => item.id !== category.id), category];
      await route.fulfill({
        status: 201,
        headers: { "X-Financy-Category-Action": "created" },
        contentType: "application/json",
        body: JSON.stringify(category)
      });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(categories) });
  });
  await page.route("**/accounts", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(accounts) });
  });
  await page.route("**/cards", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(cards) });
  });
  await page.route("**/classification-rules", async (route) => {
    if (route.request().method() === "POST") {
      ruleCreated = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "rule-openai",
          user_id: "dev-user",
          keyword: "OPENAI",
          category_id: "cat-subscriptions",
          transaction_type: "expense",
          priority: 100,
          status: "active",
          match_scope: "both",
          auto_created: false,
          created_at: "2026-07-01T00:00:00Z"
        })
      });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });
  await page.route("**/ai-finance/overview", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(overview(ruleCreated)) });
  });
  await page.route("**/ai-finance/ask", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        answer: "Encontrei 1 transacao neste mes, no valor total de R$ 100,00.",
        message: "Encontrei 1 transacao neste mes, no valor total de R$ 100,00.",
        kind: "transactions_summary",
        matched_count: 1,
        total_amount: "100.00",
        filters: ["saidas", "categoria Assinaturas", "neste mes"],
        summary: { matched_count: 1, total_amount: "100.00", currency: "BRL", period_label: "neste mes" },
        cta: {
          label: "Ver transações",
          route: "/transactions",
          query: {
            q: "openai",
            type: "expense",
            category_id: "cat-subscriptions",
            start_date: "2026-07-01",
            end_date: "2026-07-31"
          }
        }
      })
    });
  });
}

test("insights suggested rule opens prefilled dialog and removes suggestion after save", async ({ page }) => {
  await mockFinanceApi(page);
  await page.goto("/");
  await page.waitForLoadState("networkidle");

  await page.getByRole("button", { name: "Adicionar regra" }).click();
  const ruleDialog = page.getByRole("dialog", { name: "Revisar e adicionar regra" });
  await expect(ruleDialog.getByRole("heading", { name: "Revisar e adicionar regra" })).toBeVisible();
  await expect(ruleDialog.getByLabel("Palavra-chave")).toHaveValue("OPENAI");
  await expect(ruleDialog.getByLabel("Categoria")).toHaveValue("cat-subscriptions");
  await expect(ruleDialog.getByLabel("Tipo")).toHaveValue("expense");

  await ruleDialog.getByRole("button", { name: "Adicionar regra" }).click();
  await expect(page.getByText("Regra criada.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Adicionar regra" })).toHaveCount(0);
});

test("insights suggested category opens prefilled dialog and updates rule options", async ({ page }) => {
  await mockFinanceApi(page);
  await page.goto("/");
  await page.waitForLoadState("networkidle");

  await expect(page.getByText("Categorias sugeridas")).toBeVisible();
  await expect(page.getByText("Moradia para Despesa (4 ocorr")).toBeVisible();
  await page.getByRole("button", { name: "Adicionar categoria" }).click();
  const categoryDialog = page.getByRole("dialog", { name: "Adicionar categoria" });
  await expect(categoryDialog.getByRole("heading", { name: "Adicionar categoria" })).toBeVisible();
  await expect(categoryDialog.getByLabel("Nome")).toHaveValue("Moradia");
  await expect(categoryDialog.getByLabel("Tipo")).toHaveValue("expense");
  await categoryDialog.getByRole("button", { name: "Adicionar categoria" }).click();

  await expect(page.getByText("Categoria criada.")).toBeVisible();
  await expect(page.getByText("Moradia para Despesa")).toHaveCount(0);

  await page.getByRole("button", { name: "Adicionar regra" }).click();
  await expect(page.getByRole("dialog", { name: "Revisar e adicionar regra" }).getByLabel("Categoria")).toContainText("Moradia");
});

test("dashboard filters and labels open finance transactions", async ({ page }) => {
  await mockFinanceApi(page);
  await page.goto("/");
  await page.waitForLoadState("networkidle");

  await page.getByRole("combobox").filter({ hasText: "Todas as origens" }).selectOption("open_finance");
  await expect(page.getByText("OPENAI ASSINATURA")).toBeVisible();
  await expect(page.locator("span").filter({ hasText: "Open Finance" })).toBeVisible();
  await expect(page.getByText("MERCADO***TESTE")).toHaveCount(0);
});

test("insights rename CTA opens transactions with cleanup filter", async ({ page }) => {
  await mockFinanceApi(page);
  await page.goto("/");
  await page.waitForLoadState("networkidle");

  await page.getByRole("button", { name: "Ver transações" }).click();
  await expect(page).toHaveURL(/\/transactions\?cleanup=rename&transaction_ids=tx-rename/);
  await expect(page.getByText("Exibindo transacoes com sugestao de limpeza de descricao.")).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(page.locator("tbody tr").first()).toContainText("MERCADO***TESTE");
});

test("dashboard quick action buttons open prefilled transaction drawer", async ({ page }) => {
  await mockFinanceApi(page);
  await page.goto("/");
  await page.waitForLoadState("networkidle");

  await page.getByRole("link", { name: "Receita" }).click();
  await expect(page).toHaveURL(/\/transactions\?create=income/);
  await expect(page.getByRole("heading", { name: "Criar lançamento manual" })).toBeVisible();
  await expect(page.locator("aside").getByLabel("Tipo")).toHaveValue("income");

  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await page.getByRole("link", { name: "Despesa" }).click();
  await expect(page).toHaveURL(/\/transactions\?create=expense/);
  await expect(page.getByRole("heading", { name: "Criar lançamento manual" })).toBeVisible();
  await expect(page.locator("aside").getByLabel("Tipo")).toHaveValue("expense");
});

test("global assistant is absent from login and supports open close interactions", async ({ page }) => {
  await mockFinanceApi(page);

  await page.goto("/login");
  await expect(page.getByRole("button", { name: "Abrir assistente financeiro" })).toHaveCount(0);

  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Abrir assistente financeiro" }).click();
  await expect(page.getByRole("dialog", { name: "Assistente financeiro" })).toBeVisible();

  await page.getByRole("button", { name: "Fechar assistente" }).click();
  await expect(page.getByRole("dialog", { name: "Assistente financeiro" })).toBeHidden();

  await page.getByRole("button", { name: "Abrir assistente financeiro" }).click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Assistente financeiro" })).toBeHidden();

  await page.getByRole("button", { name: "Abrir assistente financeiro" }).click();
  await page.mouse.click(80, 80);
  await expect(page.getByRole("dialog", { name: "Assistente financeiro" })).toBeHidden();
});

test("global assistant sends question, renders structured response and navigates CTA", async ({ page }) => {
  await mockFinanceApi(page);
  await page.goto("/");
  await page.waitForLoadState("networkidle");

  await page.getByRole("button", { name: "Abrir assistente financeiro" }).click();
  await page.getByLabel("Pergunte sobre suas financas").fill("quanto gastei com assinaturas esse mes");
  await page.getByRole("button", { name: "Enviar pergunta" }).click();

  await expect(page.getByText("Encontrei 1 transacao neste mes, no valor total de R$ 100,00.")).toBeVisible();
  await page.getByRole("dialog", { name: "Assistente financeiro" }).getByRole("button", { name: "Ver transações" }).click();
  await expect(page).toHaveURL(/\/transactions\?/);
  await expect(page.getByPlaceholder("Buscar descrição")).toHaveValue("openai");
  await expect(page.getByLabel("Tipo")).toHaveValue("expense");
  await expect(page.getByLabel("Categoria")).toHaveValue("cat-subscriptions");
  await expect(page.locator("tbody tr")).toHaveCount(1);
});
