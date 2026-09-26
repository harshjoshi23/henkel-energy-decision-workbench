"""Executable synthetic acceptance tests; no external services or credentials."""
from copy import deepcopy
from hashlib import sha256
from http.client import HTTPConnection
from http.server import HTTPServer
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from engine import adapter


class CalculationTests(unittest.TestCase):
    def snapshot(self, candidate="C03", **overrides):
        return adapter.calculate(adapter.example_request(candidate, **overrides))["snapshot"]

    def test_c03_required_parity(self):
        for inputs, expected in [
            ({}, ("120", "6", "B", "120")),
            ({"electricity_price": "120"}, ("-440", "-22", "A", "0")),
            ({"alpha": "0.25", "k": "60"}, ("-30", "-1.5", "A", "0")),
            ({"k": "150"}, ("-30", "-1.5", "A", "0")),
            ({"alpha": "0"}, ("0", "0", "A", "0")),
            ({"alpha": "0", "k": "10"}, ("-10", "-0.5", "A", "0")),
        ]:
            with self.subTest(inputs=inputs):
                metrics = self.snapshot(**inputs)["metrics"]
                self.assertEqual(tuple(metrics[k] for k in ("net", "per_tonne", "choice", "policy_benefit")), expected)

    def test_c03_costs_k_counted_once(self):
        result = self.snapshot(k="60")["metrics"]
        self.assertEqual(result["cost_a"], "4400")
        self.assertEqual(result["alternative_energy_cost"], "4280")
        self.assertEqual(result["cost_b"], "4340")
        self.assertEqual(result["net"], "60")

    def test_infeasible_not_zero_saving(self):
        result = self.snapshot(boiler_heat_limit="8")["metrics"]
        self.assertFalse(result["feasible"])
        for key in ("cost_b", "net", "per_tonne", "alternative_energy_cost"):
            self.assertIsNone(result[key])
        self.assertEqual(result["policy_benefit"], "0")
        self.assertEqual(result["choice"], "A")

    def test_output_changes_denominator_in_both_plans(self):
        result = self.snapshot(q="10")
        self.assertEqual(result["metrics"]["per_tonne"], "12")
        self.assertEqual(result["metrics"]["net"], "120")
        self.assertEqual(result["inputs"]["q"], "10")

    def test_c01_required_parity_and_no_invented_absolute_bill(self):
        for cost, expected, policy in [("6", "0.34", "B"), ("12.80", "0", "A"), ("15", "-0.11", "A")]:
            with self.subTest(k=cost):
                snapshot = self.snapshot("C01", k=cost)
                result = snapshot["metrics"]
                self.assertEqual(result["per_tonne"], expected)
                self.assertEqual(result["choice"], policy)
                self.assertEqual(result["break_even"], "12.8")
                self.assertEqual(snapshot["metricUnits"]["break_even"], "EUR")
                for key in ("cost_a", "cost_b", "alternative_energy_cost"):
                    self.assertIsNone(result[key])

    def test_negative_gap_and_negative_price_are_not_clipped(self):
        self.assertEqual(self.snapshot("C01", gas_gap="-0.01")["metrics"]["per_tonne"], "-0.46")
        self.assertEqual(self.snapshot(electricity_price="-40")["metrics"]["per_tonne"], "34")

    def test_numeric_contract_invalid_values(self):
        for value in (None, "", 40, True, "NaN", "Infinity", "-Infinity", "1e9999", "1e2", " 40", "40 ", "1_000", "01", "١", "0.1234567890123", "1000000001", "1" * 65):
            with self.subTest(value=value):
                request = adapter.example_request()
                request["inputs"]["gas_price"] = value
                with self.assertRaises(adapter.ValidationError):
                    adapter.calculate(request)

    def test_range_contract(self):
        for inputs in ({"q": "0"}, {"q": "-1"}, {"k": "-1"}, {"alpha": "-0.1"}, {"alpha": "1.1"}, {"boiler_heat_limit": "-1"}):
            with self.subTest(inputs=inputs), self.assertRaises(adapter.ValidationError):
                self.snapshot(**inputs)

    def test_strict_request_and_candidate_keys(self):
        mutations = [
            lambda p: p.update(extra="ignored?"),
            lambda p: p.pop("approved"),
            lambda p: p["inputs"].pop("gas_price"),
            lambda p: p["inputs"].update(gas_gap="0.01"),
            lambda p: p["units"].update(gas_gap="MWh_fuel/t_product"),
            lambda p: p.update(candidate=[]),
            lambda p: p.update(candidate="C05"),
            lambda p: p.update(schemaVersion=1),
            lambda p: p.update(dataMode="customer_authorized"),
            lambda p: p.update(inputs=[]),
        ]
        for mutate in mutations:
            request = adapter.example_request()
            mutate(request)
            with self.subTest(request=request), self.assertRaises(adapter.ValidationError):
                adapter.calculate(request)
        with self.assertRaises(adapter.ValidationError):
            adapter.calculate([])

    def test_units_period_boundary_are_not_client_overrides(self):
        for field, bad in [("q", "t_steam"), ("q", "t_CO2"), ("gas_price", "EUR/MWh_th"), ("electricity_price", "EUR/kWh"), ("alpha", "percent")]:
            request = adapter.example_request()
            request["units"][field] = bad
            with self.subTest(field=field, bad=bad), self.assertRaises(adapter.ValidationError):
                adapter.calculate(request)
        for field in ("period", "boundary", "heat_grade"):
            request = adapter.example_request()
            request["inputs"][field] = "different"
            with self.assertRaises(adapter.ValidationError):
                adapter.calculate(request)

    def test_revision_and_confirmation(self):
        for value in (0, -1, 1.0, True, "1", 2147483648):
            request = adapter.example_request()
            request["revision"] = value
            with self.subTest(revision=value), self.assertRaises(adapter.ValidationError):
                adapter.calculate(request)
        for value in (False, 1, "true", None):
            request = adapter.example_request()
            request["approved"] = value
            with self.subTest(approved=value), self.assertRaises(adapter.ValidationError):
                adapter.calculate(request)

    def test_snapshot_hash_and_confirmation_bind_exact_request(self):
        payload = adapter.example_request()
        original = deepcopy(payload)
        first = adapter.calculate(payload)["snapshot"]
        second = adapter.calculate(payload)["snapshot"]
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(payload, original)
        payload["inputs"]["electricity_price"] = "120"
        third = adapter.calculate(payload)["snapshot"]
        self.assertNotEqual(first["inputHash"], third["inputHash"])
        self.assertNotEqual(first["id"], third["id"])
        self.assertEqual(first["inputs"]["electricity_price"], "40")
        self.assertEqual(third["approval"]["inputHash"], third["inputHash"])
        payload["revision"] = 2
        self.assertNotEqual(third["id"], adapter.calculate(payload)["snapshot"]["id"])

    def test_hashes_and_synthetic_provenance(self):
        result = self.snapshot()
        self.assertEqual(result["methodHash"], sha256(Path(adapter.econ.__file__).read_bytes()).hexdigest())
        self.assertEqual(result["sourceHash"], sha256((adapter.ROOT / "evidence" / "sources.md").read_bytes()).hexdigest())
        self.assertEqual(result["dataMode"], "synthetic")
        self.assertEqual(result["provenance"]["fixedService"]["heat"], "45")
        self.assertIn("Do not add", result["provenance"]["nonAdditive"])

    def test_evidence_ids_dates_limitations_and_links_travel_with_export(self):
        for candidate, expected_ids in (("C03", ["R07", "R10", "R65", "R66", "R69"]), ("C01", ["R02", "R64"])):
            response = adapter.calculate(adapter.example_request(candidate))
            evidence = response["snapshot"]["evidence"]
            self.assertEqual([record["id"] for record in evidence], expected_ids)
            for record in evidence:
                self.assertIn("accessed", record["dateAndScope"])
                self.assertTrue(record["limitations"])
                self.assertEqual(len(record["recordHash"]), 64)
                self.assertIn(f"[{record['title']}]({record['url']})", response["markdown"])
                self.assertIn(record["dateAndScope"], response["markdown"])
                self.assertIn(record["limitations"], response["markdown"])
            self.assertIn("not re-opened", evidence[0]["verification"])

    def test_first_visit_caveat_and_disclosure_are_in_exact_snapshot_export(self):
        response = adapter.calculate(adapter.example_request())
        snapshot, markdown = response["snapshot"], response["markdown"]
        for key in ("dataRequest", "stakeholder", "rationale"):
            self.assertIn(snapshot["firstVisit"][key], markdown)
        self.assertIn("existing", snapshot["firstVisit"]["dataRequest"])
        self.assertIn("unknown", snapshot["decisionCaveat"])
        self.assertIn(snapshot["decisionCaveat"], markdown)
        self.assertIn(snapshot["disclosure"], markdown)

    def test_missing_evidence_does_not_generate_unsupported_success(self):
        with patch.object(adapter, "evidence_records", side_effect=RuntimeError("Missing approved source")):
            with self.assertRaises(RuntimeError):
                self.snapshot()

    def test_server_markdown_uses_same_snapshot(self):
        for candidate, overrides in [("C03", {"electricity_price": "120"}), ("C03", {"boiler_heat_limit": "8"}), ("C01", {})]:
            response = adapter.calculate(adapter.example_request(candidate, **overrides))
            snapshot, markdown = response["snapshot"], response["markdown"]
            self.assertEqual(markdown, adapter.render_markdown(snapshot))
            for key, unit in snapshot["metricUnits"].items():
                value = snapshot["metrics"][key]
                display = "Not available / not applicable" if value is None else value
                self.assertIn(f"| {key} | {display} | {unit} |", markdown)
            self.assertIn(snapshot["id"], markdown)
            self.assertIn("**SYNTHETIC", markdown)

    def test_financial_values_are_decimal_strings_or_null(self):
        snapshot = self.snapshot()
        for key in snapshot["metricUnits"]:
            value = snapshot["metrics"][key]
            self.assertTrue(value is None or isinstance(value, str))
            if value is not None:
                self.assertTrue(adapter.Decimal(value).is_finite())
        for row in snapshot["sensitivity"]:
            self.assertIsInstance(row["electricity_price"], str)

    def test_sensitivity_uses_same_engine_and_constraints(self):
        for candidate, overrides in [("C03", {}), ("C03", {"boiler_heat_limit": "8"}), ("C01", {})]:
            snapshot = self.snapshot(candidate, **overrides)
            for row in snapshot["sensitivity"]:
                request = adapter.example_request(candidate, **{**overrides, "electricity_price": row["electricity_price"]})
                observed = adapter._metrics(candidate, adapter.validate_request(request))[0]
                self.assertEqual(row["per_tonne"], observed["per_tonne"])
                self.assertEqual(row["feasible"], observed["feasible"])

    def test_checks_execute_and_fail_closed(self):
        report = adapter.run_actual_checks()
        self.assertGreaterEqual(len(report["cases"]), 44)
        self.assertTrue(all(case["status"] == "passed" for case in report["cases"]))
        with patch.object(adapter.econ, "run_checks", side_effect=AssertionError("PRIVATE_DETAILS")):
            report = adapter.run_actual_checks()
            self.assertEqual(report["cases"][0]["status"], "failed")
            self.assertNotIn("PRIVATE_DETAILS", json.dumps(report))
            with self.assertRaises(RuntimeError):
                self.snapshot()

    def test_engine_and_trace_unchanged_by_adapter(self):
        paths = [adapter.ROOT / "engine" / name for name in ("economics.py", "economics.md")]
        before = [p.read_bytes() for p in paths]
        self.snapshot()
        adapter.run_actual_checks()
        self.assertEqual(before, [p.read_bytes() for p in paths])


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), adapter.ApiHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method="POST", path="/api/calculate", body=None, headers=None):
        if body is None:
            body = json.dumps(adapter.example_request()).encode()
        merged = {"Content-Type": "application/json"}
        merged.update(headers or {})
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=merged)
            response = connection.getresponse()
            raw = response.read()
            return response.status, dict(response.getheaders()), json.loads(raw) if raw else None
        finally:
            connection.close()

    def test_http_success_and_headers(self):
        status, headers, payload = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(payload["snapshot"]["metrics"]["per_tonne"], "6")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_http_c01_and_validation(self):
        status, _, result = self.request(body=json.dumps(adapter.example_request("C01")).encode())
        self.assertEqual(status, 200)
        self.assertEqual(result["snapshot"]["metrics"]["per_tonne"], "0.34")
        for mutate in (lambda p: p["inputs"].update(q="0"), lambda p: p["inputs"].pop("gas_price"), lambda p: p.update(unwanted=1)):
            request = adapter.example_request()
            mutate(request)
            status, _, result = self.request(body=json.dumps(request).encode())
            self.assertEqual(status, 422)
            self.assertEqual(result["error"], "validation_error")

    def test_bad_json_and_duplicate_keys(self):
        for body in (b"{", b"", b"\xff", b'{"a": NaN}', b'{"candidate":"C03","candidate":"C01"}'):
            with self.subTest(body=body):
                status, _, result = self.request(body=body)
                self.assertEqual(status, 400)
                self.assertEqual(result["error"], "invalid_json")

    def test_body_limit_and_content_type(self):
        self.assertEqual(self.request(body=b"x" * (adapter.MAX_BODY + 1))[0], 413)
        self.assertEqual(self.request(headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request(headers={"Content-Length": "-1"})[0], 400)

    def test_wrong_methods_and_routes(self):
        for method, path in (("GET", "/api/calculate"), ("POST", "/api/checks"), ("DELETE", "/api/checks"), ("OPTIONS", "/api/calculate"), ("TRACE", "/api/calculate")):
            with self.subTest(method=method, path=path):
                status, headers, payload = self.request(method, path)
                self.assertEqual(status, 405)
                self.assertIn("Allow", headers)
                self.assertEqual(payload["error"], "method_not_allowed")
        self.assertEqual(self.request(path="/api/unknown")[0], 404)

    def test_http_checks_are_actual_scoped_execution(self):
        status, _, result = self.request("GET", "/api/checks", body=b"")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(result["cases"]), 44)
        self.assertTrue(all(c["status"] == "passed" for c in result["cases"]))
        self.assertIn("Not UI", result["scope"])
        with patch.object(adapter.econ, "run_checks", side_effect=AssertionError()):
            status, _, result = self.request("GET", "/api/checks", body=b"")
            self.assertEqual(status, 200)
            self.assertTrue(any(c["status"] == "failed" for c in result["cases"]))

    def test_unexpected_failure_sanitized(self):
        with patch.object(adapter, "calculate", side_effect=RuntimeError("PRIVATE_SECRETS_INTERNAL_PATH")):
            status, _, result = self.request()
            self.assertEqual(status, 500)
            self.assertNotIn("PRIVATE", json.dumps(result))

    def test_vercel_entry_points_import_without_side_effect(self):
        from api.calculate import handler as calculate_handler
        from api.checks import handler as checks_handler
        self.assertEqual(calculate_handler.endpoint, "/api/calculate")
        self.assertEqual(checks_handler.endpoint, "/api/checks")


if __name__ == "__main__":
    unittest.main()
