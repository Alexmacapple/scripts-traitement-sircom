# Hermes Route Prompt Previews

Generated prompt previews are not execution proof. They are the bounded handoff
shape for a human, Codex or Claude operator after behavior classification.

## Route code-sircom2026-config-cd04d0d649-route

Agent: `code-sircom2026-config-cd04d0d649`

Selection reason: runtime-discovered concern area `code-sircom2026-config-cd04d0d649` for tasks touching the sircom2026-config-cd04d0d649 zone of the source (sircom2026/app.py, sircom2026/app_lifecycle.py, sircom2026/config.py, …), or behavior listed in behavior-contract.yml.

Allowed paths: sircom2026/app.py, sircom2026/app_lifecycle.py, sircom2026/config.py, sircom2026/resource_guards.py, sircom2026/worker_runner.py, scripts-2026/create_synthetic_excels.py, scripts-2026/run_worker_once.py, sircom2026/synthetic_excels.py, tests/test_csv_contract.py, tests/test_csv_preview.py, tests/test_e2e_workflow.py, tests/test_excel_diagnostic_pipeline.py, tests/test_excel_upload.py, tests/test_fusion.py, tests/test_image_upload.py, tests/test_lots_api.py, tests/test_lots_playwright.py, tests/test_mapping.py, tests/test_normalization.py, tests/test_package.py, tests/test_reports.py, tests/test_sorting.py

Route budgets: max 1 changed file(s), max 120 patch lines, new files: none

Skills to load: project-architecture, pdg-mission-guard, pdd-progressive-disclosure, hermes-memory, fable-mode, gbrain-sourced-synthesis, tdd-red-green, grillme-questioning

Prompt preview:

```text
Read .hermes/profile.yml, .hermes/control/behavior-contract.yml,
.hermes/control/task-router.yml, .hermes/control/disclosure-map.yml and
.hermes/control/tool-policy.yml.

Route: code-sircom2026-config-cd04d0d649-route
Agent card: .hermes/agents/code-sircom2026-config-cd04d0d649.agent.md
Allowed paths: sircom2026/app.py, sircom2026/app_lifecycle.py, sircom2026/config.py, sircom2026/resource_guards.py, sircom2026/worker_runner.py, scripts-2026/create_synthetic_excels.py, scripts-2026/run_worker_once.py, sircom2026/synthetic_excels.py, tests/test_csv_contract.py, tests/test_csv_preview.py, tests/test_e2e_workflow.py, tests/test_excel_diagnostic_pipeline.py, tests/test_excel_upload.py, tests/test_fusion.py, tests/test_image_upload.py, tests/test_lots_api.py, tests/test_lots_playwright.py, tests/test_mapping.py, tests/test_normalization.py, tests/test_package.py, tests/test_reports.py, tests/test_sorting.py
Route budgets: max 1 changed file(s), max 120 patch lines, new files: none
Output: bounded diff plus verification result; do not claim production readiness.

Proceed only when the touched preserve/change behavior has status: confirmed.
If behavior is proposed or missing, stop and add/request a human decision.
If the task needs more files or a bigger diff than the budgets allow, stop and
submit an update-route proposal through mutation admission.
```

## Route code-sircom2026-state-b64f8fbe54-route

Agent: `code-sircom2026-state-b64f8fbe54`

Selection reason: runtime-discovered concern area `code-sircom2026-state-b64f8fbe54` for tasks touching the sircom2026-state-b64f8fbe54 zone of the source (sircom2026/api/lots.py, sircom2026/api/lots_contract.py, sircom2026/artifacts.py, …), or behavior listed in behavior-contract.yml.

Allowed paths: sircom2026/api/lots.py, sircom2026/api/lots_contract.py, sircom2026/artifacts.py, sircom2026/csv_contract.py, sircom2026/csv_preview.py, sircom2026/excel_diagnostic_pipeline.py, sircom2026/excel_upload.py, sircom2026/invalidation.py, sircom2026/mapping.py, sircom2026/package.py, sircom2026/pipeline.py, sircom2026/reports.py, sircom2026/reports_rendering.py, sircom2026/sorting.py, sircom2026/state.py, sircom2026/transform.py, sircom2026/worker.py

