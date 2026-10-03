# NIRBHAR sample data pack

63 models, ~3 MB, all plain-text MPS (uncompressed). `manifest.json` is the source of truth: name, file, class, rows, cols, nnz,
integers, reference objective, how the reference was obtained, split (tune / report / stress / status), tier, and SHA-256.

| Folder | What | Count |
|---|---|---|
| `netlib/` | Real Netlib LPs (decompressed from the COIN-OR `Data-Netlib` repo, commit f1cc423) | 26 |
| `milp/` | Real MIPLIB 3 MILPs (COIN-OR `Data-miplib3`, commit 36c786b) | 18 |
| `qp/` | Generated convex QPs: a Netlib LP plus a PSD Q in a `QUADOBJ` section | 5 |
| `miqp/` | Generated unit-commitment MIQPs, 12 binaries each, brute-force optimum | 2 |
| `stress/` | Beale cycling LP; row/column-rescaled Netlib copies (1e3 and 1e6 tiers) | 9 |
| `infeas/` | `galenet` (Netlib infeasible LP, from COIN-OR `Data-Sample`), plus tiny infeasible and unbounded LPs | 3 |
| `tools/` | Scripts that regenerated everything (needs `highspy`, `numpy`, `scipy`, `cvxpy`) | 3 |

## How the reference values were obtained (measured, not recalled)
* LP / MILP: HiGHS 1.15.1, 1 thread, MIP gap 0. Values agree with the published Netlib / MIPLIB 3 optima that the team knows
  (afiro -464.7531428571, adlittle 225494.9631623, p0033 3089, stein27 18, flugpl 1201500, egout 568.1007, bell5 8966406.49, lseu 1120, gt2 21166).
  Re-check against the Netlib readme before quoting any value as "published" on camera.
* QP: HiGHS QP, then independently confirmed with Clarabel (relative difference <= 2e-9). Convention: `obj = c'x + 0.5 x'Qx`, one triangle of Q listed.
  Q is PSD up to rounding (min eigenvalue about -5e-16), so any PSD check needs a tolerance.
* MIQP: all 2^12 binary assignments enumerated, each continuous QP solved by HiGHS.
* Rescaled LPs: the optimum is **exactly** the original model's optimum (change of variables). At the 1e6 tier HiGHS with default settings
  returns "Optimal" with a **wrong** objective on sc50a, adlittle and kb2 (see `highs_default_objective` in the manifest). This is deliberate:
  it is the case a verifier must catch. The 1e3 tier is solved correctly by HiGHS.
* Infeasible/unbounded: expected status from HiGHS; galenet is a known infeasible Netlib model.

## Parser traps worth testing
`dcmulti.mps` has an `IMPORTANCES` block **after** `ENDATA` (must be ignored). `forplan` uses RANGES. `misc03` has an FR bound. `recipe`/`egout`/`flugpl` use FX and LO bounds.
Bound types MI, PL, LI, UI and negative UP are not present in the pack, so test them with small inline snippets.

## Licences
Netlib models are freely redistributable; MIPLIB 3 is free for research use. Generated files are ours.
