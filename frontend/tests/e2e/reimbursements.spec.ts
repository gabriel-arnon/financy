import { expect, test, type Page } from "@playwright/test";

const categories = [
  { id: "cat-health", name: "Saude", type: "expense", status: "active" },
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

const transactions = [
  {
    id: "tx-1",
    user_id: "dev-user",
    account_id: "acc-1",
    card_id: null,
    card_statement_id: null,
    transaction_date: "2026-07-10",
    description: "FARMACIA",
    original_description: "FARMACIA",
    normalized_description: "farmacia",
    amount: "100.00",
    type: "expense",
    category_id: "cat-health",
    source_file_id: null,
    installment_current: null,
    installment_total: null,
    status: "confirmed",
    created_at: "2026-07-10T12:00:00Z"
  },
  {
    id: "tx-2",
    user_id: "dev-user",
    account_id: "acc-1",
    card_id: null,
    card_statement_id: null,
    transaction_date: "2026-07-11",
    description: "SALARIO",
    original_description: "SALARIO",
    normalized_description: "salario",
    amount: "2000.00",
    type: "income",
    category_id: "cat-income",
    source_file_id: null,
    installment_current: null,
    installment_total: null,
    status: "confirmed",
    created_at: "2026-07-11T12:00:00Z"
  }
];

function buildContact(overrides = {}) {
  return {
    id: "contact-1",
    owner_user_id: "dev-user",
    display_name: "Mae",
    email: "mae@example.com",
    phone: "",
    status: "active",
    metadata: {},
    created_at: "2026-07-01T00:00:00Z",
    updated_at: "2026-07-01T00:00:00Z",
    ...overrides
  };
}

async function mockReimbursementsApi(page: Page, options: { seeded?: boolean } = {}) {
  let contacts = options.seeded ? [buildContact()] : [] as any[];
  let claims = [] as any[];
  let events = [] as any[];
  let invitations = [] as any[];
  let memberships = [] as any[];
  let guestAccessActive = true;
  let eligible = [
    {
      id: "tx-1",
      transaction_date: "2026-07-10",
      description: "FARMACIA",
      amount: "100.00",
      type: "expense",
      status: "confirmed",
      category_id: "cat-health",
      account_id: "acc-1",
      card_id: null,
      card_statement_id: null,
      allocated_amount: "0.00",
      available_amount: "100.00",
      eligible: true,
      ineligible_reason: null
    }
  ];

  const claimWithContact = (claim: any) => ({ ...claim, contact: contacts.find((contact) => contact.id === claim.contact_id) ?? null });
  const overview = () => ({
    total_sent: claims.filter((claim) => claim.status === "sent").reduce((sum, claim) => sum + Number(claim.total_amount), 0).toFixed(2),
    draft_count: claims.filter((claim) => claim.status === "draft").length,
    sent_count: claims.filter((claim) => claim.status === "sent").length,
    canceled_count: claims.filter((claim) => claim.status === "canceled").length,
    recent_claims: claims.map(claimWithContact),
    draft_claims: claims.filter((claim) => claim.status === "draft").map(claimWithContact),
    upcoming_claims: claims.filter((claim) => claim.status === "sent").map(claimWithContact)
  });

  function createClaim(payload: any) {
    const claim = {
      id: `claim-${claims.length + 1}`,
      owner_user_id: "dev-user",
      contact_id: payload.contact_id,
      title: payload.title,
      description: payload.description ?? null,
      due_date: payload.due_date ?? null,
      status: "draft",
      total_snapshot: null,
      total_amount: "0.00",
      version: 1,
      sent_at: null,
      canceled_at: null,
      first_viewed_at: null,
      last_viewed_at: null,
      view_count: 0,
      created_at: "2026-07-12T12:00:00Z",
      updated_at: "2026-07-12T12:00:00Z",
      contact: null,
      items: []
    };
    claims.push(claim);
    events.push({ id: `event-${events.length + 1}`, owner_user_id: "dev-user", claim_id: claim.id, contact_id: claim.contact_id, item_id: null, actor_type: "owner", actor_user_id: "dev-user", event_type: "claim_created", metadata: {}, created_at: "2026-07-12T12:00:00Z" });
    return claimWithContact(claim);
  }

  if (options.seeded) {
    createClaim({ contact_id: "contact-1", title: "Julho", due_date: "2026-07-31" });
  }

  await page.route("**/categories", async (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(categories) }));
  await page.route("**/accounts", async (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(accounts) }));
  await page.route("**/cards", async (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(cards) }));
  await page.route("**/transactions", async (route) => {
    if (route.request().resourceType() === "document") return route.fallback();
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(transactions) });
  });
  await page.route("**/transactions/**", async (route) => {
    if (route.request().resourceType() === "document") return route.fallback();
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(transactions[0]) });
  });
  await page.route("**/classification-rules", async (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) }));

  await page.route("**/reimbursements**", async (route) => {
    const request = route.request();
    if (request.resourceType() === "document") return route.fallback();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    if (path === "/reimbursements/overview") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(overview()) });
    }
    if (path === "/reimbursements/contacts" && method === "GET") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(contacts) });
    }
    if (path === "/reimbursements/contacts" && method === "POST") {
      const payload = request.postDataJSON();
      const contact = buildContact({ id: `contact-${contacts.length + 1}`, ...payload, status: "active" });
      contacts.push(contact);
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(contact) });
    }
    if (path.startsWith("/reimbursements/contacts/") && method === "PATCH") {
      const id = path.split("/").pop();
      const payload = request.postDataJSON();
      contacts = contacts.map((contact) => contact.id === id ? { ...contact, ...payload } : contact);
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(contacts.find((contact) => contact.id === id)) });
    }
    if (path.startsWith("/reimbursements/contacts/") && method === "DELETE") {
      const id = path.split("/").pop();
      contacts = contacts.map((contact) => contact.id === id ? { ...contact, status: "inactive" } : contact);
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(contacts.find((contact) => contact.id === id)) });
    }
    if (path === "/reimbursements/claims" && method === "GET") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(claims.map(claimWithContact)) });
    }
    if (path === "/reimbursements/claims" && method === "POST") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(createClaim(request.postDataJSON())) });
    }
    if (path === "/reimbursements/eligible-transactions") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(eligible) });
    }
    if (path === "/reimbursements/invitations" && method === "GET") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(invitations) });
    }
    if (path === "/reimbursements/invitations" && method === "POST") {
      const payload = request.postDataJSON();
      const invitation = {
        id: `invitation-${invitations.length + 1}`,
        owner_user_id: "dev-user",
        contact_id: payload.contact_id,
        claim_id: payload.claim_id ?? null,
        email: payload.email ?? contacts.find((contact) => contact.id === payload.contact_id)?.email ?? "mae@example.com",
        status: "pending",
        expires_at: "2026-07-26T12:00:00Z",
        accepted_at: null,
        accepted_by_user_id: null,
        revoked_at: null,
        created_at: "2026-07-12T12:00:00Z",
        contact: contacts.find((contact) => contact.id === payload.contact_id) ?? null,
        claim: claims.find((claim) => claim.id === payload.claim_id) ?? null,
        accept_token: "mock-token",
        accept_path: "/guest/reimbursements/accept?token=mock-token"
      };
      invitations.push(invitation);
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(invitation) });
    }
    const revokeInvitationMatch = path.match(/^\/reimbursements\/invitations\/([^/]+)\/revoke$/);
    if (revokeInvitationMatch) {
      invitations = invitations.map((invitation) => invitation.id === revokeInvitationMatch[1] ? { ...invitation, status: "revoked", revoked_at: "2026-07-12T13:00:00Z" } : invitation);
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(invitations.find((invitation) => invitation.id === revokeInvitationMatch[1])) });
    }
    if (path === "/reimbursements/memberships" && method === "GET") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(memberships) });
    }
    const revokeMembershipMatch = path.match(/^\/reimbursements\/memberships\/([^/]+)\/revoke$/);
    if (revokeMembershipMatch) {
      memberships = memberships.map((membership) => membership.id === revokeMembershipMatch[1] ? { ...membership, status: "revoked", revoked_at: "2026-07-12T13:00:00Z" } : membership);
      guestAccessActive = false;
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(memberships.find((membership) => membership.id === revokeMembershipMatch[1])) });
    }
    if (path === "/reimbursements/guest/invitations/accept" && method === "POST") {
      const membership = {
        id: "membership-1",
        owner_user_id: "dev-user",
        contact_id: "contact-1",
        auth_user_id: "guest-user",
        email: "mae@example.com",
        status: "active",
        linked_at: "2026-07-12T13:00:00Z",
        revoked_at: null,
        created_at: "2026-07-12T13:00:00Z",
        contact: contacts[0] ?? null
      };
      memberships = [membership];
      invitations = invitations.map((invitation) => ({ ...invitation, status: "accepted", accepted_at: "2026-07-12T13:00:00Z", accepted_by_user_id: "guest-user" }));
      guestAccessActive = true;
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(membership) });
    }
    if (path === "/reimbursements/guest/claims" && method === "GET") {
      const visible = guestAccessActive ? claims.filter((claim) => claim.status !== "draft").map((claim) => ({
        id: claim.id,
        title: claim.title,
        description: claim.description,
        due_date: claim.due_date,
        status: claim.status,
        total_amount: claim.total_amount,
        sent_at: claim.sent_at,
        first_viewed_at: claim.first_viewed_at,
        last_viewed_at: claim.last_viewed_at,
        attachment_count: 1,
        items: claim.items.map((item: any) => ({
          id: item.id,
          description: item.transaction_snapshot.description,
          transaction_date: item.transaction_snapshot.transaction_date,
          amount: item.transaction_snapshot.amount,
          amount_requested: item.amount_requested,
          currency: "BRL"
        }))
      })) : [];
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(visible) });
    }
    const guestActionMatch = path.match(/^\/reimbursements\/guest\/claims\/([^/]+)\/(acknowledge|dispute)$/);
    if (guestActionMatch && method === "POST") {
      const claim = claims.find((item) => item.id === guestActionMatch[1]);
      claim.status = guestActionMatch[2] === "acknowledge" ? "acknowledged" : "disputed";
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
        id: claim.id,
        title: claim.title,
        description: claim.description,
        due_date: claim.due_date,
        status: claim.status,
        total_amount: claim.total_amount,
        sent_at: claim.sent_at,
        first_viewed_at: claim.first_viewed_at,
        last_viewed_at: claim.last_viewed_at,
        attachment_count: 1,
        items: claim.items.map((item: any) => ({
          id: item.id,
          description: item.transaction_snapshot.description,
          transaction_date: item.transaction_snapshot.transaction_date,
          amount: item.transaction_snapshot.amount,
          amount_requested: item.amount_requested,
          currency: "BRL"
        }))
      }) });
    }
    const guestAttachmentsMatch = path.match(/^\/reimbursements\/guest\/claims\/([^/]+)\/attachments$/);
    if (guestAttachmentsMatch && method === "GET") {
      if (!guestAccessActive) return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ error: { message: "not found" } }) });
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "claim-attachment-1", claim_id: guestAttachmentsMatch[1], status: "active", created_at: "2026-07-12T13:00:00Z", deleted_at: null, file: { original_filename: "recibo.pdf", detected_mime_type: "application/pdf", size_bytes: 20 } }]) });
    }
    const guestSignedUrlMatch = path.match(/^\/reimbursements\/guest\/claims\/([^/]+)\/attachments\/([^/]+)\/signed-url$/);
    if (guestSignedUrlMatch && method === "GET") {
      if (!guestAccessActive) return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ error: { message: "not found" } }) });
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ file_id: "hidden", url: "http://127.0.0.1:3100/mock-recibo.pdf", expires_at: "2026-07-12T13:10:00Z" }) });
    }
    const sendMatch = path.match(/^\/reimbursements\/claims\/([^/]+)\/send$/);
    if (sendMatch) {
      const claim = claims.find((item) => item.id === sendMatch[1]);
      claim.status = "sent";
      claim.sent_at = "2026-07-12T13:00:00Z";
      claim.total_snapshot = claim.total_amount;
      events.push({ id: `event-${events.length + 1}`, owner_user_id: "dev-user", claim_id: claim.id, contact_id: claim.contact_id, item_id: null, actor_type: "owner", actor_user_id: "dev-user", event_type: "claim_sent", metadata: {}, created_at: "2026-07-12T13:00:00Z" });
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(claimWithContact(claim)) });
    }
    const cancelMatch = path.match(/^\/reimbursements\/claims\/([^/]+)\/cancel$/);
    if (cancelMatch) {
      const claim = claims.find((item) => item.id === cancelMatch[1]);
      claim.status = "canceled";
      claim.canceled_at = "2026-07-12T14:00:00Z";
      claim.items = claim.items.map((item: any) => ({ ...item, status: "canceled" }));
      eligible = eligible.map((item) => item.id === "tx-1" ? { ...item, allocated_amount: "0.00", available_amount: "100.00", eligible: true } : item);
      events.push({ id: `event-${events.length + 1}`, owner_user_id: "dev-user", claim_id: claim.id, contact_id: claim.contact_id, item_id: null, actor_type: "owner", actor_user_id: "dev-user", event_type: "claim_canceled", metadata: {}, created_at: "2026-07-12T14:00:00Z" });
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(claimWithContact(claim)) });
    }
    const eventsMatch = path.match(/^\/reimbursements\/claims\/([^/]+)\/events$/);
    if (eventsMatch) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(events.filter((event) => event.claim_id === eventsMatch[1])) });
    }
    const itemMatch = path.match(/^\/reimbursements\/claims\/([^/]+)\/items$/);
    if (itemMatch && method === "POST") {
      const claim = claims.find((item) => item.id === itemMatch[1]);
      const payload = request.postDataJSON();
      const source = eligible.find((item) => item.id === payload.transaction_id)!;
      if (Number(payload.amount_requested) > Number(source.available_amount)) {
        return route.fulfill({ status: 400, contentType: "application/json", body: JSON.stringify({ error: { code: "reimbursement_amount_exceeds_transaction", message: "Valor solicitado excede o saldo ressarcivel da transacao." } }) });
      }
      const newItem = {
        id: `item-${claim.items.length + 1}`,
        owner_user_id: "dev-user",
        claim_id: claim.id,
        transaction_id: payload.transaction_id,
        amount_requested: Number(payload.amount_requested).toFixed(2),
        status: "active",
        transaction_snapshot: { description: source.description, transaction_date: source.transaction_date, amount: source.amount, amount_requested: Number(payload.amount_requested).toFixed(2), category_id: source.category_id },
        snapshot_is_current: true,
        position: claim.items.length,
        canceled_at: null,
        created_at: "2026-07-12T12:20:00Z"
      };
      claim.items.push(newItem);
      claim.total_amount = claim.items.filter((item: any) => item.status === "active").reduce((sum: number, item: any) => sum + Number(item.amount_requested), 0).toFixed(2);
      eligible = eligible.map((item) => item.id === payload.transaction_id ? { ...item, allocated_amount: claim.total_amount, available_amount: (Number(item.available_amount) - Number(payload.amount_requested)).toFixed(2), eligible: Number(item.available_amount) > Number(payload.amount_requested) } : item);
      events.push({ id: `event-${events.length + 1}`, owner_user_id: "dev-user", claim_id: claim.id, contact_id: claim.contact_id, item_id: newItem.id, actor_type: "owner", actor_user_id: "dev-user", event_type: "item_added", metadata: {}, created_at: "2026-07-12T12:20:00Z" });
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(claimWithContact(claim)) });
    }
    const deleteItemMatch = path.match(/^\/reimbursements\/claims\/([^/]+)\/items\/([^/]+)$/);
    if (deleteItemMatch && method === "DELETE") {
      const claim = claims.find((item) => item.id === deleteItemMatch[1]);
      claim.items = claim.items.filter((item: any) => item.id !== deleteItemMatch[2]);
      claim.total_amount = "0.00";
      eligible = eligible.map((item) => item.id === "tx-1" ? { ...item, allocated_amount: "0.00", available_amount: "100.00", eligible: true } : item);
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(claimWithContact(claim)) });
    }
    return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ error: { message: "not mocked" } }) });
  });
}

