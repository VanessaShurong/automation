from decimal import Decimal
import  datetime
import numpy as np
import collections

TWOPLACES = Decimal("0.01")
SEVENPLACES = Decimal("0.0000001")


class Position:
    def __init__(
            self, action, ticker, init_quantity,
            init_price, category, currency, entry_date=datetime.datetime.today(), contract_size=1):
        """
        Set up the initial "account" of the Position to be
        zero for most items, with the exception of the initial
        purchase/sale.

        Then calculate the initial values and finally update the
        market value of the transaction.
        
        :param action: "BOT" OR "SLD" representing a buy or a sell. (str)
        :param ticker: Unique Security Identifier such as ISIN. (str)
        :param init_quantity: The initial number of units taken position in. (Decimal object)
        :param init_price: The initial average price.(Decimal object)
        :param category: Asset Class.
        :param currency: main currency of the security.
        :param entry_date: Date position was first created.

        :return: 
        """
        self.action = action
        self.ticker = ticker
        self.quantity = init_quantity
        self.contract_size = contract_size
        self.init_price = init_price

        self.currency = currency
        self.category = category
        self.entry_date = entry_date

        # The decision of whether to initialize the attributes below in the initializer
        #   or in self._calculate_initial_value() depends on whether I want to reset those attributes for those positions
        #   that are flipped. (i.e. when self._calculate_initial_value is called from somewhere else.)

        # self.buys = Decimal("0")
        # self.sells = Decimal("0")
        # self.avg_bot = Decimal("0.00")
        # self.avg_sld = Decimal("0.00")
        # self.total_bot = Decimal("0.00")
        # self.total_sld = Decimal("0.00")

        self.log = collections.defaultdict(list)
        # Decided to put self.update_market_value and self._log_trade inside self._calculate_initial_value
        # Reason being is that the only time _calculate_initial_value is called is when position is created, or
        # when you flip long/short and you create a new position. In both cases, I would like to log the opening
        # trade as "Inception".
        self._calculate_initial_value(contract_size=contract_size)
        self.update_market_value(init_price)
        self._log_trade(entry_date, init_price, "Inception")

    def _calculate_initial_value(self, quantity=None, price=None, date=None, record=None, contract_size=1):
        """
        Depending upon whether the action was a buy or sell ("BOT"
        or "SLD") calculate the average bought cost, the total bought
        cost, the average price and the cost basis.

        Usually called when the position is first entered into. Optional arguments quantity and price
            can be used to call this function from somewhere else. An example is when we are long a security, and then
            a short order comes in that is enough to close the long position and create a short position. In this case,
            the design decision was to allow for modifying the position by just switching it to Short.

        All params are optional and indeed as of 28/01/2020, the only use for them is when this function is called
        from inside self.transact_shares to flip a long/short position short/long.

        :return: None
        """
        raise NotImplementedError

    def update_market_value(self, price):
        """
        Method which will be used to update the market values of securities once when the position is first created,
            and then everytime new position data arrives.
        :param price:
        :return:
        """
        raise NotImplementedError

    def update_realized_pnl(self):
        """ Called after every transaction. Uses quantities computed by transact_shares such as avg_sld, avg_bot
            to calculate the realized PnL on a given position.
        """
        raise NotImplementedError

    def _log_trade(self, date, price, event):
        """
        Save the trade details over the livespan of the position so it could be recorded and analyzed later.
            This should generate data for a report that could be exported and stored somewhere else.
            Example:
                - How long did we have the position?
                - How much money did we make from this?
                - Daily prices in main currency.
                - Drawdown (if possible; can be done using daily prices)


        :param date: string/datetime denoting the trade date
        :param price: latest market quote (per unit)
        :param event: What event is being logged? three choices initially: "Inception", "Trade", "Close".
        :return: Dict["attribute": [data]]
        """
        # self.log[len(self.log.keys()) + 1] = [
        #     dat for dat in [date, (self.quantity).quantize(TWOPLACES),
        #                     (price).quantize(FIVEPLACES),
        #                     (self.market_value).quantize(TWOPLACES),
        # (self.cost_basis).quantize(TWOPLACES) if self.net == 0  else (self.cost_basis / self.net).quantize(FIVEPLACES),
        # (self.cost_basis).quantize(TWOPLACES), (self.unrealized_pnl).quantize(TWOPLACES),
        #                     (self.realized_pnl).quantize(TWOPLACES), event]
        # ]
        #
        self.log["date"].append(date)
        self.log["quantity"].append(self.quantity.quantize(TWOPLACES))
        self.log["price"].append(price.quantize(SEVENPLACES))
        self.log["market_value"].append(self.market_value.quantize(TWOPLACES))
        self.log["unit_cost"].append(
            self.cost_basis.quantize(TWOPLACES) if self.net == 0 else (self.cost_basis / (self.net * self.contract_size)).quantize(SEVENPLACES)
        )
        self.log["cost_basis"].append(self.cost_basis.quantize(TWOPLACES))
        self.log["unrealized_pnl"].append(self.unrealized_pnl.quantize(TWOPLACES))
        self.log["realized_pnl"].append(self.realized_pnl.quantize(TWOPLACES))
        self.log["event"].append(event)

    def transact_shares(self, action, quantity, price, date, contract_size=1):
        """
        Calculates the adjustments to the Position that occur once new shares are bought and sold.

        Takes care to update the average bought/sold, total bought/sold, the cost basis and PnL calculations.

        An assumption we make is that we update the self.market_value attribute everytime we transact a share. The logic
            is that the trade price represents the most current market value estimate at the time of transaction i.e.
            (at the time of calling of this  function).
        Another assumption is that contract_size does not change. For ex: when trading new units of existing Futures
            or Options contracts, we assume contract_size is unchanged.

        This method saves transactions to the log file and labels them as "Trades".

        Known Bugs:
        1) If you are long a position and you enter a SLD trade with (0) quantity, then this method
                throws an error because  avg_sld = (xxx)/(self.sells + self.quantity) is division by 0.
                Vice versa if you are short a position and enter into a (0) quantity BOT trade.


        :param action: "BOT" or "SLD" (str)
        :param quantity: Additional quantity bought or sold.
        :param price: The average price at which quantity was transacted.
        :param date: The date of the transaction.
        :param contract_size: Non-zero only for Futures & Options.
        :return: None
        """
        flip = False
        if action == "BOT":
            if action != self.action and quantity > abs(self.net):
                flip = True
                remainder = quantity - abs(self.net)
                quantity = abs(self.net)
            self.avg_bot = (
                (self.avg_bot*self.buys + price*quantity)/(self.buys + quantity)
            ).quantize(SEVENPLACES)
            if self.action != "SLD":  # If already long, then buying more should change the average price.
                self.avg_price = (
                    (
                        self.avg_price*self.buys + price*quantity
                    ) / (self.buys + quantity)
                ).quantize(SEVENPLACES)
            self.buys += quantity
            self.total_bot = (self.buys * self.avg_bot).quantize(TWOPLACES)
        else:
            if action != self.action and quantity > abs(self.net):
                flip = True
                remainder = quantity - abs(self.net)
                quantity = self.net
            self.avg_sld = (
                (self.avg_sld*self.sells + price*quantity)/(self.sells + quantity)
            ).quantize(SEVENPLACES)
            if self.action != "BOT":
                self.avg_price = (
                    (
                        self.avg_price*self.sells + price*quantity
                    ) / (self.sells + quantity)
                ).quantize(SEVENPLACES)
            self.sells += quantity
            self.total_sld = (self.sells * self.avg_sld).quantize(TWOPLACES)

        self.net = self.buys - self.sells
        self.quantity = self.net
        self.net_total = (self.total_sld - self.total_bot).quantize(TWOPLACES)
        self.cost_basis = (
            self.quantity * self.contract_size * self.avg_price
        ).quantize(TWOPLACES)

        self.update_realized_pnl()
        self.update_market_value(price)
        if self.market_value == 0 and self.unrealized_pnl == 0:  # We exited the position.
            self._log_trade(date, price,  "Close")
        elif quantity == 0:  # No trades occurred.
            self._log_trade(date, price, "Market_Update")
        else:  # Quantity held has changed. Indicates a trade.
            self._log_trade(date, price, "Trade")
        if flip:  # Position flipped (longs-> short and vice versa).
            self.action = action
            self._calculate_initial_value(
                quantity=remainder, price=price, date=date, contract_size=contract_size, record=True
            )


