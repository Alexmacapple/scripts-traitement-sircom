from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates

from sircom2026 import __version__

TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
DSFR_VERSION = "1.14.4"
DSFR_ASSETS_PATH = f"/static/dsfr/{DSFR_VERSION}"
UI_DONE_STEP_STATUSES = {"termine", "termine_avec_alertes", "ignore"}
UI_IDLE_STEP_STATUSES = {"non_demarre", "invalide"}
UI_PENDING_STEP_STATUSES = {"pret", "en_cours"}
CSV_WORKFLOW_STEP_KEYS = {
    "fusion_multi_onglets",
    "normalisation_contenu",
    "tri_region_departement",
    "verification_csv_indesign",
    "previsualisation_csv",
}
IMAGE_WORKFLOW_STEP_KEYS = {
    "upload_images",
    "inspection_images",
    "matching_images",
}

WORKFLOW_SCREEN_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "excel",
        "label": "Traitement Excel",
        "lead": "Contrôler l'Excel, choisir les colonnes, préparer et valider le CSV.",
        "step_keys": (
            "upload_excel",
            "diagnostic_excel",
            "mapping",
            "fusion_multi_onglets",
            "normalisation_contenu",
            "tri_region_departement",
            "verification_csv_indesign",
            "previsualisation_csv",
        ),
    },
    {
        "key": "images",
        "label": "Traitement images",
        "lead": "Déposer le zip images, inspecter son contenu et valider les associations.",
        "step_keys": ("upload_images", "inspection_images", "matching_images"),
    },
    {
        "key": "export",
        "label": "Export final",
        "lead": "Contrôler les rapports, valider la génération et récupérer le package InDesign.",
        "step_keys": ("rapports", "package_final"),
    },
)
WORKFLOW_SCREEN_BY_KEY = {
    str(screen["key"]): screen for screen in WORKFLOW_SCREEN_DEFINITIONS
}
WORKFLOW_SCREEN_BY_STEP_KEY = {
    str(step_key): str(screen["key"])
    for screen in WORKFLOW_SCREEN_DEFINITIONS
    for step_key in screen["step_keys"]
}


def static_asset_version() -> str:
    asset_paths = (STATIC_DIR / "sircom.css", STATIC_DIR / "app.js")
    mtimes = [path.stat().st_mtime_ns for path in asset_paths if path.exists()]
    return str(max(mtimes)) if mtimes else __version__


