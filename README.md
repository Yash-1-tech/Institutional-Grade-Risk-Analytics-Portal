# Fixed Income Portfolio & Sensitivities Tracker

Prices bonds from their cash flows, computes Macaulay/Modified Duration and
Convexity, and shows how a hypothetical yield curve shift moves portfolio
value — including the dollar amount convexity saves you versus a duration-only
estimate.

## Stack
Next.js (frontend) → Django REST Framework (API) → PostgreSQL (bond terms,
yield curves) → NumPy (the actual math). No async task queue here — bond
pricing is cheap enough (closed-form sums over a few dozen cash flows per
bond) to run synchronously inside the request, unlike the Monte Carlo VaR
engine.

## Repo layout
```
backend/
  config/                   Django project (settings, urls)
  bonds/
    pricing.py              Pure math — price, duration, convexity, shocks
    test_pricing.py         Unit tests (no DB needed)
    models.py                BondRecord, YieldCurvePoint, PortfolioPosition
    serializers.py            DRF serializers
    views.py                   API endpoints
    curve_data.py               FRED ingestion + caching + interpolation
frontend/
  app/dashboard/page.jsx      Yield curve chart + sensitivities table + shock widget
sql/schema.sql                 Raw schema
docker-compose.yml              Postgres for local dev
```

## Running it locally
```bash
docker compose up -d
cd backend
pip install -r requirements.txt
export FRED_API_KEY=your_key_here   # https://fred.stlouisfed.org/docs/api/api_key.html
python manage.py migrate
python manage.py runserver

cd ../frontend
npm install
npm run dev
```
Open `http://localhost:3000/dashboard`.

## Why this architecture
- **No Celery here, unlike the VaR engine**: repricing a portfolio of bonds
  is a closed-form sum over each bond's cash flows — microseconds of NumPy,
  not a 10,000-path simulation. Async infrastructure would be overhead with
  no payoff, so the sensitivities endpoint computes synchronously and
  returns directly.
- **`pricing.py` has zero Django imports**: same principle as the VaR
  project — the math that has to be *correct* is isolated and tested
  against textbook closed-form results independent of the web framework.
- **Two shock estimates, not one**: the API always computes both the Taylor
  (duration + convexity) approximation *and* the exact reprice at the
  shifted yield. The gap between them is what the "convexity benefit"
  widget visualizes — it's the whole pedagogical point of the project.
- **Yield curve interpolation**: a bond maturing in 7.5 years doesn't sit on
  a standard tenor point (5Y, 10Y), so `curve_data.interpolated_rate()`
  linearly interpolates between the two nearest curve points to mark that
  bond to market.

## Testing the math independently of the whole stack
```bash
cd backend/bonds
python3 test_pricing.py
```
Checks: a bond priced at its own coupon rate equals par, price falls as
yield rises, a zero-coupon bond's duration exactly equals its maturity, a
higher coupon lowers duration, convexity is always positive for a plain
vanilla bond, the Taylor approximation tracks the exact reprice closely for
small shifts, and the convexity-adjusted estimate beats duration-only for
large shifts in either direction.
