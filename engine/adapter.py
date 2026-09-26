"""Strict, stateless adapter. The frozen economics module owns all economics.

No accounts, network requests, storage mutations, customer data or AI calls.
An approval flag records confirmation of this exact request; it is not identity
authentication or permission to publish, trade, or control equipment.
"""
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from hashlib import sha256
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from . import economics as econ

ROOT = Path(__file__).resolve().parents[1]
MAX_BODY = 16 * 1024
MAX_MAGNITUDE = Decimal("1000000000")
NUMBER = re.compile(r"[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]{1,12})?\Z", re.ASCII)
FIELDS = {
    "C03": {"gas_price", "electricity_price", "k", "q", "alpha", "boiler_heat_limit"},
    "C01": {"gas_price", "electricity_price", "k", "q", "gas_gap", "electric_gap"},
}
UNITS = {
    "q": "t_product", "gas_price": "EUR/MWh_fuel",
    "electricity_price": "EUR/MWh_electric", "k": "EUR",
    "alpha": "fraction", "boiler_heat_limit": "MWh_th",
    "gas_gap": "MWh_fuel/t_product", "electric_gap": "MWh_electric/t_product",
}
REQUEST_KEYS = {"schemaVersion", "candidate", "revision", "dataMode", "approved", "inputs", "units"}
EVIDENCE_IDS = {"C03": ("R07", "R10", "R65", "R66", "R69"), "C01": ("R02", "R64")}


class ValidationError(ValueError):
    """Safe input-validation message suitable for the caller."""


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def hashes():
    return {"methodHash": sha256(Path(econ.__file__).read_bytes()).hexdigest(),
            "adapterHash": sha256(Path(__file__).read_bytes()).hexdigest(),
            "sourceHash": sha256((ROOT / "evidence" / "sources.md").read_bytes()).hexdigest()}


def evidence_records(candidate):
    """Parse approved bundled source records only; no fetches or instructions."""
    text = (ROOT / "evidence" / "sources.md").read_text(encoding="utf-8")
    sections = re.split(r"(?m)^## (R[0-9]+)\s*$", text)
    blocks = {sections[i]: sections[i + 1].strip() for i in range(1, len(sections), 2)}
    records = []
    for source_id in EVIDENCE_IDS[candidate]:
        block = blocks[source_id]
        heading = re.search(r"\*\*(.+?)\*\*\s+\[Direct (?:source|PDF)\]\((https://[^)]+)\)", block)
        if heading is None or "**Limitation:**" not in block:
            raise RuntimeError("Bundled evidence record is incomplete")
        details = block[heading.end():].strip()
        date_and_scope, limitations = details.split("**Limitation:**", 1)
        records.append({"id": source_id, "title": heading.group(1), "url": heading.group(2),
                        "dateAndScope": date_and_scope.strip(), "limitations": limitations.strip(),
                        "recordHash": sha256(block.encode("utf-8")).hexdigest(),
                        "verification": "Previously checked as recorded; not re-opened when this snapshot was generated"})
    return records


def decimal_text(value):
    if value is None:
        return None
    value = Decimal(value)
    if not value.is_finite():
        raise ArithmeticError("Non-finite result")
    if value == 0:
        return "0"
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _exact_keys(value, expected, label):
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be an object")
    missing, extra = expected - value.keys(), value.keys() - expected
    if missing:
        raise ValidationError(f"{label}: missing fields: {', '.join(sorted(missing))}")
    if extra:
        # Do not reflect arbitrary client strings into an error response.
        raise ValidationError(f"{label}: unsupported fields")


def validate_request(payload):
    _exact_keys(payload, REQUEST_KEYS, "request")
    if payload["schemaVersion"] != "1":
        raise ValidationError("schemaVersion must be '1'")
    candidate = payload["candidate"]
    if not isinstance(candidate, str) or candidate not in FIELDS:
        raise ValidationError("candidate must be C03 or C01")
    revision = payload["revision"]
    if type(revision) is not int or not 1 <= revision <= 2147483647:
        raise ValidationError("revision must be a positive bounded integer")
    if payload["dataMode"] != "synthetic":
        raise ValidationError("Only explicitly synthetic scenarios are supported")
    if payload["approved"] is not True:
        raise ValidationError("Confirm the exact scenario inputs before calculation")
    _exact_keys(payload["inputs"], FIELDS[candidate], "inputs")
    _exact_keys(payload["units"], FIELDS[candidate], "units")
    values = {}
    for name in sorted(FIELDS[candidate]):
        if payload["units"][name] != UNITS[name]:
            raise ValidationError(f"{name}: expected unit {UNITS[name]}")
        raw = payload["inputs"][name]
        if not isinstance(raw, str) or len(raw) > 64 or not NUMBER.fullmatch(raw):
            raise ValidationError(f"{name}: use a finite decimal string with at most 12 decimal places; exponent notation is unsupported")
        try:
            number = Decimal(raw)
        except InvalidOperation as exc:
            raise ValidationError(f"{name}: invalid decimal") from exc
        if not number.is_finite() or abs(number) > MAX_MAGNITUDE:
            raise ValidationError(f"{name}: magnitude must not exceed 1000000000")
        values[name] = number
    if values["q"] <= 0:
        raise ValidationError("q: matching product output must be positive")
    if values["k"] < 0:
        raise ValidationError("k: incremental cost must be non-negative")
    if candidate == "C03":
        if not 0 <= values["alpha"] <= 1:
            raise ValidationError("alpha: permitted switch fraction must be in [0, 1]")
        if values["boiler_heat_limit"] < 0:
            raise ValidationError("boiler_heat_limit must be non-negative")
    return values