Route budgets: max 6 changed file(s), max 720 patch lines, new files: none

Skills to load: project-architecture, pdg-mission-guard, pdd-progressive-disclosure, hermes-memory, fable-mode, gbrain-sourced-synthesis, tdd-red-green, grillme-questioning

Prompt preview:

```text
Read .hermes/profile.yml, .hermes/control/behavior-contract.yml,
.hermes/control/task-router.yml, .hermes/control/disclosure-map.yml and
.hermes/control/tool-policy.yml.

Route: code-sircom2026-state-b64f8fbe54-route
Agent card: .hermes/agents/code-sircom2026-state-b64f8fbe54.agent.md
Allowed paths: sircom2026/api/lots.py, sircom2026/api/lots_contract.py, sircom2026/artifacts.py, sircom2026/csv_contract.py, sircom2026/csv_preview.py, sircom2026/excel_diagnostic_pipeline.py, sircom2026/excel_upload.py, sircom2026/invalidation.py, sircom2026/mapping.py, sircom2026/package.py, sircom2026/pipeline.py, sircom2026/reports.py, sircom2026/reports_rendering.py, sircom2026/sorting.py, sircom2026/state.py, sircom2026/transform.py, sircom2026/worker.py
Route budgets: max 6 changed file(s), max 720 patch lines, new files: none
Output: bounded diff plus verification result; do not claim production readiness.

Proceed only when the touched preserve/change behavior has status: confirmed.
If behavior is proposed or missing, stop and add/request a human decision.
If the task needs more files or a bigger diff than the budgets allow, stop and
submit an update-route proposal through mutation admission.
```

## Route code-sircom2026-web-context-ac4baca60c-route

Agent: `code-sircom2026-web-context-ac4baca60c`

Selection reason: runtime-discovered concern area `code-sircom2026-web-context-ac4baca60c` for tasks touching the sircom2026-web-context-ac4baca60c zone of the source (sircom2026/__init__.py, sircom2026/api/artifacts.py, sircom2026/api/dependencies.py, …), or behavior listed in behavior-contract.yml.

Allowed paths: sircom2026/__init__.py, sircom2026/api/artifacts.py, sircom2026/api/dependencies.py, sircom2026/api/errors.py, sircom2026/api/security.py, sircom2026/api/storage.py, sircom2026/app_factory.py, sircom2026/web_constants.py, sircom2026/web_context.py, sircom2026/web_routes.py, sircom2026/web_ui.py, tests/test_api_access_errors.py, tests/test_database.py

Route budgets: max 6 changed file(s), max 720 patch lines, new files: none

Skills to load: project-architecture, pdg-mission-guard, pdd-progressive-disclosure, hermes-memory, fable-mode, gbrain-sourced-synthesis, tdd-red-green, grillme-questioning

Prompt preview:

```text
Read .hermes/profile.yml, .hermes/control/behavior-contract.yml,
.hermes/control/task-router.yml, .hermes/control/disclosure-map.yml and
.hermes/control/tool-policy.yml.

Route: code-sircom2026-web-context-ac4baca60c-route
Agent card: .hermes/agents/code-sircom2026-web-context-ac4baca60c.agent.md
Allowed paths: sircom2026/__init__.py, sircom2026/api/artifacts.py, sircom2026/api/dependencies.py, sircom2026/api/errors.py, sircom2026/api/security.py, sircom2026/api/storage.py, sircom2026/app_factory.py, sircom2026/web_constants.py, sircom2026/web_context.py, sircom2026/web_routes.py, sircom2026/web_ui.py, tests/test_api_access_errors.py, tests/test_database.py
Route budgets: max 6 changed file(s), max 720 patch lines, new files: none
Output: bounded diff plus verification result; do not claim production readiness.

Proceed only when the touched preserve/change behavior has status: confirmed.
If behavior is proposed or missing, stop and add/request a human decision.
If the task needs more files or a bigger diff than the budgets allow, stop and
submit an update-route proposal through mutation admission.
```

