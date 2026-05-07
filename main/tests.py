from django.test import SimpleTestCase

from main.views.utils import _build_market_price_position


class MarketPricePositionTests(SimpleTestCase):
    def test_ceiling_price_uses_ci_midpoint_when_low_high_are_available(self):
        result = _build_market_price_position(
            comparables=[],
            price_range={'low': 230, 'high': 260, 'min': 100, 'max': 999},
            recommended_price=245,
            average_price=245,
        )

        self.assertEqual(result['floor_price'], 100)
        self.assertEqual(result['recommended_price'], 245)
        self.assertEqual(result['ceiling_price'], 245)

    def test_ceiling_price_uses_min_max_midpoint_when_low_high_are_unavailable(self):
        result = _build_market_price_position(
            comparables=[],
            price_range={'min': 100, 'max': 260},
            recommended_price=200,
            average_price=200,
        )

        self.assertEqual(result['floor_price'], 100)
        self.assertEqual(result['recommended_price'], 200)
        self.assertEqual(result['ceiling_price'], 180)

    def test_ceiling_price_falls_back_to_max_when_lower_bound_is_unavailable(self):
        result = _build_market_price_position(
            comparables=[],
            price_range={'max': 260},
            recommended_price=200,
            average_price=200,
        )

        self.assertEqual(result['floor_price'], 200)
        self.assertEqual(result['recommended_price'], 200)
        self.assertEqual(result['ceiling_price'], 260)