class Stock(Position):
    def __init__(
            self, action, ticker, init_quantity,
            init_price, category, currency, entry_date, contract_size=1):
        """

        :param action:
        :param ticker:
        :param init_quantity:
        :param init_price:
        :param category: Asset class of the position.
        :param currency: The currency in which we will receive price information for this security.
        """
        super().__init__(action, ticker, init_quantity,
                         init_price, category, currency, entry_date, contract_size)

    def _calculate_initial_value(self, quantity=None, price=None, date=None, record=None, contract_size=1):
        """
        Calculating Initial Value for Stocks.

        :param quantity: can be supplied if this function is called sometime other than when the position is first
                created. For example, when longs switch short and vise versa.
        :param price: can be supplied if this function is called sometime other than when the position is first
                created. For example, when longs switch short and vise versa.
        :param record: bool indicator; only changed to True if you want to update_market_value and log trade. You
                        would need to do this if you call this method after flipping of position.
        :return: None
        """

        if quantity is not None:
            self.quantity = quantity
        if price is not None:
            self.init_price = price

        self.realized_pnl = Decimal("0.00")
        self.unrealized_pnl = Decimal("0.00")

        self.buys = Decimal("0")
        self.sells = Decimal("0")
        self.avg_bot = Decimal("0.00")
        self.avg_sld = Decimal("0.00")
        self.total_bot = Decimal("0.00")
        self.total_sld = Decimal("0.00")

        contract_size = Decimal(contract_size)

        if self.action == "BOT":
            self.buys = self.quantity
            self.avg_bot = self.init_price.quantize(SEVENPLACES)
            self.total_bot = (self.buys * contract_size * self.init_price).quantize(TWOPLACES)
            self.avg_price = (
                (self.init_price * self.quantity) / self.quantity
            ).quantize(SEVENPLACES)
            self.cost_basis = (
                self.quantity * contract_size * self.avg_price
            ).quantize(TWOPLACES)
        else:
            self.sells = self.quantity
            self.avg_sld = self.init_price.quantize(SEVENPLACES)
            self.total_sld = (self.sells * contract_size * self.init_price).quantize(TWOPLACES)
            self.avg_price = (
                (self.init_price * self.quantity) / self.quantity
            ).quantize(SEVENPLACES)
            self.cost_basis = (
                -(self.quantity * contract_size) * self.avg_price
            ).quantize(TWOPLACES)

        self.net = self.buys - self.sells  # non-negative for long positions, non-positive for short positions.
        self.quantity = self.net
        self.net_total = (self.total_sld - self.total_bot).quantize(TWOPLACES)
        if record:  # This function was called not __init__ but from somewhere else. (self.transact_shares for example)
            self.update_market_value(price)
            self._log_trade(date, price, "Inception")

    def update_market_value(self, price):
        """
        Update the market value when we receive the latest market value per share/unit.
        :param price: Latest market value per unit quote. Goes into Market Value per unit.
        :return: None
        """
        self.market_value = (self.quantity * price).quantize(TWOPLACES)
        if self.action == "BOT":
            self.unrealized_pnl = (self.market_value - self.cost_basis).quantize(TWOPLACES)
        else:
            self.unrealized_pnl = (abs(self.cost_basis) - abs(self.market_value)).quantize(TWOPLACES)

    def update_realized_pnl(self):
        """
        Called after every transaction. Uses quantities computed by transact_shares such as avg_sld, avg_bot
            to calculate the realized PnL on a given position.
        :return: None
        """
        if self.action == "BOT":
            self.realized_pnl = ((self.avg_sld - self.avg_bot) * self.sells * self.contract_size).quantize(TWOPLACES)
        else:
            self.realized_pnl = ((self.avg_sld - self.avg_bot) * self.buys * self.contract_size).quantize(TWOPLACES)


