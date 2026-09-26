#!/usr/bin/env python3
"""Deterministic SYNTHETIC/SYMBOLIC assessment economics; Python standard library only.

No network, customer data, optimizer, forecast, or external file inputs.
Default: print the complete trace. --check: test and compare the saved trace.
--write: deliberately regenerate the adjacent economics.md after tests pass.
All numeric model fixtures are SYNTHETIC, never Henkel parameters.
"""

from dataclasses import dataclass, replace
from decimal import Decimal, getcontext
from pathlib import Path
import argparse

getcontext().prec = 28
D = Decimal
UNKNOWN = "UNKNOWN — not estimated"
SYN = "SYNTHETIC"


def number(value, label):
    if value is None:
        raise ValueError(f"{label}: unknown is not zero")
    result = D(str(value))
    if not result.is_finite():
        raise ValueError(f"{label}: finite value required")
    return result


def quantity(value, unit, expected):
    if unit != expected:
        raise ValueError(f"Expected {expected}, received {unit}")
    return number(value, expected)


@dataclass(frozen=True)
class Service:
    period: str = "fictional one-hour interval"
    product_family: str = "fictional product family with unchanged mix and quality"
    boundary: str = "fictional isolated manufacturing service"
    heat_grade: str = "same usable delivery temperature and pressure"
    product_tonnes: D = D("20")
    output_unit: str = "t_product"
    electricity_mwh: D = D("45")
    heat_mwh: D = D("45")


@dataclass(frozen=True)
class Plan:
    name: str
    chp_fuel_mwh: D
    boiler_fuel_mwh: D
    import_mwh: D
    service: Service = Service()
    electric_efficiency: D = D("0.35")
    heat_efficiency: D = D("0.45")
    boiler_efficiency: D = D("0.90")


A = Plan("A", D("100"), D("0"), D("10"))
B = Plan("B", D("80"), D("10"), D("17"))


def flows(plan):
    return {
        "chp_electricity": plan.chp_fuel_mwh * plan.electric_efficiency,
        "chp_heat": plan.chp_fuel_mwh * plan.heat_efficiency,
        "boiler_heat": plan.boiler_fuel_mwh * plan.boiler_efficiency,
        "fuel": plan.chp_fuel_mwh + plan.boiler_fuel_mwh,
    }


def validate(plan):
    s = plan.service
    q = quantity(s.product_tonnes, s.output_unit, "t_product")
    if q <= 0:
        raise ValueError("Matching product output must be positive")
    for label, value in [("CHP fuel", plan.chp_fuel_mwh),
                         ("boiler fuel", plan.boiler_fuel_mwh),
                         ("electricity import", plan.import_mwh),
                         ("electric demand", s.electricity_mwh),
                         ("heat demand", s.heat_mwh)]:
        if number(value, label) < 0:
            raise ValueError(f"{label} must be non-negative")
    for value in [plan.electric_efficiency, plan.heat_efficiency, plan.boiler_efficiency]:
        if not D("0") < number(value, "efficiency") <= D("1"):
            raise ValueError("Efficiencies must lie in (0, 1]")
    if plan.electric_efficiency + plan.heat_efficiency > 1:
        raise ValueError("CHP outputs exceed fuel input on the chosen common basis")
    f = flows(plan)
    if f["chp_electricity"] + plan.import_mwh != s.electricity_mwh:
        raise ValueError("Electricity service is not met")
    if f["chp_heat"] + f["boiler_heat"] != s.heat_mwh:
        raise ValueError("Useful heat service is not met")
    return f


def purchased_cost(energy, energy_unit, price, price_unit):
    if energy_unit not in ("MWh_fuel", "MWh_electric") or price_unit != "EUR/" + energy_unit:
        raise ValueError("Purchased-energy quantity and price carrier units must match")
    return number(energy, energy_unit) * number(price, price_unit)


