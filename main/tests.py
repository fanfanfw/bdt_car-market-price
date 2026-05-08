from django.test import SimpleTestCase

from main.views.utils import (
    _build_market_price_position,
    _build_outlier_filtered_market_stats,
)


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


class PriceOutlierDetectionTests(SimpleTestCase):
    def _listing(self, price, listing_id=None, mileage=50000):
        return {
            'id': listing_id,
            'price': price,
            'mileage': mileage,
            'listing': {
                'brand': 'TOYOTA',
                'model': 'VIOS',
                'variant': 'GR S',
                'title': 'TOYOTA VIOS GR S',
            },
            'year': 2021,
            'source': 'test',
        }

    def test_sample_size_below_10_does_not_apply_outlier_filtering(self):
        listings = [
            self._listing(price, listing_id=index)
            for index, price in enumerate([60000, 62000, 64000, 66000, 68000, 132000], start=1)
        ]

        result = _build_outlier_filtered_market_stats(listings)

        self.assertFalse(result['outlier_detection_applied'])
        self.assertEqual(result['original_sample_size'], 6)
        self.assertEqual(result['clean_sample_size'], 6)
        self.assertEqual(result['excluded_outliers_count'], 0)
        self.assertEqual(result['market_average_before_outlier_filter'], result['market_average_after_outlier_filter'])

    def test_sample_size_at_least_10_flags_and_excludes_extreme_price(self):
        prices = [60000, 62000, 63000, 64000, 65000, 66000, 67000, 68000, 69000, 70000, 132000]
        listings = [self._listing(price, listing_id=index) for index, price in enumerate(prices, start=1)]

        result = _build_outlier_filtered_market_stats(listings)

        self.assertTrue(result['outlier_detection_applied'])
        self.assertEqual(result['original_sample_size'], 11)
        self.assertEqual(result['clean_sample_size'], 10)
        self.assertEqual(result['excluded_outliers_count'], 1)
        self.assertEqual(result['excluded_outliers'][0]['price'], 132000)
        self.assertLess(
            result['market_average_after_outlier_filter'],
            result['market_average_before_outlier_filter'],
        )

    def test_sample_size_at_least_10_with_normal_prices_excludes_nothing(self):
        prices = [60000, 61500, 63000, 64000, 65500, 67000, 68500, 70000, 71500, 73000]
        listings = [self._listing(price, listing_id=index) for index, price in enumerate(prices, start=1)]

        result = _build_outlier_filtered_market_stats(listings)

        self.assertTrue(result['outlier_detection_applied'])
        self.assertEqual(result['clean_sample_size'], 10)
        self.assertEqual(result['excluded_outliers_count'], 0)
        self.assertEqual(result['excluded_outliers'], [])

    def test_high_z_score_with_small_market_deviation_is_not_excluded(self):
        prices = [
            60000, 62000, 63000, 63780, 63780, 63780, 63780, 63780,
            64780, 65000, 69800, 132000,
        ]
        listings = [self._listing(price, listing_id=index) for index, price in enumerate(prices, start=1)]

        result = _build_outlier_filtered_market_stats(listings)

        self.assertTrue(result['outlier_detection_applied'])
        self.assertEqual(result['excluded_outliers_count'], 1)
        self.assertEqual(result['excluded_outliers'][0]['price'], 132000)
        clean_prices = [listing['price'] for listing in listings if listing['price'] != 132000]
        self.assertEqual(result['market_average_after_outlier_filter'], round(sum(clean_prices) / len(clean_prices)))

    def test_duplicate_or_repeated_listings_do_not_break_calculation(self):
        listings = [
            self._listing(60000, listing_id=1, mileage=45000)
            for _ in range(9)
        ]
        listings.append(self._listing(132000, listing_id=99, mileage=47000))

        result = _build_outlier_filtered_market_stats(listings)

        self.assertTrue(result['outlier_detection_applied'])
        self.assertEqual(result['original_sample_size'], 10)
        self.assertEqual(result['clean_sample_size'], 9)
        self.assertEqual(result['excluded_outliers_count'], 1)
        self.assertEqual(result['excluded_outliers'][0]['price'], 132000)

    def test_mad_zero_fallback_does_not_crash_when_all_prices_identical(self):
        listings = [self._listing(60000, listing_id=index) for index in range(1, 11)]

        result = _build_outlier_filtered_market_stats(listings)

        self.assertTrue(result['outlier_detection_applied'])
        self.assertEqual(result['clean_sample_size'], 10)
        self.assertEqual(result['excluded_outliers_count'], 0)
        self.assertEqual(result['standard_deviation_after_outlier_filter'], 0.0)