def _metrics(candidate, v):
    """Delegate economics, deriving presentation fields from engine results."""
    if candidate == "C03":
        service = replace(econ.A.service, product_tonnes=v["q"])
        baseline = replace(econ.A, service=service)
        alternative = replace(econ.interpolated(v["alpha"]), service=service)
        result = econ.compare(baseline, alternative, v["gas_price"], v["electricity_price"],
                              v["k"], v["boiler_heat_limit"])
        metrics = dict(result)
        metrics["alternative_energy_cost"] = (econ.energy_cost(alternative, v["gas_price"], v["electricity_price"])
                                               if result["feasible"] else None)
        metrics["incremental_cost"] = v["k"]
        metrics["policy_per_tonne"] = result["policy_benefit"] / v["q"]
        metrics["break_even"] = econ.break_even(v["gas_price"], v["k"], v["alpha"])
        fa, fb = econ.flows(baseline), econ.flows(alternative)
        trace = [
            ("Baseline external fuel", fa["fuel"], "MWh_fuel"),
            ("Alternative external fuel", fb["fuel"], "MWh_fuel"),
            ("Baseline electricity import", baseline.import_mwh, "MWh_electric"),
            ("Alternative electricity import", alternative.import_mwh, "MWh_electric"),
            ("Matching useful heat service", service.heat_mwh, "MWh_th"),
            ("Matching electricity service", service.electricity_mwh, "MWh_electric"),
            ("Baseline net external cost", result["cost_a"], "EUR"),
            ("Alternative energy cost before K", metrics["alternative_energy_cost"], "EUR"),
            ("Incremental K counted once", v["k"], "EUR"),
            ("Alternative total cost including K", result["cost_b"], "EUR"),
            ("Electricity-price break-even (algebra only, feasibility separate)", metrics["break_even"], "EUR/MWh_electric"),
        ]
    else:
        per_tonne = econ.residual_value(v["gas_gap"], v["electric_gap"], v["gas_price"],
                                        v["electricity_price"], v["k"], v["q"])
        gross_per_tonne = econ.residual_value(v["gas_gap"], v["electric_gap"], v["gas_price"],
                                              v["electricity_price"], Decimal(0), v["q"])
        net = per_tonne * v["q"]
        metrics = {"feasible": True, "reason": "Direct purchased-energy arithmetic only; actual residual gap and operating feasibility are unverified",
                   "cost_a": None, "cost_b": None, "alternative_energy_cost": None,
                   "incremental_cost": v["k"], "net": net, "per_tonne": per_tonne,
                   "choice": "B" if net > 0 else "A", "policy_benefit": max(Decimal(0), net),
                   "policy_per_tonne": max(Decimal(0), per_tonne),
                   "break_even": gross_per_tonne * v["q"]}
        trace = [
            ("Residual gas intensity gap", v["gas_gap"], UNITS["gas_gap"]),
            ("Residual electricity intensity gap", v["electric_gap"], UNITS["electric_gap"]),
            ("Gross avoided purchased-energy cost", gross_per_tonne * v["q"], "EUR"),
            ("Incremental K counted once", v["k"], "EUR"),
            ("Break-even incremental K", metrics["break_even"], "EUR"),
        ]
    trace += [("Signed benefit of proposed change", metrics["net"], "EUR"),
              ("Matching product output", v["q"], "t_product"),
              ("Signed benefit per product tonne", metrics["per_tonne"], "EUR/t_product"),
              ("Benefit of chosen feasible policy", metrics["policy_benefit"], "EUR")]
    serialized = {key: value if isinstance(value, (str, bool)) else decimal_text(value)
                  for key, value in metrics.items()}
    return serialized, [{"label": label, "value": decimal_text(value), "unit": unit}
                        for label, value, unit in trace]


