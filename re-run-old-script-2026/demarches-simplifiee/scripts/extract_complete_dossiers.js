// Extraction des dossiers complets depuis demarche.numerique.gouv.fr
//
// Ce script produit :
// - dossiers-complets-pieces-jointes.csv : tous les liens de pièces jointes
// - dossiers-complets-textes.json : texte intégral visible de chaque dossier

const SOURCE = `
`;

const PROCEDURE_ID = "140205";
const BASE = "https://demarche.numerique.gouv.fr";
const DELAY_MS = 250;

const ids = [...new Set(SOURCE.split(/\r?\n/).map(line => {
  const urlMatch = line.match(/\/dossiers\/(\d+)/);
  if (urlMatch) return urlMatch[1];
  const idMatch = line.match(/\b\d{6,}\b/);
  return idMatch?.[0];
}).filter(Boolean))];

const clean = value => String(value || "").replace(/\s+/g, " ").trim();

function filenameFromUrl(url) {
  const parsed = new URL(url, BASE);
  return decodeURIComponent(parsed.pathname.split("/").pop() || "");
}

function cleanAttachmentFilename(value) {
  return clean(value)
    .replace(/^Télécharger le fichier\s+/i, "")
    .replace(/^Telecharger le fichier\s+/i, "")
    .replace(/\s+(AVIF|GIF|HEIC|HEIF|JPE?G|PNG|TIFF?|WEBP|PDF)\s+[–-].*$/i, "");
}

function filenameFromLink(link, downloadUrl) {
  const fromUrl = filenameFromUrl(downloadUrl);
  const fromText = cleanAttachmentFilename(link.textContent);
  return /\.[A-Za-z0-9]{2,6}\b/.test(fromUrl) ? fromUrl : fromText || fromUrl;
}

function downloadFile(filename, content, mimeType) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([content], { type: mimeType }));
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function csvText(rows, columns) {
  const quote = value => `"${String(value ?? "").replaceAll('"', '""')}"`;
  return "\uFEFF" + [
    columns.join(";"),
    ...rows.map(row => columns.map(column => quote(row[column])).join(";"))
  ].join("\n");
}

function attachmentLabelFromContext(link, fallbackLabel) {
  if (fallbackLabel) return fallbackLabel;

  const filename = clean(link.textContent) || filenameFromUrl(link.href);
  const container = link.closest("li, tr, dd, .fr-fieldset__element, .champ, .field, section, article, div");
  const text = clean(container?.innerText || "");
  if (!text) return "";

  const beforeFile = text.split(filename)[0] || text;
  const labelMatch = beforeFile.match(/([^:]{3,180})\s*:?\s*$/);
  return clean(labelMatch?.[1] || "");
}

function extractAttachments(doc, dossierId, dossierUrl) {
  const rows = [];
  const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
  let currentLabel = "";
  let node;

  while ((node = walker.nextNode())) {
    if (node.nodeType === Node.TEXT_NODE) {
      const text = clean(node.nodeValue);
      if (
        text.endsWith(":") &&
        !/^Source\s*:/i.test(text) &&
        !/^Sauf mention contraire/i.test(text) &&
        !/^Cliquer pour copier/i.test(text) &&
        !/^Telecharger le fichier/i.test(text) &&
        !/^Télécharger le fichier/i.test(text)
      ) {
        currentLabel = text.replace(/:$/, "");
      }
      continue;
    }

    if (
      node.nodeType === Node.ELEMENT_NODE &&
      node.matches?.('a[href*="/rails/active_storage/blobs/redirect/"]')
    ) {
      const downloadUrl = new URL(node.getAttribute("href"), BASE).href;
      const linkText = clean(node.textContent);
      rows.push({
        dossier_id: dossierId,
        attachment_index: rows.length + 1,
        field_label: attachmentLabelFromContext(node, currentLabel),
        filename: filenameFromLink(node, downloadUrl),
        download_url: downloadUrl,
        dossier_url: dossierUrl,
        status: "ok",
        link_text: linkText
      });
    }
  }

  if (!rows.length) {
    rows.push({
      dossier_id: dossierId,
      attachment_index: "",
      field_label: "",
      filename: "",
      download_url: "",
      dossier_url: dossierUrl,
      status: "aucune pièce jointe"
    });
  }

  return rows;
}

