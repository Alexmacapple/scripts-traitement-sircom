const messageBox = document.querySelector("#ui-message");
const createLotForm = document.querySelector("#create-lot-form");
const deleteLotButton = document.querySelector("#delete-lot-button");
const excelUploadForm = document.querySelector("#excel-upload-form");
const imageUploadForm = document.querySelector("#image-upload-form");
const mappingForm = document.querySelector("#mapping-form");
const mappingProfileForm = document.querySelector("#mapping-profile-form");
const applyMappingProfileButtons = document.querySelectorAll("[data-apply-mapping-profile-id]");
const sortDecisionButtons = document.querySelectorAll("[data-sort-decision]");
const csvPreviewValidateButtons = document.querySelectorAll("[data-csv-preview-validate]");
const packageGenerateButtons = document.querySelectorAll("[data-package-generate-lot-id]");
const retryButtons = document.querySelectorAll("[data-retry-step-key]");
const imageResolutionForms = document.querySelectorAll("[data-image-resolution-form]");
const postSubmitFocusKey = "sircom2026.postSubmitFocus";
let createLotInFlight = false;
let createLotIdempotencyKey = null;
let excelUploadInFlight = false;
let imageUploadInFlight = false;
let mappingInFlight = false;
let sortInFlight = false;
let csvPreviewInFlight = false;
let packageInFlight = false;
let imageResolutionInFlight = false;

function showError(title, cause, action) {
  if (!messageBox) return;
  const heading = messageBox.querySelector("[data-error-title]");
  const causeElement = messageBox.querySelector("[data-error-cause]");
  const actionElement = messageBox.querySelector("[data-error-action]");
  if (heading) heading.textContent = title;
  setStructuredLine(causeElement, "Cause :", cause);
  setStructuredLine(actionElement, "Action attendue :", action);
  messageBox.hidden = false;
}

function setStructuredLine(element, label, text) {
  if (!element) return;
  element.replaceChildren();
  const strong = document.createElement("strong");
  strong.textContent = label;
  element.append(strong, ` ${text}`);
}

async function parseJsonResponse(response) {
  const payload = await response.json();
  if (!response.ok) {
    const error = payload.error || {};
    throw new Error(error.message || "Action impossible.");
  }
  return payload;
}

