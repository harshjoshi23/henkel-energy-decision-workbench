# Verification — 26 September 2026

This record separates executed local checks from remaining release gates. It is not a hiring score, a customer savings validation or production-safety certification.

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
| Automated Playwright suite | 12 tests authored and attempted. **Blocked before page execution**: macOS sandbox denied Chromium's MachPort bootstrap. None of those 12 executions is claimed passed. |
| Native download delivery | Confirmed for all seven fixtures on the final formatted UI: 14 JSON/Markdown files were downloaded. Their content matched the visible previews; each Markdown file exactly matched the Python renderer applied to the downloaded JSON. The earlier event timeout was a browser-control notification limitation, not a failed file download. |
| Deployment | Not deployed. Vercel CLI reported logged out. Hosting destination and access still need to be established. |
| GitHub remote | Owner confirmed public `harshjoshi23/henkel-energy-decision-workbench`. Creation/push is pending the final local commit; no remote publication is claimed in this record yet. |

The seven browser-observed signed values were C03: `6`, `-22`, `-1.5`, and `null` for the infeasible switch; C01: `0.34`, `-0.11`, and `0`. For each, the JSON preview and Markdown preview preserved the same result ID and metric. Negative C03 switches retained baseline A with zero incremental policy value.

## Reproduce and finish release verification

Follow the root README commands. Run `npm run test:e2e` in an environment that permits Chromium to start; it asserts the actual downloaded JSON and Markdown against the API response. The suite also covers a delayed in-flight response, injected server failure and negative electricity prices; these automated browser cases are authored but not yet executed successfully here. Python equivalents and static race/error review do not replace those browser tests.

After an authorized Vercel preview exists, run the same suite with `PLAYWRIGHT_BASE_URL` set to that URL. Confirm public reviewer access, Python function imports, static assets, security headers and calculation/export behavior. Do not describe the app as live before that smoke check. The local build has not validated Vercel packaging or hosting-scale behavior.

No customer data, trained forecast, LLM, private workspace or external automation is enabled; their corresponding evaluations are not applicable, not passed. Full assistive-technology testing, load testing, a formal security audit and real plant feasibility remain outside the executed checks.

## Independent review

A separate verifier checked the frozen assessment baseline (34 economics checks, 14 publication/tool tests, zero repository-check errors or warnings, identical source/release/staging/manifest bytes). It also independently passed 21 app calculation/export tests and TypeScript checking; its sandbox blocked real socket tests. The coordinator's 29-test HTTP-inclusive run is distinguished above. Independent review found no material defect in the local implementation; scoped score **9/10**. The verifier ran 34 engine checks, 21 calculation/export tests, TypeScript checking and 80 separately recomputed Decimal scenarios; its HTTP setup was sandbox-blocked. Download delivery was subsequently confirmed by the coordinator for all seven fixtures on the final formatted UI. Automated browser race/outage cases and Vercel deployment remain unverified release gates. The included Linux CI workflow is prepared, but no remote workflow result is claimed.
