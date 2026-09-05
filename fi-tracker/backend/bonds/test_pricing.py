"""
Run with: python3 test_pricing.py
No Django/DB needed — exercises pricing.py in isolation.
"""
from pricing import Bond, price, macaulay_duration, modified_duration, \
    convexity, shock_analysis


def test_bond_priced_at_coupon_rate_equals_par():
    b = Bond("T1", coupon_rate=0.10, face_value=1000, frequency=1,
              years_to_maturity=3)
    assert abs(price(b, ytm=0.10) - 1000.0) < 1e-6


def test_price_falls_as_yield_rises():
    b = Bond("T2", coupon_rate=0.05, face_value=1000, frequency=2,
              years_to_maturity=10)
    p_low = price(b, ytm=0.03)
    p_high = price(b, ytm=0.08)
    assert p_low > p_high


def test_zero_coupon_duration_equals_maturity():
    zcb = Bond("Z1", coupon_rate=0.0, face_value=1000, frequency=1,
               years_to_maturity=7)
    assert abs(macaulay_duration(zcb, ytm=0.04) - 7.0) < 1e-9
    # for a zero coupon bond, D_mod = D_mac / (1+y)
    assert abs(modified_duration(zcb, ytm=0.04) - 7.0 / 1.04) < 1e-9


def test_higher_coupon_means_lower_duration():
    """A higher coupon returns cash sooner, pulling duration down."""
    low_coupon = Bond("LC", coupon_rate=0.02, face_value=1000, frequency=2,
                       years_to_maturity=10)
    high_coupon = Bond("HC", coupon_rate=0.08, face_value=1000, frequency=2,
                        years_to_maturity=10)
    assert modified_duration(high_coupon, 0.05) < modified_duration(low_coupon, 0.05)


def test_convexity_always_positive_for_plain_vanilla_bond():
    b = Bond("T3", coupon_rate=0.04, face_value=1000, frequency=2,
              years_to_maturity=20)
    assert convexity(b, ytm=0.045) > 0


def test_taylor_approximation_close_to_exact_reprice_for_small_shift():
    b = Bond("T4", coupon_rate=0.04, face_value=1000, frequency=2,
              years_to_maturity=10)
    result = shock_analysis([b], [0.04], [1], shift_bps=25)  # 25bps: small shift
    # small shifts: Taylor (duration+convexity) should track the exact
    # reprice very closely
    assert abs(result["est_value_change_pct"] - result["exact_value_change_pct"]) < 0.05


def test_convexity_benefit_is_positive_for_large_shift():
    """Positive convexity means the bond loses less than duration-only
    predicts on a rate rise, and gains more than duration-only predicts on
    a rate fall — the actual value should exceed the duration-only estimate
    on any large parallel shift, in either direction."""
    b = Bond("T5", coupon_rate=0.04, face_value=1000, frequency=2,
              years_to_maturity=20)
    up = shock_analysis([b], [0.04], [1], shift_bps=200)
    down = shock_analysis([b], [0.04], [1], shift_bps=-200)
    assert up["convexity_dollar_benefit"] > 0
    assert down["convexity_dollar_benefit"] > 0


if __name__ == "__main__":
    import sys
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    sys.exit(1 if failed else 0)
