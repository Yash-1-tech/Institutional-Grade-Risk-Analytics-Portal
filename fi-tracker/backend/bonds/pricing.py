"""
bonds.pricing
-------------
Pure-NumPy bond pricing and sensitivity engine. No Django dependency, so it
can be unit-tested and reasoned about independent of the web framework.

Conventions:
    coupon_rate, ytm are ANNUAL rates (e.g. 0.045 for 4.5%)
    frequency is payments per year (1 = annual, 2 = semi-annual, 4 = quarterly)
    All per-period math uses y = ytm / frequency, n = years_to_maturity * frequency
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class Bond:
    isin: str
    coupon_rate: float          # annual, e.g. 0.045
    face_value: float           # e.g. 1000.00
    frequency: int              # payments per year
    years_to_maturity: float    # can be fractional


def _cash_flows(bond: Bond) -> np.ndarray:
    """Coupon each period, plus face value returned in the final period."""
    n = round(bond.years_to_maturity * bond.frequency)
    coupon_per_period = bond.face_value * bond.coupon_rate / bond.frequency
    cash_flows = np.full(n, coupon_per_period)
    cash_flows[-1] += bond.face_value
    return cash_flows


def price(bond: Bond, ytm: float) -> float:
    """
    P = sum_t [ CF_t / (1+y)^t ],  y = ytm / frequency
    """
    cash_flows = _cash_flows(bond)
    n = len(cash_flows)
    y = ytm / bond.frequency
    periods = np.arange(1, n + 1)
    discount_factors = 1.0 / (1.0 + y) ** periods
    return float(np.sum(cash_flows * discount_factors))


def macaulay_duration(bond: Bond, ytm: float) -> float:
    """
    D_mac = (1/P) * sum_t [ t * CF_t / (1+y)^t ]     -- in PERIODS
    Reported in YEARS by dividing by frequency, matching market convention.
    """
    cash_flows = _cash_flows(bond)
    n = len(cash_flows)
    y = ytm / bond.frequency
    periods = np.arange(1, n + 1)
    discount_factors = 1.0 / (1.0 + y) ** periods
    pv_flows = cash_flows * discount_factors

    p = pv_flows.sum()
    d_mac_periods = float(np.sum(periods * pv_flows) / p)
    return d_mac_periods / bond.frequency  # convert periods -> years


def modified_duration(bond: Bond, ytm: float) -> float:
    """D_mod = D_mac / (1 + y),  y = ytm / frequency (per-period yield)."""
    d_mac = macaulay_duration(bond, ytm)
    y = ytm / bond.frequency
    return d_mac / (1 + y)


def convexity(bond: Bond, ytm: float) -> float:
    """
    Convexity = (1 / (P * (1+y)^2)) * sum_t [ t(t+1) * CF_t / (1+y)^t ]   -- in PERIODS^2
    Reported in YEARS^2 by dividing by frequency^2, matching modified duration's convention.
    """
    cash_flows = _cash_flows(bond)
    n = len(cash_flows)
    y = ytm / bond.frequency
    periods = np.arange(1, n + 1)
    discount_factors = 1.0 / (1.0 + y) ** periods
    p = float(np.sum(cash_flows * discount_factors))

    weight = periods * (periods + 1)
    raw = float(np.sum(weight * cash_flows * discount_factors))
    convexity_periods = raw / (p * (1 + y) ** 2)
    return convexity_periods / (bond.frequency ** 2)  # periods^2 -> years^2


def bond_metrics(bond: Bond, ytm: float) -> dict:
    return {
        "isin": bond.isin,
        "pv": round(price(bond, ytm), 2),
        "ytm": ytm,
        "macaulay_duration": round(macaulay_duration(bond, ytm), 4),
        "modified_duration": round(modified_duration(bond, ytm), 4),
        "convexity": round(convexity(bond, ytm), 4),
    }


# ---------------------------------------------------------------------------
# Portfolio-level aggregation & shock analysis
# ---------------------------------------------------------------------------
def portfolio_sensitivities(bonds: list[Bond], ytms: list[float],
                             quantities: list[int]) -> dict:
    """
    Weighted-average duration/convexity across a portfolio, weighted by each
    bond's market-value contribution (quantity * price), not face value —
    this is the standard convention since it reflects actual dollar exposure.
    """
    per_bond = []
    market_values = []

    for bond, ytm, qty in zip(bonds, ytms, quantities):
        metrics = bond_metrics(bond, ytm)
        mv = metrics["pv"] * qty
        metrics["quantity"] = qty
        metrics["market_value"] = round(mv, 2)
        per_bond.append(metrics)
        market_values.append(mv)

    total_pv = sum(market_values)
    weights = [mv / total_pv for mv in market_values]

    weighted_mod_duration = sum(
        w * m["modified_duration"] for w, m in zip(weights, per_bond)
    )
    weighted_convexity = sum(
        w * m["convexity"] for w, m in zip(weights, per_bond)
    )

    return {
        "bonds": per_bond,
        "total_pv": round(total_pv, 2),
        "weighted_mod_duration": round(weighted_mod_duration, 4),
        "weighted_convexity": round(weighted_convexity, 4),
    }


def shock_analysis(bonds: list[Bond], ytms: list[float], quantities: list[int],
                    shift_bps: float) -> dict:
    """
    Two ways of estimating the shocked portfolio value:
      1. Taylor series approximation using duration + convexity (fast, the
         quantity actually asked for by the API contract).
      2. Full reprice at the shifted yield (exact, used to show how good the
         Taylor approximation is — this is the point of the convexity term).
    """
    sens = portfolio_sensitivities(bonds, ytms, quantities)
    delta_y = shift_bps / 10_000.0  # bps -> decimal

    # 1. Taylor series approximation:
    #    dP/P ≈ -D_mod * Δy + 0.5 * Convexity * Δy^2
    pct_change_duration_only = -sens["weighted_mod_duration"] * delta_y
    pct_change_approx = (
        pct_change_duration_only
        + 0.5 * sens["weighted_convexity"] * delta_y ** 2
    )
    duration_only_value = sens["total_pv"] * (1 + pct_change_duration_only)
    approx_value = sens["total_pv"] * (1 + pct_change_approx)

    # 2. Exact reprice: shift every bond's yield by the same amount and
    #    sum full present values (works for parallel shifts; a curve
    #    steepen/flatten would key this off tenor instead of a flat delta_y).
    shifted_ytms = [y + delta_y for y in ytms]
    exact_value = sum(
        price(bond, y) * qty
        for bond, y, qty in zip(bonds, shifted_ytms, quantities)
    )
    pct_change_exact = (exact_value - sens["total_pv"]) / sens["total_pv"]

    # The classic textbook point: duration alone is a straight tangent line
    # to a convex price/yield curve, so it *always* underestimates the true
    # price on any shift, in either direction. The convexity term is what
    # closes most of that gap — that's "the exact dollar amount saved by
    # the positive convexity adjustment" the dashboard is meant to show.
    convexity_benefit = exact_value - duration_only_value

    return {
        "total_pv": sens["total_pv"],
        "weighted_mod_duration": sens["weighted_mod_duration"],
        "weighted_convexity": sens["weighted_convexity"],
        "shift_bps": shift_bps,
        "est_value_change_pct": round(pct_change_approx * 100, 2),
        "shocked_value_taylor": round(approx_value, 2),
        "shocked_value_exact": round(exact_value, 2),
        "exact_value_change_pct": round(pct_change_exact * 100, 2),
        "convexity_dollar_benefit": round(convexity_benefit, 2),
    }
