# LLM-Wiki Log

## [2026-05-20] start | 491742074

## [2026-05-21] ingest | 491742074 | Fixed playbook container step duplicate matching bug and added robust unit tests.

## [2026-05-22] ingest | PR-795 | Implemented and verified robust pagination and search aggregation for TIPCommon package.

## [2026-05-22] ingest | 491742074 | Migrated tests to black-box integration testing framework using GitSyncMockSession and mock_data.json.

## [2026-06-02] ingest | 514347461 | Fixed host parsing crash, implemented DNS fallback hostname matching, resolved all PR review comments with type annotations, robust parsing, styleguide-compliant Ping output messages, added linter parameter exclusions for "IPs/Ranges" to `mp`, and bumped package version to `1.30.14`.

## [2026-06-10] start | 494154345

## [2026-06-10] ingest | 494154345 | Analyzed the implemented Wiz 'List Resource Vulnerability Findings' action, query builder, datamodels, widgets, and verified via passing integration tests.

## [2026-06-17] start | 452223618

## [2026-06-17] ingest | 452223618 | Implemented pull view and push view commands, deconstruction/building for views, V2 view types in OverviewType, and added comprehensive CLI integration tests.

## [2026-06-17] ingest | 452223618 | Resolved all PR linter warnings and type-checking (ty check) errors. Fixed all 30 comments from Gemini Code Review bot, adding comprehensive safety checks on JSON/dict parsing, logical operator coercion fixes on pull/push, filename sanitization sync, and robust directory path resolution.

## [2026-06-18] ingest | 452223618 | Resolved remaining comments #31-47 from review bot (including case-insensitive UUID matching, index fallback consistency, pull input validation, and frozen dataclasses mutation fix). Reverted V2 case views support from production code to match platform release status.

## [2026-06-18] start | wiz_remove_related_issue_severity

## [2026-06-18] ingest | wiz_remove_related_issue_severity | Removed the optional Related Issue Severity parameter from the List Resource Vulnerability Findings action's YAML definition, python scripts, API client, query builder, and unit tests. Verified all tests passed successfully.

## [2026-06-18] start | PR-957

## [2026-06-18] ingest | PR-957 | Fixed E501 line-too-long linter failure by extracting html_content file read into a local variable in build.py.

## [2026-06-19] ingest | 452223618 | Updated API key verification endpoint to GetOverviewTemplateCards to support remote SaaS environments and prevent 404 errors during login.

## [2026-06-19] ingest | 452223618 | Fixed widget conditions list camelCase to PascalCase normalization on pull, and PascalCase to camelCase denormalization on push. Expanded WidgetType enum to support SaaS-only values 22-29 (COMPOSITE_ALERT, RULE_OVERVIEW, CASE_DETECTIONS, etc.) to prevent ValueError parser crashes.