def energy_cost(plan, gas_price, electricity_price):
    f = validate(plan)
    return (purchased_cost(f["fuel"], "MWh_fuel", gas_price, "EUR/MWh_fuel")
            + purchased_cost(plan.import_mwh, "MWh_electric", electricity_price, "EUR/MWh_electric"))


def compare(base, alternative, gas_price, electricity_price, k,
            boiler_heat_limit=D("9")):
    """K is incremental cash for the alternative in this same modeled period.

    An infeasible choice produces no admissible benefit; it is not zero value.
    This toy gate does not validate real plant performance or permissions.
    """
    fa, fb = validate(base), validate(alternative)
    if base.service != alternative.service:
        raise ValueError("Period, product, output, heat quality and service boundaries must match")
    extra = number(k, "incremental K in EUR for this period")
    limit = number(boiler_heat_limit, "boiler useful-heat limit MWh_th")
    if extra < 0 or limit < 0:
        raise ValueError("K and the boiler limit must be non-negative")
    if fa["boiler_heat"] > limit:
        raise ValueError("Baseline is infeasible under the same constraint")
    ca = energy_cost(base, gas_price, electricity_price)
    if fb["boiler_heat"] > limit:
        return {"feasible": False, "reason": "Alternative exceeds boiler useful-heat limit",
                "cost_a": ca, "cost_b": None, "net": None, "per_tonne": None,
                "choice": "A", "policy_benefit": D("0")}
    cb = energy_cost(alternative, gas_price, electricity_price) + extra
    net = ca - cb
    return {"feasible": True, "reason": "Toy constraints satisfied, real feasibility unverified",
            "cost_a": ca, "cost_b": cb, "net": net,
            "per_tonne": net / base.service.product_tonnes,
            "choice": "B" if net > 0 else "A", "policy_benefit": max(D("0"), net)}


def interpolated(alpha):
    """SYNTHETIC continuous feasible fraction; no claim of Henkel turndown freedom."""
    x = number(alpha, "fraction of the illustrative switch")
    if not 0 <= x <= 1:
        raise ValueError("Fraction must lie in [0, 1]")
    return replace(B, chp_fuel_mwh=D("100")-D("20")*x,
                   boiler_fuel_mwh=D("10")*x, import_mwh=D("10")+D("7")*x)


def break_even(gas_price, k, alpha=D("1")):
    x = number(alpha, "switch fraction")
    interpolated(x)
    extra = number(k, "K")
    if extra < 0:
        raise ValueError("K must be non-negative")
    if x == 0:
        return None
    return (D("10")*x*number(gas_price, "gas price")-extra)/(D("7")*x)


def residual_value(gas_gap, electric_gap, gas_price, electricity_price, k, q,
                   output_unit="t_product"):
    """C01 SYMBOLIC variables: gaps in MWh of external purchased energy/t_product.

    Unknowns stay unknown. Negative gaps/outcomes remain visible. For shared heat,
    replace a simple purchased-fuel gap with the joint C03 calculation.
    """
    if output_unit != "t_product":
        raise ValueError("Steam or CO2 tonnes are not product tonnes")
    if any(v is None for v in [gas_gap, electric_gap, gas_price, electricity_price, k, q]):
        return None
    q = quantity(q, output_unit, "t_product")
    if q <= 0:
        raise ValueError("Matching product output must be positive")
    extra = number(k, "K_dryer")
    if extra < 0:
        raise ValueError("K_dryer must be non-negative")
    return (number(gas_gap, "residual gas intensity gap")*number(gas_price, "gas price")
            + number(electric_gap, "residual electric intensity gap")
            * number(electricity_price, "electricity price") - extra/q)