def example_request(candidate="C03", **overrides):
    defaults = {"gas_price": "40", "electricity_price": "40", "k": "0", "q": "20",
                "alpha": "1", "boiler_heat_limit": "9"} if candidate == "C03" else {
                "gas_price": "40", "electricity_price": "120", "k": "6", "q": "20",
                "gas_gap": "0.01", "electric_gap": "0.002"}
    defaults.update(overrides)
    return {"schemaVersion": "1", "candidate": candidate, "revision": 1,
            "dataMode": "synthetic", "approved": True, "inputs": defaults,
            "units": {key: UNITS[key] for key in FIELDS[candidate]}}


def _observed_metric(candidate, metric, **overrides):
    request = example_request(candidate, **overrides)
    return _metrics(candidate, validate_request(request))[0][metric]


def run_actual_checks():
    """Run now; never infer green status from a saved specification."""
    cases = []
    try:
        for index, description in enumerate(econ.run_checks(), 1):
            cases.append({"id": f"engine-{index:02}", "status": "passed",
                          "expected": description, "observed": "Engine assertion executed without failure"})
    except Exception:
        cases.append({"id": "engine-suite", "status": "failed", "expected": "All embedded economics assertions pass",
                      "observed": "Engine assertion execution failed; details withheld"})
    tests = [
        ("adapter-c03-base", lambda: _observed_metric("C03", "per_tonne"), "6"),
        ("adapter-c03-negative", lambda: _observed_metric("C03", "per_tonne", electricity_price="120"), "-22"),
        ("adapter-c03-policy", lambda: _observed_metric("C03", "choice", electricity_price="120"), "A"),
        ("adapter-c03-limited", lambda: _observed_metric("C03", "per_tonne", alpha="0.25", k="60"), "-1.5"),
        ("adapter-c03-infeasible", lambda: _observed_metric("C03", "per_tonne", boiler_heat_limit="8"), None),
        ("adapter-c03-nochange", lambda: _observed_metric("C03", "net", alpha="0"), "0"),
        ("adapter-c01-positive", lambda: _observed_metric("C01", "per_tonne"), "0.34"),
        ("adapter-c01-negative", lambda: _observed_metric("C01", "per_tonne", k="15"), "-0.11"),
        ("adapter-c01-breakeven", lambda: _observed_metric("C01", "per_tonne", k="12.8"), "0"),
        ("adapter-c01-noinventedbill", lambda: _observed_metric("C01", "cost_a"), None),
    ]
    for identifier, evaluate, expected in tests:
        try:
            observed = evaluate()
            passed = observed == expected
        except Exception:
            observed, passed = "Execution failed; details withheld", False
        cases.append({"id": identifier, "status": "passed" if passed else "failed",
                      "expected": expected, "observed": observed})
    return {"executedAt": _now(), **hashes(), "cases": cases,
            "scope": "Executed Python engine assertions and adapter fixture parity only. Not UI, security, deployment, all planned evaluations, or customer validation."}