test("shows reimbursements navigation on desktop and mobile", async ({ page }) => {
  await mockReimbursementsApi(page);
  await page.goto("/reimbursements");
  await expect(page.getByRole("heading", { name: "Cobranças a receber" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Ressarcimentos" })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Abrir menu" }).click();
  await expect(page.getByRole("link", { name: "Ressarcimentos" })).toBeVisible();
});

test("guest accepts invite sees limited portal acts and loses access after revocation", async ({ page }) => {
  await mockReimbursementsApi(page, { seeded: true });
  await page.goto("/reimbursements");
  await page.getByRole("button", { name: "Cobranças" }).click();
  await page.getByLabel("Valor para FARMACIA").fill("50.00");
  await page.getByRole("button", { name: "Adicionar" }).click();
  await page.getByRole("button", { name: "Finalizar cobrança" }).click();
  await page.getByRole("dialog", { name: "Finalizar cobranca" }).getByRole("button", { name: "Finalizar cobranca" }).click();
  await page.getByRole("button", { name: "Criar convite" }).click();
  await expect(page.getByText("/guest/reimbursements/accept?token=mock-token")).toBeVisible();

  await page.goto("/guest/reimbursements/accept?token=mock-token");
  await expect(page.getByText("Acesso liberado")).toBeVisible();
  await page.getByRole("link", { name: "Abrir portal" }).click();
  await expect(page.getByRole("heading", { name: "Cobranças compartilhadas" })).toBeVisible();
  await expect(page.getByText("Julho")).toBeVisible();
  await expect(page.getByText("FARMACIA")).toBeVisible();
  await expect(page.getByText("Conta Corrente")).toHaveCount(0);

  await page.getByRole("button", { name: "Ver comprovantes" }).click();
  await expect(page.getByRole("button", { name: "recibo.pdf" })).toBeVisible();
  await page.getByRole("button", { name: "Reconhecer" }).click();
  await expect(page.getByText(/Reconhecida .*1 itens/)).toBeVisible();
  await page.getByRole("button", { name: "Contestar" }).click();
  await expect(page.getByText(/Contestada .*1 itens/)).toBeVisible();

  await page.goto("/reimbursements");
  await page.getByRole("button", { name: "Pessoas" }).click();
  await page.getByRole("button", { name: "Revogar" }).click();
  await page.getByRole("dialog", { name: "Revogar acesso" }).getByRole("button", { name: "Revogar acesso" }).click();
  await page.goto("/guest/reimbursements");
  await expect(page.getByText("Nenhuma cobrança compartilhada")).toBeVisible();
});

test("creates edits and inactivates reimbursement contacts", async ({ page }) => {
  await mockReimbursementsApi(page);
  await page.goto("/reimbursements");
  await page.getByRole("button", { name: "Pessoas" }).click();
  await page.getByRole("button", { name: "Nova pessoa" }).click();
  await page.getByLabel("Nome").fill("Mae");
  await page.getByLabel("E-mail").fill("mae@example.com");
  await page.getByRole("button", { name: "Salvar pessoa" }).click();
  await expect(page.getByText("Mae").first()).toBeVisible();

  await page.getByRole("button", { name: "Editar pessoa" }).click();
  await page.getByLabel("Nome").fill("Pai");
  await page.getByRole("button", { name: "Salvar pessoa" }).click();
  await expect(page.getByText("Pai").first()).toBeVisible();

  await page.getByRole("button", { name: "Inativar pessoa" }).click();
  await expect(page.getByRole("dialog", { name: "Inativar pessoa" })).toBeVisible();
  await page.getByRole("dialog", { name: "Inativar pessoa" }).getByRole("button", { name: "Inativar pessoa" }).click();
  await expect(page.getByText("Pai").first()).toBeHidden();
});

test("creates claim adds item finalizes cancels and shows timeline", async ({ page }) => {
  await mockReimbursementsApi(page, { seeded: true });
  await page.goto("/reimbursements");
  await page.getByRole("button", { name: "Cobranças" }).click();
  await expect(page.getByText("Julho").first()).toBeVisible();

  await page.getByLabel("Valor para FARMACIA").fill("999.00");
  await page.getByRole("button", { name: "Adicionar" }).click();
  await expect(page.getByText("Valor solicitado excede")).toBeVisible();

  await page.getByLabel("Valor para FARMACIA").fill("50.00");
  await page.getByRole("button", { name: "Adicionar" }).click();
  await expect(page.getByText("Solicitado R$ 50,00")).toBeVisible();
  await expect(page.getByText("Item adicionado").first()).toBeVisible();

  await page.getByRole("button", { name: "Finalizar cobrança" }).click();
  await expect(page.getByRole("dialog", { name: "Finalizar cobranca" })).toBeVisible();
  await page.getByRole("dialog", { name: "Finalizar cobranca" }).getByRole("button", { name: "Finalizar cobranca" }).click();
  await expect(page.getByText("Dados congelados no envio")).toBeVisible();
  await expect(page.getByRole("button", { name: "Editar" })).toBeHidden();

  await page.getByRole("button", { name: "Cancelar" }).click();
  await expect(page.getByRole("dialog", { name: "Cancelar cobranca" })).toBeVisible();
  await page.getByRole("dialog", { name: "Cancelar cobranca" }).getByRole("button", { name: "Cancelar cobranca" }).click();
  await expect(page.getByRole("row", { name: /Julho.*Cancelada/ })).toBeVisible();
  await expect(page.getByText("Cobrança cancelada")).toBeVisible();
});

test("starts reimbursement flow from transactions with mixed selection", async ({ page }) => {
  await mockReimbursementsApi(page, { seeded: true });
  await page.goto("/transactions");
  await page.locator("tbody input[type='checkbox']").nth(0).check();
  await page.locator("tbody input[type='checkbox']").nth(1).check();
  await page.locator("button").filter({ hasText: "Solicitar ressarcimento" }).click();
  await expect(page.getByRole("heading", { name: "Solicitar ressarcimento" })).toBeVisible();
  await expect(page.getByText("não entram no ressarcimento")).toBeVisible();
  await expect(page.getByRole("dialog").getByText("FARMACIA")).toBeVisible();
  await page.getByRole("button", { name: "Confirmar inclusão" }).click();
  await expect(page).toHaveURL(/\/reimbursements/);
});
