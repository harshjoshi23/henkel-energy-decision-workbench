import { useEffect, useRef, useState } from "react";
import { Evidence } from "./Evidence";
import { Architecture } from "./Architecture";

type Candidate = "C03" | "C01";
type Tab = Candidate | "Evidence" | "Method" | "Checks";
type Inputs = Record<string, string>;
type Metric = string | null;
type Snapshot = {
  id: string;
  createdAt: string;
  candidate: Candidate;
  revision: number;
  dataMode: string;
  inputs: Inputs;
  units: Inputs;
  methodHash: string;
  sourceHash: string;
  metrics: {
    feasible: boolean;
    reason: string;
    cost_a: Metric;
    cost_b: Metric;
    alternative_energy_cost: Metric;
    incremental_cost: Metric;
    net: Metric;
    per_tonne: Metric;
    choice: string;
    policy_benefit: Metric;
    policy_per_tonne: Metric;
    break_even: Metric;
  };
  trace: { label: string; value: Metric; unit: string }[];
  sensitivity: {
    electricity_price: string;
    per_tonne: Metric;
    feasible: boolean;
  }[];
};
type Result = { snapshot: Snapshot; markdown: string };
type Check = {
  id: string;
  status: string;
  expected: unknown;
  observed: unknown;
};
type Checks = {
  executedAt: string;
  methodHash: string;
  cases: Check[];
  scope: string;
};

const fields: Record<
  string,
  { label: string; unit: string; help: string; min?: string; max?: string }
