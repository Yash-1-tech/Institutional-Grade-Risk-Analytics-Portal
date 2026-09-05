import datetime as dt

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import BondRecord, PortfolioPosition
from .serializers import BondSerializer, SensitivitiesQuerySerializer
from .pricing import Bond, shock_analysis
from .curve_data import ensure_fresh_curve, latest_curve_dict, interpolated_rate


class BondListCreateView(APIView):
    """POST /api/v1/bonds/"""

    def post(self, request):
        serializer = BondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bond = serializer.save()
        return Response(
            {"status": "created", "bond_id": bond.isin},
            status=status.HTTP_201_CREATED,
        )


class LatestCurveView(APIView):
    """GET /api/v1/curve/latest/"""

    def get(self, request):
        ensure_fresh_curve()
        return Response(latest_curve_dict())


class PortfolioSensitivitiesView(APIView):
    """
    GET /api/v1/portfolio/<id>/sensitivities/?shift_bps=100

    Pulls each position's bond terms from Postgres, marks each bond to the
    current curve (or its purchase yield if the user pinned one), then runs
    the pure-math shock_analysis() from pricing.py.
    """

    def get(self, request, portfolio_id):
        query = SensitivitiesQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        shift_bps = query.validated_data["shift_bps"]

        positions = (PortfolioPosition.objects
                     .filter(portfolio_id=portfolio_id)
                     .select_related("bond"))
        if not positions:
            return Response({"detail": "no positions for this portfolio"},
                             status=status.HTTP_404_NOT_FOUND)

        ensure_fresh_curve()
        curve = latest_curve_dict()["rates"]
        tenor_years = {"3M": 0.25, "6M": 0.5, "1Y": 1, "2Y": 2, "5Y": 5,
                       "7Y": 7, "10Y": 10, "30Y": 30}
        curve_by_years = {tenor_years[k]: v for k, v in curve.items()
                            if k in tenor_years}

        bonds, ytms, quantities = [], [], []
        today = dt.date.today()

        for pos in positions:
            years_to_maturity = (pos.bond.maturity_date - today).days / 365.25
            bond = Bond(
                isin=pos.bond.isin,
                coupon_rate=float(pos.bond.coupon_rate),
                face_value=float(pos.bond.face_value),
                frequency=pos.bond.payment_frequency,
                years_to_maturity=years_to_maturity,
            )
            # use the pinned purchase yield if the user set one, else mark
            # to the current curve at this bond's tenor
            ytm = (float(pos.purchase_yield) if pos.purchase_yield is not None
                   else interpolated_rate(curve_by_years, years_to_maturity))

            bonds.append(bond)
            ytms.append(ytm)
            quantities.append(pos.quantity)

        result = shock_analysis(bonds, ytms, quantities, shift_bps)
        return Response(result)