class Fund(Stock):
    def __init__(
            self, action, ticker, init_quantity, init_price, category, currency, entry_date
    ):
        """

        :param action:
        :param ticker:
        :param init_quantity:
        :param init_price:
        :param category:
        :param currency:
        :param entry_date:
        """

        super().__init__(action, ticker, init_quantity, init_price, category, currency, entry_date)


class ETF(Stock):
    def __init__(
            self, action, ticker, init_quantity, init_price, category, currency, entry_date
    ):
        """

        :param action:
        :param ticker:
        :param init_quantity:
        :param init_price:
        :param category:
        :param currency:
        :param entry_date:
        """
        super().__init__(action,  ticker, init_quantity, init_price, category, currency, entry_date)


class Future(Stock):
    def __init__(
            self, action, ticker, init_quantity, init_price, category, currency, entry_date, contract_size, wkn=None
    ):
        self.contract_size = contract_size
        super().__init__(action, ticker, init_quantity, init_price, category, currency, entry_date,
                         contract_size=contract_size)
        # self.underlying = self.get_underlying(wkn)
        self.exposure = self.quantity * self.contract_size * init_price

    def update_market_value(self, price):
        """
        Update the market value when we receive the latest market value per share/unit.
        :param price: Latest market value per unit quote. Goes into Market Value per unit.
        :return: None
        """
        self.exposure = (self.quantity * self.contract_size * price).quantize(TWOPLACES)
        if self.action == "BOT":
            self.unrealized_pnl = (self.exposure - self.cost_basis).quantize(TWOPLACES)
        else:
            self.unrealized_pnl = (abs(self.cost_basis) - abs(self.exposure)).quantize(TWOPLACES)

        self.market_value = self.unrealized_pnl