## Route code-sircom2026-database-1aa5e56000-route

Agent: `code-sircom2026-database-1aa5e56000`

Selection reason: runtime-discovered concern area `code-sircom2026-database-1aa5e56000` for tasks touching the sircom2026-database-1aa5e56000 zone of the source (sircom2026/database.py, sircom2026/database_repositories.py, sircom2026/lots.py, …), or behavior listed in behavior-contract.yml.

Allowed paths: sircom2026/database.py, sircom2026/database_repositories.py, sircom2026/lots.py, sircom2026/purge.py, tests/test_artifacts.py, tests/test_invalidation.py, tests/test_purge.py, tests/test_state.py

Route budgets: max 6 changed file(s), max 720 patch lines, new files: none

Skills to load: project-architecture, pdg-mission-guard, pdd-progressive-disclosure, hermes-memory, fable-mode, gbrain-sourced-synthesis, tdd-red-green, grillme-questioning

Prompt preview:

```text
Read .hermes/profile.yml, .hermes/control/behavior-contract.yml,
.hermes/control/task-router.yml, .hermes/control/disclosure-map.yml and
.hermes/control/tool-policy.yml.

Route: code-sircom2026-database-1aa5e56000-route
Agent card: .hermes/agents/code-sircom2026-database-1aa5e56000.agent.md
Allowed paths: sircom2026/database.py, sircom2026/database_repositories.py, sircom2026/lots.py, sircom2026/purge.py, tests/test_artifacts.py, tests/test_invalidation.py, tests/test_purge.py, tests/test_state.py
Route budgets: max 6 changed file(s), max 720 patch lines, new files: none
Output: bounded diff plus verification result; do not claim production readiness.

Proceed only when the touched preserve/change behavior has status: confirmed.
If behavior is proposed or missing, stop and add/request a human decision.
If the task needs more files or a bigger diff than the budgets allow, stop and
submit an update-route proposal through mutation admission.
```

## Route code-sircom2026-image-matching-3fdbae9c97-route

Agent: `code-sircom2026-image-matching-3fdbae9c97`

Selection reason: runtime-discovered concern area `code-sircom2026-image-matching-3fdbae9c97` for tasks touching the sircom2026-image-matching-3fdbae9c97 zone of the source (sircom2026/image_formats.py, sircom2026/image_matching.py, sircom2026/image_matching_rules.py, …), or behavior listed in behavior-contract.yml.

Allowed paths: sircom2026/image_formats.py, sircom2026/image_matching.py, sircom2026/image_matching_rules.py, sircom2026/image_naming.py, sircom2026/images.py, sircom2026/processed_images.py, tests/test_image_formats.py, tests/test_image_matching.py

Route budgets: max 6 changed file(s), max 720 patch lines, new files: none

Skills to load: project-architecture, pdg-mission-guard, pdd-progressive-disclosure, hermes-memory, fable-mode, gbrain-sourced-synthesis, tdd-red-green, grillme-questioning

Prompt preview:

```text
Read .hermes/profile.yml, .hermes/control/behavior-contract.yml,
.hermes/control/task-router.yml, .hermes/control/disclosure-map.yml and
.hermes/control/tool-policy.yml.

Route: code-sircom2026-image-matching-3fdbae9c97-route
Agent card: .hermes/agents/code-sircom2026-image-matching-3fdbae9c97.agent.md
Allowed paths: sircom2026/image_formats.py, sircom2026/image_matching.py, sircom2026/image_matching_rules.py, sircom2026/image_naming.py, sircom2026/images.py, sircom2026/processed_images.py, tests/test_image_formats.py, tests/test_image_matching.py
Route budgets: max 6 changed file(s), max 720 patch lines, new files: none
Output: bounded diff plus verification result; do not claim production readiness.

Proceed only when the touched preserve/change behavior has status: confirmed.
If behavior is proposed or missing, stop and add/request a human decision.
If the task needs more files or a bigger diff than the budgets allow, stop and
submit an update-route proposal through mutation admission.
```

