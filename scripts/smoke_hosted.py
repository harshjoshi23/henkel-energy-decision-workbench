"""Unauthenticated smoke checks for this project's public synthetic deployment."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import adapter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    if not re.fullmatch(r"https://henkel-energy-decision-workbench(?:-[a-z0-9-]+)?\.vercel\.app", base):
        parser.error("Use this workbench's HTTPS Vercel deployment URL.")
    records = []

    def request(path, *, method="GET", body=None, content_type="application/json", expected=200):
        headers = {"User-Agent": "energy-workbench-release-smoke/1"}
        if body is not None:
            headers["Content-Type"] = content_type
        req = Request(base + path, data=body, headers=headers, method=method)
        try:
            response = urlopen(req, timeout=40)
        except HTTPError as exc:
            response = exc
        with response:
            raw = response.read()
            assert response.url == base + path, f"Unexpected redirect for {path}"
            assert response.status == expected, f"{method} {path}: {response.status}, expected {expected}"
            assert response.headers.get("X-Content-Type-Options") == "nosniff"
            assert response.headers.get("X-Frame-Options") == "DENY"
            assert "default-src 'self'" in response.headers.get("Content-Security-Policy", "")
            if path.startswith("/api/"):
                assert response.headers.get("Cache-Control") == "no-store"
                assert "application/json" in response.headers.get("Content-Type", "")
            return raw

    def record(name, **details):
        records.append({"check": name, "status": "passed", **details})

    html = request("/").decode()
    assert '<div id="root"></div>' in html
    record("public HTML and security headers")
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
    assert len(assets) >= 2
    for path in assets + ["/diagrams/architecture.svg", "/diagrams/decision-flow.svg"]:
        assert len(request(path)) > 100
    record("built assets and diagrams", count=len(assets) + 2)

    live_checks = json.loads(request("/api/checks"))
    assert len(live_checks["cases"]) == 44
    assert all(c["status"] == "passed" for c in live_checks["cases"])
    record("hosted engine and adapter assertions", count=44)

    fixtures = [
        ("C03", {}, "6"),
        ("C03", {"electricity_price": "120"}, "-22"),
        ("C03", {"alpha": "0.25", "k": "60"}, "-1.5"),
        ("C03", {"boiler_heat_limit": "8"}, None),
        ("C01", {}, "0.34"),
        ("C01", {"k": "15"}, "-0.11"),
        ("C01", {"k": "12.8"}, "0"),
    ]
    for candidate, inputs, expected in fixtures:
        payload = adapter.example_request(candidate, **inputs)
        result = json.loads(request("/api/calculate", method="POST", body=json.dumps(payload).encode()))
        snapshot = result["snapshot"]
        local = adapter.calculate(payload)["snapshot"]
        assert snapshot["metrics"]["per_tonne"] == expected
        assert snapshot["metrics"] == local["metrics"]
        for key in ("id", "inputHash", "methodHash", "adapterHash", "sourceHash", "inputs", "units"):
            assert snapshot[key] == local[key], f"Hosted/local mismatch: {key}"
        assert result["markdown"] == adapter.render_markdown(snapshot)
        record("fixture API/export/local parity", candidate=candidate, inputs=inputs, per_tonne=expected)

    invalid = []
    for field, value in (("q", "0"), ("gas_price", "NaN")):
        p = adapter.example_request(); p["inputs"][field] = value
        invalid.append((field + " invalid", p))
    p = adapter.example_request(); p["inputs"].pop("gas_price"); invalid.append(("missing input", p))
    p = adapter.example_request(); p["units"]["q"] = "t_steam"; invalid.append(("wrong denominator unit", p))
    p = adapter.example_request(); p["approved"] = False; invalid.append(("unconfirmed inputs", p))
    p = adapter.example_request(); p["dataMode"] = "customer"; invalid.append(("unsupported customer mode", p))
    for name, payload in invalid:
        data = json.loads(request("/api/calculate", method="POST", body=json.dumps(payload).encode(), expected=422))
        assert "error" in data and "snapshot" not in data
        record(name)
    for name, body, content_type, status in [
        ("malformed JSON", b"{", "application/json", 400),
        ("duplicate JSON keys", b'{"candidate":"C03","candidate":"C01"}', "application/json", 400),
        ("unsupported media", b"{}", "text/plain", 415),
        ("bounded request size", b" " * 17000, "application/json", 413),
    ]:
        data = json.loads(request("/api/calculate", method="POST", body=body, content_type=content_type, expected=status))
        assert "error" in data and "snapshot" not in data
        record(name)
    request("/api/calculate", expected=405)
    record("calculation method gate")
    request("/api/checks", method="POST", body=b"{}", expected=405)
    record("checks method gate")
    print(json.dumps({
        "baseUrl": base,
        "executedAt": datetime.now(timezone.utc).isoformat(),
        "authentication": "none",
        "passed": len(records),
        "checks": records,
        "scope": "Functional release checks with synthetic inputs; not capacity, formal accessibility, penetration testing or customer validation.",
    }, indent=2))


if __name__ == "__main__":
    main()
