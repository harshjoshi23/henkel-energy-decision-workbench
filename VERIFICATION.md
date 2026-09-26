# Verification — 26 September 2026

This record distinguishes local implementation checks, actual hosted verification and remaining limitations. It is not a hiring score, a customer savings validation or production-safety certification.

## Final preparation pass

The fresh hosted [run 36248489881](https://github.com/harshjoshi23/henkel-energy-decision-workbench/actions/runs/36248489881), at test revision `9ae50108425cc18e7216bb308a1edf197f2f4993`, passed **22 smoke checks and all 12 browser tests** (7.7 seconds for the browser suite). It captured the two actual synthetic-app screenshots now used by the README. This rerun is separate from the earlier evidence below.

The deployed runtime remains source `5424dc53fd12450417750c7c7d11c652e9f98d00`. The later test and README commits do not change runtime code. A fresh public fetch compared both deployed JavaScript/CSS assets and both diagrams with the local build: all four matched byte-for-byte. No unnecessary redeployment was performed for documentation changes.

A bounded independent security review checked the six-commit history at `1e4bc78` (42 unique blobs), followed by five changed blobs in `9ae5010` and `82511d9`. Configured secret/private-path patterns found no matches, and the two new screenshots were visually checked for private content. The review did not read local secret stores or environment contents. Its 21 unit tests and 12 additional in-memory handler probes passed. The reviewer could not rerun live network or socket checks in its environment; hosted checks above ran in GitHub Actions. A fresh `npm audit --json` reported zero known vulnerabilities at the time of this pass.

This is a scoped review, not proof of absolute security. Public abuse/rate/spend controls and hosting-log retention were not verified. The app has no database, but that does not establish that hosting infrastructure retains no request data. Use fictional inputs only. The confirmation checkbox is not authentication, and content hashes are not signatures or proof that inputs are true. No formal penetration test, capacity test or comprehensive accessibility audit was performed.

The frozen six-file assessment remains a separate, byte-identical release. Its earlier app-status statement belongs to that edition; the current README describes this later companion. The public role page was reviewed previously, but a separate detailed scorecard was not recovered or claimed as read. The owner supplies the assessment repository and optional video links when available.

| Check | Actual result |
|---|---|
| Frozen assessment economics | 34 embedded checks passed; copied engine and saved trace match the reviewed assessment bytes. |
| Python adapter and real loopback HTTP suite | 29 tests passed in the coordinator's environment. Includes validation, units, missing/zero/non-finite inputs, negative values, K once, infeasibility, evidence, exports and safe error responses. |
| Production build | TypeScript no-emit and Vite build passed. |
| Dependency audit | npm install reported zero known vulnerabilities for the 30 installed package records at that execution. This is not a guarantee of absence of vulnerabilities. |
| UI fixture checks through the controlled in-app browser | All seven acceptance fixtures rendered the expected signed value and selected policy. JSON and Markdown previews matched the displayed result, snapshot ID and exact underlying metric. |
| UI guards | Blank state, disabled calculation before acceptance, approval reset after edit, stale-result warning and disabled export observed. An out-of-range request returned a visible validation message and preserved inputs. |
| UI evidence / visuals | Evidence cards rendered; both SVG diagrams loaded. Desktop result layout inspected. At 390-pixel viewport, page width was 390 pixels with no horizontal overflow. |
| Live checks view | 44 actual server assertions (34 engine + 10 adapter parity cases) executed and displayed passed. This is a narrower scope than the whole release. |
| Automated Playwright suite | **12/12 passed on Linux GitHub Actions**, including all fixture API/UI/download parity cases, delayed-response staleness, injected API failure, input validation and mobile layout. The initial macOS attempt was blocked before page execution; CI resolved that environment limitation. |
| Native download delivery | Confirmed for all seven fixtures on the final formatted UI: 14 JSON/Markdown files were downloaded. Their content matched the visible previews; each Markdown file exactly matched the Python renderer applied to the downloaded JSON. The earlier event timeout was a browser-control notification limitation, not a failed file download. |
| Deployment | **Live and verified** at [the public workbench](https://henkel-energy-decision-workbench.vercel.app); both Python functions, static assets, headers and ordinary reviewer access passed unauthenticated checks. |
| Hosted release suite | [Run 36246111118](https://github.com/harshjoshi23/henkel-energy-decision-workbench/actions/runs/36246111118) passed **22 HTTP/API/export smoke checks and 12/12 browser tests** against the production URL. Includes seven API/UI/JSON/Markdown cases, validation, negative results, infeasibility, stale responses and mobile layout. |
| GitHub remote | Published to the owner-confirmed public [repository](https://github.com/harshjoshi23/henkel-energy-decision-workbench). Implementation commit `fff94133b1eaab6177e473578b7a6fc64960fa26` passed [CI run 36244908051](https://github.com/harshjoshi23/henkel-energy-decision-workbench/actions/runs/36244908051). |

The seven browser-observed signed values were C03: `6`, `-22`, `-1.5`, and `null` for the infeasible switch; C01: `0.34`, `-0.11`, and `0`. For each, the JSON preview and Markdown preview preserved the same result ID and metric. Negative C03 switches retained baseline A with zero incremental policy value.

## Deployment identity and repeatability

- Public URL: https://henkel-energy-decision-workbench.vercel.app
- Immutable deployment: https://henkel-energy-decision-workbench-mh1au3ouh.vercel.app
- Vercel deployment ID: `dpl_86wWt4JGDpcv9ko81KNq2KLd9SmW`; personal workspace `harshjoshi23s-projects`.
- Deployed source: `5424dc53fd12450417750c7c7d11c652e9f98d00`; generated `dist` is excluded from uploads and rebuilt on hosting. Both Python functions use Python 3.12.
- Hosted test revision: `fa31486b11bfc7c70828413e0a94b9c107e67301`. Later test/documentation commits do not change the deployed application. The smoke checker verifies the hosted engine, adapter and evidence hashes against the checkout.
- First deployment was automatically assigned to production by Vercel and verified there. No prior preview promotion is claimed.
- GitHub automatic deployment connection failed; publishing source and direct CLI deployment succeeded. Future pushes do not update the live app until the Git integration is connected or a new CLI deployment is made.
- Render remains reserved for future forecasting jobs by owner choice. No Render resources were created.

## Reproduce release verification

Follow the root README commands. Linux CI successfully ran the actual browser suite: 12 tests passed in 8.0 seconds, alongside the 29 Python tests, 34 engine assertions and production build. It compares downloaded JSON/Markdown with the API response and exercises delayed requests, API failure, negative prices and mobile layout. The macOS launch restriction remains specific to that local environment.

The public hosted suite passed in [run 36246111118](https://github.com/harshjoshi23/henkel-energy-decision-workbench/actions/runs/36246111118): 22 smoke checks and 12 browser tests (8.7 seconds). The earlier [run 36245836454](https://github.com/harshjoshi23/henkel-energy-decision-workbench/actions/runs/36245836454) was **11/12**, because the delayed-response test ended before its route completed and leaked a teardown error into the next test. The test now waits until a response is held, edits inputs, releases it and waits for route completion before checking that the UI is still stale. No failure was ignored and no application code changed. [Local CI at the corrected test revision also passed](https://github.com/harshjoshi23/henkel-energy-decision-workbench/actions/runs/36245950589).

Run `python3 -B scripts/smoke_hosted.py --base-url https://henkel-energy-decision-workbench.vercel.app` and `PLAYWRIGHT_BASE_URL=https://henkel-energy-decision-workbench.vercel.app npm run test:e2e`, or dispatch **Verify public deployment** in GitHub Actions. The smoke test uses synthetic requests, requires no credentials, checks HTTP headers and fingerprints, and compares server Markdown to the authoritative renderer. Hosted packaging is verified; hosting capacity remains untested.

No customer data, trained forecast, LLM, private workspace or external automation is enabled; their corresponding evaluations are not applicable, not passed. Full assistive-technology testing, load testing, a formal security audit and real plant feasibility remain outside the executed checks.

## Independent review

A separate verifier checked the frozen assessment baseline (34 economics checks, 14 publication/tool tests, zero repository-check errors or warnings, identical source/release/staging/manifest bytes). It also independently passed 21 app calculation/export tests and TypeScript checking; its sandbox blocked real socket tests. The coordinator's 29-test HTTP-inclusive run is distinguished above. Independent review found no material defect in the local implementation; scoped score **9/10**. The verifier ran 34 engine checks, 21 calculation/export tests, TypeScript checking and 80 separately recomputed Decimal scenarios; its HTTP setup was sandbox-blocked. Download delivery was subsequently confirmed by the coordinator for all seven fixtures on the final formatted UI. Linux CI subsequently passed all automated browser cases on the implementation commit. The deployment follow-up independently reviewed the upload exclusions, smoke checker, hosted workflow and test-race correction. Its environment could not perform a live network fetch, so remote results are attributed to the coordinator and GitHub Actions, not presented as an independent live rerun. The historical local review score is not a production-safety rating.
