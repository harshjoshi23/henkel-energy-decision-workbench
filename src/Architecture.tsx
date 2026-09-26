export function Architecture() {
  return (
    <section aria-labelledby="architecture-heading">
      <div className="section-heading">
        <p className="eyebrow">System design</p>
        <h2 id="architecture-heading">
          A traceable decision, not an autonomous controller
        </h2>
        <p>
          The demonstration separates evidence, deterministic arithmetic and
          human judgment. It has no connection to Henkel systems or plant
          controls.
        </p>
      </div>
      <figure className="diagram">
        <img
          src="/diagrams/decision-flow.svg"
          alt="Fictional teaching boundary: gas supplies CHP and boiler; CHP and grid provide electricity; CHP and boiler provide heat. Alternatives must satisfy equal service."
        />
        <figcaption className="muted">
          Conceptual teaching boundary only. Not a Henkel site schematic or a
          verified current asset configuration. Heat quality, constraints and
          authority must be validated separately.
        </figcaption>
      </figure>
      <div className="flow-steps">
        <article className="step">
          <span className="pill">01 · Planner</span>
          <h3>Declare the question</h3>
          <p>
            Set a synthetic scenario, matched service and product boundary. Keep
            missing customer inputs visible.
          </p>
        </article>
        <article className="step">
          <span className="pill">02 · Evidence</span>
          <h3>Keep provenance</h3>
          <p>
            Attach stable source IDs, dates, scopes and limitations. Evidence
            does not automatically validate a scenario input.
          </p>
        </article>
        <article className="step">
          <span className="pill">03 · Calculator</span>
          <h3>Use one authority</h3>
          <p>
            Python computes feasible comparisons and sensitivities. Numerical
            claims come from calculation code, not generated prose.
          </p>
        </article>
        <article className="step">
          <span className="pill">04 · Verifier</span>
          <h3>Check the result</h3>
          <p>
            Inspect units, feasibility, synthetic labels and input/output
            consistency. Human review owns the decision; failed or stale results
            must remain visible.
          </p>
        </article>
      </div>
      <p className="callout">
        These names describe logical responsibilities and deterministic
        functions. They are not four live LLM agents. Defined checks are not
        proof that every application evaluation has passed.
      </p>
      <figure className="diagram">
        <img
          src="/diagrams/architecture.svg"
          alt="Browser scenario passes to stateless Python API and authoritative economics; results return as frozen decision snapshots and downloadable exports. No customer-system connection."
        />
        <figcaption className="muted">
          Application boundary: explicit inputs → validated calculation → result
          snapshot and export. A snapshot records an input/result version; it
          does not imply persistent cloud storage.
        </figcaption>
      </figure>
      <div className="grid-2">
        <article className="card">
          <h3>Controls that matter</h3>
          <ul>
            <li>Preserve synthetic labels across screen and export.</li>
            <li>
              Reject invalid or infeasible inputs before recommending an action.
            </li>
            <li>Invalidate old results when inputs change.</li>
            <li>
              Keep C01 independent of C03 until a coupled model reconciles them.
            </li>
            <li>
              Show errors and unknowns rather than inventing a favorable result.
            </li>
          </ul>
        </article>
        <article className="card">
          <h3>Extensions remain off</h3>
          <p>
            <strong>Forecasting:</strong> requires decision-relevant data,
            chronological evaluation and a benchmark.
          </p>
          <p>
            <strong>LLM:</strong> requires grounded tool/citation evaluations
            and deterministic fallback.
          </p>
          <p>
            <strong>Convex / n8n:</strong> require a justified persistence or
            workflow need, access controls and reviewed execution boundaries.
          </p>
          <p className="muted">
            No live trading, automated plant action, customer-data ingestion or
            production-scale claim.
          </p>
        </article>
      </div>
    </section>
  );
}
