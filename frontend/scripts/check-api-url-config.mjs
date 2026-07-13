import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const LOCAL_API_URL = "http://127.0.0.1:8000";

function parseEnvFile(path) {
  if (!existsSync(path)) return {};
  const values = {};
  for (const line of readFileSync(path, "utf-8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const match = trimmed.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
    if (!match) continue;
    let value = match[2].trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    values[match[1]] = value;
  }
  return values;
}

function envValue(name) {
  if (process.env[name]) return process.env[name];
  for (const file of [".env.local", ".env.development.local", ".env"]) {
    const value = parseEnvFile(resolve(process.cwd(), file))[name];
    if (value) return value;
  }
  return "";
}

function isLocalHostname(hostname) {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1" || hostname === "0.0.0.0";
}

function contextFromArgs() {
  const explicit = process.argv.find((arg) => arg.startsWith("--context="))?.split("=")[1];
  if (explicit) return explicit;
  if (process.env.VERCEL_ENV) return process.env.VERCEL_ENV;
  if (process.env.VERCEL || process.env.CI === "true") return "preview";
  return process.env.NODE_ENV === "production" ? "production" : "development";
}

export function validateApiUrlConfig({ value = envValue("NEXT_PUBLIC_API_URL"), context = contextFromArgs() } = {}) {
  const remote = ["production", "preview"].includes(context);
  if (!value?.trim()) {
    if (remote) throw new Error("NEXT_PUBLIC_API_URL is required for remote frontend builds.");
    return LOCAL_API_URL;
  }

  let parsed;
  try {
    parsed = new URL(value.trim());
  } catch {
    throw new Error("NEXT_PUBLIC_API_URL must be an absolute valid URL.");
  }
  if (parsed.username || parsed.password) {
    throw new Error("NEXT_PUBLIC_API_URL must not contain credentials.");
  }
  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error("NEXT_PUBLIC_API_URL must use http or https.");
  }
  if (remote) {
    if (parsed.protocol !== "https:") {
      throw new Error("NEXT_PUBLIC_API_URL must use https for remote frontend builds.");
    }
    if (isLocalHostname(parsed.hostname)) {
      throw new Error("NEXT_PUBLIC_API_URL must not point to localhost for remote frontend builds.");
    }
  }
  return parsed.toString().replace(/\/+$/, "");
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  validateApiUrlConfig();
  console.log("NEXT_PUBLIC_API_URL configuration looks safe for this context.");
}