> = {
  gas_price: {
    label: "Fuel price",
    unit: "EUR/MWh_fuel",
    help: "Applicable external purchase price; fictional here.",
  },
  electricity_price: {
    label: "Electricity price",
    unit: "EUR/MWh_electric",
    help: "Applicable purchase price, not an assumed spot-market exposure.",
  },
  k: {
    label: "Incremental cost",
    unit: "EUR",
    help: "Additional cash cost for this period, deducted once.",
    min: "0",
  },
  q: {
    label: "Matching product output",
    unit: "t_product",
    help: "Same period, product mix, quality and service boundary.",
    min: "0.000001",
  },
  alpha: {
    label: "Switch fraction",
    unit: "fraction",
    help: "0 = baseline; 1 = full fictional switch. Real turndown is unknown.",
    min: "0",
    max: "1",
  },
  boiler_heat_limit: {
    label: "Boiler useful-heat limit",
    unit: "MWh_th",
    help: "A toy feasibility constraint; not an actual plant rating.",
    min: "0",
  },
  gas_gap: {
    label: "Residual fuel intensity gap",
    unit: "MWh_fuel/t_product",
    help: "Avoidable external purchased fuel per product tonne.",
  },
  electric_gap: {
    label: "Residual electricity intensity gap",
    unit: "MWh_electric/t_product",
    help: "Avoidable purchased electricity per product tonne.",
  },
};
const fieldKeys: Record<Candidate, string[]> = {
  C03: [
    "gas_price",
    "electricity_price",
    "alpha",
    "k",
    "boiler_heat_limit",
    "q",
  ],
  C01: ["gas_gap", "electric_gap", "gas_price", "electricity_price", "k", "q"],
};
const presets: Record<Candidate, { name: string; inputs: Inputs }[]> = {
  C03: [
    {
      name: "Base switch",
      inputs: {
        gas_price: "40",
        electricity_price: "40",
        alpha: "1",
        k: "0",
        boiler_heat_limit: "9",
        q: "20",
      },
    },
    {
      name: "Higher power price",
      inputs: {
        gas_price: "40",
        electricity_price: "120",
        alpha: "1",
        k: "0",
        boiler_heat_limit: "9",
        q: "20",
      },
    },
    {
      name: "Limited flexibility",
      inputs: {
        gas_price: "40",
        electricity_price: "40",
        alpha: "0.25",
        k: "60",
        boiler_heat_limit: "9",
        q: "20",
      },
    },
    {
      name: "Infeasible switch",
      inputs: {
        gas_price: "40",
        electricity_price: "40",
        alpha: "1",
        k: "0",
        boiler_heat_limit: "8",
        q: "20",
      },
    },
  ],
  C01: [
    {
      name: "Residual improvement",
      inputs: {
        gas_gap: "0.01",
        electric_gap: "0.002",
        gas_price: "40",
        electricity_price: "120",
        k: "6",
        q: "20",
      },
    },
    {
      name: "Cost exceeds benefit",
      inputs: {
        gas_gap: "0.01",
        electric_gap: "0.002",
        gas_price: "40",
        electricity_price: "120",
        k: "15",
        q: "20",
      },
    },
    {
      name: "Break-even cost",
      inputs: {
        gas_gap: "0.01",
        electric_gap: "0.002",
        gas_price: "40",
        electricity_price: "120",
        k: "12.8",
        q: "20",
      },
    },
  ],
};
// Number conversion is for display and SVG coordinates only. All money comes from Python.
function number(value: Metric, digits = 2) {
  if (value === null || value === undefined) return "Not admissible";
  return new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number(value));
}
function download(content: string, filename: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function stringify(value: unknown) {
  return typeof value === "string" ? value : JSON.stringify(value);
}

function CostChart({ snapshot: s }: { snapshot: Snapshot }) {
  const rows =
    s.candidate === "C03"
      ? [
          { name: "Baseline A", value: s.metrics.cost_a },
          { name: "Alternative B · includes K", value: s.metrics.cost_b },
        ]
      : [
          { name: "Signed change", value: s.metrics.net },
          { name: "Selected policy", value: s.metrics.policy_benefit },
        ];
  const max = Math.max(1, ...rows.map((x) => Math.abs(Number(x.value || 0))));
  return (
    <div className="chart-card">
      <h3>
        {s.candidate === "C03"
          ? "External cost comparison"
          : "Change for the matched period"}
      </h3>
      <p className="muted">EUR · synthetic, one modeled period</p>
      <svg
        viewBox="0 0 550 162"
        role="img"
        aria-label="Cost comparison, exact values in adjacent labels"
      >
        {rows.map((r, i) => (
          <g key={r.name} transform={`translate(0 ${i * 77})`}>
            <text x="0" y="20" className="chart-label">
              {r.name}
            </text>
            <rect x="0" y="32" width="380" height="24" rx="4" fill="#e7eeeb" />
            {r.value !== null && (
              <rect
                x="0"
                y="32"
                width={(Math.abs(Number(r.value)) / max) * 380}
                height="24"
                rx="4"
                fill={
                  Number(r.value) < 0
                    ? "#a74330"
                    : i === 0
                      ? "#70828a"
                      : "#087d73"
                }
              />
            )}
            <text x="396" y="49" className="chart-value">
              {r.value === null ? "Infeasible" : number(r.value)}
            </text>
          </g>
        ))}
      </svg>
      <p className="caption">
        Bar length shows magnitude. Signed values remain visible; no value is
        estimated for an infeasible alternative.
      </p>
    </div>
  );
}
function Sensitivity({ snapshot: s }: { snapshot: Snapshot }) {
  const points = s.sensitivity.filter((p) => p.per_tonne !== null);
  if (!points.length)
    return (
      <div className="callout">
        No admissible sensitivity curve under this feasibility constraint.
      </div>
    );
  const xs = points.map((p) => Number(p.electricity_price));
  const ys = points.map((p) => Number(p.per_tonne));
  const xmin = Math.min(...xs);
  const xmax = Math.max(...xs);
  const ymin = Math.min(0, ...ys);
  const ymax = Math.max(0, ...ys);
  const x = (v: number) => 50 + ((v - xmin) / (xmax - xmin || 1)) * 440;
  const y = (v: number) => 190 - ((v - ymin) / (ymax - ymin || 1)) * 145;
  return (
    <div className="chart-card">
      <h3>Where does the decision reverse?</h3>
      <p className="muted">
        Electricity price sensitivity · other inputs held fixed by Python
      </p>
      <svg
        viewBox="0 0 550 245"
        role="img"
        aria-label="Signed value per product tonne across electricity-price scenarios"
      >
        <line
          x1="50"
          x2="490"
          y1={y(0)}
          y2={y(0)}
          stroke="#94a3a8"
          strokeDasharray="4 4"
        />
        <text x="8" y={y(0) + 4} className="chart-label">
          0
        </text>
        <polyline
          points={points
            .map(
              (p) =>
                `${x(Number(p.electricity_price))},${y(Number(p.per_tonne))}`,
            )
            .join(" ")}
          fill="none"
          stroke="#087d73"
          strokeWidth="3"
        />
        {points.map((p) => (
          <circle
            key={p.electricity_price}
            cx={x(Number(p.electricity_price))}
            cy={y(Number(p.per_tonne))}
            r="4"
            fill="#087d73"
          >
            <title>
              {p.electricity_price} EUR/MWh_electric: {p.per_tonne}{" "}
              EUR/t_product
            </title>
          </circle>
        ))}
        <text x="50" y="218" className="chart-label">
          {xmin}
        </text>
        <text x="470" y="218" className="chart-label">
          {xmax}
        </text>
        <text x="50" y="24" className="chart-label">
          EUR/t_product
        </text>
        <text x="165" y="239" className="chart-label">
          Electricity price · EUR/MWh_electric
        </text>
      </svg>
      <details>
        <summary>Read the exact sensitivity values</summary>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Electricity price</th>
                <th>Signed EUR/t_product</th>
              </tr>
            </thead>
            <tbody>
              {s.sensitivity.map((p) => (
                <tr key={p.electricity_price}>
                  <td>{p.electricity_price}</td>
                  <td>{p.per_tonne ?? "Not admissible"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
function ResultView({ result, stale }: { result: Result; stale: boolean }) {
  const s = result.snapshot;
  const m = s.metrics;
  return (
    <section
      className={`result-panel ${stale ? "stale" : ""}`}
      aria-label="Calculation result"
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">Frozen calculation · revision {s.revision}</p>
          <h2>
            {stale
              ? "Inputs changed — recalculate"
              : "A decision you can inspect"}
          </h2>
        </div>
        <span className={`pill ${!m.feasible ? "warning" : ""}`}>
          {stale
            ? "STALE"
            : m.feasible
              ? s.candidate === "C01"
                ? "ARITHMETIC ONLY"
                : "TOY CONSTRAINTS MET"
              : "INFEASIBLE"}
        </span>
      </div>
      {stale && (
        <p className="callout warning" role="status">
          This is the previous result. Approval was reset and exports are
          disabled until the new inputs are accepted and calculated.
        </p>
      )}
      <div className="metrics">
        <article className="metric primary">
          <span>
            Signed {s.candidate === "C03" ? "switch" : "residual"} value
          </span>
          <strong data-testid="per-tonne">{number(m.per_tonne)}</strong>
          <small>EUR / product tonne</small>
        </article>
        <article className="metric">
          <span>Chosen toy policy</span>
          <strong data-testid="choice">
            {m.choice === "B" ? "Alternative B" : "Retain baseline A"}
          </strong>
          <small>{m.reason}</small>
        </article>
        <article className="metric">
          <span>Policy value</span>
          <strong data-testid="policy-value">
            {number(m.policy_per_tonne)}
          </strong>
          <small>EUR / product tonne · baseline may be retained</small>
        </article>
      </div>
      <p className="callout">
        {!m.feasible
          ? "An infeasible switch has no admissible switching value. Keeping baseline A has zero incremental policy benefit."
          : m.choice === "A"
            ? "A negative or zero switch value does not justify changing the baseline under this cost-only rule."
            : "The alternative has lower modeled cost under these fictional inputs. Real feasibility and authority remain unverified."}
      </p>
      <div className="grid-2">
        <CostChart snapshot={s} />
        <Sensitivity snapshot={s} />
      </div>
      <div className="card">
        <h3>Calculation trace</h3>
        <p className="muted">
          Unrounded decimal strings from Python. K is counted once.
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Step</th>
                <th>Value</th>
                <th>Unit</th>
              </tr>
            </thead>
            <tbody>
              {s.trace.map((t, i) => (
                <tr key={i}>
                  <td>{t.label}</td>
                  <td className="mono">
                    {t.value ?? "Unknown / not admissible"}
                  </td>
                  <td>{t.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="export-bar">
        <div>
          <h3>Take the exact result with you</h3>
          <p>
            Inputs, limits, source and method fingerprints travel with this
            snapshot.
          </p>
        </div>
        <div className="button-row">
          <button
            disabled={stale}
            onClick={() =>
              download(
                JSON.stringify(s, null, 2),
                `${s.candidate}-${s.id.slice(0, 12)}.json`,
                "application/json",
              )
            }
          >
            Export JSON
          </button>
          <button
            disabled={stale}
            onClick={() =>
              download(
                result.markdown,
                `${s.candidate}-${s.id.slice(0, 12)}.md`,
                "text/markdown",
              )
            }
          >
            Export Markdown
          </button>
        </div>
      </div>
      <details className="provenance">
        <summary>Preview exact exports</summary>
        <p>
          These read-only previews are the same frozen content used by the
          download buttons. If your browser blocks downloads, copy the content
          here. Stale previews describe the previous revision.
        </p>
        <label htmlFor={`${s.candidate}-json`}>JSON snapshot</label>
        <textarea
          id={`${s.candidate}-json`}
          readOnly
          rows={10}
          value={JSON.stringify(s, null, 2)}
        />
        <label htmlFor={`${s.candidate}-markdown`}>Markdown snapshot</label>
        <textarea
          id={`${s.candidate}-markdown`}
          readOnly
          rows={10}
          value={result.markdown}
        />
      </details>
      <details className="provenance">
        <summary>Inspect provenance and all frozen inputs</summary>
        <dl>
          <dt>Result ID</dt>
          <dd>{s.id}</dd>
          <dt>Calculated at</dt>
          <dd>{s.createdAt}</dd>
          <dt>Python engine SHA-256</dt>
          <dd>{s.methodHash}</dd>
          <dt>Evidence SHA-256</dt>
          <dd>{s.sourceHash}</dd>
        </dl>
        <pre>{JSON.stringify(s.inputs, null, 2)}</pre>
        <p>
          These fingerprints identify content; they are not signatures or
          independent certification.
        </p>
      </details>
    </section>
  );
}
function Scenario({ candidate }: { candidate: Candidate }) {
  const [inputs, setInputs] = useState<Inputs>(() =>
    Object.fromEntries(fieldKeys[candidate].map((k) => [k, ""])),
  );
  const [revision, setRevision] = useState(1);
  const rev = useRef(1);
  const [approved, setApproved] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  function edit(next: Inputs) {
    controller.current?.abort();
    rev.current += 1;
    setRevision(rev.current);
    setInputs(next);
    setApproved(false);
    setError("");
    setLoading(false);
  }
  async function calculate(e: React.FormEvent) {
    e.preventDefault();
    if (!approved) return;
    const runRevision = revision;
    const abort = new AbortController();
    controller.current?.abort();
    controller.current = abort;
    const timeout = setTimeout(() => abort.abort("timeout"), 15000);
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: abort.signal,
        body: JSON.stringify({
          schemaVersion: "1",
          candidate,
          revision,
          dataMode: "synthetic",
          approved,
          inputs,
          units: Object.fromEntries(
            fieldKeys[candidate].map((k) => [k, fields[k].unit]),
          ),
        }),
      });
      const data = await response.json();
      if (!response.ok)
        throw new Error(
          data.message ||
            (typeof data.error === "string"
              ? data.error
              : data.error?.message) ||
            "The calculation could not be validated.",
        );
      if (runRevision === rev.current && !abort.signal.aborted) setResult(data);
    } catch (err) {
      if (runRevision !== rev.current) return;
      if (!abort.signal.aborted || abort.signal.reason === "timeout")
        setError(
          abort.signal.reason === "timeout"
            ? "Calculation timed out. Check the API and try again."
            : err instanceof Error
              ? err.message
              : "API unavailable. Please try again.",
        );
    } finally {
      clearTimeout(timeout);
      if (runRevision === rev.current) setLoading(false);
    }
  }
  return (
    <>
      <section className="intro">
        <div>
          <p className="eyebrow">
            {candidate === "C03"
              ? "01 / Investigation lead"
              : "02 / Comparison & fallback"}
          </p>
          <h1>
            {candidate === "C03" ? (
              <>
                Heat and power.
                <br />
                One decision boundary.
              </>
            ) : (
              <>
                Find the gap.
                <br />
                Respect the baseline.
              </>
            )}
          </h1>
          <p className="lead">
            {candidate === "C03"
              ? "Compare permitted heat and electricity supply options on one external cost ledger. See when the economics change — and when a switch is infeasible."
              : "Test whether an avoidable dryer energy gap could remain after existing controls. Customer gaps are unknown; start blank or explore a clearly fictional example."}
          </p>
        </div>
        <div className="principle">
          <span className="mini-icon">↗</span>
          <span>THE QUESTION</span>
          <h3>
            {candidate === "C03"
              ? "Is a different feasible supply choice worth making?"
              : "Is there a controllable, additional improvement left?"}
          </h3>
          <p>Method first. Evidence before action.</p>
        </div>
      </section>
      <div className="boundary-strip">
        <span>FIXED SERVICE</span>
        {candidate === "C03"
          ? "Fictional one-hour interval · 45 MWh electricity + 45 MWh useful heat · same product mix and heat quality"
          : "Fictional one-period dryer boundary · directly purchased fuel and electricity · matching product tonnes"}
      </div>
      {candidate === "C01" && (
        <p className="callout warning">
          Do not add this standalone value to C03. If the dryer uses shared
          utilities, recalculate the marginal effect inside the joint
          heat-and-power ledger.
        </p>
      )}
      <section className="card input-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Your scenario</p>
            <h2>Make every assumption visible</h2>
          </div>
          <span className="pill">SYNTHETIC ONLY</span>
        </div>
        <div className="presets">
          <span>Explore a fixture</span>
          {presets[candidate].map((p) => (
            <button key={p.name} onClick={() => edit({ ...p.inputs })}>
              {p.name}
            </button>
          ))}
          <button
            className="text-button"
            onClick={() =>
              edit(Object.fromEntries(fieldKeys[candidate].map((k) => [k, ""])))
            }
          >
            Clear inputs
          </button>
        </div>
        <form onSubmit={calculate}>
          <div className="input-grid">
            {fieldKeys[candidate].map((key) => {
              const f = fields[key];
              return (
                <div className="field" key={key}>
                  <label htmlFor={`${candidate}-${key}`}>{f.label}</label>
                  <div className="input-wrap">
                    <input
                      id={`${candidate}-${key}`}
                      name={key}
                      type="number"
                      step="any"
                      required
                      min={f.min}
                      max={f.max}
                      value={inputs[key]}
                      placeholder="Unknown"
                      onChange={(e) =>
                        edit({ ...inputs, [key]: e.target.value })
                      }
                      aria-describedby={`${candidate}-${key}-help`}
                    />
                    <span>{f.unit}</span>
                  </div>
                  <small id={`${candidate}-${key}-help`}>{f.help}</small>
                </div>
              );
            })}
          </div>
          <label className="approval">
            <input
              type="checkbox"
              checked={approved}
              onChange={(e) => setApproved(e.target.checked)}
            />
            I accept these exact inputs as a fictional scenario. This does not
            authorize a plant action.
          </label>
          <div className="form-footer">
            <p>Revision {revision} · changing an input resets acceptance.</p>
            <button
              className="primary-button"
              type="submit"
              disabled={!approved || loading}
            >
              {loading ? "Calculating…" : "Calculate scenario"}{" "}
              <span aria-hidden="true">→</span>
            </button>
          </div>
        </form>
        {error && (
          <div className="callout warning" role="alert">
            {error} Your entered inputs are preserved.
          </div>
        )}
        {loading && (
          <p role="status">Validating inputs and running the Python engine…</p>
        )}
      </section>
      {result ? (
        <ResultView
          result={result}
          stale={result.snapshot.revision !== revision || !approved}
        />
      ) : (
        <section className="empty-state">
          <span aria-hidden="true">◎</span>
          <h2>No result has been calculated</h2>
          <p>
            Load a fictional fixture or enter synthetic inputs, accept the
            scenario, then calculate. Missing customer values never become zero.
          </p>
        </section>
      )}
      <section className="next-step">
        <p className="eyebrow">From demonstration to investigation</p>
        <h2>One report. One responsible owner.</h2>
        <div className="grid-2">
          <p>
            <strong>Request:</strong> one existing utilities operating/dispatch
            report, with the definitions already used to interpret it. First
            establish the real boundary and permitted alternatives.
          </p>
          <p>
            <strong>Meet:</strong> the site utilities / energy operations owner
            for 30 minutes. Confirm feasibility, authority and who owns the
            resulting cash flows.
          </p>
        </div>
        <p className="muted">
          If dispatch rights or applicable commercial terms decide whether any
          action is possible, ask for that evidence first instead. This is a
          conditional priority, not a bundled request for every dataset.
        </p>
      </section>
    </>
  );
}
function CheckView() {
  const [data, setData] = useState<Checks | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function run() {
    setLoading(true);
    setError("");
    setData(null);
    try {
      const r = await fetch("/api/checks", {
        signal: AbortSignal.timeout(15000),
      });
      const d = await r.json();
      if (!r.ok) throw new Error("Checks endpoint failed.");
      setData(d);
    } catch {
      setError(
        "Could not execute checks. No pass result is claimed. Check the API and retry.",
      );
    } finally {
      setLoading(false);
    }
  }
  return (
    <>
      <div className="intro">
        <div>
          <p className="eyebrow">Verification / actual execution</p>
          <h1>
            Trust the trace.
            <br />
            Test the boundaries.
          </h1>
          <p className="lead">
            Run the engine and adapter fixtures on this server. These checks
            cover arithmetic and validation; they do not certify Henkel
            operations or this browser.
          </p>
        </div>
      </div>
      <div className="card">
        <button className="primary-button" disabled={loading} onClick={run}>
          {loading ? "Running checks…" : "Run verification checks"}
        </button>
        {error && (
          <p role="alert" className="callout warning">
            {error}
          </p>
        )}
        {!data && !loading && (
          <p className="muted">Not run in this view yet.</p>
        )}
        {loading && <p role="status">Executing checks…</p>}
        {data && (
          <>
            <p className="callout">
              Executed {data.executedAt}. {data.scope}
            </p>
            <p className="mono hash">Engine {data.methodHash}</p>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Case</th>
                    <th>Expected</th>
                    <th>Observed</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.cases.map((c) => (
                    <tr key={c.id}>
                      <td>{c.id}</td>
                      <td>{stringify(c.expected)}</td>
                      <td>{stringify(c.observed)}</td>
                      <td>
                        <span
                          className={`pill ${c.status === "passed" ? "" : "warning"}`}
                        >
                          {c.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
      <div className="grid-2 roadmap">
        <article className="card">
          <h3>Separate release checks</h3>
          <p>
            Browser, export, API-error and mobile tests run from the repository.
            Their recorded release results are separate from this live
            arithmetic check.
          </p>
        </article>
        <article className="card">
          <h3>Not applicable in this build</h3>
          <p>
            Model accuracy, prompt-injection defenses, tenant isolation and
            workflow replay are not marked passed. No LLM, forecasting, private
            workspaces or external workflows are enabled.
          </p>
        </article>
      </div>
    </>
  );
}
export default function App() {
  const [tab, setTab] = useState<Tab>("C03");
  const tabs: { id: Tab; label: string; sub: string }[] = [
    { id: "C03", label: "Coupled utilities", sub: "C03 · lead" },
    { id: "C01", label: "Residual dryer", sub: "C01 · comparison" },
    { id: "Evidence", label: "Evidence & choices", sub: "Sources and limits" },
    { id: "Method", label: "How it works", sub: "Method & architecture" },
    { id: "Checks", label: "Verification", sub: "Execute actual checks" },
  ];
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="app-shell">
        <aside className="sidebar">
          <a
            href="#"
            className="brand"
            onClick={(e) => {
              e.preventDefault();
              setTab("C03");
            }}
          >
            <span className="brand-mark">
              e<span>↗</span>
            </span>
            <span>
              ENERGY
              <br />
              <b>DECISION LAB</b>
            </span>
          </a>
          <div className="side-label">ASSESSMENT COMPANION</div>
          <nav aria-label="Workbench sections">
            {tabs.map((t) => (
              <button
                key={t.id}
                aria-current={tab === t.id ? "page" : undefined}
                className={tab === t.id ? "active" : ""}
                onClick={() => setTab(t.id)}
              >
                <span>{t.label}</span>
                <small>{t.sub}</small>
              </button>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <span className="status-dot" /> Independent demonstration
            <p>
              RIZM / Henkel Düsseldorf
              <br />
              Public evidence. Synthetic scenarios.
            </p>
          </div>
        </aside>
        <div className="main-shell">
          <header className="topbar">
            <span>
              Energy Decision Workbench <span className="version">v1.0</span>
            </span>
            <span className="synthetic-badge">
              SYNTHETIC · NO PLANT CONNECTION
            </span>
          </header>
          <main id="main" tabIndex={-1}>
            {/* Keep both scenarios mounted: tab changes preserve accepted snapshots. */}
            <div hidden={tab !== "C03"}>
              <Scenario candidate="C03" />
            </div>
            <div hidden={tab !== "C01"}>
              <Scenario candidate="C01" />
            </div>
            {tab === "Evidence" && <Evidence />}
            {tab === "Method" && <Architecture />}
            {tab === "Checks" && <CheckView />}
          </main>
          <footer>
            Independent assessment companion · Not RIZM software · Not a Henkel
            digital twin or energy audit.
            <br />
            Decisions stay with people. The six-file assessment remains
            independently usable.
          </footer>
        </div>
      </div>
    </>
  );
}
