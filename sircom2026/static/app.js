const messageBox = document.querySelector("#ui-message");
const createLotForm = document.querySelector("#create-lot-form");
const deleteLotButton = document.querySelector("#delete-lot-button");
const retryButtons = document.querySelectorAll("[data-retry-step-key]");
let createLotInFlight = false;
let createLotIdempotencyKey = null;

function showError(title, cause, action) {
  if (!messageBox) return;
  const heading = messageBox.querySelector("[data-error-title]");
  const causeElement = messageBox.querySelector("[data-error-cause]");
  const actionElement = messageBox.querySelector("[data-error-action]");
  if (heading) heading.textContent = title;
  setStructuredLine(causeElement, "Cause :", cause);
  setStructuredLine(actionElement, "Action attendue :", action);
  messageBox.hidden = false;
  messageBox.focus({ preventScroll: false });
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

if (createLotForm) {
  createLotForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (createLotInFlight) return;

    const formData = new FormData(createLotForm);
    const title = String(formData.get("title") || "").trim();
    createLotInFlight = true;
    createLotIdempotencyKey = createLotIdempotencyKey || nextIdempotencyKey();

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

    try {
      const response = await fetch(`/api/lots/${encodeURIComponent(lotId)}`, {
        method: "DELETE",
      });
      await parseJsonResponse(response);
      window.location.assign("/");
    } catch (error) {
      showError(
        "Suppression impossible",
        error.message,
        "Verifier l'etat du lot puis reessayer."
      );
    }
  });
}

retryButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const lotId = button.dataset.retryLotId;
    const stepKey = button.dataset.retryStepKey;
    if (!lotId || !stepKey || button.disabled) return;

    button.disabled = true;
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
      window.location.assign(`/?lot_id=${encodeURIComponent(lotId)}`);
    } catch (error) {
      button.disabled = false;
      showError(
        "Relance impossible",
        error.message,
        "Verifier l'etat du lot puis reessayer."
      );
    }
  });
});
