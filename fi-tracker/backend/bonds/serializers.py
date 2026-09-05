from rest_framework import serializers
from .models import BondRecord, PortfolioPosition


class BondSerializer(serializers.ModelSerializer):
    class Meta:
        model = BondRecord
        fields = ["isin", "issuer_name", "maturity_date", "coupon_rate",
                  "face_value", "payment_frequency"]
        extra_kwargs = {
            "issuer_name": {"required": False, "default": ""},
        }


class PortfolioPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioPosition
        fields = ["bond", "quantity", "purchase_yield"]


class SensitivitiesQuerySerializer(serializers.Serializer):
    shift_bps = serializers.FloatField(default=0.0)
