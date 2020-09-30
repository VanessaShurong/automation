from position import Position, Stock, Fund, ETF, Cash, Future, Option
from decimal import Decimal
import collections


class Portfolio:
    def __init__(self):
        """
        On creation, the Portfolio object contains no positions and all values are "reset" to the initial
        cash, with no PnL - realised or unrealised.

        Notes:
        1) Right now, cash is being modelled as a feature of the portfolio. This means that  we can update cash values as
            we buy and sell securities automatically. This is more flexible but adds to complexity to the design.
            Initially, we will just read off the cash values from daily trade files and work our way to modelling the
            portfolio cash positions through trade data.


        """
        # self.price_handler = price_handler
        # self.init_cash = cash
        # self.cur_cash = cash
        self.positions = collections.defaultdict(list)
        self.closed_positions = collections.defaultdict(list)
        self.ids = collections.defaultdict(list)
        self._reset_values()
        self.wkn = {}

    def _reset_values(self):
        """

        This is called after every position addition or modification. It allows the  calculations to be carried  out
        "from scratch" in order to minimize errors.

        All cash is reset to the inital_values and  the  PnL is set to be zero.
        :return:
        """
        # self.cur_cash = self.init_cash
        self.equity = Decimal("0.00")
        self.unrealized_pnl = Decimal("0.00")
        self.realized_pnl = Decimal("0.00")

    def _update_portfolio(self):
        """
        Updates the Portfolio total values (cash, equity, unrealized_pnl, realized_pnl, cost_basis etc.) based on all
            of the current ticker values.

            Next: I need to remove Positions from the Portfolio once their quantity reaches 0. Otherwise

        This method is called after every Position modification.
        :return:
        """
        for ticker in self.positions:
            pt = self.positions[ticker]
            if pt.category == "Cash":   # Cash does not have realized/unrealized pnl.
                continue
            self.unrealized_pnl += pt.unrealized_pnl
            self.realized_pnl += pt.realized_pnl
            # self.cur_cash -= pt.cost_basis
            pnl_diff = pt.realized_pnl - pt.unrealized_pnl
            # self.cur_cash += pnl_diff
            self.equity += (
                pt.market_value - pt.cost_basis + pnl_diff
            )

    def _add_position(
            self, action, ticker, quantity, price, category, currency, date, contract_size=1, strike=None, history=None
    ):
        self._reset_values()
        if ticker not in self.positions:
            if category in ["Stock", "Certificate"]:
                position = Stock(
                        action, ticker, quantity, price, category, currency, date
                    )
            elif category == "Fund":
                position = Fund(
                    action, ticker, quantity, price, category, currency, date
                )
            elif category == "ETF":
                position = ETF(
                    action, ticker, quantity, price, category, currency, date
                )
            elif category == "Futures":
                if not history:
                    wkn = self.wkn[ticker]
                else:
                    wkn = None
                position = Future(
                    action, ticker, quantity, price, category, currency, date, contract_size, wkn
                    # self.wkn[ticker] uncomment this line when reading from daily files.
                )
            elif category == "Index Put Option":
                if not history:
                    strike = self.ids[ticker]["G_ID_VALUE"][self.ids[ticker]["C_ID_TYPE"].index(6)].split(" ")[-2][1:]
                else:
                    strike = strike
                position = Option(action, ticker, quantity, price, category, currency, date, contract_size,
                                  strike_price=strike
   # Uncomment this when extracting data from daily files (as opposed to history_movements())
                # strike_price=self.ids[ticker]["G_ID_VALUE"][self.ids[ticker]["C_ID_TYPE"].index(6)].split(" ")[-2][1:]
                                  )
            else:
                position = Position(
                    action, ticker, quantity, price, category, currency, date
                )
            self.positions[ticker] = position
            self._update_portfolio()
        else:
            print(
                """Ticker f{ticker} is already in the positions list. 
                    Could not add a new position.
                """
            )

    def _modify_position(
            self, ticker, quantity, price, date, position, action, history=None
    ):
        """
        This method is called (only) from transact position when `ticker` is already present in self.positions.
            Since the position already exists, we determine the 'action' parameter by checking whether the new position
            size is more positive (then action="BOT") or more negative (then action="SLD").
        :param ticker:
        :param quantity:
        :param price:
        :param date:
        :param position: This is only supplied (True value) if this method is being called from read_positions()
        :param history: Flag (True/False(None)). If true, check if self.category==option.
                If true, divide price by contract_size.
        :return:
        """
        self._reset_values()
        if ticker in self.positions:
            if history:  # We already do this for _calculate_initial_value, need to do for updating transactions too.
                if self.positions[ticker].category=="Index Put Option":
                    price = price/self.positions[ticker].contract_size
            if position:  # Method called from read_positions()
                # No new trades were made. Check if this "if" is necessary
                if quantity == self.positions[ticker].quantity:
                    quantity = Decimal(0.00)
                    action = self.positions[ticker].action  # So that we don't end up dividing up 0 in avg_sld/bot
            else:  # Method called from read_movements()
                quantity = Decimal(quantity)
            self.positions[ticker].transact_shares(
                action=action,
                quantity=quantity,
                price=Decimal(price),
                date=date
            )
            self._update_portfolio()
        else:
            print(
                """
                Ticker f{ticker} is not in the current position list. 
                Could not modify a current position.
                """
            )

    def transact_position(
            self, ticker, quantity, price, date, action=None, category=None, currency=None, position=None,
            contract_size=1, strike=None, history=None
    ):
        """
        Wrapper method for _add_positions and _modify_position
        :param ticker: C_IN_ID of the security.
        :param quantity:  Quantity of units being transacted.
        :param price: Latest Market Value per unit of unit transacted.
        :param date: Date of the transaction.
        :param action: "BOT" for Long transactions and "SLD" for Short transactions.
        :param category: Asset class category of the underlying being transacted.
        :param currency: Currency of the transaction.
        :param position: Flag (True/False). If True, we will just modify current market value and set quantity=0
        :param contract_size: Only used for Futures and Options. Defines the multiple of units the contract is trade in.
        :param strike: Only used for Options. Defines the strike price of an Options contract.
        :param history: Flag (True/False). If True, this method was called from history_movements which reads from files
                    with different formats to the daily file. Some changes include adjusting option price and strike,
                    reading wkn values.
        :return:
        """
        if ticker not in self.positions:
            self._add_position(action=action,
                               ticker=ticker,
                               quantity=quantity,
                               price=price,
                               category=category,
                               currency=currency,
                               date=date,
                               contract_size=contract_size,
                               strike=strike,
                               history=history
                               )
        else:
            self._modify_position(ticker=ticker,
                                  quantity=quantity,
                                  price=price,
                                  date=date,
                                  position=position,
                                  action=action,
                                  history=history)

    def transact_cash(
            self, currency, market_value, cost_basis, date
    ):
        """
        Since Cash does not share the same interface as other Positions (Cash is not a subclass of Position), we would
            need a different method to add Cash positions to the portfolio.
        :param currency: Currency in which the cash is denominated in.
        :param market_value: Total market value of the Cash position.
        :param date: Cash position is as of this date.
        :param cost_basis: Cost of cash position in EUR.
        :return:
        """
        if currency not in self.positions:
            position = Cash(currency, market_value, cost_basis, date)
            self.positions[currency] = position
        else:
            self.positions[currency].update_cash_position(market_value, cost_basis, date)
        # self._update_portfolio() # For now, not calling this function after updating Cash positions because
        # Cash positions do not have unrealized/realized profits.

    def export_logs(self):
        """

        Combines the self.log from every Position in the Portfolio and exports the resulting data as a csv file.
        :return: pd.DataFrame(int, [date, quantity, price, market_value, unit_cost_basis, cost_basis, unrealized_pnl,
                                                    realized_pnl]
        """
        import pandas as pd
        current_positions = [lambda x: pd.DataFrame(x.log) for x in self.positions]
        closed_positions = [lambda y: pd.DataFrame(y.log) for y in self.closed_positions]




