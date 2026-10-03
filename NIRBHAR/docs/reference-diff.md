# Reference Diff — NIRBHAR Showcase Seed Validation

This file logs any discrepancies between externally supplied reference data and the values computed or used in the NIRBHAR Showcase.

Per the design brief, every external numerical result is treated as unverified until it is recomputed in-browser. If our computed result differs, we show our value and log the difference here.

Per the same requirement, if reference data is hard-coded, inconsistent, or physically implausible, we flag it here and fix it in our copy with a note.

---

## Status

The current project uses its own seeded synthetic dataset and does not depend on any external reference prototype. No external-reference diff entries are currently required.
When external benchmark or refinery data is provided, add entries in the format below.

---

## Log Format

| Instance | Reference value | Our value | Likely reason |
|----------|----------------|-----------|---------------|
| (example) afiro objective | −464.5 | −464.7531428571 | Reference shows rounded display value; ours matches Netlib readme exactly |

---

(No entries yet — no external reference dataset is currently in use)