CANDIDATES = [
    ("C01", "Residual dryer", "Provisional comparison/fallback", "Keep only if a controllable residual gap survives existing control and quality constraints.", "R02 R64"),
    ("C02", "Production-aware forecasting", "Deferred", "Reopen only when a named C03/C01 decision needs a future input and has suitable decision-time data.", "R02 R07"),
    ("C03", "Coupled heat and electricity", "Provisional lead", "Continue only with a feasible, authorized alternative and matching net cash/output boundary.", "R65 R66 R69"),
    ("C04", "Heat-export coordination", "Nested within C03", "Split only for a distinct controllable action with demonstrably non-overlapping cash benefit.", "R10"),
    ("C05", "Maintenance prioritization", "Deferred", "Reopen for confirmed unresolved faults whose repair changes net measured cost beyond existing monitoring.", "R55"),
    ("C06", "Production timing", "Deferred", "Reopen for a specific shiftable process, feasible service constraints and applicable price exposure.", "R07"),
    ("C07", "Commercial reconciliation", "C03 dependency", "Separate only if evidence identifies a distinct avoidable charge; no billing error is alleged.", "R07 R65"),
    ("C08", "Warehouse loads", "Deferred", "Reopen for material controllable measured loads and defensible logistics/product allocation.", "R67"),
    ("C09", "Research/building loads", "Deferred", "Reopen for safely avoidable operation with measured loads and defensible allocation.", "R08"),
    ("C10", "Supply investment", "Deferred", "Reopen for a specific asset alternative supported by residual demand, constraints and cost evidence.", "R65"),
]


SCENARIOS = [
    ("Base switch", "40", "40", "1", "0", "9"),
    ("Higher electricity price", "40", "120", "1", "0", "9"),
    ("Lower gas price", "20", "40", "1", "0", "9"),
    ("Incremental cost", "40", "40", "1", "60", "9"),
    ("Cost reverses switch", "40", "40", "1", "150", "9"),
    ("Limited flexibility, same incremental cost", "40", "40", "0.25", "60", "9"),
    ("No flexibility", "40", "40", "0", "0", "9"),
    ("Insufficient boiler capacity", "40", "40", "1", "0", "8"),
]

# Authored fixtures for a separate, directly purchased-energy dryer boundary.
# These are not measured residual gaps or additions to the C03 result.
C01_EXAMPLE = {"gas_gap": "0.01", "electric_gap": "0.002",
               "gas_price": "40", "electricity_price": "120", "q": "20"}
C01_COSTS = [("Residual improvement", "6"),
             ("Break-even incremental cost", "12.8"),
             ("Cost exceeds benefit", "15")]