class Option(Stock):
    def __init__(
            self, action, ticker, init_quantity, init_price, category, currency, entry_date, contract_size, strike_price
    ):
        self.contract_size = contract_size
        super().__init__(action, ticker, init_quantity, init_price / contract_size, category, currency, entry_date,
                         contract_size=contract_size)
        # self.exposure = We need the price of an underlying to determine the delta hedged exposure
        self.strike = Decimal(strike_price)  #  need to get strike_price from portfolio._add_position()

    def update_market_value(self, price):
        """
        Update the market value when we receive the latest market value per share/unit.
        :param price: Latest market value per unit quote. Goes into Market Value per unit.
        :return: None
        """
        self.market_value = self.quantity * self.contract_size * price
        if self.action == "BOT":
            self.unrealized_pnl = ((self.quantity * self.contract_size * price) - self.cost_basis).quantize(TWOPLACES)
        else:
            self.unrealized_pnl = (self.cost_basis - (self.quantity * self.contract_size * price)).quantize(TWOPLACES)



class Cash:
    def __init__(self, currency, market_value, cost_basis, date):
        """
        Class to represent cash positions in the portfolio.
        :param currency: The currency in which the cash is denominated.
        :param market_value: The total market value of the cash position.
        :param date: The Cash position is as of this date.
        :param cost_basis: Cost-weighted average of Cash position in EUR. For EUR positions, it is equal to market_value
        """
        self.currency = currency
        self.market_value = Decimal(market_value)
        self.cost_basis = Decimal(cost_basis)
        self.log = collections.defaultdict(list)
        self._log_trade(date)
        self.category = "Cash"

    def update_cash_position(
            self, market_value, cost_basis, date
    ):
        """
        This method is used to update existing Cash balances.
        :param market_value: The new market value of the Cash position
        :param date: The new market value is as of this date.
        :param cost_basis: Cost-weighted average of Cash position in EUR. For EUR positions, it is equal to market_value
        :return:
        """
        self.market_value = Decimal(market_value)
        self.cost_basis = Decimal(cost_basis)
        self._log_trade(date)

    def _log_trade(self, date):
        """
        This method should be called every time a new Cash reading is obtained. There is a need  for Cash logs
        to be similar to other position logs to facilitate data analysis.

        Next: I have unrealized profit being logged as np.nan, maybe I can convert the market_value to EUR and then
                I will be able to calculate an unrealized profit in EUR using cost_basis and market_value.
        :param date: The date of the market_value update.
        :return:
        """
        self.log["date"].append(date)
        self.log["quantity"].append(np.nan)
        self.log["price"].append(np.nan)
        self.log["market_value"].append(self.market_value.quantize(TWOPLACES))
        self.log["unit_cost"].append(np.nan)
        self.log["cost_basis"].append(self.cost_basis.quantize(TWOPLACES))
        self.log["unrealized_pnl"].append(np.nan)
        self.log["realized_pnl"].append(np.nan)
        self.log["currrency"].append(self.currency)
        self.log["event"].append("Update")
        # self.log[len(self.log.keys()) + 1] = [
        #     dat for dat in [date, np.nan, np.nan, self.market_value.quantize(TWOPLACES),
        #                     np.nan, self.cost_basis.quantize(TWOPLACES), np.nan, np.nan, self.currency]
        # ]


    # Next, I need to implement a log_trade method for Cash.
    # Next, I need to implement the Futures/Options positions and decide whether they inherit the interface from
    #       Position.


