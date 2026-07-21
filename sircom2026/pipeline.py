from __future__ import annotations

from sircom2026.lots import STEP_ORDER


V1_INVALIDATION_DAG: dict[str, tuple[str, ...]] = {
    "upload_excel": ("diagnostic_excel",),
    "diagnostic_excel": ("mapping",),
    "mapping": ("fusion_multi_onglets",),
    "fusion_multi_onglets": ("normalisation_contenu",),
    "normalisation_contenu": (
        "tri_region_departement",
        "verification_csv_indesign",
        "matching_images",
    ),
    "tri_region_departement": ("previsualisation_csv",),
    "verification_csv_indesign": ("previsualisation_csv",),
    "previsualisation_csv": ("rapports", "package_final"),
    "upload_images": ("inspection_images",),
    "inspection_images": ("matching_images",),
    "matching_images": ("previsualisation_csv", "rapports", "package_final"),
    "rapports": ("package_final",),
    "package_final": ("purge_retention",),
    "purge_retention": (),
}
V1_EXTERNAL_STEP_KEYS = ("purge_retention",)
V1_WORKER_STEP_KEYS = (
    "diagnostic_excel",
    "fusion_multi_onglets",
    "normalisation_contenu",
    "verification_csv_indesign",
    "inspection_images",
    "matching_images",
    "rapports",
    "package_final",
)
V1_AUTO_ENQUEUE_STEP_KEYS = ("matching_images", "rapports")
V1_AUTO_ENQUEUE_PARENT_STATUSES = ("termine", "termine_avec_alertes")


class UnknownStepError(ValueError):
    """Raised when a step is not part of the Sircom 2026 V1 DAG."""


def downstream_step_keys(step_key: str, *, include_external: bool = False) -> tuple[str, ...]:
    _require_known_step(step_key)

    external_steps = set(V1_EXTERNAL_STEP_KEYS)
    visited: set[str] = set()
    pending = list(V1_INVALIDATION_DAG[step_key])
    while pending:
        candidate = pending.pop(0)
        if candidate in visited:
            continue
        visited.add(candidate)
        pending.extend(V1_INVALIDATION_DAG.get(candidate, ()))

    if not include_external:
        visited -= external_steps

    return tuple(sorted(visited, key=lambda key: STEP_ORDER.get(key, 999)))


def ready_auto_enqueue_step_keys(repositories, *, lot_id: str, source_step_key: str) -> tuple[str, ...]:
    _require_known_step(source_step_key)
    auto_steps = set(V1_AUTO_ENQUEUE_STEP_KEYS)
    ready_parent_statuses = set(V1_AUTO_ENQUEUE_PARENT_STATUSES)
    steps_by_key = {
        step["step_key"]: step
        for step in repositories.steps.list_for_lot(lot_id)
    }
    ready_children: list[str] = []
    for child_key in V1_INVALIDATION_DAG[source_step_key]:
        if child_key not in auto_steps:
            continue
        child_step = steps_by_key.get(child_key)
        if child_step is None:
            continue
        parents = V1_INVALIDATION_PARENTS.get(child_key, ())
        if all(
            steps_by_key.get(parent_key, {}).get("status") in ready_parent_statuses
            for parent_key in parents
        ):
            ready_children.append(child_key)
    return tuple(sorted(ready_children, key=lambda key: STEP_ORDER.get(key, 999)))


def _require_known_step(step_key: str) -> None:
    if step_key not in V1_INVALIDATION_DAG:
        raise UnknownStepError(f"Unknown step key: {step_key}.")


def _parent_map() -> dict[str, tuple[str, ...]]:
    parents: dict[str, list[str]] = {step_key: [] for step_key in V1_INVALIDATION_DAG}
    for source, children in V1_INVALIDATION_DAG.items():
        for child in children:
            parents.setdefault(child, []).append(source)
    return {
        step_key: tuple(sorted(values, key=lambda key: STEP_ORDER.get(key, 999)))
        for step_key, values in parents.items()
    }


V1_INVALIDATION_PARENTS = _parent_map()
FINGERPRINT_REQUIRED_STEP_KEYS = tuple(
    step_key
    for step_key, parents in V1_INVALIDATION_PARENTS.items()
    if parents and step_key not in V1_EXTERNAL_STEP_KEYS
)
