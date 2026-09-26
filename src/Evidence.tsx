const sources = [
  {
    id: "R07",
    title: "Standort Düsseldorf",
    publisher: "Henkel Deutschland",
    date: "Undated · observed 19 Sep 2026",
    url: "https://www.henkel.de/presse-und-medien/zahlen-und-fakten/standort-duesseldorf",
    fact: "A mixed campus: manufacturing, headquarters, logistics and energy infrastructure.",
    limit:
      "Not a current meter map or matched cost/output dataset. Earlier heat-export wording is superseded by R10.",
  },
  {
    id: "R10",
    title: "Industrial heat for Düsseldorf",
    publisher: "Henkel Deutschland",
    date: "13 Apr 2026 · rechecked 21 Sep 2026",
    url: "https://www.henkel.de/presse-und-medien/presseinformationen-und-pressemappen/2026-04-13-stadtwerke-duesseldorf-und-henkel-versorgen-ab-sofort-den-duesseldorfer-sueden-mit-industrieabwaerme-2142728",
    fact: "Henkel announced the heat-export energy center entering operation, with CHP heat supplementing recovered heat when needed.",
    limit:
      "Commissioning does not establish incremental financial value, current dispatch rights or settlement terms.",
  },
  {
    id: "R64",
    title: "Automatic process control in detergent production",
    publisher: "dena",
    date: "Pilot commissioned Jan 2021 · rechecked 21 Sep 2026",
    url: "https://www.dena.de/energy-award/good-practice/duesseldorf-henkel/",
    fact: "Existing Düsseldorf spray-dryer control reportedly saved 1,800 MWh gas and 300 MWh electricity annually.",
    limit:
      "Historical existing-project savings are not residual opportunity. Matching process output, prices and full costs are unavailable.",
  },
  {
    id: "R65",
    title: "Henkel Annual Report 2025",
    publisher: "Henkel",
    date: "Reporting year 2025 · accessed 20 Sep 2026",
    url: "https://www.henkel.com/resource/blob/2131544/e5b32595fccb9c899816cfb539438f41/data/2025-annual-report.pdf",
    fact: "Printed pages 203–204 discuss the Düsseldorf power plant and third-party energy boundary.",
    limit:
      "Group consumption is not site consumption. This does not provide current operating curves or plant economics.",
  },
  {
    id: "R66",
    title: "Thermodynamic simulation of an industrial power plant",
    publisher: "Wolter, Zekorn & Neef · BWK ENERGIE",
    date: "Jun 2016 · accessed 20 Sep 2026",
    url: "https://www.researchgate.net/publication/309160233_Stationare_thermodynamische_Prozesssimulationen_am_Beispiel_eines_Industriekraftwerks",
    fact: "An author-uploaded technical paper describes a historical model of Düsseldorf-Holthausen CHP.",
    limit:
      "A historical model does not establish today’s configuration, an accessible twin or current operating freedom.",
  },
  {
    id: "R02",
    title: "Big factories, smaller footprint",
    publisher: "Henkel",
    date: "2 Sep 2021 · accessed 19 Sep 2026",
    url: "https://www.henkel.com/spotlight/2021-09-02-big-factories-smaller-footprint-1320318",
    fact: "Historical Düsseldorf detergent-production, metering and spray-dryer context.",
    limit:
      "The reported approximately 400,000 tonnes/year is historical production at the article’s scope, not current campus output or a matched denominator for R64.",
  },
];

export function Evidence() {
  return (
    <section aria-labelledby="evidence-heading">
      <div className="section-heading">
        <p className="eyebrow">Evidence → decision</p>
        <h2 id="evidence-heading">Start from what already exists</h2>
        <p>
          Public evidence supports an investigation. It does not establish an
          unexploited Henkel saving.
        </p>
      </div>
      <div className="callout">
        <strong>Hypothetical pilot · customer inputs unknown.</strong> Current
        topology, feasible operating points, applicable prices, contractual
        authority and matching product output have not been supplied.
      </div>
      <div className="grid-2">
        <article className="card">
          <span className="pill">C03 · lead</span>
          <h3>Coupled heat and power dispatch</h3>
          <p>
            Compare permitted alternatives delivering equal useful service. The
            utility evidence makes the trade-off worth investigating; existing
            optimization may already capture it.
          </p>
          <p className="muted">
            Stop if no feasible authorized alternative or incremental net
            benefit survives.
          </p>
        </article>
        <article className="card">
          <span className="pill">C01 · comparison / fallback</span>
          <h3>Residual dryer operation</h3>
          <p>
            Investigate a controllable gap after installed automatic control.
            Normalize recipe, moisture, quality and operating conditions before
            attributing an improvement.
          </p>
          <p className="muted">
            Customer value is unknown. The separate synthetic example is not a
            measured residual.
          </p>
        </article>
        <article className="card">
          <span className="pill">C04 nested · C07 dependency</span>
          <h3>One boundary, one cost ledger</h3>
          <p>
            Heat exports can change fuel, power purchases and receipts together.
            Keep C04 inside C03; commercial terms and cost ownership determine
            valid economics. Do not add standalone benefits twice.
          </p>
        </article>
        <article className="card">
          <span className="pill">C02 · gated</span>
          <h3>Forecast only for a decision</h3>
          <p>
            A forecast needs a future unknown, an action that can change and
            suitable decision-time data. There is no trained Henkel forecast
            here.
          </p>
          <p className="muted">
            C05 means maintenance; C06 means production timing. Neither is
            assumed feasible.
          </p>
        </article>
      </div>
      <div className="section-heading">
        <p className="eyebrow">First visit</p>
        <h3>One artifact. One accountable role.</h3>
      </div>
      <div className="grid-2">
        <article className="card">
          <h3>The data request</h3>
          <p>
            An existing utilities operating or dispatch report for a
            representative recent period, with the meter and asset definitions
            already used in that report.
          </p>
          <p className="muted">
            Not a request to build a joined data warehouse. It may not settle
            tariffs, production allocation or contracts.
          </p>
        </article>
        <article className="card">
          <h3>The 30-minute stakeholder</h3>
          <p>
            The site utilities / energy operations owner: confirm what runs,
            which constraints bind and who can authorize a focused follow-up.
          </p>
          <p className="muted">
            If dispatch rights become the pivotal uncertainty, replace the
            report request with the specific rights/settlement artifact. Do not
            disguise two requests as one.
          </p>
        </article>
      </div>
      <div className="section-heading">
        <p className="eyebrow">Source register</p>
        <h3>Claims with their limits attached</h3>
        <p className="muted">
          Selected public records from the approved evidence extract. Titles may
          be shortened or translated for readability. Recorded checks mean
          supporting content was read, not independently audited.
        </p>
      </div>
      <div className="grid-2">
        {sources.map((source) => (
          <article
            className="card source-card"
            key={source.id}
            id={`source-${source.id}`}
          >
            <span className="pill">{source.id}</span>
            <h3>
              <a href={source.url} target="_blank" rel="noopener noreferrer">
                {source.title} ↗
              </a>
            </h3>
            <p className="muted">
              {source.publisher}
              <br />
              {source.date}
            </p>
            <p>{source.fact}</p>
            <p>
              <strong>Boundary:</strong> {source.limit}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