function nextIdempotencyKey() {
  if (window.crypto && window.crypto.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function setButtonBusy(button, busy, busyText) {
  if (!button) return;
  if (!button.dataset.defaultText) {
    button.dataset.defaultText = button.textContent.trim();
  }
  if (busy) {
    button.disabled = true;
    button.setAttribute("aria-disabled", "true");
    button.setAttribute("aria-busy", "true");
    if (busyText) {
      button.textContent = busyText;
    }
    return;
  }
  button.disabled = false;
  button.removeAttribute("aria-disabled");
  button.removeAttribute("aria-busy");
  button.textContent = button.dataset.defaultText;
}

function confirmLotDeletion(button) {
  const lotTitle = (button.dataset.lotTitle || "").trim();
  const heading = lotTitle ? `Supprimer le lot "${lotTitle}" ?` : "Supprimer ce lot ?";
  return window.confirm(
    `${heading}\n\nCette action retire le lot de la liste. Vous pouvez annuler maintenant.`
  );
}

function getSessionStorage() {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function rememberPostSubmitFocus(targetId, fallbackId) {
  const storage = getSessionStorage();
  if (!targetId || !storage) return;
  try {
    storage.setItem(
      postSubmitFocusKey,
      JSON.stringify({ targetId, fallbackId: fallbackId || "", scrollY: window.scrollY || 0 })
    );
  } catch {
    // Session storage is optional; upload still succeeds without focus restoration.
  }
}

function rememberActionFocus(element, fallbackId) {
  if (!element && !fallbackId) return;
  if (element && !element.id) {
    element.id = `sircom-action-${nextIdempotencyKey()}`;
  }
  rememberPostSubmitFocus(element ? element.id : fallbackId, fallbackId);
}

function currentViewKey() {
  const params = new URLSearchParams(window.location.search);
  return params.get("view") || "";
}

function lotUrl(lotId, options = {}) {
  const params = new URLSearchParams();
  params.set("lot_id", lotId);
  const view = options.view || currentViewKey();
  if (view) {
    params.set("view", view);
  }
  if (options.uploaded) {
    params.set("uploaded", options.uploaded);
  }
  return `/?${params.toString()}`;
}

function restorePostSubmitFocus() {
  const storage = getSessionStorage();
  if (!storage) return;
  let payload = null;
  try {
    payload = JSON.parse(storage.getItem(postSubmitFocusKey) || "null");
    storage.removeItem(postSubmitFocusKey);
  } catch {
    storage.removeItem(postSubmitFocusKey);
    return;
  }
  if (!payload || !payload.targetId) return;

  window.requestAnimationFrame(() => {
    if (Number.isFinite(payload.scrollY)) {
      window.scrollTo(0, payload.scrollY);
    }
    const target = document.getElementById(payload.targetId) ||
      (payload.fallbackId ? document.getElementById(payload.fallbackId) : null);
    if (target) {
      target.focus({ preventScroll: true });
    }
  });
}

function formatFileSize(size) {
  if (!Number.isFinite(size) || size <= 0) return "";
  if (size < 1024 * 1024) {
    return `${Math.round(size / 1024)} Ko`;
  }
  return `${(size / 1024 / 1024).toFixed(1)} Mo`;
}

function initializeUploadSelection(form, options) {
  if (!form) return;
  const fileInput = form.querySelector(options.inputSelector);
  const submitButton = form.querySelector(options.buttonSelector);
  const selectedMessage = form.querySelector(options.messageSelector);
  if (!fileInput || !submitButton || !selectedMessage) return;

  const updateSelectedFile = () => {
    const file = fileInput.files && fileInput.files.length ? fileInput.files[0] : null;
    submitButton.dataset.uploadReady = file ? "true" : "false";
    submitButton.removeAttribute("aria-disabled");
    if (!file) {
      selectedMessage.textContent = "Aucun fichier sélectionné.";
      return;
    }
    const size = formatFileSize(file.size);
    selectedMessage.textContent = [
      `Fichier sélectionné : ${file.name}.`,
      size ? `Taille : ${size}.` : "",
      `Cliquer sur « ${submitButton.textContent.trim()} » pour lancer l'upload.`,
    ]
      .filter(Boolean)
      .join(" ");
  };

  fileInput.addEventListener("change", updateSelectedFile);
  updateSelectedFile();
}

restorePostSubmitFocus();

initializeUploadSelection(excelUploadForm, {
  inputSelector: "#excel-file",
  buttonSelector: '[data-upload-submit="excel"]',
  messageSelector: '[data-file-selected-message="excel"]',
});
initializeUploadSelection(imageUploadForm, {
  inputSelector: "#image-zip-file",
  buttonSelector: '[data-upload-submit="images"]',
  messageSelector: '[data-file-selected-message="images"]',
});

if (createLotForm) {
  createLotForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (createLotInFlight) return;

    const submitButton = event.submitter || createLotForm.querySelector('button[type="submit"]');
    const formData = new FormData(createLotForm);
    const title = String(formData.get("title") || "").trim();
    createLotInFlight = true;
    createLotIdempotencyKey = createLotIdempotencyKey || nextIdempotencyKey();
    setButtonBusy(submitButton, true, "Création en cours");

    try {
      const response = await fetch("/api/lots", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Idempotency-Key": createLotIdempotencyKey,
        },
        body: JSON.stringify({ title: title || null }),
      });
      const payload = await parseJsonResponse(response);
      window.location.assign(`/?lot_id=${encodeURIComponent(payload.lot.id)}`);
    } catch (error) {
      createLotInFlight = false;
      createLotIdempotencyKey = null;
      setButtonBusy(submitButton, false);
      showError(
        "Creation impossible",
        error.message,
        "Verifier le formulaire puis reessayer."
      );
    }
  });
}

