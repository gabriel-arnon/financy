import { expect, test } from "@playwright/test";

test("upload area sends selected file and opens preview", async ({ page }) => {
  let uploadCalled = false;

  await page.route("**/imports/upload", async (route) => {
    uploadCalled = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        import_id: "e2e-import-1",
        file_id: "e2e-file-1",
        filename: "fatura.pdf",
        preview_count: 1
      })
    });
  });

  await page.route("**/imports/e2e-import-1/preview", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        import_id: "e2e-import-1",
        categories: [{ id: "cat-food", name: "Alimentacao" }],
        items: [
          {
            id: "preview-1",
            transaction_date: "2026-06-07",
            description: "OPENAI TESTE",
            original_description: "OPENAI TESTE",
            amount: "99.90",
            type: "expense",
            category_id: "cat-food",
            suggested_category: "Assinaturas",
            merchant_country: "BR",
            account_id: null,
            card_id: null,
            card_statement_id: null,
            installment_current: null,
            installment_total: null,
            raw_text: "07/06 OPENAI TESTE BR R$ 99,90",
            parser_confidence: 0.95,
            needs_review: false,
            duplicate_candidate: false,
            default_selected: true,
            excluded_reason: null,
            classification_rule_id: "rule-1",
            classification_label: "Regra: OPENAI -> Assinaturas",
            statement_total_amount: "99.90",
            statement_due_date: "2026-07-05",
            statement_reference_month: "2026-06",
            card_last_digits: null,
            status: "pending"
          }
        ]
      })
    });
  });

  await page.route("**/accounts", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });

  await page.route("**/cards", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });

  await page.goto("/importacao");
  await page.waitForLoadState("networkidle");

  await expect(page.getByText("Arraste um arquivo ou clique para enviar")).toBeVisible();
  await expect(page.locator('input[type="file"]')).toHaveAttribute("accept", ".pdf,.ofx,.csv,.xlsx");
  const fileChooserPromise = page.waitForEvent("filechooser");
  await page.getByText("Arraste um arquivo ou clique para enviar").click();
  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles({
    name: "fatura.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 e2e")
  });

  await expect(page).toHaveURL(/\/importacao\?importId=e2e-import-1/);
  await expect(page.locator('input[value="OPENAI TESTE"]')).toBeVisible();
  await expect(page.getByRole("cell", { name: "Assinaturas", exact: true })).toBeVisible();
  expect(uploadCalled).toBe(true);
});
