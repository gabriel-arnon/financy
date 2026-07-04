import { expect, test, type Page } from "@playwright/test";

const categories = [
  { id: "cat-food", name: "Alimentação" },
  { id: "cat-subscriptions", name: "Assinaturas" }
];

const accounts = [
  {
    id: "acc-1",
    user_id: "dev-user",
    name: "Conta Corrente",
    institution: "Banco do Brasil",
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
    name: "Ourocard",
    institution: "Banco do Brasil",
    brand: "Elo",
    last_digits: "6149",
    limit_amount: "5000.00",
    closing_day: 25,
    due_day: 5,
    status: "active",
    created_at: "2026-06-01T00:00:00Z"
  }
];

const transactions = [
  {
    id: "tx-1",
    user_id: "dev-user",
    account_id: null,
    card_id: "card-1",
    card_statement_id: "statement-1",
    transaction_date: "2026-06-07",
    description: "OPENAI ASSINATURA",
    original_description: "OPENAI ASSINATURA",
    amount: "99.90",
    type: "expense",
    category_id: "cat-subscriptions",
    source_file_id: "file-1",
    installment_current: null,
    installment_total: null,
    status: "confirmed",
    created_at: "2026-06-07T12:00:00Z"
  }
];

const statements = [
  {
    id: "statement-1",
    user_id: "dev-user",
    card_id: "card-1",
    account_id: "acc-1",
    reference_month: "2026-06-01",
    due_date: "2026-07-05",
    closing_date: null,
    reported_total: "120.00",
    minimum_payment_amount: null,
    status: "open",
    paid_at: null,
    source_file_id: "file-1",
    transaction_count: 1,
    calculated_total: "99.90",
    difference: "20.10",
    integrity_status: "difference",
    integrity_label: "Divergência",
    created_at: "2026-06-07T12:00:00Z"
  },
  {
    id: "statement-2",
    user_id: "dev-user",
    card_id: "card-1",
    account_id: "acc-1",
    reference_month: "2026-05-01",
    due_date: "2026-06-05",
    closing_date: null,
    reported_total: "80.00",
    minimum_payment_amount: null,
    status: "open",
    paid_at: null,
    source_file_id: "file-2",
    transaction_count: 0,
    calculated_total: "0",
    difference: "80.00",
    integrity_status: "no_transactions",
    integrity_label: "Sem transa\u00e7\u00f5es",
    created_at: "2026-06-01T12:00:00Z"
  }
];

const statementDetail = {
  ...statements[0],
  transactions
};

const accountSummary = {
  account: accounts[0],
  cards: [
    {
      ...cards[0],
      open_statement_count: 2,
      open_statement_total: "200.00"
    }
  ],
  open_statements: statements,
  total_open_statements: "200.00",
  total_open_statements_ok: "120.00",
  total_open_statements_warning: "80.00",
  transaction_count: 1,
  total_income: "0",
  total_expense: "99.90",
  net_balance_period: "-99.90",
  recent_transactions: transactions
};

const cardSummary = {
  card: cards[0],
  account: accounts[0],
  limit_total: "5000.00",
  limit_used: "200.00",
  limit_available: "4800.00",
  usage_percent: "4.00",
  upcoming_statements: statements,
  statement_history: statements,
  recent_transactions: transactions
};

const previewResponse = {
  import_id: "responsive-import",
  categories,
  items: [
    {
      id: "preview-1",
      transaction_date: "2026-06-07",
      description: "OPENAI ASSINATURA",
      original_description: "OPENAI ASSINATURA",
      amount: "99.90",
      type: "expense",
      category_id: "cat-subscriptions",
      suggested_category: "Assinaturas",
      merchant_country: "BR",
      account_id: null,
      card_id: null,
      card_statement_id: null,
      installment_current: null,
      installment_total: null,
      raw_text: "07/06 OPENAI ASSINATURA BR 99,90",
      parser_confidence: 0.96,
      needs_review: false,
      duplicate_candidate: false,
      default_selected: true,
      excluded_reason: null,
      classification_rule_id: "rule-1",
      classification_label: "Regra: OPENAI → Assinaturas",
      statement_total_amount: "99.90",
      statement_due_date: "2026-07-05",
      statement_reference_month: "2026-06",
      card_last_digits: "6149",
      status: "pending"
    }
  ]
};

async function mockApi(page: Page) {
  await page.route("**/categories", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(categories) });
  });
  await page.route("**/accounts", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(accounts) });
  });
  await page.route("**/accounts/acc-1/summary**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(accountSummary) });
  });
  await page.route("**/cards/card-1/summary**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(cardSummary) });
  });
  await page.route("**/cards", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(cards) });
  });
  await page.route("**/transactions?**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(transactions) });
  });
  await page.route("**/transactions", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(transactions) });
  });
  await page.route("**/statements/statement-1", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(statementDetail) });
  });
  await page.route("**/statements/statement-1/status", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...statementDetail, status: "paid", paid_at: "2026-06-07T12:30:00Z" }) });
  });
  await page.route("**/statements", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(statements) });
  });
  await page.route("**/classification-rules", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "rule-1",
          user_id: "dev-user",
          keyword: "OPENAI",
          category_id: "cat-subscriptions",
          transaction_type: "expense",
          priority: 100,
          status: "active",
          match_scope: "both",
          auto_created: false,
          created_at: "2026-06-01T00:00:00Z"
        }
      ])
    });
  });
  await page.route("**/imports/responsive-import/preview", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(previewResponse) });
  });
}

async function expectVisibleButtonsNotClipped(page: Page) {
  const issues = await page.locator('button, a[href="/importacao"], a[href="/transactions"]').evaluateAll((elements) =>
    elements
      .filter((element) => {
        const rect = element.getBoundingClientRect();
        const style = window.getComputedStyle(element);
        return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
      })
      .map((element) => {
        const rect = element.getBoundingClientRect();
        const text = element.textContent?.replace(/\s+/g, " ").trim() ?? "";
        return {
          text,
          width: rect.width,
          clientWidth: element.clientWidth,
          scrollWidth: element.scrollWidth
        };
      })
      .filter((item) => item.text && item.scrollWidth > item.clientWidth + 2)
  );

  expect(issues).toEqual([]);
}

for (const width of [375, 430]) {
  test(`main action buttons do not clip at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await mockApi(page);

    for (const path of ["/accounts", "/accounts/acc-1", "/cards", "/cards/card-1", "/rules", "/transactions", "/transactions?card_id=card-1", "/statements", "/statements/statement-1", "/importacao", "/importacao?importId=responsive-import", "/"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await expectVisibleButtonsNotClipped(page);
    }

    await page.goto("/");
    await expect(page.locator("nav").filter({ hasText: "Faturas" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Cartões de Crédito" })).toBeVisible();
  });
}