## Route code-sircom2026-excel-diagnostic-30392172b5-route

Agent: `code-sircom2026-excel-diagnostic-30392172b5`

Selection reason: runtime-discovered concern area `code-sircom2026-excel-diagnostic-30392172b5` for tasks touching the sircom2026-excel-diagnostic-30392172b5 zone of the source (sircom2026/excel_diagnostic.py, sircom2026/mapping_rules.py, scripts-2026/diagnose_excel.py, …), or behavior listed in behavior-contract.yml.

Allowed paths: sircom2026/excel_diagnostic.py, sircom2026/mapping_rules.py, scripts-2026/diagnose_excel.py, tests/test_excel_diagnostic.py

Route budgets: max 4 changed file(s), max 480 patch lines, new files: none

Skills to load: project-architecture, pdg-mission-guard, pdd-progressive-disclosure, hermes-memory, fable-mode, gbrain-sourced-synthesis, tdd-red-green, grillme-questioning

Prompt preview:

```text
Read .hermes/profile.yml, .hermes/control/behavior-contract.yml,
.hermes/control/task-router.yml, .hermes/control/disclosure-map.yml and
.hermes/control/tool-policy.yml.

Route: code-sircom2026-excel-diagnostic-30392172b5-route
Agent card: .hermes/agents/code-sircom2026-excel-diagnostic-30392172b5.agent.md
Allowed paths: sircom2026/excel_diagnostic.py, sircom2026/mapping_rules.py, scripts-2026/diagnose_excel.py, tests/test_excel_diagnostic.py
Route budgets: max 4 changed file(s), max 480 patch lines, new files: none
Output: bounded diff plus verification result; do not claim production readiness.

Proceed only when the touched preserve/change behavior has status: confirmed.
If behavior is proposed or missing, stop and add/request a human decision.
If the task needs more files or a bigger diff than the budgets allow, stop and
submit an update-route proposal through mutation admission.
```

## Route code-tests-template-contracts-27743ce500-route

Agent: `code-tests-template-contracts-27743ce500`

Selection reason: runtime-discovered concern area `code-tests-template-contracts-27743ce500` for tasks touching the tests-template-contracts-27743ce500 zone of the source (tests/template_contracts.py, tests/test_ui_button_contract.py), or behavior listed in behavior-contract.yml.

Allowed paths: tests/template_contracts.py, tests/test_ui_button_contract.py

Route budgets: max 2 changed file(s), max 240 patch lines, new files: none

Skills to load: project-architecture, pdg-mission-guard, pdd-progressive-disclosure, hermes-memory, fable-mode, gbrain-sourced-synthesis, tdd-red-green, grillme-questioning

Prompt preview:

```text
Read .hermes/profile.yml, .hermes/control/behavior-contract.yml,
.hermes/control/task-router.yml, .hermes/control/disclosure-map.yml and
.hermes/control/tool-policy.yml.

Route: code-tests-template-contracts-27743ce500-route
Agent card: .hermes/agents/code-tests-template-contracts-27743ce500.agent.md
Allowed paths: tests/template_contracts.py, tests/test_ui_button_contract.py
Route budgets: max 2 changed file(s), max 240 patch lines, new files: none
Output: bounded diff plus verification result; do not claim production readiness.

Proceed only when the touched preserve/change behavior has status: confirmed.
If behavior is proposed or missing, stop and add/request a human decision.
If the task needs more files or a bigger diff than the budgets allow, stop and
submit an update-route proposal through mutation admission.
```

## Route code-hardening-route

Agent: `code-hardening`

Selection reason: runtime-discovered concern area `code-hardening` for tasks touching the project sources outside every derived zone, or behavior listed in behavior-contract.yml.