def calculate(payload):
    values = validate_request(payload)
    # Fix precision per call, including HTTP worker threads.
    with localcontext() as context:
        context.prec = 28
        metrics, trace = _metrics(payload["candidate"], values)
        sensitivity = []
        for price in sorted({Decimal(x) for x in ("0", "40", "80", "120", "160")} | {values["electricity_price"]}):
            result, _ = _metrics(payload["candidate"], {**values, "electricity_price": price})
            sensitivity.append({"electricity_price": decimal_text(price), "per_tonne": result["per_tonne"],
                                "feasible": result["feasible"]})
        checks = run_actual_checks()
    if any(case["status"] != "passed" for case in checks["cases"]):
        raise RuntimeError("Calculation self-check failed")
    provenance = {
        "classification": "SYNTHETIC — teaching assumptions, not Henkel measurements or savings",
        "period": "fictional one-hour interval",
        "product": "fictional product family; unchanged mix and quality between choices",
        "outputUnit": "t_product",
        "boundary": "fictional isolated manufacturing service" if payload["candidate"] == "C03" else "fictional independent dryer with directly purchased energy",
        "nonAdditive": "Do not add independent C01 and C03 benefits; shared utility heat requires a joint ledger.",
        "fixedService": {"electricity": decimal_text(econ.A.service.electricity_mwh), "electricityUnit": "MWh_electric",
                         "heat": decimal_text(econ.A.service.heat_mwh), "heatUnit": "MWh_th",
                         "heatGrade": econ.A.service.heat_grade} if payload["candidate"] == "C03" else None,
        "constraints": "Only the teaching-model constraints are represented. Actual Henkel topology, permission, tariffs and residual opportunities remain unknown.",
    }
    version_hashes = hashes()
    input_hash = _hash(payload)
    snapshot = {"id": _hash({"inputHash": input_hash, **version_hashes}), "createdAt": _now(),
                "schemaVersion": "1", "candidate": payload["candidate"], "revision": payload["revision"],
                "dataMode": "synthetic", "approved": True,
                "inputs": dict(payload["inputs"]), "units": dict(payload["units"]),
                **version_hashes, "inputHash": input_hash,
                "approval": {"scope": "Exact posted inputs only; user confirmation, not authenticated identity or authority for external actions",
                             "inputHash": input_hash, "revision": payload["revision"]},
                "metrics": metrics,
                "metricUnits": {key: ("EUR/t_product" if key in {"per_tonne", "policy_per_tonne"} else
                                      ("EUR/MWh_electric" if payload["candidate"] == "C03" else "EUR") if key == "break_even" else "EUR")
                                for key in ("cost_a", "cost_b", "alternative_energy_cost", "incremental_cost", "net", "per_tonne", "policy_benefit", "policy_per_tonne", "break_even")},
                "trace": trace, "sensitivity": sensitivity, "checks": checks["cases"],
                "checksExecutedAt": checks["executedAt"], "checksScope": checks["scope"], "provenance": provenance,
                "evidence": evidence_records(payload["candidate"]),
                "firstVisit": {
                    "status": "Provisional, owner-approved investigation priority; not a validated intervention",
                    "dataRequest": "One existing utilities operating/dispatch report with its existing definitions",
                    "stakeholder": "Site utilities / energy operations owner",
                    "rationale": "Test the actual operating boundary, constraints, existing decisions and who has authority to change them before estimating customer value.",
                },
                "decisionCaveat": "C03 is the provisional lead and C01 the comparison/fallback; C04 stays nested and C07 is a commercial dependency. Customer tariffs, matching output, current operating freedom and residual opportunities remain unknown. This synthetic result is not a recommendation to operate equipment.",
                "disclosure": "Codex assisted software and test authoring. The frozen Python Decimal economics engine performs this calculation, and the server renders the export from the same snapshot without an LLM. No trained forecast, customer-system connection, real operational action or verified Henkel savings is established."}
    return {"snapshot": snapshot, "markdown": render_markdown(snapshot)}


