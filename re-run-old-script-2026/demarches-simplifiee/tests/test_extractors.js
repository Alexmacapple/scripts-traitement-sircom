const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");

async function runExtractor(filename) {
  const tables = [];
  const errors = [];
  const source = fs
    .readFileSync(path.join(ROOT, "scripts", filename), "utf8")
    .replace(/const SOURCE = `[\s\S]*?`;/, "const SOURCE = `\n12345678\n`;")
    .replace("const DELAY_MS = 250;", "const DELAY_MS = 0;");

  class FakeDOMParser {
    parseFromString() {
      return {
        title: "Connexion",
        body: { innerText: "Se connecter à votre compte" },
        querySelector: selector => selector.includes("password") ? {} : null
      };
    }
  }

  const document = {
    body: { appendChild() {} },
    createElement() {
      return {
        click() {},
        remove() {}
      };
    }
  };
  const context = vm.createContext({
    Blob,
    DOMParser: FakeDOMParser,
    NodeFilter: { SHOW_ELEMENT: 1, SHOW_TEXT: 4 },
    URL,
    clearTimeout,
    console: {
      error: (...args) => errors.push(args),
      log() {},
      table: value => tables.push(value)
    },
    document,
    fetch: async () => ({
      ok: true,
      redirected: true,
      status: 200,
      url: "https://demarche.numerique.gouv.fr/users/sign_in",
      text: async () => "<html>login</html>"
    }),
    setTimeout
  });

  vm.runInContext(source, context, { filename });
  await new Promise(resolve => setTimeout(resolve, 30));
  assert.deepEqual(errors, []);
  assert.equal(tables.length, 1);
  return tables[0];
}

test("l'extracteur photo signale une session expirée", async () => {
  const rows = await runExtractor("extract_product_photos.js");
  assert.equal(rows.length, 1);
  assert.match(rows[0].status, /session Chrome expirée/);
  assert.equal(rows[0].download_url, "");
});

test("l'extracteur complet signale une session expirée", async () => {
  const rows = await runExtractor("extract_complete_dossiers.js");
  assert.equal(rows.length, 1);
  assert.match(rows[0].status, /session Chrome expirée/);
  assert.equal(rows[0].download_url, "");
});