Allowed paths: sircom2026/static/app.js, re-run-2026/0-extract_departement_to_sircom.py, re-run-2026/0-si-cellule-vide-na.py, re-run-2026/1-header_lettres_colonne.py, re-run-2026/10-process-images.py, re-run-2026/11-create_mapping_excel.py, re-run-2026/12-verify_data_integrity.py, re-run-2026/2-image_id_adder.py, re-run-2026/3-fusion_tri_region_departement.py, re-run-2026/4-changer-date-format.py, re-run-2026/5-livrable-final.py, re-run-2026/6-clean_headers_excel.py, re-run-2026/7-add_pathimg_excel.py, re-run-2026/8-optimize_content_excel.py, re-run-2026/9-export_csv_utf16_final.py, scripts-2025/0-extract_departement_to_sircom.py, scripts-2025/0-si-cellule-vide-na.py, scripts-2025/1-header_lettres_colonne.py, scripts-2025/10-process-images.py, scripts-2025/11-create_mapping_excel.py, scripts-2025/12-verify_data_integrity.py, scripts-2025/2-image_id_adder.py, scripts-2025/3-fusion_tri_region_departement.py, scripts-2025/4-changer-date-format.py, scripts-2025/5-livrable-final.py, scripts-2025/6-clean_headers_excel.py, scripts-2025/7-add_pathimg_excel.py, scripts-2025/8-optimize_content_excel.py, scripts-2025/9-export_csv_utf16_final.py, scripts-2026/build_exploitable_bdd_etablissements.py, sircom2026/_database_artifacts.py, sircom2026/_database_events.py, sircom2026/_database_jobs.py, sircom2026/_database_lots.py, sircom2026/_database_problems.py, sircom2026/_database_purge.py, sircom2026/_database_shared.py, sircom2026/_database_steps.py, sircom2026/api/__init__.py, sircom_master_script.py, tests/__init__.py, tests/test_package_data.py, tests/test_scripts_2025_fill_empty_na.py, tests/test_scripts_2025_optimize_content.py, tests/test_scripts_2025_process_images.py, tests/test_sircom_master_dependencies.py

Route budgets: max 1 changed file(s), max 120 patch lines, new files: none

Skills to load: project-architecture, pdg-mission-guard, pdd-progressive-disclosure, hermes-memory, fable-mode, gbrain-sourced-synthesis, tdd-red-green, grillme-questioning

Prompt preview:

```text
Read .hermes/profile.yml, .hermes/control/behavior-contract.yml,
.hermes/control/task-router.yml, .hermes/control/disclosure-map.yml and
.hermes/control/tool-policy.yml.

Route: code-hardening-route
Agent card: .hermes/agents/code-hardening.agent.md
Allowed paths: sircom2026/static/app.js, re-run-2026/0-extract_departement_to_sircom.py, re-run-2026/0-si-cellule-vide-na.py, re-run-2026/1-header_lettres_colonne.py, re-run-2026/10-process-images.py, re-run-2026/11-create_mapping_excel.py, re-run-2026/12-verify_data_integrity.py, re-run-2026/2-image_id_adder.py, re-run-2026/3-fusion_tri_region_departement.py, re-run-2026/4-changer-date-format.py, re-run-2026/5-livrable-final.py, re-run-2026/6-clean_headers_excel.py, re-run-2026/7-add_pathimg_excel.py, re-run-2026/8-optimize_content_excel.py, re-run-2026/9-export_csv_utf16_final.py, scripts-2025/0-extract_departement_to_sircom.py, scripts-2025/0-si-cellule-vide-na.py, scripts-2025/1-header_lettres_colonne.py, scripts-2025/10-process-images.py, scripts-2025/11-create_mapping_excel.py, scripts-2025/12-verify_data_integrity.py, scripts-2025/2-image_id_adder.py, scripts-2025/3-fusion_tri_region_departement.py, scripts-2025/4-changer-date-format.py, scripts-2025/5-livrable-final.py, scripts-2025/6-clean_headers_excel.py, scripts-2025/7-add_pathimg_excel.py, scripts-2025/8-optimize_content_excel.py, scripts-2025/9-export_csv_utf16_final.py, scripts-2026/build_exploitable_bdd_etablissements.py, sircom2026/_database_artifacts.py, sircom2026/_database_events.py, sircom2026/_database_jobs.py, sircom2026/_database_lots.py, sircom2026/_database_problems.py, sircom2026/_database_purge.py, sircom2026/_database_shared.py, sircom2026/_database_steps.py, sircom2026/api/__init__.py, sircom_master_script.py, tests/__init__.py, tests/test_package_data.py, tests/test_scripts_2025_fill_empty_na.py, tests/test_scripts_2025_optimize_content.py, tests/test_scripts_2025_process_images.py, tests/test_sircom_master_dependencies.py
Route budgets: max 1 changed file(s), max 120 patch lines, new files: none
Output: bounded diff plus verification result; do not claim production readiness.

Proceed only when the touched preserve/change behavior has status: confirmed.
If behavior is proposed or missing, stop and add/request a human decision.
If the task needs more files or a bigger diff than the budgets allow, stop and
submit an update-route proposal through mutation admission.
```