def render_markdown(snapshot):
    """Render this exact snapshot, without recalculation or AI."""
    rows = [f"# {snapshot['candidate']} — synthetic decision snapshot", "",
            "**SYNTHETIC: not Henkel measurements, validated savings or an operating instruction.**", "",
            f"Snapshot: `{snapshot['id']}`  ", f"Created: {snapshot['createdAt']}  ",
            f"Revision: {snapshot['revision']}  ", f"Input hash: `{snapshot['inputHash']}`  ",
            f"Economics method hash: `{snapshot['methodHash']}`  ",
            f"Adapter hash: `{snapshot['adapterHash']}`  ", f"Source hash: `{snapshot['sourceHash']}`", "",
            "## Boundary", "", snapshot["provenance"]["boundary"],
            snapshot["provenance"]["period"], snapshot["provenance"]["product"],
            snapshot["provenance"]["nonAdditive"], snapshot["provenance"]["constraints"], "",
            "## Confirmed inputs", "", "| Input | Value | Unit |", "|---|---:|---|"]
    rows += [f"| {key} | {snapshot['inputs'][key]} | {snapshot['units'][key]} |" for key in sorted(snapshot["inputs"])]
    rows += ["", "Confirmation applies only to these posted inputs; it is not authenticated customer approval.", "",
             "## Result", "", f"Feasible under teaching constraints: {str(snapshot['metrics']['feasible']).lower()}. {snapshot['metrics']['reason']}",
             f"Policy choice: {snapshot['metrics']['choice']} (A retains baseline; B takes the proposed change).", "",
             "| Metric | Value | Unit |", "|---|---:|---|"]
    for key, unit in snapshot["metricUnits"].items():
        value = snapshot["metrics"][key]
        rows.append(f"| {key} | {'Not available / not applicable' if value is None else value} | {unit} |")
    rows += ["", "C01 absolute bills are unavailable; its residual avoided-cost calculation is not an invented baseline bill.",
             "Break-even is an algebraic threshold, not a guarantee of physical feasibility. No annual extrapolation is made.", "",
             "## Calculation trace", "", "| Step | Value | Unit |", "|---|---:|---|"]
    rows += [f"| {item['label']} | {'Not available' if item['value'] is None else item['value']} | {item['unit']} |" for item in snapshot["trace"]]
    rows += ["", "## Sensitivity", "", "| Electricity price (EUR/MWh_electric) | Signed EUR/t_product | Feasible |", "|---:|---:|---|"]
    rows += [f"| {item['electricity_price']} | {'Infeasible' if item['per_tonne'] is None else item['per_tonne']} | {str(item['feasible']).lower()} |" for item in snapshot["sensitivity"]]
    rows += ["", "## Executed checks", "", snapshot["checksScope"], f"Executed: {snapshot['checksExecutedAt']}", "",
             "| Case | Status | Expected | Observed |", "|---|---|---|---|"]
    for case in snapshot["checks"]:
        display = lambda value: "null" if value is None else str(value).replace("|", "\\|").replace("\n", " ")
        rows.append("| " + " | ".join(display(case[key]) for key in ("id", "status", "expected", "observed")) + " |")
    rows += ["", "## Evidence and limitations", "",
             "These are previously checked public records, with their original date and scope limitations. Creating this export does not recheck the websites or independently audit company claims. They establish context, not the synthetic numerical inputs."]
    for source in snapshot["evidence"]:
        rows += ["", f"### {source['id']}", "", f"[{source['title']}]({source['url']})", "",
                 source["dateAndScope"], "", f"**Limitation:** {source['limitations']}",
                 f"Record hash: `{source['recordHash']}`"]
    rows += ["", "## First visit and decision status", "", snapshot["firstVisit"]["status"], "",
             f"**Single data request:** {snapshot['firstVisit']['dataRequest']}.", "",
             f"**Single stakeholder:** {snapshot['firstVisit']['stakeholder']}.", "",
             snapshot["firstVisit"]["rationale"], "", snapshot["decisionCaveat"], "",
             "## Disclosure", "", snapshot["disclosure"], ""]
    return "\n".join(rows)


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def decode_json(body):
    def reject_constant(_):
        raise ValueError("Nonstandard JSON number")
    return json.loads(body.decode("utf-8"), object_pairs_hook=_no_duplicates, parse_constant=reject_constant)


class ApiHandler(BaseHTTPRequestHandler):
    """Shared by Vercel function handlers and the loopback development server."""
    endpoint = None
    server_version = "EnergyWorkbench/1"

    def log_message(self, *_):
        # Request bodies and error details never enter default access logs.
        pass

    def _send(self, status, payload, allow=None):
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        if allow:
            self.send_header("Allow", allow)
        self.end_headers()
        self.close_connection = True
        if self.command != "HEAD":
            self.wfile.write(encoded)

    def _dispatch(self):
        route = urlsplit(self.path).path
        if route not in {"/api/calculate", "/api/checks"} or (self.endpoint and route != self.endpoint):
            self._send(404, {"error": "not_found", "message": "Unknown API route"})
            return
        allowed = "POST" if route == "/api/calculate" else "GET"
        if self.command != allowed:
            self._send(405, {"error": "method_not_allowed", "message": f"Use {allowed} for this route"}, allowed)
            return
        if route == "/api/checks":
            try:
                with localcontext() as context:
                    context.prec = 28
                    response = run_actual_checks()
                self._send(200, response)
            except Exception:
                self._send(500, {"error": "internal_error", "message": "Checks could not complete"})
            return
        if self.headers.get("Transfer-Encoding"):
            self._send(400, {"error": "invalid_request", "message": "Transfer encoding is unsupported"})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,10}", lengths[0]):
            self._send(400, {"error": "invalid_request", "message": "A valid single Content-Length is required"})
            return
        size = int(lengths[0])
        if size > MAX_BODY:
            self._send(413, {"error": "body_too_large", "message": "JSON body limit is 16384 bytes"})
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self._send(415, {"error": "unsupported_media_type", "message": "Use application/json"})
            return
        try:
            self.connection.settimeout(5)
            body = self.rfile.read(size)
            if len(body) != size:
                raise ValueError("Truncated body")
            payload = decode_json(body)
        except (ValueError, UnicodeError, OSError, RecursionError):
            self._send(400, {"error": "invalid_json", "message": "Body must be valid UTF-8 JSON without duplicate keys or nonstandard numbers"})
            return
        try:
            result = calculate(payload)
        except ValidationError as exc:
            self._send(422, {"error": "validation_error", "message": str(exc)})
        except Exception:
            self._send(500, {"error": "internal_error", "message": "Calculation could not complete; no result was accepted"})
        else:
            self._send(200, result)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = do_TRACE = do_CONNECT = _dispatch