# tsla = Stock("BOT", "TSLA", Decimal(100), Decimal(74.78), 'USD', 'Stock', datetime.datetime.strptime("2019/09/10", "%Y/%m/%d"))
# tsla.transact_shares("BOT", Decimal(200), Decimal(74.63), datetime.datetime.strptime("2019/09/11", "%Y/%m/%d"))
# tsla.transact_shares("BOT", Decimal(250), Decimal(74.62), datetime.datetime.strptime("2019/09/17", "%Y/%m/%d"))
#
# tsla.transact_shares("SLD", Decimal(200), Decimal(75.26), datetime.datetime.strptime("2019/10/07", "%Y/%m/%d"))
# tsla.transact_shares('SLD', Decimal(250), Decimal(77.75), datetime.datetime.strptime("2019/10/29", "%Y/%m/%d"))
# tsla.transact_shares('SLD', Decimal(200), Decimal(77.75), datetime.datetime.strptime("2019/10/30", "%Y/%m/%d"))
# print(tsla.unrealized_pnl) # CORRECT
# print(tsla.realized_pnl) #CORRECT. Works for round trip.
# print(tsla.quantity) # CORRECT, works for flipped positions.
# print(tsla.avg_price) # CORRECT, works for flipped positions
# for key in tsla.log.keys():
#     print(tsla.log[key]) # Worked perfectly for the round trip and the long->short flip.
# tsla = Stock("SLD", "TSLA", Decimal(100), Decimal(74.78), 'USD', 'Stock', datetime.datetime.strptime("2019/09/10", "%Y/%m/%d"))
# tsla.transact_shares("SLD", Decimal(200), Decimal(74.63), datetime.datetime.strptime("2019/09/11", "%Y/%m/%d"))
# tsla.transact_shares("SLD", Decimal(250), Decimal(74.62), datetime.datetime.strptime("2019/10/07", "%Y/%m/%d"))
# #
# tsla.transact_shares("BOT", Decimal(200), Decimal(75.26), datetime.datetime.strptime("2019/10/29", "%Y/%m/%d"))
# tsla.transact_shares('BOT', Decimal(250), Decimal(77.75), datetime.datetime.strptime("2019/10/30", "%Y/%m/%d"))
# tsla.transact_shares('BOT', Decimal(1100), Decimal(60.75), datetime.datetime.strptime("2019/10/30", "%Y/%m/%d"))
# tsla.transact_shares('BOT', Decimal(0), Decimal(64.75), datetime.datetime.strptime("2019/12/30", "%Y/%m/%d"))



# print(tsla.unrealized_pnl) # CORRECT
# print(tsla.realized_pnl) #CORRECT

# for key in tsla.log.keys():
#     print(tsla.log[key]) # Worked perfectly for the long round trip and the long->short flip.
                        # Worked perfectly for  the short round trip and the short->long flip
