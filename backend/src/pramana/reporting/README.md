# reporting

## Purpose
Per-device compliance reports. One Jinja2 template (autoescape ON) renders both the
HTML preview and the WeasyPrint PDF. One definition, never two.

## Public API (`api.py`)
| Export | Description |
|---|---|
| `ReportData` | Canonical JSON object; SHA-256 printed in footer |
| `ReportingError` | Report generation failure |
| `ReportingService` | `build_report_data()` / `render_html()` / `render_pdf()` |

## Invariants
- **INV-07** Two-number scores always shown side by side.
- **INV-08** Every verdict carries trust class and evidence pointers.
- **INV-15** Residual risk stated in Appendix B; never claimed solved.
- **INV-16** Secrets redacted before rendering.
- Unverified framework mappings tagged in report.

## Track / Tier
Track 5 · Tier 1 (signing T3)

## Owner
Track 5