function accessErrorStatus(doc, response) {
  const responsePath = new URL(response.url || BASE, BASE).pathname;
  const visibleText = clean(`${doc.title || ""} ${doc.body?.innerText || ""}`).slice(0, 3000);
  const loginForm = doc.querySelector?.(
    'input[type="password"], form[action*="sign_in"], form[action*="login"]'
  );

  if (
    /\/(users\/sign_in|login|connexion)\b/i.test(responsePath) ||
    loginForm ||
    /\b(se connecter|connectez-vous|connexion à votre compte)\b/i.test(visibleText)
  ) {
    return "session Chrome expirée : reconnecte-toi puis relance l'extraction";
  }
  if (/\b(vous n'avez pas accès|accès non autorisé|accès interdit)\b/i.test(visibleText)) {
    return "accès refusé à ce dossier";
  }
  return "";
}

async function extractDossier(dossierId, index, total) {
  const dossierUrl = `${BASE}/procedures/${PROCEDURE_ID}/a-suivre/dossiers/${dossierId}`;
  console.log(`${index + 1}/${total}`, dossierId);

  const response = await fetch(dossierUrl, {
    credentials: "include",
    headers: { Accept: "text/html" }
  });
  if (!response.ok) {
    return {
      text: {
        dossier_id: dossierId,
        dossier_url: dossierUrl,
        title: "",
        text: "",
        status: `HTTP ${response.status}`
      },
      attachments: [{
        dossier_id: dossierId,
        attachment_index: "",
        field_label: "",
        filename: "",
        download_url: "",
        dossier_url: dossierUrl,
        status: `HTTP ${response.status}`
      }]
    };
  }

  const html = await response.text();
  const doc = new DOMParser().parseFromString(html, "text/html");
  const accessError = accessErrorStatus(doc, response);
  if (accessError) {
    return {
      text: {
        dossier_id: dossierId,
        dossier_url: dossierUrl,
        title: clean(doc.title),
        text: "",
        status: accessError
      },
      attachments: [{
        dossier_id: dossierId,
        attachment_index: "",
        field_label: "",
        filename: "",
        download_url: "",
        dossier_url: dossierUrl,
        status: accessError
      }]
    };
  }

  const title = clean(doc.title);
  const text = clean(doc.body?.innerText || "");

  return {
    text: {
      dossier_id: dossierId,
      dossier_url: dossierUrl,
      title,
      text,
      status: "ok"
    },
    attachments: extractAttachments(doc, dossierId, dossierUrl)
  };
}

void (async () => {
  if (!ids.length) {
    console.error("Aucun numéro de dossier trouvé dans SOURCE.");
    return;
  }

  const textRows = [];
  const attachmentRows = [];

  for (let i = 0; i < ids.length; i++) {
    try {
      const result = await extractDossier(ids[i], i, ids.length);
      textRows.push(result.text);
      attachmentRows.push(...result.attachments);
    } catch (error) {
      const dossierUrl = `${BASE}/procedures/${PROCEDURE_ID}/a-suivre/dossiers/${ids[i]}`;
      textRows.push({
        dossier_id: ids[i],
        dossier_url: dossierUrl,
        title: "",
        text: "",
        status: error?.message || String(error)
      });
      attachmentRows.push({
        dossier_id: ids[i],
        attachment_index: "",
        field_label: "",
        filename: "",
        download_url: "",
        dossier_url: dossierUrl,
        status: error?.message || String(error)
      });
    }

    await new Promise(resolve => setTimeout(resolve, DELAY_MS));
  }

  const attachmentColumns = [
    "dossier_id",
    "attachment_index",
    "field_label",
    "filename",
    "download_url",
    "dossier_url",
    "status",
    "link_text"
  ];

  const summary = attachmentRows.reduce((acc, row) => {
    acc[row.status] = (acc[row.status] || 0) + 1;
    return acc;
  }, {});

  console.table(attachmentRows);
  console.log("Synthèse pièces jointes", summary);

  downloadFile(
    "dossiers-complets-pieces-jointes.csv",
    csvText(attachmentRows, attachmentColumns),
    "text/csv;charset=utf-8"
  );

  downloadFile(
    "dossiers-complets-textes.json",
    JSON.stringify(textRows, null, 2),
    "application/json;charset=utf-8"
  );
})();