if (deleteLotButton) {
  deleteLotButton.addEventListener("click", async () => {
    const lotId = deleteLotButton.dataset.lotId;
    if (!lotId) return;
    if (!confirmLotDeletion(deleteLotButton)) return;

    setButtonBusy(deleteLotButton, true, "Suppression en cours");
    try {
      const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}`, {
        method: "DELETE",
      });
      await parseJsonResponse(response);
      window.location.assign("/");
    } catch (error) {
      setButtonBusy(deleteLotButton, false);
      showError(
        "Suppression impossible",
        error.message,
        "Verifier l'etat du lot puis reessayer."
      );
    }
  });
}

if (excelUploadForm) {
  excelUploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (excelUploadInFlight) return;

    const submitButton = event.submitter || excelUploadForm.querySelector('button[type="submit"]');
    const lotId = excelUploadForm.dataset.excelUploadLotId;
    const fileInput = excelUploadForm.querySelector("#excel-file");
    const file = fileInput && fileInput.files ? fileInput.files[0] : null;
    if (!lotId || !file) {
      showError(
        "Dépôt impossible",
        "Aucun fichier Excel n'a été sélectionné.",
        "Sélectionner un fichier .xlsx ou .xlsm, puis réessayer."
      );
      return;
    }

    excelUploadInFlight = true;
    setButtonBusy(submitButton, true, "Dépôt en cours");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/excel`, {
        method: "POST",
        headers: {
          "X-Idempotency-Key": nextIdempotencyKey(),
        },
        body: formData,
      });
      await parseJsonResponse(response);
      rememberActionFocus(submitButton, "excel-upload-feedback");
      window.location.assign(lotUrl(lotId, { view: "upload_excel", uploaded: "excel" }));
    } catch (error) {
      excelUploadInFlight = false;
      setButtonBusy(submitButton, false);
      showError(
        "Dépôt impossible",
        error.message,
        "Vérifier le fichier Excel puis réessayer."
      );
    }
  });
}

