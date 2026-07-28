// Extraction des photos produit depuis demarche.numerique.gouv.fr
//
// Mode d'emploi :
// 1. Ouvrir Chrome sur demarche.numerique.gouv.fr en étant connecté.
// 2. Coller les numéros de dossier dans SOURCE, un par ligne.
// 3. Coller tout ce script dans la console Chrome, puis Entrer.
// 4. Télécharger les fichiers juste après, car les URLs expirent.

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
const imageAttachmentPattern = /(\.(avif|gif|heic|heif|jpe?g|png|tiff?|webp)\b|\b(AVIF|GIF|HEIC|HEIF|JPE?G|PNG|TIFF?|WEBP)\b)/i;

function isActiveStorageBlobLink(node) {
  if (node.nodeType !== Node.ELEMENT_NODE || !node.matches?.("a[href]")) {
    return false;
  }
  try {
    const path = new URL(node.getAttribute("href"), BASE).pathname;
    return /\/rails\/active_storage\/blobs\//.test(path);
  } catch (_error) {
    return false;
  }
}

function filenameFromUrl(url) {
  const parsed = new URL(url, BASE);
  return decodeURIComponent(parsed.pathname.split("/").pop() || "");
}

function cleanAttachmentFilename(value) {
  return clean(value)
    .replace(/^Télécharger le fichier\s+/i, "")
    .replace(/^Telecharger le fichier\s+/i, "")
    .replace(/\s+(AVIF|GIF|HEIC|HEIF|JPE?G|PNG|TIFF?|WEBP)\s+[–-].*$/i, "");
}

function filenameFromLink(link, downloadUrl) {
  const fromUrl = filenameFromUrl(downloadUrl);
  const fromText = cleanAttachmentFilename(link.textContent);
  return /\.[A-Za-z0-9]{2,6}\b/.test(fromUrl) ? fromUrl : fromText || fromUrl;
}

function isImageAttachment(row) {
  return imageAttachmentPattern.test([
    row.filename,
    row.field_label,
    row.link_text,
    row.download_url
  ].join(" "));
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

function collectAttachments(doc) {
  const attachments = [];
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

    if (isActiveStorageBlobLink(node)) {
      const downloadUrl = new URL(node.getAttribute("href"), BASE).href;
      const linkText = clean(node.textContent);
      attachments.push({
        field_label: attachmentLabelFromContext(node, currentLabel),
        filename: filenameFromLink(node, downloadUrl),
        download_url: downloadUrl,
        link_text: linkText
      });
    }
  }

  return attachments;
}

function productPhotoScore(row) {
  const text = `${row.field_label} ${row.filename} ${row.link_text}`;
  if (/photo/i.test(text) && /(produit|candidat|fond blanc)/i.test(text)) return 0;
  if (/photo/i.test(text)) return 1;
  return 2;
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
    return [{
      dossier_id: dossierId,
      attachment_index: "",
      filename: "",
      field_label: "",
      download_url: "",
      dossier_url: dossierUrl,
      status: `HTTP ${response.status}`
    }];
  }

  const html = await response.text();
  const doc = new DOMParser().parseFromString(html, "text/html");
  const accessError = accessErrorStatus(doc, response);
  if (accessError) {
    return [{
      dossier_id: dossierId,
      attachment_index: "",
      filename: "",
      field_label: "",
      download_url: "",
      dossier_url: dossierUrl,
      status: accessError
    }];
  }

  const selected = collectAttachments(doc)
    .filter(isImageAttachment)
    .sort((left, right) => productPhotoScore(left) - productPhotoScore(right));

  if (!selected.length) {
    return [{
      dossier_id: dossierId,
      attachment_index: "",
      filename: "",
      field_label: "",
      download_url: "",
      dossier_url: dossierUrl,
      status: "pièce photo introuvable"
    }];
  }

  return selected.map((row, photoIndex) => ({
    dossier_id: dossierId,
    attachment_index: photoIndex + 1,
    filename: row.filename,
    field_label: row.field_label,
    download_url: row.download_url,
    dossier_url: dossierUrl,
    status: "ok",
    link_text: row.link_text
  }));
}

void (async () => {
  if (!ids.length) {
    console.error("Aucun numéro de dossier trouvé dans SOURCE.");
    return;
  }

  const rows = [];
  for (let i = 0; i < ids.length; i++) {
    try {
      rows.push(...await extractDossier(ids[i], i, ids.length));
    } catch (error) {
      rows.push({
        dossier_id: ids[i],
        attachment_index: "",
        filename: "",
        field_label: "",
        download_url: "",
        dossier_url: `${BASE}/procedures/${PROCEDURE_ID}/a-suivre/dossiers/${ids[i]}`,
        status: error?.message || String(error)
      });
    }
    await new Promise(resolve => setTimeout(resolve, DELAY_MS));
  }

  const columns = ["dossier_id", "attachment_index", "filename", "field_label", "download_url", "dossier_url", "status", "link_text"];
  const anomalies = rows.filter(row => row.status !== "ok");
  const summary = rows.reduce((acc, row) => {
    acc[row.status] = (acc[row.status] || 0) + 1;
    return acc;
  }, {});

  console.table(rows);
  console.log("Synthèse photos produit", summary);

  downloadFile("photos-produits-dossiers.csv", csvText(rows, columns), "text/csv;charset=utf-8");
  downloadFile("photos-produits-dossiers-anomalies.csv", csvText(anomalies, columns), "text/csv;charset=utf-8");
})();
