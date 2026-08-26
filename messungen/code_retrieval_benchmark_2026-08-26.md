# Frozen multilingual code-retrieval measurement — 2026-08-26

> **INVALIDATED — retained audit evidence.** `L-0f0b4b` found that its queries
> contained target symbol identifiers also present in positive candidates. The
> reported gains and route activation are not semantic evidence and must not be
> used. A replacement fixture rejects exact/split/case identifier and file leaks
> before any new frozen rerun.

## Replacement v2 (leak-free, BGE-only decision)

- Fixture manifest SHA-256: `57d6201f9929248f09cfa79837a88d108f85d63eb065de71b60feafdca044c85`
- Full 28-matrix report SHA-256: `77d59017125d8cd62a1f041b257121dd141bce0d87885fc599b6f8e0b3424da0`
- Decision report SHA-256: `28d136573fbc69e0a488cdce334cdbeeaefc9848b17cd68ff9db8195de44cba7`
- 140 generated cases passed exact/split/case/file identifier exclusion. Every
  language now has four source candidates: three positive targets plus a
  same-language numeric-range implementation as a dedicated code hard negative.
- All candidate channels were measured separately with the documented CodeRank
  query prefix. CodeRank, RRF and the fixed modality router each fail at least
  one mandatory-matrix non-regression gate; BGE-M3 therefore remains the sole
  active channel. The v2 router has macro gains `+0.023810` Recall@1 and
  `+0.016865` MRR, but is ineligible because it loses Recall@1 in a required
  matrix. Prose-control Recall@1 is unchanged at `0.800` for BGE-M3/router.

This is the compact, reproducible evidence record; model caches, vectors and
the full per-query reports remain outside Git under `/Volumes/daten`.

## Frozen inputs and decision rule

- Fixture manifest SHA-256: `2cdc570a731ba4e04e4e59a802b15c8c9bee9b3c92454c576823a96a8b6985b5`
- Existing prose-control goldset SHA-256: `c0a5b760955c064175f8067c7288bd1318f435ab5e8d5deb683e959b7662ef20`
- First local report SHA-256: `5feff18b314f072a3f49f232c33d60a0cf06c3cebf0b4a4f80091fbb9a77b1e4`
- Idle rerun report SHA-256: `4f9ea49aae12a6a9b5c21d561f9703c7664dd4deeed3c21ca2d1f0be82c68c57`
- Seven syntax-validated languages × four modalities: signature → implementation,
  code → consumer, German prose → code, English prose → code; three targets each.
- Candidates: BGE-M3, CodeRankEmbed with its required query prefix, fixed RRF (`k=60`),
  and a fixed router: `signature_to_implementation|code_to_consumer → CodeRankEmbed`,
  all other or ambiguous modalities → BGE-M3. The rule was registered before results.
- Activation needs ≥0.01 macro gain in Recall@1 and MRR, zero Recall@1 loss in each
  mandatory matrix, and zero Recall@1 loss in the frozen German prose control.

## Accuracy result

| Language | BGE-M3 R@1 / MRR | Fixed router R@1 / MRR |
| --- | --- | --- |
| Python | 0.750 / 0.847 | 1.000 / 1.000 |
| TypeScript | 0.833 / 0.917 | 0.833 / 0.917 |
| Rust | 0.833 / 0.903 | 1.000 / 1.000 |
| Java | 0.667 / 0.819 | 0.667 / 0.833 |
| Go | 0.833 / 0.917 | 0.917 / 0.958 |
| Swift | 0.500 / 0.750 | 0.833 / 0.917 |
| Dart/Flutter | 0.583 / 0.792 | 0.750 / 0.875 |

All 28 matrices were present.  The router gained `+0.142857` macro Recall@1 and
`+0.079365` macro MRR, with neither mandatory-matrix loss nor prose-control loss
(BGE-M3 and router prose Recall@1: `0.800`).  CodeRankEmbed alone (`0.600`) and
RRF (`0.700`) regress the prose control and are not activated.

The first wall times and RSS were contaminated by concurrent OMLX experiments and
are discarded. After the operator stopped that work, the idle rerun reproduced
every rank/metric exactly. It measured 6.879 seconds for the runner’s encode/rank
sections across the seven isolated processes (model-load startup excluded by the
runner timer) and peak RSS `1512439808` bytes. The compact report’s decision is
the separate, revision-bound CodeRank route for two explicit code modalities. It
does not concatenate vectors or feed raw analyzer payloads into the normal
knowledge index.