## Route ui-verification-route

Agent: `ui-verification`

Selection reason: runtime-discovered concern area `ui-verification` for tasks touching the UI pages, templates, styles or browser-visible behavior.

Allowed paths: sircom2026/templates/index.html, sircom2026/templates/info.html, sircom2026/templates/partials/footer.html, sircom2026/templates/partials/header.html, sircom2026/templates/partials/home_view.html, sircom2026/templates/partials/lot_breadcrumb.html, sircom2026/templates/partials/overview.html, sircom2026/templates/partials/skiplinks.html, sircom2026/templates/partials/source_uploads.html, sircom2026/templates/partials/workflow_csv.html, sircom2026/templates/partials/workflow_deliverables.html, sircom2026/templates/partials/workflow_details.html, sircom2026/templates/partials/workflow_excel.html, sircom2026/templates/partials/workflow_images.html, sircom2026/templates/partials/workflow_source_actions.html, sircom2026/templates/partials/workflow_view.html, visual-tests/_review-template.html

Route budgets: max 6 changed file(s), max 720 patch lines, new files: none

Skills to load: project-architecture, pdg-mission-guard, pdd-progressive-disclosure, hermes-memory, fable-mode, gbrain-sourced-synthesis, shipguard-browser-scenarios

Prompt preview:

```text
Read .hermes/profile.yml, .hermes/control/behavior-contract.yml,
.hermes/control/task-router.yml, .hermes/control/disclosure-map.yml and
.hermes/control/tool-policy.yml.

Route: ui-verification-route
Agent card: .hermes/agents/ui-verification.agent.md
Allowed paths: sircom2026/templates/index.html, sircom2026/templates/info.html, sircom2026/templates/partials/footer.html, sircom2026/templates/partials/header.html, sircom2026/templates/partials/home_view.html, sircom2026/templates/partials/lot_breadcrumb.html, sircom2026/templates/partials/overview.html, sircom2026/templates/partials/skiplinks.html, sircom2026/templates/partials/source_uploads.html, sircom2026/templates/partials/workflow_csv.html, sircom2026/templates/partials/workflow_deliverables.html, sircom2026/templates/partials/workflow_details.html, sircom2026/templates/partials/workflow_excel.html, sircom2026/templates/partials/workflow_images.html, sircom2026/templates/partials/workflow_source_actions.html, sircom2026/templates/partials/workflow_view.html, visual-tests/_review-template.html
Route budgets: max 6 changed file(s), max 720 patch lines, new files: none
Output: bounded diff plus verification result; do not claim production readiness.

Proceed only when the touched preserve/change behavior has status: confirmed.
If behavior is proposed or missing, stop and add/request a human decision.
If the task needs more files or a bigger diff than the budgets allow, stop and
submit an update-route proposal through mutation admission.
```
