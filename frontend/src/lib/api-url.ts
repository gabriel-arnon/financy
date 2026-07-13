const LOCAL_API_URL = "http://127.0.0.1:8000";

function isLocalHostname(hostname: string) {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1" || hostname === "0.0.0.0";
}

function isRemoteRuntime() {
  return Boolean(process.env.VERCEL) || Boolean(process.env.VERCEL_ENV) || process.env.CI === "true" || process.env.FINANCY_REMOTE_BUILD === "true";
}

function normalizeApiUrl(value: string, context: string) {
  let parsed: URL;
  try {
    parsed = new URL(value.trim());
  } catch {
    throw new Error(`${context}: NEXT_PUBLIC_API_URL deve ser uma URL absoluta valida.`);
  }

  if (parsed.username || parsed.password) {
    throw new Error(`${context}: NEXT_PUBLIC_API_URL nao deve conter credenciais.`);
  }

  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error(`${context}: NEXT_PUBLIC_API_URL deve usar http ou https.`);
  }

  if (isRemoteRuntime()) {
    if (parsed.protocol !== "https:") {
      throw new Error(`${context}: NEXT_PUBLIC_API_URL deve usar https em Preview/Production.`);
    }
    if (isLocalHostname(parsed.hostname)) {
      throw new Error(`${context}: NEXT_PUBLIC_API_URL nao pode apontar para localhost em Preview/Production.`);
    }
  }

  return parsed.toString().replace(/\/+$/, "");
}

export function resolveApiBaseUrl(context = "Financy frontend") {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) {
    return normalizeApiUrl(configured, context);
  }
  if (isRemoteRuntime()) {
    throw new Error(`${context}: NEXT_PUBLIC_API_URL e obrigatoria em Preview/Production.`);
  }
  return LOCAL_API_URL;
}
