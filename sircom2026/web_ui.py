from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

from sircom2026.mapping import MappingError
from sircom2026.purge import format_bytes
from sircom2026.web_constants import (
    CSV_WORKFLOW_STEP_KEYS,
    IMAGE_BINDING_STATUS_LABELS,
    IMAGE_MATCH_LEVEL_LABELS,
    IMAGE_WORKFLOW_STEP_KEYS,
    SORT_DECISION_LABELS,
    SORT_DETECTION_STATUS_LABELS,
    STEP_NAV_ANCHORS,
    STEP_VIEW_DESCRIPTIONS,
    STEP_VIEW_GUIDANCE,
    UI_DONE_STEP_STATUSES,
    UI_IDLE_STEP_STATUSES,
    UI_PENDING_STEP_STATUSES,
    UI_STEP_STATUS_PRESENTATION,
    UX_PHASE_DEFINITIONS,
    WORKFLOW_SCREEN_BY_KEY,
    WORKFLOW_SCREEN_BY_STEP_KEY,
    WORKFLOW_SCREEN_DEFINITIONS,
)


def lot_ui_summary(
    lot: dict[str, Any],
    *,
    active_view_key: str | None = None,
    active_screen_key: str | None = None,
) -> dict[str, Any]:
    steps = list(lot.get("steps") or [])
    total = len(steps)
    if not steps:
        return {
            "breadcrumb_label": "Lot",
            "completed": False,
            "current_step": None,
            "current_step_number": 0,
            "current_phase": None,
            "current_phase_number": 0,
            "active_phase": None,
            "active_screen": None,
            "active_step": None,
            "active_view_key": None,
            "csv_workflow_steps": [],
            "image_workflow_steps": [],
            "next_step": None,
            "next_phase": None,
            "previous_view_step": None,
            "next_view_step": None,
            "phase_total": 0,
            "phase_navigation": [],
            "screen_step_navigation": [],
            "screen_steps_total": 0,
            "step_navigation": [],
            "steps_total": 0,
            "workflow_screens": [],
        }

    completed = all(step["status"] in UI_DONE_STEP_STATUSES for step in steps)
    current_index = (
        total - 1
        if completed
        else next(
            (
                index
                for index, step in enumerate(steps)
                if step["status"] not in UI_DONE_STEP_STATUSES
            ),
            total - 1,
        )
    )
    step_navigation = [
        step_navigation_item(
            step,
            index=index,
            current_index=current_index,
            completed=completed,
        )
        for index, step in enumerate(steps)
    ]
    current_step = None if completed else steps[current_index]
    current_step_key = current_step["key"] if current_step else None
    phase_navigation = build_phase_navigation(
        step_navigation,
        current_step_key=current_step_key,
    )
    current_phase = next(
        (phase for phase in phase_navigation if phase["is_current"]),
        None,
    )
    current_phase_number = (
        len(phase_navigation)
        if completed
        else current_phase["number"]
        if current_phase
        else 0
    )
    active_step = selected_active_step(
        step_navigation,
        active_view_key=active_view_key,
        active_screen_key=active_screen_key,
        current_step=step_navigation[current_index],
    )
    active_view_key = active_step["key"] if active_step else None
    active_screen_key = (
        screen_key_for_step(active_view_key) or active_screen_key or "excel"
    )
    step_navigation = enrich_step_navigation(
        step_navigation,
        lot_id=lot["id"],
        active_view_key=active_view_key,
    )
    screen_step_navigation = screen_steps_for_screen(
        step_navigation,
        active_screen_key=active_screen_key,
    )
    active_step = next(
        (step for step in step_navigation if step["is_active_view"]),
        active_step,
    )
    active_step = apply_screen_step_number(
        active_step,
        screen_step_navigation=screen_step_navigation,
    )
    previous_view_step, next_view_step = adjacent_view_steps(
        screen_step_navigation,
        active_view_key=active_view_key,
    )
    active_screen = workflow_screen_summary(
        active_screen_key,
        screen_step_navigation=screen_step_navigation,
    )
    workflow_screens = workflow_screen_navigation(
        step_navigation,
        lot_id=lot["id"],
        active_screen_key=active_screen_key,
    )
    next_phase = (
        None
        if completed
        or not current_phase_number
        or current_phase_number >= len(phase_navigation)
        else phase_navigation[current_phase_number]
    )
    csv_workflow_steps = [
        step for step in step_navigation if step["key"] in CSV_WORKFLOW_STEP_KEYS
    ]
    image_workflow_steps = [
        step for step in step_navigation if step["key"] in IMAGE_WORKFLOW_STEP_KEYS
    ]
    return {
        "breadcrumb_label": (
            active_step["label"]
            if active_step
            else "Traitement terminé"
            if completed
            else current_step["label"]
        ),
        "completed": completed,
        "current_step": current_step,
        "current_step_number": current_index + 1,
        "current_phase": current_phase,
        "current_phase_number": current_phase_number,
        "active_step": active_step,
        "active_phase": current_phase,
        "active_screen": active_screen,
        "active_view_key": active_view_key,
        "csv_workflow_started": workflow_started(csv_workflow_steps),
        "csv_workflow_steps": csv_workflow_steps,
        "image_workflow_started": workflow_started(image_workflow_steps),
        "image_workflow_steps": image_workflow_steps,
        "next_step": (
            None
            if completed or current_index + 1 >= total
            else steps[current_index + 1]
        ),
        "next_phase": next_phase,
        "previous_view_step": previous_view_step,
        "next_view_step": next_view_step,
        "phase_total": len(phase_navigation),
        "phase_navigation": phase_navigation,
        "primary_action": lot_primary_action(
            lot,
            current_step=current_step,
            current_phase=current_phase,
            completed=completed,
        ),
        "screen_step_navigation": screen_step_navigation,
        "screen_steps_total": len(screen_step_navigation),
        "step_navigation": step_navigation,
        "steps_total": total,
        "workflow_screens": workflow_screens,
    }


