"""
Fetches the latest treasury par yield curve from FRED (or falls back to
yfinance treasury futures/yield tickers) and caches it into PostgreSQL.
Kept separate from pricing.py so the pure math never touches the network.
"""
import datetime as dt
import os

import requests

from .models import YieldCurvePoint

# FRED series IDs for constant-maturity treasury yields, by tenor in months
FRED_SERIES = {
    3: "DGS3MO",
    6: "DGS6MO",
    12: "DGS1",
    24: "DGS2",
    60: "DGS5",
    84: "DGS7",
    120: "DGS10",
    360: "DGS30",
}

FRED_API_KEY = os.environ.get("FRED_API_KEY")
STALE_AFTER_DAYS = 1


def ensure_fresh_curve() -> None:
    latest = YieldCurvePoint.objects.order_by("-curve_date").first()
    is_stale = (
        latest is None
        or (dt.date.today() - latest.curve_date).days > STALE_AFTER_DAYS
    )
    if is_stale:
        _fetch_and_cache_curve()


def _fetch_and_cache_curve() -> None:
    today = dt.date.today()
    points = []

    for tenor_months, series_id in FRED_SERIES.items():
        resp = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1,
            },
            timeout=10,
        )
        resp.raise_for_status()
        obs = resp.json()["observations"][0]
        if obs["value"] == ".":  # FRED's marker for a missing observation
            continue
        points.append(YieldCurvePoint(
            curve_date=today,
            tenor_months=tenor_months,
            rate=float(obs["value"]) / 100.0,  # FRED reports percent, we store decimal
        ))

    YieldCurvePoint.objects.filter(curve_date=today).delete()
    YieldCurvePoint.objects.bulk_create(points, ignore_conflicts=True)


def latest_curve_dict() -> dict:
    """Returns e.g. {'1Y': 0.042, '5Y': 0.038, '10Y': 0.039}"""
    latest_date = YieldCurvePoint.objects.order_by("-curve_date").values_list(
        "curve_date", flat=True
    ).first()
    points = YieldCurvePoint.objects.filter(curve_date=latest_date)

    label_by_months = {3: "3M", 6: "6M", 12: "1Y", 24: "2Y", 60: "5Y",
                        84: "7Y", 120: "10Y", 360: "30Y"}
    rates = {label_by_months[p.tenor_months]: float(p.rate) for p in points
              if p.tenor_months in label_by_months}
    return {"date": str(latest_date), "rates": rates}


def interpolated_rate(curve_points: dict, years_to_maturity: float) -> float:
    """
    Linear interpolation across the tenor/rate points for a bond whose
    maturity falls between two curve tenors (e.g. a 7.5y bond between the
    5Y and 10Y points). curve_points maps tenor-in-years -> rate.
    """
    tenors = sorted(curve_points.keys())
    if years_to_maturity <= tenors[0]:
        return curve_points[tenors[0]]
    if years_to_maturity >= tenors[-1]:
        return curve_points[tenors[-1]]

    for lo, hi in zip(tenors, tenors[1:]):
        if lo <= years_to_maturity <= hi:
            weight = (years_to_maturity - lo) / (hi - lo)
            return curve_points[lo] + weight * (curve_points[hi] - curve_points[lo])