UX_PHASE_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "sources",
        "label": "Déposer les sources",
        "anchor": "lot-actions-title",
        "description": "Excel et zip images.",
        "step_keys": ("upload_excel", "upload_images"),
    },
    {
        "key": "diagnostic",
        "label": "Vérifier l'Excel",
        "anchor": "excel-diagnostic-title",
        "description": "Structure, en-têtes et points bloquants.",
        "step_keys": ("diagnostic_excel",),
    },
    {
        "key": "mapping",
        "label": "Choisir les colonnes",
        "anchor": "mapping-step-title",
        "description": "Champs exportés et noms CSV.",
        "step_keys": ("mapping",),
    },
    {
        "key": "csv",
        "label": "Contrôler le CSV",
        "anchor": "csv-workflow-title",
        "description": "Fusion, tri, normalisation et aperçu.",
        "step_keys": (
            "fusion_multi_onglets",
            "normalisation_contenu",
            "tri_region_departement",
            "verification_csv_indesign",
            "previsualisation_csv",
        ),
    },
    {
        "key": "images",
        "label": "Traiter les images",
        "anchor": "image-workflow-title",
        "description": "Inspection, association et export JPG.",
        "step_keys": ("inspection_images", "matching_images"),
    },
    {
        "key": "deliverables",
        "label": "Récupérer les livrables",
        "anchor": "reports-title",
        "description": "Rapports et package final.",
        "step_keys": ("rapports", "package_final"),
    },
)
STEP_NAV_ANCHORS = {
    "upload_excel": "lot-actions-title",
    "diagnostic_excel": "excel-diagnostic-title",
    "mapping": "mapping-step-title",
    "fusion_multi_onglets": "csv-workflow-title",
    "normalisation_contenu": "csv-workflow-title",
    "tri_region_departement": "csv-workflow-title",
    "verification_csv_indesign": "csv-workflow-title",
    "previsualisation_csv": "csv-workflow-title",
    "upload_images": "lot-actions-title",
    "inspection_images": "image-workflow-title",
    "matching_images": "image-workflow-title",
    "rapports": "reports-title",
    "package_final": "package-title",
}
UI_STEP_STATUS_PRESENTATION = {
    "non_demarre": {"ui_status_label": "À venir", "ui_badge_class": "info"},
    "pret": {"ui_status_label": "En attente", "ui_badge_class": "info"},
    "en_cours": {"ui_status_label": "En cours", "ui_badge_class": "info"},
    "action_requise": {
        "ui_status_label": "Action requise",
        "ui_badge_class": "warning",
    },
    "bloque": {"ui_status_label": "À corriger", "ui_badge_class": "error"},
    "termine": {"ui_status_label": "Terminé", "ui_badge_class": "success"},
    "termine_avec_alertes": {
        "ui_status_label": "Terminé avec alertes",
        "ui_badge_class": "warning",
    },
    "echoue": {"ui_status_label": "Erreur", "ui_badge_class": "error"},
    "ignore": {"ui_status_label": "Ignoré", "ui_badge_class": "info"},
    "annule": {"ui_status_label": "Annulé", "ui_badge_class": "warning"},
    "invalide": {"ui_status_label": "À refaire", "ui_badge_class": "warning"},
}
SORT_DETECTION_STATUS_LABELS = {
    "detected": "Colonnes détectées",
    "ambiguous": "Colonnes ambiguës",
    "missing": "Colonnes manquantes",
}
SORT_DECISION_LABELS = {
    "tri_region_departement": "Tri région puis département confirmé",
    "ordre_source": "Ordre source conservé",
}
IMAGE_BINDING_STATUS_LABELS = {
    "matched": "Associée",
    "missing": "Manquante",
    "ambiguous": "À résoudre",
    "conversion_failed": "Conversion échouée",
}
IMAGE_MATCH_LEVEL_LABELS = {
    "none": "Aucune correspondance",
    "final_name_collision": "Collision de nom final",
    "manual_invalid": "Choix manuel invalide",
    "manual": "Choix manuel",
    "original_exact": "Nom source exact",
    "original_exact_stem": "Nom source exact sans extension",
    "original_tolerant": "Nom source proche",
    "id_fallback_exact": "ID dossier exact de secours",
    "id_fallback_exact_final_name": "ID dossier exact de secours par nom final",
    "id_fallback_tolerant": "ID dossier proche de secours",
    "id_fallback_tolerant_final_name": "ID dossier proche de secours par nom final",
    "partial_suggestion": "Suggestion partielle",
}
STEP_VIEW_DESCRIPTIONS = {
    "upload_excel": "Déposer uniquement le fichier Excel source du lot.",
    "diagnostic_excel": "Lire le résultat de contrôle de l'Excel avant le mapping.",
    "mapping": "Choisir les colonnes exportées et valider les noms CSV.",
    "fusion_multi_onglets": "Suivre la fusion à plat des onglets par id_dossier.",
    "normalisation_contenu": "Suivre le nettoyage des contenus avant export.",
    "tri_region_departement": "Valider l'ordre des lignes avant l'aperçu CSV.",
    "verification_csv_indesign": "Suivre la vérification du contrat CSV InDesign.",
    "previsualisation_csv": "Contrôler et valider l'aperçu du CSV final.",
    "upload_images": "Déposer uniquement le zip des images produit.",
    "inspection_images": "Lire le contrôle du zip images et des fichiers détectés.",
    "matching_images": "Contrôler les associations entre dossiers et images.",
    "rapports": "Récupérer les rapports métier et technique quand ils sont prêts.",
    "package_final": "Générer ou télécharger le package final.",
}
STEP_VIEW_GUIDANCE = {
    "upload_excel": {
        "user_action": "Sélectionner l'Excel, vérifier son nom, puis cliquer sur le bouton de dépôt.",
        "system_action": "Le dépôt crée une tâche de diagnostic en arrière-plan.",
        "result": "Un message confirme la réception du fichier et l'étape diagnostic devient disponible.",
    },
    "diagnostic_excel": {
        "user_action": "Lire les blocages, alertes et informations avant de continuer.",
        "system_action": "Le traitement local contrôle les onglets, en-têtes, colonnes masquées, formules et id_dossier.",
        "result": "L'Excel est soit refusé avec corrections attendues, soit importable pour le mapping.",
    },
    "mapping": {
        "user_action": "Choisir les colonnes exportées, vérifier les rôles, puis valider le mapping.",
        "system_action": "L'application conserve la provenance sans afficher de valeurs métier.",
        "result": "Le mapping validé déclenche la préparation du CSV.",
    },
    "fusion_multi_onglets": {
        "user_action": "Surveiller l'état ; aucune saisie n'est attendue.",
        "system_action": "Le traitement local fusionne les onglets à plat par id_dossier.",
        "result": "Une table consolidée est prête pour normalisation.",
    },
    "normalisation_contenu": {
        "user_action": "Surveiller l'état ; aucune saisie n'est attendue.",
        "system_action": "Le traitement local nettoie les textes, dates, retours ligne et cellules vides.",
        "result": "Les contenus sont prêts pour le contrat CSV InDesign.",
    },
    "tri_region_departement": {
        "user_action": "Confirmer le tri s'il est proposé ; sinon conserver l'ordre source ou corriger le mapping.",
        "system_action": "L'application vérifie les rôles région et département issus du mapping.",
        "result": "L'ordre retenu est enregistré avant l'aperçu CSV.",
    },
    "verification_csv_indesign": {
        "user_action": "Surveiller l'état ; aucune saisie n'est attendue.",
        "system_action": "Le traitement local vérifie le format UTF-16, les colonnes image et le contrat d'export.",
        "result": "Le CSV est prêt à être prévisualisé.",
    },
    "previsualisation_csv": {
        "user_action": "Contrôler l'aperçu puis valider explicitement le CSV.",
        "system_action": "L'application montre les en-têtes, lignes et suppressions sans exposer de données sensibles inutiles.",
        "result": "La validation autorise la suite images et livrables.",
    },
    "upload_images": {
        "user_action": "Sélectionner le zip images, vérifier son nom, puis cliquer sur le bouton de dépôt.",
        "system_action": "Le dépôt crée une tâche d'inspection du zip en arrière-plan.",
        "result": "Un message confirme la réception du zip et l'inspection devient disponible.",
    },
    "inspection_images": {
        "user_action": "Lire le contrôle du zip et vérifier les images détectées.",
        "system_action": "Le traitement local inspecte la racine du zip, les formats, tailles et entrées ignorées.",
        "result": "Les images inspectées sont prêtes pour l'association aux dossiers.",
    },
    "matching_images": {
        "user_action": "Résoudre les ambiguïtés puis valider chaque association demandée.",
        "system_action": "Le traitement local renomme, convertit et prépare les JPG finaux.",
        "result": "Les images finales sont disponibles pour le package.",
    },
    "rapports": {
        "user_action": "Télécharger ou vérifier les rapports disponibles.",
        "system_action": "L'application sépare rapport métier et capsule technique sans valeurs métier.",
        "result": "Les informations de suivi sont prêtes avant génération du package.",
    },
    "package_final": {
        "user_action": "Générer le package final ou télécharger le package existant.",
        "system_action": "Le traitement local assemble CSV, images, rapports et manifeste.",
        "result": "Un zip final compatible avec la chaîne InDesign est disponible.",
    },
}
INFO_PAGES = {
    "plan-du-site": {
        "title": "Plan du site",
        "lead": "Accès aux principales pages de l'application locale.",
        "callout_title": "Navigation disponible",
        "callout_text": (
            "Le parcours métier principal se trouve sur l'accueil. Les liens API "
            "et Santé restent en pied de page pour les besoins techniques."
        ),
        "links": [
            {"label": "Accueil", "href": "/"},
            {"label": "API", "href": "/docs"},
            {"label": "Santé", "href": "/health"},
        ],
    },
    "accessibilite": {
        "title": "Accessibilité",
        "lead": "Statut d'accessibilité à formaliser avant toute publication.",
        "callout_title": "Statut non audité",
        "callout_text": (
            "Aucun audit RGAA complet n'a été réalisé sur cette application locale. "
            "L'interface utilise des composants DSFR et doit être auditée avant exposition publique."
        ),
        "links": [{"label": "Retour à l'accueil", "href": "/"}],
    },
    "mentions-legales": {
        "title": "Mentions légales",
        "lead": "Mentions à finaliser avec le responsable de publication.",
        "callout_title": "Prototype local",
        "callout_text": (
            "Cette page évite une impasse de navigation. Les mentions définitives "
            "devront être renseignées avant publication hors poste local."
        ),
        "links": [{"label": "Retour à l'accueil", "href": "/"}],
    },
    "donnees-personnelles": {
        "title": "Données personnelles",
        "lead": "Traitement local des lots Sircom 2026.",
        "callout_title": "Données stockées localement",
        "callout_text": (
            "Les fichiers déposés et artefacts de lot restent stockés dans le répertoire "
            "local configuré. Les rapports techniques ne doivent pas exposer de valeurs métier."
        ),
        "links": [{"label": "Retour à l'accueil", "href": "/"}],
    },
    "gestion-cookies": {
        "title": "Gestion des cookies",
        "lead": "Gestion à confirmer avant publication.",
        "callout_title": "Aucun consentement configuré",
        "callout_text": (
            "La V1 locale ne configure pas de bannière de consentement. Toute mesure "
            "d'audience ou publication future devra préciser la politique cookies."
        ),
        "links": [{"label": "Retour à l'accueil", "href": "/"}],
    },
}

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