def selected_active_step(
    step_navigation: list[dict[str, Any]],
    *,
    active_view_key: str | None,
    active_screen_key: str | None,
    current_step: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if active_view_key:
        requested = next(
            (step for step in step_navigation if step["key"] == active_view_key),
            None,
        )
        if requested:
            return requested
    if active_screen_key:
        screen_steps = screen_steps_for_screen(
            step_navigation,
            active_screen_key=active_screen_key,
        )
        if current_step and current_step["key"] in screen_step_keys(active_screen_key):
            return current_step
        return first_open_step(screen_steps) or (
            screen_steps[-1] if screen_steps else None
        )
    if current_step:
        return current_step
    return step_navigation[0] if step_navigation else None


def screen_key_for_step(step_key: str | None) -> str | None:
    if step_key is None:
        return None
    return WORKFLOW_SCREEN_BY_STEP_KEY.get(step_key)


def screen_step_keys(screen_key: str | None) -> tuple[str, ...]:
    if screen_key is None:
        return ()
    screen = WORKFLOW_SCREEN_BY_KEY.get(screen_key)
    if not screen:
        return ()
    return tuple(str(step_key) for step_key in screen["step_keys"])


def screen_steps_for_screen(
    step_navigation: list[dict[str, Any]],
    *,
    active_screen_key: str | None,
) -> list[dict[str, Any]]:
    step_keys = screen_step_keys(active_screen_key)
    if not step_keys:
        return []
    screen_steps = [step for step in step_navigation if step["key"] in step_keys]
    return [
        {
            **step,
            "screen_number": index,
        }
        for index, step in enumerate(screen_steps, start=1)
    ]


def first_open_step(steps: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next(
        (step for step in steps if step["status"] not in UI_DONE_STEP_STATUSES),
        None,
    )


def apply_screen_step_number(
    active_step: dict[str, Any] | None,
    *,
    screen_step_navigation: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if active_step is None:
        return None
    screen_step = next(
        (step for step in screen_step_navigation if step["key"] == active_step["key"]),
        None,
    )
    if screen_step is None:
        return active_step
    return {**active_step, "screen_number": screen_step["screen_number"]}


def workflow_screen_summary(
    active_screen_key: str | None,
    *,
    screen_step_navigation: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if active_screen_key is None:
        return None
    definition = WORKFLOW_SCREEN_BY_KEY.get(active_screen_key)
    if not definition:
        return None
    status = phase_status(screen_step_navigation)
    return {
        "key": active_screen_key,
        "label": definition["label"],
        "lead": definition["lead"],
        "steps_count": len(screen_step_navigation),
        **status,
    }


def workflow_screen_navigation(
    step_navigation: list[dict[str, Any]],
    *,
    lot_id: str,
    active_screen_key: str | None,
) -> list[dict[str, Any]]:
    navigation: list[dict[str, Any]] = []
    for definition in WORKFLOW_SCREEN_DEFINITIONS:
        screen_key = str(definition["key"])
        screen_steps = screen_steps_for_screen(
            step_navigation,
            active_screen_key=screen_key,
        )
        target_step = first_open_step(screen_steps) or (
            screen_steps[-1] if screen_steps else None
        )
        status = phase_status(screen_steps)
        navigation.append(
            {
                "key": screen_key,
                "label": definition["label"],
                "lead": definition["lead"],
                "href": lot_screen_href(
                    lot_id,
                    screen_key,
                    target_step["key"] if target_step else None,
                    "lot-workspace-title",
                ),
                "is_active": screen_key == active_screen_key,
                **status,
            }
        )
    return navigation


def enrich_step_navigation(
    step_navigation: list[dict[str, Any]],
    *,
    lot_id: str,
    active_view_key: str | None,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for step in step_navigation:
        view_key = step["key"]
        enriched.append(
            {
                **step,
                "href": step_href(lot_id, view_key),
                "is_active_view": view_key == active_view_key,
            }
        )
    return enriched


def adjacent_view_steps(
    step_navigation: list[dict[str, Any]],
    *,
    active_view_key: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not active_view_key:
        return None, None
    active_index = next(
        (
            index
            for index, step in enumerate(step_navigation)
            if step["key"] == active_view_key
        ),
        None,
    )
    if active_index is None:
        return None, None
    previous_step = step_navigation[active_index - 1] if active_index > 0 else None
    next_step = (
        step_navigation[active_index + 1]
        if active_index + 1 < len(step_navigation)
        else None
    )
    return previous_step, next_step


def step_navigation_item(
    step: dict[str, Any],
    *,
    index: int,
    current_index: int,
    completed: bool,
) -> dict[str, Any]:
    is_current = not completed and index == current_index
    is_done = step["status"] in UI_DONE_STEP_STATUSES
    is_future = not completed and index > current_index
    presentation = step_status_presentation(
        step["status"],
        is_current=is_current,
        is_future=is_future,
    )
    return {
        **step,
        "anchor": STEP_NAV_ANCHORS.get(step["key"], "timeline-title"),
        "is_current": is_current,
        "is_done": is_done,
        "is_future": is_future,
        "number": index + 1,
        "ui_description": STEP_VIEW_DESCRIPTIONS.get(
            step["key"],
            "Suivre cette étape du traitement.",
        ),
        "ui_guidance": STEP_VIEW_GUIDANCE.get(
            step["key"],
            {
                "user_action": "Suivre l'état de cette étape.",
                "system_action": "L'application orchestre le traitement prévu.",
                "result": "Le lot avance vers l'étape suivante.",
            },
        ),
        **presentation,
    }


def step_status_presentation(
    status: str,
    *,
    is_current: bool,
    is_future: bool,
) -> dict[str, str]:
    if status == "invalide" and is_future:
        return {"ui_status_label": "À venir", "ui_badge_class": "info"}
    if status == "invalide" and not is_current:
        return {"ui_status_label": "À venir", "ui_badge_class": "info"}
    return UI_STEP_STATUS_PRESENTATION.get(
        status,
        {"ui_status_label": status, "ui_badge_class": "info"},
    )


def workflow_started(steps: list[dict[str, Any]]) -> bool:
    return any(step["status"] not in UI_IDLE_STEP_STATUSES for step in steps)


def build_phase_navigation(
    steps: list[dict[str, Any]],
    *,
    current_step_key: str | None,
) -> list[dict[str, Any]]:
    steps_by_key = {step["key"]: step for step in steps}
    phases: list[dict[str, Any]] = []
    for index, definition in enumerate(UX_PHASE_DEFINITIONS, start=1):
        phase_steps = [
            steps_by_key[step_key]
            for step_key in definition["step_keys"]
            if step_key in steps_by_key
        ]
        status = phase_status(phase_steps)
        is_current = current_step_key in definition["step_keys"]
        if is_current and status["status_label"] == "À venir":
            status = {"status_label": "À faire maintenant", "badge_class": "info"}
        phases.append(
            {
                "number": index,
                "key": definition["key"],
                "label": definition["label"],
                "anchor": definition["anchor"],
                "description": definition["description"],
                "is_current": is_current,
                **status,
            }
        )
    return phases


def lot_primary_action(
    lot: dict[str, Any],
    *,
    current_step: dict[str, Any] | None,
    current_phase: dict[str, Any] | None,
    completed: bool,
) -> dict[str, str] | None:
    lot_id = lot["id"]
    if completed:
        return action_link(
            "Télécharger ou vérifier les livrables",
            lot_view_href(lot_id, "package_final", "package-title"),
            "fr-icon-download-line",
            "Les livrables disponibles sont dans la dernière section.",
        )
    if current_step is None:
        return None

    key = current_step["key"]
    status = current_step["status"]
    phase_label = current_phase["label"] if current_phase else current_step["label"]

    if status in UI_PENDING_STEP_STATUSES:
        return action_link(
            f"Actualiser l'état : {phase_label}",
            lot_view_href(
                lot_id,
                view_key_for_step(key),
                STEP_NAV_ANCHORS.get(key, "lot-detail-title"),
            ),
            "fr-icon-refresh-line",
            "Le traitement local tourne en arrière-plan ; l'actualisation montre le dernier état connu.",
        )
    if status in {"bloque", "echoue"} and key in {"diagnostic_excel", "upload_excel"}:
        return action_link(
            "Ouvrir le dépôt Excel",
            lot_sources_href(lot_id, "excel-file"),
            "fr-icon-upload-line",
            "Corriger le fichier puis redéposer l'Excel source.",
        )
    if status in {"bloque", "echoue"}:
        return action_link(
            "Voir les problèmes à corriger",
            lot_view_href(lot_id, key, "lot-problems-title"),
            "fr-icon-error-line",
            "Corriger la cause indiquée avant de continuer.",
        )
    if key == "upload_excel":
        return action_link(
            "Ouvrir le dépôt Excel source",
            lot_sources_href(lot_id, "excel-file"),
            "fr-icon-upload-line",
            "Le diagnostic Excel démarre après le dépôt.",
        )
    if key == "mapping":
        return action_link(
            "Ouvrir le mapping",
            lot_view_href(lot_id, "mapping", "mapping-step-title"),
            "fr-icon-arrow-right-line",
            "Choisir les colonnes exportées puis valider.",
        )
    if key == "tri_region_departement":
        return action_link(
            "Ouvrir le tri région/département",
            lot_view_href(lot_id, "tri_region_departement", "sort-title"),
            "fr-icon-arrow-right-line",
            "Valider l'ordre des lignes avant l'aperçu CSV.",
        )
    if key == "previsualisation_csv":
        return action_link(
            "Ouvrir l'aperçu CSV",
            lot_view_href(lot_id, "previsualisation_csv", "csv-preview-title"),
            "fr-icon-arrow-right-line",
            "Vérifier l'aperçu avant de produire les livrables.",
        )
    if key == "upload_images":
        return action_link(
            "Ouvrir le dépôt du zip images",
            lot_sources_href(lot_id, "image-zip-file"),
            "fr-icon-upload-line",
            "Le traitement images démarre après le dépôt du zip.",
        )
    if key == "matching_images":
        return action_link(
            "Ouvrir les associations images",
            lot_view_href(lot_id, "matching_images", "image-matching-title"),
            "fr-icon-arrow-right-line",
            "Résoudre les ambiguïtés si l'application en détecte.",
        )
    if key == "package_final":
        return action_link(
            "Ouvrir le package final",
            lot_view_href(lot_id, "package_final", "package-title"),
            "fr-icon-arrow-right-line",
            "Assembler le CSV, les images et les rapports dans un zip final.",
        )
    return action_link(
        f"Continuer vers : {phase_label}",
        lot_view_href(
            lot_id,
            view_key_for_step(key),
            STEP_NAV_ANCHORS.get(key, "lot-detail-title"),
        ),
        "fr-icon-arrow-right-line",
        "Ouvrir la section concernée.",
    )


def lot_view_href(lot_id: str, view_key: str, anchor: str | None = None) -> str:
    return lot_screen_href(
        lot_id,
        screen_key_for_step(view_key) or "excel",
        view_key,
        anchor,
    )


def lot_screen_href(
    lot_id: str,
    screen_key: str,
    view_key: str | None = None,
    anchor: str | None = None,
) -> str:
    href = f"/lots/{quote(lot_id, safe='')}/{quote(screen_key, safe='')}"
    if view_key:
        href = f"{href}?view={quote(view_key, safe='')}"
    return f"{href}#{anchor}" if anchor else href


def lot_sources_href(lot_id: str, anchor: str | None = None) -> str:
    href = f"/?lot_id={quote(lot_id, safe='')}"
    return f"{href}#{anchor}" if anchor else href


def step_href(lot_id: str, view_key: str) -> str:
    return lot_view_href(lot_id, view_key, "lot-workspace-title")


def view_key_for_step(step_key: str) -> str:
    return step_key


def action_link(label: str, href: str, icon_class: str, hint: str) -> dict[str, str]:
    return {
        "label": label,
        "href": href,
        "icon_class": icon_class,
        "hint": hint,
    }


def lot_sources_summary(repositories: Any, lot: dict[str, Any]) -> dict[str, Any]:
    steps_by_key = {step["key"]: step for step in lot.get("steps") or []}
    excel_artifact = current_source_artifact(
        repositories,
        lot_id=lot["id"],
        step_key="upload_excel",
    )
    images_artifact = current_source_artifact(
        repositories,
        lot_id=lot["id"],
        step_key="upload_images",
    )
    excel = source_card_summary(
        lot,
        kind="excel",
        title="Fichier Excel source",
        missing_status="À déposer",
        uploaded_status="Déposé",
        artifact=excel_artifact,
        upload_step=steps_by_key.get("upload_excel"),
        processing_step=steps_by_key.get("diagnostic_excel"),
        missing_action=action_link(
            "Aller au formulaire Excel",
            lot_sources_href(lot["id"], "excel-file"),
            "fr-icon-arrow-down-line",
            "Le diagnostic Excel démarre après le dépôt.",
        ),
        pending_action=action_link(
            "Actualiser l'état du diagnostic Excel",
            lot_view_href(lot["id"], "diagnostic_excel", "excel-diagnostic-title"),
            "fr-icon-refresh-line",
            "Le traitement local traite le diagnostic en arrière-plan.",
        ),
        ready_action=action_link(
            "Continuer vers le mapping",
            lot_view_href(lot["id"], "mapping", "mapping-step-title"),
            "fr-icon-arrow-right-line",
            "Le fichier Excel est importable ; vérifier les colonnes à exporter.",
        ),
        blocked_action=action_link(
            "Redéposer un Excel corrigé",
            lot_sources_href(lot["id"], "excel-file"),
            "fr-icon-upload-line",
            "Corriger le fichier puis déposer une nouvelle version.",
        ),
    )
    images = source_card_summary(
        lot,
        kind="images",
        title="Zip images produit",
        missing_status="À déposer",
        uploaded_status="Déposé",
        artifact=images_artifact,
        upload_step=steps_by_key.get("upload_images"),
        processing_step=steps_by_key.get("inspection_images"),
        missing_action=action_link(
            "Aller au formulaire zip images",
            lot_sources_href(lot["id"], "image-zip-file"),
            "fr-icon-arrow-down-line",
            "L'inspection démarre après le dépôt du zip.",
        ),
        pending_action=action_link(
            "Actualiser l'état des images",
            lot_view_href(lot["id"], "inspection_images", "image-workflow-title"),
            "fr-icon-refresh-line",
            "Le traitement local inspecte le zip en arrière-plan.",
        ),
        ready_action=action_link(
            "Voir le traitement images",
            lot_view_href(lot["id"], "matching_images", "image-matching-title"),
            "fr-icon-arrow-right-line",
            "Consulter l'inspection, les associations et les images traitées.",
        ),
        blocked_action=action_link(
            "Redéposer un zip images corrigé",
            lot_sources_href(lot["id"], "image-zip-file"),
            "fr-icon-upload-line",
            "Corriger le zip puis déposer une nouvelle version.",
        ),
    )
    image_inspection = lot.get("image_inspection")
    if images["uploaded"] and isinstance(image_inspection, dict):
        images["details"].append(
            ("Images détectées", str(image_inspection.get("image_count", 0)))
        )
        images["details"].append(
            ("Entrées du zip", str(image_inspection.get("entries_count", 0)))
        )
    return {
        "excel": excel,
        "images": images,
        "all_required_uploaded": bool(excel["uploaded"] and images["uploaded"]),
        "items": [excel, images],
    }


def source_card_summary(
    lot: dict[str, Any],
    *,
    kind: str,
    title: str,
    missing_status: str,
    uploaded_status: str,
    artifact: dict[str, Any] | None,
    upload_step: dict[str, Any] | None,
    processing_step: dict[str, Any] | None,
    missing_action: dict[str, str],
    pending_action: dict[str, str],
    ready_action: dict[str, str],
    blocked_action: dict[str, str],
) -> dict[str, Any]:
    uploaded = artifact is not None
    metadata = artifact_metadata(artifact) if artifact else {}
    details: list[tuple[str, str]] = []
    if uploaded and artifact is not None:
        details.append(("État du dépôt", uploaded_status))
        details.append(("Taille reçue", format_bytes(int(artifact["size_bytes"] or 0))))
        details.append(
            ("Reçu le", format_datetime_label(str(artifact.get("created_at") or "")))
        )
        extension = metadata.get("extension")
        if isinstance(extension, str) and extension:
            details.append(("Format", extension))
        if kind == "excel":
            sheet_count = metadata.get("sheet_count")
            if isinstance(sheet_count, int):
                details.append(("Onglets détectés", str(sheet_count)))
        action = action_for_uploaded_source(
            processing_step=processing_step,
            pending_action=pending_action,
            ready_action=ready_action,
            blocked_action=blocked_action,
        )
        processing_label = source_processing_label(processing_step)
    else:
        details.append(("État du dépôt", missing_status))
        details.append(("Taille reçue", "Aucun fichier"))
        action = missing_action
        processing_label = "En attente du dépôt"

    return {
        "kind": kind,
        "title": title,
        "uploaded": uploaded,
        "status_label": uploaded_status if uploaded else missing_status,
        "badge_class": "success" if uploaded else "info",
        "upload_status_label": (
            upload_step["status_label"] if upload_step else "Non démarrée"
        ),
        "processing_label": processing_label,
        "details": details,
        "action": action,
    }


def action_for_uploaded_source(
    *,
    processing_step: dict[str, Any] | None,
    pending_action: dict[str, str],
    ready_action: dict[str, str],
    blocked_action: dict[str, str],
) -> dict[str, str]:
    status = processing_step["status"] if processing_step else "non_demarre"
    if status in UI_PENDING_STEP_STATUSES:
        return pending_action
    if status in {"bloque", "echoue"}:
        return blocked_action
    return ready_action


def source_processing_label(processing_step: dict[str, Any] | None) -> str:
    if processing_step is None:
        return "Traitement non démarré"
    status = processing_step["status"]
    if status == "pret":
        return "Traitement en attente"
    if status == "en_cours":
        return "Traitement en cours"
    if status in UI_DONE_STEP_STATUSES:
        return processing_step["status_label"]
    if status in {"bloque", "echoue"}:
        return "Correction attendue"
    return processing_step["status_label"]


def sort_ui_payload(payload: dict[str, Any]) -> dict[str, Any]:
    proposal = dict(payload.get("proposal") or {})
    detection_status = proposal.get("detection_status")
    if isinstance(detection_status, str):
        proposal["detection_status_label"] = SORT_DETECTION_STATUS_LABELS.get(
            detection_status,
            "Statut de détection non traduit",
        )
    default_decision = proposal.get("default_decision")
    if isinstance(default_decision, str):
        proposal["default_decision_label"] = SORT_DECISION_LABELS.get(
            default_decision,
            "Décision non traduite",
        )

    decision = payload.get("decision")
    decision_payload = dict(decision) if isinstance(decision, dict) else decision
    if isinstance(decision_payload, dict):
        decision_value = decision_payload.get("decision")
        if isinstance(decision_value, str):
            decision_payload["decision_label"] = SORT_DECISION_LABELS.get(
                decision_value,
                "Décision non traduite",
            )
        decision_detection_status = decision_payload.get("detection_status")
        if isinstance(decision_detection_status, str):
            decision_payload["detection_status_label"] = (
                SORT_DETECTION_STATUS_LABELS.get(
                    decision_detection_status,
                    "Statut de détection non traduit",
                )
            )

    return {
        **payload,
        "proposal": proposal,
        "decision": decision_payload,
    }


def image_matching_ui_payload(matching: dict[str, Any]) -> dict[str, Any]:
    bindings: list[Any] = []
    for binding in matching.get("bindings") or []:
        if not isinstance(binding, dict):
            bindings.append(binding)
            continue
        ui_binding = dict(binding)
        status = ui_binding.get("status")
        match_level = ui_binding.get("match_level")
        ui_binding["status_label"] = (
            IMAGE_BINDING_STATUS_LABELS.get(status, "Statut non traduit")
            if isinstance(status, str)
            else "Statut non traduit"
        )
        ui_binding["match_level_label"] = (
            IMAGE_MATCH_LEVEL_LABELS.get(match_level, "Niveau non traduit")
            if isinstance(match_level, str)
            else "Niveau non traduit"
        )
        bindings.append(ui_binding)
    return {
        **matching,
        "bindings": bindings,
    }


def current_source_artifact(
    repositories: Any,
    *,
    lot_id: str,
    step_key: str,
) -> dict[str, Any] | None:
    row = repositories.connection.execute(
        """
        SELECT *
        FROM artefacts
        WHERE lot_id = ?
          AND step_key = ?
          AND role = 'source'
          AND status = 'committed'
        ORDER BY COALESCE(committed_at, created_at) DESC, created_at DESC, id DESC
        LIMIT 1
        """,
        (lot_id, step_key),
    ).fetchone()
    return dict(row) if row is not None else None


def artifact_metadata(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if artifact is None:
        return {}
    value = artifact.get("metadata_json")
    if not isinstance(value, str) or not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def format_datetime_label(value: str) -> str:
    if not value:
        return "Date inconnue"
    return value.replace("T", " ").split("+", 1)[0].removesuffix("Z")


def phase_status(steps: list[dict[str, Any]]) -> dict[str, str]:
    statuses = {step["status"] for step in steps}
    if not steps:
        return {"status_label": "À venir", "badge_class": "info"}
    if statuses & {"bloque", "echoue"}:
        return {"status_label": "À corriger", "badge_class": "error"}
    if "action_requise" in statuses:
        return {"status_label": "Action requise", "badge_class": "warning"}
    if "en_cours" in statuses:
        return {"status_label": "En cours", "badge_class": "info"}
    if "pret" in statuses:
        return {"status_label": "Prêt", "badge_class": "info"}
    if all(status in UI_DONE_STEP_STATUSES for status in statuses):
        if "termine_avec_alertes" in statuses:
            return {"status_label": "Terminé avec alertes", "badge_class": "warning"}
        return {"status_label": "Terminé", "badge_class": "success"}
    if statuses & UI_DONE_STEP_STATUSES:
        return {"status_label": "Partiel", "badge_class": "info"}
    if statuses <= {"non_demarre", "invalide"}:
        return {"status_label": "À venir", "badge_class": "info"}
    return {"status_label": "À suivre", "badge_class": "info"}


def ui_error(title: str, cause: str, action: str) -> dict[str, str]:
    return {
        "title": title,
        "cause": cause,
        "action": action,
    }


def upload_confirmation(uploaded: str | None) -> dict[str, str] | None:
    if uploaded == "excel":
        return {
            "kind": "excel",
            "title": "Votre document a bien été déposé",
            "cause": "Le fichier Excel source est reçu par le lot.",
            "action": "Attendre le diagnostic Excel, puis valider le mapping quand il apparaît.",
        }
    if uploaded == "images":
        return {
            "kind": "images",
            "title": "Votre document a bien été déposé",
            "cause": "Le zip images produit est reçu par le lot.",
            "action": "Attendre l'inspection images, puis résoudre les associations si demandé.",
        }
    return None


def mapping_ui_error(exc: MappingError) -> dict[str, str]:
    if exc.code == "SIRCOM_MAPPING_SOURCE_HEADERS_MISSING":
        action = (
            "Relancer le diagnostic Excel ou redéposer l'Excel pour reconstruire "
            "les métadonnées de colonnes."
        )
    elif exc.code == "SIRCOM_MAPPING_DIAGNOSTIC_BLOCKED":
        action = "Corriger l'Excel bloquant puis redéposer le fichier."
    else:
        action = "Relancer l'étape précédente ou redéposer l'Excel."
    return {
        "title": "Mapping indisponible",
        "cause": exc.message,
        "action": action,
        "code": exc.code,
    }