def run_checks():
    passed = []
    def require(condition, name):
        if not condition:
            raise AssertionError(name)
        passed.append(name)
    def rejected(fn, name):
        try:
            fn()
        except (ValueError, ArithmeticError):
            passed.append(name)
        else:
            raise AssertionError(name)
    rejected(lambda: purchased_cost("1", "MWh_th", "40", "EUR/MWh_fuel"), "Reject useful heat valued directly as purchased fuel without a supply conversion")
    rejected(lambda: purchased_cost("1", "MWh_electric", "40", "EUR/MWh_fuel"), "Reject mismatched purchased-energy and price units")
    require(flows(A)["chp_electricity"] == D("35") and flows(B)["chp_heat"] == D("36"), "SYNTHETIC CHP output arithmetic")
    validate(A); validate(B)
    passed.append("SYNTHETIC electricity and useful-heat balances for both plans")
    require(compare(A, B, "40", "40", "0")["per_tonne"] == D("6"), "SYNTHETIC positive switch benefit")
    require(compare(A, B, "40", "120", "0")["per_tonne"] == D("-22"), "SYNTHETIC negative switch preserved; policy retains baseline")
    require(compare(A, B, "40", "120", "0")["choice"] == "A", "Cost policy does not recommend a losing switch")
    require(compare(A, B, "40", "40", "150")["per_tonne"] == D("-1.5"), "Incremental K counted once and can reverse sign")
    require(compare(A, interpolated("0.25"), "40", "40", "60")["per_tonne"] == D("-1.5"), "Reduced synthetic flexibility can reverse sign with K held fixed")
    require(compare(A, A, "40", "40", "0")["net"] == 0, "Unchanged action with no incremental cost gives zero benefit")
    require(not compare(A, B, "40", "40", "0", D("8"))["feasible"], "Infeasible alternative rejected regardless of apparent price benefit")
    require(compare(A, B, "40", "40", "0", D("8"))["per_tonne"] is None, "Infeasibility is not reported as a zero-valued feasible switch")
    require(abs(D("7")*break_even("40", "0")-D("400")) < D("1e-20"), "Break-even reconciles unrounded cost difference")
    require(break_even("40", "0", D("0")) is None, "No switch implies no electricity break-even")
    require(residual_value(None, None, None, None, None, None) is None, "Unknown residual economics stay unknown")
    for unit in ["t_steam", "t_CO2"]:
        rejected(lambda unit=unit: validate(replace(A, service=replace(A.service, output_unit=unit))), f"Reject denominator unit {unit}")
    for field, value in [("product_tonnes", D("19")), ("period", "different period"),
                         ("product_family", "different mix"), ("boundary", "whole campus"),
                         ("heat_grade", "incompatible delivery pressure")]:
        bad = replace(B, service=replace(B.service, **{field: value}))
        rejected(lambda bad=bad: compare(A, bad, "40", "40", "0"), f"Reject mismatched {field}")
    rejected(lambda: validate(replace(A, service=replace(A.service, product_tonnes=D("0")))), "Reject zero product output")
    rejected(lambda: validate(replace(B, import_mwh=D("16"))), "Reject unmet electricity demand")
    rejected(lambda: compare(A, B, None, "40", "0"), "Unknown tariff is not zero")
    rejected(lambda: compare(A, B, "NaN", "40", "0"), "Reject non-finite tariff")
    require(energy_cost(B, "40", "40") == D("4280"), "CHP fuel and boiler fuel counted once; internal heat has no duplicate cash debit")
    require([c[0] for c in CANDIDATES] == [f"C{i:02d}" for i in range(1, 11)], "All ten candidate dispositions are present")
    for cost, expected in [("6", "0.34"), ("12.8", "0"), ("15", "-0.11")]:
        require(residual_value(**C01_EXAMPLE, k=cost) == D(expected),
                f"C01 synthetic residual value at K={cost} reconciles")
    require(residual_value("-0.01", "0", "40", "120", "0", "20") == D("-0.4"),
            "C01 deterioration remains negative")
    rejected(lambda: residual_value("0.01", "0.002", "40", "120", "6", "0"),
             "C01 rejects zero matching product output")
    rejected(lambda: residual_value("0.01", "0.002", "40", "120", "6", "20", "t_steam"),
             "C01 rejects steam denominator")
    return passed


def fmt(value):
    return format(value.quantize(D("0.01")), "f") if value is not None else "not applicable"


def syn(value):
    return f"{SYN} {fmt(value)}"


def citations(ids):
    return ", ".join(f"[{r}](sources.md#{r.lower()})" for r in ids.split())


