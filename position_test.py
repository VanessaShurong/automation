from position import Position, Stock

from decimal import Decimal
import unittest


class TestRoundTripXOMPosition(unittest.TestCase):
    """
    Test a round-trip trade in Exxon-Mobil where the initial
    trade is a buy/long of 100 shares of XOM, at a price of
    $74.78, with $1.00 commission.
    """

    def setUp(self):
        """
        Set up the Position object that will store the PnL.
        """
        self.position = Stock(
            "BOT", "XOM", Decimal('100'),
            Decimal("74.78"), "Stock",
            "USD"
        )

    def test_calculate_round_trip(self):
        """
        After the subsequent purchase, carry out two more buys/longs
        and then close the position out with two additional sells/shorts.

        The following prices have been tested against those calculated
        via Interactive Brokers' Trader Workstation (TWS).
        """
        self.position.transact_shares(
            "BOT", Decimal('200'), Decimal('74.63')
        )
        self.position.transact_shares(
            "BOT", Decimal('250'), Decimal('74.620')
        )
        self.position.transact_shares(
            "SLD", Decimal('200'), Decimal('74.58')
        )
        self.position.transact_shares(
            "SLD", Decimal('250'), Decimal('75.26')
        )
        self.position.update_market_value(Decimal("77.75"))

        self.assertEqual(self.position.action, "BOT")
        self.assertEqual(self.position.ticker, "XOM")
        self.assertEqual(self.position.quantity, Decimal("0"))

        self.assertEqual(self.position.buys, Decimal("450"))
        self.assertEqual(self.position.sells, Decimal("450"))
        self.assertEqual(self.position.net, Decimal("0"))
        self.assertEqual(self.position.total_bot, Decimal("33596.00"))
        self.assertEqual(self.position.total_sld, Decimal("33731.00"))
        self.assertEqual(self.position.net_total, Decimal("135.00"))

        self.assertEqual(self.position.avg_price, Decimal("74.65778"))
        self.assertEqual(self.position.cost_basis, Decimal("0.00"))
        self.assertEqual(self.position.market_value, Decimal("7775"))
        self.assertEqual(self.position.unrealized_pnl, Decimal("309.73"))
        self.assertEqual(self.position.realized_pnl, Decimal("135.00"))


# class TestRoundTripPGPosition(unittest.TestCase):
#     """
#     Test a round-trip trade in Proctor & Gamble where the initial
#     trade is a sell/short of 100 shares of PG, at a price of
#     $77.69, with $1.00 commission.
#     """
#
#     def setUp(self):
#         self.position = Stock(
#             "SLD", "PG", Decimal('100'),
#             Decimal("77.69"), "Hedge Fund", "EUR"
#         )

    # def test_calculate_round_trip(self):
    #     """
    #     After the subsequent sale, carry out two more sells/shorts
    #     and then close the position out with two additional buys/longs.
    #
    #     The following prices have been tested against those calculated
    #     via Interactive Brokers' Trader Workstation (TWS).
    #     """
    #     self.position.transact_shares(
    #         "SLD", Decimal('100'), Decimal('77.68')
    #     )
    #     self.position.transact_shares(
    #         "SLD", Decimal('50'), Decimal('77.70')
    #     )
    #     self.position.transact_shares(
    #         "BOT", Decimal('100'), Decimal('77.77')
    #     )
    #     self.position.transact_shares(
    #         "BOT", Decimal('150'), Decimal('77.73')
    #     )
    #     self.position.update_market_value(Decimal("77.72"))
    #
    #     self.assertEqual(self.position.action, "SLD")
    #     self.assertEqual(self.position.ticker, "PG")
    #     self.assertEqual(self.position.quantity, Decimal("0"))
    #
    #     self.assertEqual(self.position.buys, Decimal("250"))
    #     self.assertEqual(self.position.sells, Decimal("250"))
    #     self.assertEqual(self.position.net, Decimal("0"))
    #     self.assertEqual(self.position.avg_bot, Decimal("77.746"))
    #     self.assertEqual(self.position.avg_sld, Decimal("77.688"))
    #     self.assertEqual(self.position.total_bot, Decimal("19436.50"))
    #     self.assertEqual(self.position.total_sld, Decimal("19422.00"))
    #     self.assertEqual(self.position.net_total, Decimal("-14.50"))
    #
    #
    #     self.assertEqual(self.position.avg_price, Decimal("77.68800"))
    #     self.assertEqual(self.position.cost_basis, Decimal("0.00"))
    #     self.assertEqual(self.position.market_value, Decimal("0.00"))
    #     self.assertEqual(self.position.unrealized_pnl, Decimal("0.00"))
    #     self.assertEqual(self.position.realized_pnl, Decimal("-14.50"))


if __name__ == "__main__":
    unittest.main()