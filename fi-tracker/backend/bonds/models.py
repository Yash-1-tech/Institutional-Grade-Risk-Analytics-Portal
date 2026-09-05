from django.db import models


class BondRecord(models.Model):
    isin = models.CharField(max_length=12, primary_key=True)
    issuer_name = models.CharField(max_length=100)
    maturity_date = models.DateField()
    coupon_rate = models.DecimalField(max_digits=5, decimal_places=4)
    face_value = models.DecimalField(max_digits=15, decimal_places=2, default=1000.00)
    payment_frequency = models.IntegerField(default=2)  # 1=Annual, 2=Semi-Annual

    def __str__(self):
        return f"{self.isin} ({self.issuer_name})"


class YieldCurvePoint(models.Model):
    curve_date = models.DateField()
    tenor_months = models.IntegerField()  # 3, 6, 12, 60, 120, 360
    rate = models.DecimalField(max_digits=5, decimal_places=4)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["curve_date", "tenor_months"],
                                     name="unique_curve_date_tenor")
        ]

    def __str__(self):
        return f"{self.curve_date} @ {self.tenor_months}mo: {self.rate}"


class PortfolioPosition(models.Model):
    id = models.BigAutoField(primary_key=True)
    portfolio_id = models.UUIDField()
    bond = models.ForeignKey(BondRecord, related_name="positions",
                              on_delete=models.CASCADE, db_column="bond_isin")
    quantity = models.IntegerField()
    purchase_yield = models.DecimalField(max_digits=5, decimal_places=4,
                                          null=True, blank=True)

    def __str__(self):
        return f"{self.quantity}x {self.bond_id} in {self.portfolio_id}"