def render(checks):
    rows = ["# Economics: auditable synthetic and symbolic trace", "",
            "Generated by `economics.py`. Do not edit this trace independently; run `python3 -B economics.py --write` after changing the authoritative script.", "",
            "**No Henkel savings estimate.** Public evidence is labeled HISTORICAL/REPORTED with source IDs; model inputs and outputs are SYNTHETIC; unresolved inputs are UNKNOWN. No proxy tariff is used. Scenarios are not probabilities or confidence intervals.", "",
            "## Candidate register", "",
            "These are the selected investigation priorities. Evidence establishes context, not remaining profitability. Deferred cases have no assigned zero benefit.", "",
            "| Candidate | Decision | Disposition | Continue/reopen condition | Context sources |",
            "|---|---|---|---|---|"]
    rows += [f"| {cid} | {name} | {status} | {condition} | {citations(ids)} |" for cid,name,status,condition,ids in CANDIDATES]
    rows += ["", "## Boundaries and cost method", "",
             "For real C03: product family, analyzed period, meter boundary, present topology, energy service, tariffs and matching output Q are UNKNOWN. Offices, laboratories, third-party supply, goods merely stored on site, steam tonnes and CO2 tonnes cannot enter Q as manufactured product. Shared costs need an explicit allocation before a product metric is claimed. The source context is a mixed site and third-party energy boundary, not a public matched cost/output dataset. "+citations("R07 R65"), "",
             "For real C01: Q_dryer is good output of the same defined dryer/product family over the same period, with moisture, recipe, quality and relevant operating conditions normalized. No current matched value is available in the cited historical process records. "+citations("R02 R64"), "",
             "For the fictional comparison only: an isolated fictional product family, unchanged mix/quality, SYNTHETIC one-hour period, and SYNTHETIC 20 product tonnes are served by both choices. All modeled external costs belong to that service; there are no campus overheads or third-party obligations in this fixture. This is an assumption, not a Henkel topology.", "",
             "Net benefit = baseline net external cash cost − alternative net external cash cost − incremental K not already included. Divide by the same positive Q. Internal heat/steam transfers are not another fuel purchase. Count export revenue once only when ownership, metered service and applicable terms are established. Unchanged fixed charges cancel; changed charges must be modeled. K covers applicable starts, wear, fees and other incremental costs in the same period; a project investment requires a separate horizon calculation, not an arbitrary one-hour capex deduction.", "",
             "UNIT DEFINITIONS: MWh_fuel, MWh_electric and MWh_th are different energy carriers. 1 MWh = 1,000 kWh; MW × hours = MWh. €/MWh × MWh = €; € / t_product = €/product-tonne. A metric tonne of product is not a tonne of steam or CO2. The model uses a common fuel heating-value basis and net electricity after auxiliaries. Equal heat amounts also require compatible delivery temperature and pressure.", "",
             "## C03 matched fictional example", "",
             "**Every value in this table is SYNTHETIC.** The two operating points are assumed feasible in the toy system. Efficiencies, dispatch, heat quality and permissions are unvalidated for Henkel.", "",
             "Why these inputs: round operating points preserve equal useful service and expose the coupled trade-off between less fuel and more electricity purchases. Prices span a sign reversal; output Q is a transparent normalization assumption. None is a calibrated plant parameter, market forecast or sourced Henkel estimate.", "",
             "| Input or flow | Choice A | Choice B |", "|---|---:|---:|"]
    fa, fb = flows(A), flows(B)
    table = [
        ("CHP fuel, MWh_fuel", A.chp_fuel_mwh, B.chp_fuel_mwh),
        ("CHP electrical efficiency, %", A.electric_efficiency*100, B.electric_efficiency*100),
        ("CHP useful-heat efficiency, %", A.heat_efficiency*100, B.heat_efficiency*100),
        ("CHP electricity, MWh_electric", fa["chp_electricity"], fb["chp_electricity"]),
        ("CHP useful heat, MWh_th", fa["chp_heat"], fb["chp_heat"]),
        ("Additional boiler fuel, MWh_fuel", A.boiler_fuel_mwh, B.boiler_fuel_mwh),
        ("Boiler useful-heat efficiency, %", A.boiler_efficiency*100, B.boiler_efficiency*100),
        ("Additional boiler useful heat, MWh_th", fa["boiler_heat"], fb["boiler_heat"]),
        ("Electricity bought, MWh_electric", A.import_mwh, B.import_mwh),
        ("Total electricity served, MWh_electric", A.service.electricity_mwh, B.service.electricity_mwh),
        ("Total useful heat served, MWh_th", A.service.heat_mwh, B.service.heat_mwh),
        ("Matching good product output, t_product", A.service.product_tonnes, B.service.product_tonnes)]
    rows += [f"| {label} | {syn(a)} | {syn(b)} |" for label,a,b in table]
    rows += ["", "G is the applicable marginal gas price in €/MWh_fuel; P is the applicable marginal electricity purchase price in €/MWh_electric. The fictional base G is SYNTHETIC €40/MWh_fuel. P is never silently a wholesale-market proxy.", "",
             "With SYNTHETIC coefficients from the table: A = 100G + 10P; B = 90G + 17P + K; switch benefit per product tonne = (10G − 7P − K) / Q. Total B below already includes K: it must not be subtracted again.", "",
             f"At SYNTHETIC K = €0, the derived electricity break-even is {syn(break_even('40','0'))} €/MWh_electric. At SYNTHETIC K = €60 it is {syn(break_even('40','60'))} €/MWh_electric. Calculations retain Decimal precision; displayed money is rounded only for reading.", "",
             "## C03 sensitivity and infeasibility", "",
             "Alpha is the SYNTHETIC permitted fraction of the A-to-B switch; linear interpolation is an illustrative assumption, not evidence of actual part-load efficiency. At alpha below the full switch, K remains the stated fixed incremental cost for that period. The formula becomes (10 alpha G − 7 alpha P − K) / Q, with SYNTHETIC coefficients. At zero flexibility and zero K there is no change; at zero flexibility with positive K the unnecessary cost is a loss.", "",
             "All numeric cells below are SYNTHETIC. 'B switch' is the consequence of choosing B; the simple comparison policy keeps A when B loses or is infeasible. Its avoided loss is not an additional savings claim.", "",
             "| Scenario | G €/MWh_fuel | P €/MWh_electric | Alpha | K € | Boiler heat limit MWh_th | A € | B including K € | B switch €/product-tonne | Choice |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for name, gas, power, alpha, k, limit in SCENARIOS:
        r = compare(A, interpolated(alpha), gas, power, k, D(limit))
        numbers = [syn(D(v)) for v in [gas,power,alpha,k,limit]]
        numbers += [syn(r["cost_a"]), syn(r["cost_b"]) if r["feasible"] else "INFEASIBLE",
                    syn(r["per_tonne"]) if r["feasible"] else "NOT ADMISSIBLE"]
        rows.append("| "+" | ".join([name]+numbers+[r["choice"]])+" |")
    rows += ["", "In the rejected scenario, B needs SYNTHETIC 9 MWh_th from the boiler but the limit is SYNTHETIC 8 MWh_th. A remains feasible. A positive unconstrained spreadsheet margin cannot override that limit. Real constraints would also include pressure, temperature, ramps, availability, startup, quality, contracts and operating authority; these are not validated by the toy gate.", "",
             "No export is modeled in the fixture. C04 is nested in C03, not assigned an additive savings number. If heat delivery or export revenues are introduced, recalculate one joint baseline-versus-alternative cash ledger, including coupled fuel and power effects and unchanged obligations. Do not add the advertised benefit of an existing heat project. "+citations("R10"), "",
             "## C01 residual dryer economics", "",
             "HISTORICAL REPORTED [R64](sources.md#r64): the existing automatic-control project reports annual gas savings of 1,800 MWh and electricity savings of 300 MWh. Its symbolic avoided-energy value is `1,800 MWh_gas/year × P_gas + 300 MWh_electric/year × P_elec`. Prices must match the original carrier, period and avoidable cost basis. This is a valuation expression for an EXISTING intervention, not new residual benefit or a verified net-cash result; implementation costs and matched original prices/output are unavailable.", "",
             "HISTORICAL REPORTED [R02](sources.md#r02): about 400,000 tonnes/year refers to the article's production scope in 2021. The program never uses it as Q, never divides the dena MWh by it, and makes no current Düsseldorf €/tonne claim.", "",
             "For the proposed residual decision, let Δi_gas and Δi_elec be baseline-minus-alternative external purchased-energy intensity in MWh/product-tonne, after existing control and matched process conditions. Let K_dryer be the incremental cost in the same period and Q_dryer its matching good product output. Then:", "",
             "`Residual benefit €/product-tonne = Δi_gas × P_gas + Δi_elec × P_elec − K_dryer / Q_dryer`", "",
             "`Break-even Δi_gas = (K_dryer / Q_dryer − Δi_elec × P_elec) / P_gas`, only when P_gas is positive and the other inputs are known. Negative residual gaps or net benefit must remain visible. All these customer inputs and the result are UNKNOWN — not estimated; no remaining-saving percentage is invented. If the process uses shared utility heat rather than directly avoidable purchased fuel, evaluate its actual marginal supply effect within C03. Do not add the standalone C01 and C03 values: demand reduction changes utility dispatch.", "",
             "## C01 fictional worked example", "",
             "All values below are SYNTHETIC. This separate fictional dryer purchases its relevant gas and electricity directly. Good output, recipe, moisture and quality are held constant after existing control. It is not the C03 plant; do not add the results.", "",
             "Assume residual gas intensity falls by 0.010 MWh_fuel/product-tonne and electric intensity by 0.002 MWh_electric/product-tonne. At authored prices of €40/MWh_fuel and €120/MWh_electric, gross avoided cost is €0.64/product-tonne. Matching output is 20 product tonnes in the same fictional period. These small round gaps make the unit conversion and break-even transparent; they are not an assumed percentage of Henkel consumption or proof that a residual gap exists.", "",
             "| Fictional test | Incremental K, € | Net €/product-tonne | Interpretation |",
             "|---|---:|---:|---|"]
    for name, cost in C01_COSTS:
        value = residual_value(**C01_EXAMPLE, k=cost)
        decision = "Investigate only if feasible" if value > 0 else "No positive incremental benefit"
        rows.append(f"| {name} | {syn(D(cost))} | {syn(value)} | {decision} |")
    rows += ["", "At the fictional K=€6, the gas-gap break-even is 0.0015 MWh_fuel/product-tonne when the other inputs are fixed. The maximum tolerable K is €12.80 for this fictional period. Customer value remains UNKNOWN. A zero or negative measured residual gap, unstable quality, or non-avoidable energy cost can invalidate the case.", "",
             "## Executed checks and limits", "",
             "The following checks run on every invocation. PASS means the implemented calculation or rejection behaved as specified, not that customer inputs or plant feasibility are verified.", ""]
    rows += [f"- PASS — {name}." for name in checks]
    rows += ["", "Coverage boundaries: units are explicit field contracts, not a general dimensional-analysis library. Heat-grade/period/product equality checks compare declared metadata; they do not measure physical compatibility. The no-double-counting ledger has only external gas and electricity purchases plus K; export optimization is deliberately not implemented. This is a deterministic comparison, not a dispatch optimizer, trained forecast, calibrated twin or deployed application. No annual extrapolation or confidence interval is produced.", ""]
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="test and compare economics.md without writing")
    group.add_argument("--write", action="store_true", help="test and regenerate adjacent economics.md")
    args = parser.parse_args()
    checks = run_checks()
    trace = render(checks)
    destination = Path(__file__).resolve().with_name("economics.md")
    if args.check:
        if not destination.is_file() or destination.read_text(encoding="utf-8") != trace:
            raise SystemExit("FAIL: economics.md differs from the authoritative script; inspect changes before --write")
        print(f"PASS: {len(checks)} checks; economics.md matches deterministic output. No Henkel savings validation.")
    elif args.write:
        destination.write_text(trace, encoding="utf-8")
        print(f"Wrote economics.md after {len(checks)} checks. All numeric model fixtures are SYNTHETIC.")
    else:
        print(trace, end="")


if __name__ == "__main__":
    main()
