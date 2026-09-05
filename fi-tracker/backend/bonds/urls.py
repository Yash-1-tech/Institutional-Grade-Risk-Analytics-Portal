from django.urls import path
from .views import BondListCreateView, LatestCurveView, PortfolioSensitivitiesView

urlpatterns = [
    path("v1/bonds/", BondListCreateView.as_view(), name="bonds"),
    path("v1/curve/latest/", LatestCurveView.as_view(), name="curve-latest"),
    path("v1/portfolio/<uuid:portfolio_id>/sensitivities/",
         PortfolioSensitivitiesView.as_view(), name="portfolio-sensitivities"),
]
