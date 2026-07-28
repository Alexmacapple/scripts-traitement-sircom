const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const ELEMENT_NODE = 1;
const TEXT_NODE = 3;

function fakeAttachmentDocument(links) {
  const nodes = [];
  const textParts = [];

  for (const link of links) {
    const label = link.label || "";
    const text = link.text || "";
    const href = new URL(link.href, "https://demarche.numerique.gouv.fr").href;
    const container = {
      innerText: `${label}: ${text}`
    };

    if (label) {
      nodes.push({ nodeType: TEXT_NODE, nodeValue: `${label}:` });
      textParts.push(`${label}:`);
    }
    nodes.push({
      nodeType: ELEMENT_NODE,
      href,
      textContent: text,
      getAttribute: attribute => attribute === "href" ? link.href : null,
      matches: selector => selector === "a[href]",
      closest: () => container
    });
    textParts.push(text);
  }

  return {
    title: "Dossier test",
    body: { innerText: textParts.join("\n") },
    querySelector: () => null,
    createTreeWalker() {
      let index = -1;
      return {
        nextNode() {
          index += 1;
          return nodes[index] || null;
        }
      };
    }
  };
}

async function runExtractor(filename, options = {}) {
  const tables = [];
  const errors = [];
  const source = fs
    .readFileSync(path.join(ROOT, "scripts", filename), "utf8")
    .replace(/const SOURCE = `[\s\S]*?`;/, "const SOURCE = `\n12345678\n`;")
    .replace("const DELAY_MS = 250;", "const DELAY_MS = 0;");

  class FakeDOMParser {
    parseFromString(html) {
      if (options.document) {
        return options.document;
      }
      if (options.documentFactory) {
        return options.documentFactory(html);
      }
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
    Node: { ELEMENT_NODE, TEXT_NODE },
    NodeFilter: { SHOW_ELEMENT: 1, SHOW_TEXT: 4 },
    URL,
    clearTimeout,
    console: {
      error: (...args) => errors.push(args),
      log() {},
      table: value => tables.push(value)
    },
    document,
    fetch: async () => options.response || ({
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

test("l'extracteur photo accepte les liens ActiveStorage proxy", async () => {
  const rows = await runExtractor("extract_product_photos.js", {
    document: fakeAttachmentDocument([{
      label: "Une (seule) photo du produit candidat (sur fond blanc)",
      text: "Télécharger le fichier produit.jpg JPG - 10 ko",
      href: "/rails/active_storage/blobs/proxy/signed/produit.jpg?disposition=attachment"
    }]),
    response: {
      ok: true,
      status: 200,
      url: "https://demarche.numerique.gouv.fr/procedures/140205/a-suivre/dossiers/12345678",
      text: async () => "<html>dossier</html>"
    }
  });

  assert.equal(rows.length, 1);
  assert.equal(rows[0].status, "ok");
  assert.equal(rows[0].filename, "produit.jpg");
  assert.match(rows[0].download_url, /\/rails\/active_storage\/blobs\/proxy\//);
});

test("l'extracteur complet accepte les variantes blob ActiveStorage", async () => {
  const rows = await runExtractor("extract_complete_dossiers.js", {
    document: fakeAttachmentDocument([{
      label: "Documentation commerciale",
      text: "Télécharger le fichier fiche.pdf PDF - 20 ko",
      href: "/rails/active_storage/blobs/proxy/signed/fiche.pdf?disposition=attachment"
    }]),
    response: {
      ok: true,
      status: 200,
      url: "https://demarche.numerique.gouv.fr/procedures/140205/a-suivre/dossiers/12345678",
      text: async () => "<html>dossier</html>"
    }
  });

  assert.equal(rows.length, 1);
  assert.equal(rows[0].status, "ok");
  assert.equal(rows[0].field_label, "Documentation commerciale");
  assert.equal(rows[0].filename, "fiche.pdf");
  assert.match(rows[0].download_url, /\/rails\/active_storage\/blobs\/proxy\//);
});
