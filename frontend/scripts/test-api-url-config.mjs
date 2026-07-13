import assert from "node:assert/strict";
import { validateApiUrlConfig } from "./check-api-url-config.mjs";

assert.equal(validateApiUrlConfig({ value: "", context: "development" }), "http://127.0.0.1:8000");
assert.equal(validateApiUrlConfig({ value: "https://api.example.com/", context: "production" }), "https://api.example.com");
assert.throws(() => validateApiUrlConfig({ value: "", context: "production" }), /required/);
assert.throws(() => validateApiUrlConfig({ value: "", context: "preview" }), /required/);
assert.throws(() => validateApiUrlConfig({ value: "http://127.0.0.1:8000", context: "production" }), /https/);
assert.throws(() => validateApiUrlConfig({ value: "https://localhost:8000", context: "production" }), /localhost/);
assert.throws(() => validateApiUrlConfig({ value: "not-a-url", context: "development" }), /valid URL/);
assert.throws(() => validateApiUrlConfig({ value: "https://user:pass@api.example.com", context: "production" }), /credentials/);

console.log("API URL config checks passed.");