if (imageUploadForm) {
  imageUploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (imageUploadInFlight) return;

    const submitButton = event.submitter || imageUploadForm.querySelector('button[type="submit"]');
    const lotId = imageUploadForm.dataset.imageUploadLotId;
    const fileInput = imageUploadForm.querySelector("#image-zip-file");
    const file = fileInput && fileInput.files ? fileInput.files[0] : null;
    if (!lotId || !file) {
      showError(
        "Dépôt impossible",
        "Aucun zip images n'a été sélectionné.",
        "Sélectionner un fichier .zip, puis réessayer."
      );
      return;
    }

    imageUploadInFlight = true;
    setButtonBusy(submitButton, true, "Dépôt en cours");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/images`, {
        method: "POST",
        headers: {
          "X-Idempotency-Key": nextIdempotencyKey(),
        },
        body: formData,
      });
      await parseJsonResponse(response);
      rememberActionFocus(submitButton, "image-upload-feedback");
      window.location.assign(lotUrl(lotId, { view: "upload_images", uploaded: "images" }));
    } catch (error) {
      imageUploadInFlight = false;
      setButtonBusy(submitButton, false);
      showError(
        "Dépôt zip impossible",
        error.message,
        "Vérifier le zip images puis réessayer."
      );
    }
  });
}

function collectMappingSubmission() {
  if (!mappingForm) return null;
  const structuralFingerprint = mappingForm.dataset.mappingStructuralFingerprint || "";
  const columns = Array.from(mappingForm.querySelectorAll("[data-mapping-column]")).map(
    (row) => {
      const exported = row.querySelector("[data-mapping-exported]");
      const csvName = row.querySelector("[data-mapping-csv-name]");
      const role = row.querySelector("[data-mapping-role]");
      return {
        id: row.dataset.columnId || "",
        status: exported && exported.checked ? "exporte" : "supprime",
        csv_name: csvName ? csvName.value : "",
        logical_role: role ? role.value : "texte",
        suppression_reason: exported && exported.checked ? null : "Supprimée dans le mapping.",
      };
    }
  );
  return {
    structural_fingerprint: structuralFingerprint,
    columns,
  };
}

async function submitMapping(action, button) {
  if (!mappingForm || mappingInFlight) return;
  const lotId = mappingForm.dataset.mappingLotId;
  const submission = collectMappingSubmission();
  if (!lotId || !submission) return;

  mappingInFlight = true;
  setButtonBusy(
    button,
    true,
    action === "draft" ? "Sauvegarde en cours" : "Validation en cours"
  );
  const path = action === "draft" ? "draft" : "validate";
  try {
    const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/mapping/${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Idempotency-Key": nextIdempotencyKey(),
      },
      body: JSON.stringify(submission),
    });
    await parseJsonResponse(response);
    rememberActionFocus(button, "mapping-step-title");
    window.location.assign(lotUrl(lotId, { view: "mapping" }));
  } catch (error) {
    mappingInFlight = false;
    setButtonBusy(button, false);
    showError(
      action === "draft" ? "Brouillon impossible" : "Validation impossible",
      error.message,
      "Corriger le mapping puis réessayer."
    );
  }
}

if (mappingForm) {
  mappingForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const submitButton = event.submitter || mappingForm.querySelector('[data-mapping-action="validate"]');
    submitMapping("validate", submitButton);
  });

  const draftButton = mappingForm.querySelector('[data-mapping-action="draft"]');
  if (draftButton) {
    draftButton.addEventListener("click", () => {
      submitMapping("draft", draftButton);
    });
  }
}

if (mappingProfileForm) {
  mappingProfileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitButton = event.submitter || mappingProfileForm.querySelector('button[type="submit"]');
    const lotId = mappingProfileForm.dataset.mappingProfileLotId;
    if (!lotId) return;
    const formData = new FormData(mappingProfileForm);
    const name = String(formData.get("name") || "").trim();

    setButtonBusy(submitButton, true, "Sauvegarde en cours");
    try {
      const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/mapping/profile`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: name || null }),
      });
      await parseJsonResponse(response);
      rememberActionFocus(submitButton, "mapping-profile-name");
      window.location.assign(lotUrl(lotId, { view: "mapping" }));
    } catch (error) {
      setButtonBusy(submitButton, false);
      showError(
        "Profil impossible",
        error.message,
        "Vérifier qu'un mapping validé existe puis réessayer."
      );
    }
  });
}

applyMappingProfileButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const lotId = button.dataset.applyMappingLotId;
    const profileId = button.dataset.applyMappingProfileId;
    if (!lotId || !profileId || mappingInFlight) return;

    mappingInFlight = true;
    setButtonBusy(button, true, "Chargement en cours");
    try {
      const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/mapping/profile-draft`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Idempotency-Key": nextIdempotencyKey(),
        },
        body: JSON.stringify({ profile_id: profileId }),
      });
      await parseJsonResponse(response);
      rememberActionFocus(button, "mapping-step-title");
      window.location.assign(lotUrl(lotId, { view: "mapping" }));
    } catch (error) {
      mappingInFlight = false;
      setButtonBusy(button, false);
      showError(
        "Profil impossible",
        error.message,
        "Choisir un profil compatible avec l'Excel courant."
      );
    }
  });
});

sortDecisionButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const lotId = button.dataset.sortLotId;
    const decision = button.dataset.sortDecision;
    if (!lotId || !decision || sortInFlight) return;

    sortInFlight = true;
    setButtonBusy(button, true, "Décision en cours");
    try {
      const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/tri/validate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Idempotency-Key": nextIdempotencyKey(),
        },
        body: JSON.stringify({ decision }),
      });
      await parseJsonResponse(response);
      rememberActionFocus(button, "sort-title");
      window.location.assign(lotUrl(lotId, { view: "tri_region_departement" }));
    } catch (error) {
      sortInFlight = false;
      setButtonBusy(button, false);
      showError(
        "Tri impossible",
        error.message,
        "Vérifier les rôles région et département puis réessayer."
      );
    }
  });
});

csvPreviewValidateButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const lotId = button.dataset.csvPreviewLotId;
    if (!lotId || csvPreviewInFlight) return;

    csvPreviewInFlight = true;
    setButtonBusy(button, true, "Validation en cours");
    try {
      const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/csv/preview/validate`, {
        method: "POST",
        headers: {
          "X-Idempotency-Key": nextIdempotencyKey(),
        },
      });
      await parseJsonResponse(response);
      rememberActionFocus(button, "csv-preview-title");
      window.location.assign(lotUrl(lotId, { view: "previsualisation_csv" }));
    } catch (error) {
      csvPreviewInFlight = false;
      setButtonBusy(button, false);
      showError(
        "Validation CSV impossible",
        error.message,
        "Vérifier l'aperçu et les problèmes ouverts puis réessayer."
      );
    }
  });
});

