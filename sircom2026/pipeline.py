from __future__ import annotations

from sircom2026.lots import STEP_ORDER


V1_INVALIDATION_DAG: dict[str, tuple[str, ...]] = {
    "upload_excel": ("diagnostic_excel",),
    "diagnostic_excel": ("mapping",),
    "mapping": ("fusion_multi_onglets", "matching_images"),
    "fusion_multi_onglets": ("normalisation_contenu",),
    "normalisation_contenu": ("tri_region_departement", "verification_csv_indesign"),
    "tri_region_departement": ("previsualisation_csv",),
    "verification_csv_indesign": ("previsualisation_csv",),
    "previsualisation_csv": ("rapports", "package_final"),
    "upload_images": ("inspection_images",),
    "inspection_images": ("matching_images",),
    "matching_images": ("rapports", "package_final"),
    "rapports": ("package_final",),
    "package_final": ("purge_retention",),
    "purge_retention": (),
}
V1_EXTERNAL_STEP_KEYS = ("purge_retention",)


class UnknownStepError(ValueError):
    """Raised when a step is not part of the Sircom 2026 V1 DAG."""


def downstream_step_keys(step_key: str, *, include_external: bool = False) -> tuple[str, ...]:
    if step_key not in V1_INVALIDATION_DAG:
        raise UnknownStepError(f"Unknown step key: {step_key}.")

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
