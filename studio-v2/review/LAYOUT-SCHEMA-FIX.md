# Full04: image-record contract repair

2026-11-05. User/relay failure report `WD_DOCSCTL_FULL04_SCHEMA_50c1dba9`: one run, exit 2, KeyError `x_pt`, only partial A4 PDF and glyph report. Reported failure receipt SHA256 `50c1dba9d876b9aeeb1e6ab70f73ac345279d413b2fbd6a3b3aacf1e0d3a61c0`; separate failure-reader receipt `c4c7ffd7dfba422a1dd305b58a732986527d0e5d21bf9e38a08d62d9b37f2740`. These new failure bytes were not attached in this working context; the provided standalone receipt still hashes to the earlier Build03 receipt. Failure details are attributed to the relay, not claimed as freshly byte-verified here.

## Reproduced contract mismatch

The existing raster Painter records physical page-point geometry using `x_pt`, `y_top_pt`, `width_pt`, `height_pt`. The vector provider renderer recorded only page, role, source hash and transformation. That exact geometryless record form exists in the retained Build03 layout evidence (SHA256 in `painter-record-fixtures.json`). Full04's audit unconditionally indexed `x_pt`.

The vector producer now records its actual aspect-fitted placement, not the allocated cell. Top-left origin, physical PDF points, A2 scaling applied exactly once. The drawing command, paths, colors, typography, cover and page functions are unchanged.

The audit validates every record before comparisons. Missing/nonfinite/nonpositive geometry is `IMAGE_RECORD_SCHEMA` and therefore `FAIL_GEOMETRY`; it is never zero-filled, exempted or marked passed. Valid image boxes still participate in text/image collisions. Image bounds, text bounds and text/text guards are retained. Schema errors fail even on a page without text.

## Evidence and regression scope

141 pure tests pass: 123 previous plus 18 focused tests. Fixtures project exact retained record fields/coordinates without private image bytes. The real provider function is invoked with recording-only ReportLab stubs and synthetic inert geometry at the observed viewBox aspect, then passed to the real layout audit. Tests cover A4/A2, actual fitted placement, overlap detected, clear layout, legacy malformed vector, every missing coordinate, NaN/infinity/bools, nonpositive size, page bounds and unchanged input.

These tests do not render PDFs or load fonts. Fresh guest execution and all fourteen page rasters remain NOT_RUN. This is a repaired full-report package, not another mini-proof or a replacement for the Quarto/Typst pipeline. Existing fonts/assets/source text stay unchanged. The failed Full04 output and previous baselines must be retained.

The single owner relay may start the new job only before 2026-11-05 10:00:00 UTC (11:00 Vienna). The private runner enforces this start cutoff; no auto-retry, installation, model/browser launch or additional worker. After cutoff retain the package as a checkpoint, do not start a build/prompt/publisher.

DESIGN_REJECTED / REWORK_REQUIRED and all separate production/native-Mermaid/product/print/integration/user-acceptance gates remain open. No merge or deployment.