imageResolutionForms.forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (imageResolutionInFlight) return;

    const submitButton = event.submitter || form.querySelector('button[type="submit"]');
    const lotId = form.dataset.imageResolutionLotId;
    const idDossier = form.dataset.imageResolutionIdDossier;
    const sourceSelect = form.querySelector('select[name="source_name"]');
    const sourceName = sourceSelect ? sourceSelect.value : "";
    if (!lotId || !idDossier || !sourceName) return;

    imageResolutionInFlight = true;
    setButtonBusy(submitButton, true, "Validation en cours");
    try {
      const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/images/resolutions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Idempotency-Key": nextIdempotencyKey(),
        },
        body: JSON.stringify({
          resolutions: [{ id_dossier: idDossier, source_name: sourceName }],
        }),
      });
      await parseJsonResponse(response);
      rememberActionFocus(submitButton, "image-matching-title");
      window.location.assign(lotUrl(lotId, { view: "matching_images" }));
    } catch (error) {
      imageResolutionInFlight = false;
      setButtonBusy(submitButton, false);
      showError(
        "Résolution image impossible",
        error.message,
        "Choisir une image source proposée puis réessayer."
      );
    }
  });
});

packageGenerateButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const lotId = button.dataset.packageGenerateLotId;
    const acceptWarnings = button.dataset.packageAcceptWarnings === "true";
    if (!lotId || packageInFlight) return;

    packageInFlight = true;
    setButtonBusy(button, true, "Génération en cours");
    try {
      const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/package`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Idempotency-Key": nextIdempotencyKey(),
        },
        body: JSON.stringify({ accept_warnings: acceptWarnings }),
      });
      await parseJsonResponse(response);
      rememberActionFocus(button, "package-title");
      window.location.assign(lotUrl(lotId, { view: "package_final" }));
    } catch (error) {
      packageInFlight = false;
      setButtonBusy(button, false);
      showError(
        "Package impossible",
        error.message,
        "Vérifier les problèmes ouverts puis réessayer."
      );
    }
  });
});

retryButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const lotId = button.dataset.retryLotId;
    const stepKey = button.dataset.retryStepKey;
    if (!lotId || !stepKey || button.disabled) return;

    setButtonBusy(button, true, "Relance en cours");
    try {
      const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}/retry`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Idempotency-Key": nextIdempotencyKey(),
        },
        body: JSON.stringify({ step_key: stepKey }),
      });
      await parseJsonResponse(response);
      rememberActionFocus(button, "timeline-title");
      window.location.assign(lotUrl(lotId, { view: stepKey }));
    } catch (error) {
      setButtonBusy(button, false);
      showError(
        "Relance impossible",
        error.message,
        "Verifier l'etat du lot puis reessayer."
      );
    }
  });
});
