from position import Position, Stock
from portfolio import Portfolio
from decimal import Decimal
import datetime
import pandas as pd
from SecurityID import retrieve_category
from analysis import Analysis as ana
from tqdm import tqdm
import numpy as np
import pickle
import os

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

class Reader:
    """
    This class is used to read data files to update the portfolio information.

    """

    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.trades = {}

    def history_movements(self, path, end_date):
        """
        Since we have daily files for Zobel going back to only 12/March/2019, we need to obtain the
        earlier transactions from a different file that was sent to us by DZ Bank upon request from Marc.
        This file contains transactions that occured from 30/December/2016 all the way up to 19/December/2019
        However, my intention is to only read those transactions up to a certain date, say 12/03/2019, and then
        use the daily files from there onwards.

        Changes made to the Original Transactions File:
        1) The excel file must be sorted by D_NAV (newest to oldest) and by N_NEXT (largest to smallset). This
        helps us achieve a serial reading of the transactions log.
        2)  Two futures  contracts had their L_Detail columns changed so we can read their price.
        3) Considering removing the  block of trades for NTAsian funds since each trade cancels the one before it.
        4) Considering whether negative quantity trades should be replaced with positive quantity.

        I reckon I'll have to another history_positions method to do the same but for position data.
        :param path:  path to the transactions file.
        :param end_date: Only trades happening before end_date will be processed by this  method. %m/%d/%Y
        :return: None
        """
        end_date = datetime.datetime.strptime(end_date, "%m/%d/%Y")
        data = pd.read_excel(os.path.join(path, "Copy of Transactions.xls"), sheet_name="Movements", skiprows=3)
        data = data.loc[~data["D_NAV"].isna()]
        data["D_NAV"] = pd.to_datetime(data["D_NAV"])
        data = data.loc[~(data["D_NAV"] >= end_date)]
        # data.sort_values(by="D_NAV", inplace=True)
        data = data.assign(
            Currency=pd.Series(["EUR" if all((data.iloc[i, 22] == data.iloc[i, 23], data.iloc[i, 28] == data.iloc[i, 29])) else "USD" for i in range(len(data.index))]).values)
        for row in data[::-1].itertuples():  # read in reverse order.
            quantity = row.Q_QTY
            category = retrieve_category(row.GTI)
            if category == "Futures":
                price = float(row.L_DEAL.split(" ")[2].replace(",", "."))
            else:
                price = row.P_PRICE
            if category == "Futures":
                contract_size = row.P_PRICE/price
            elif category == "Index Put Option":
                contract_size = row.G_CONTRACT
            else:
                contract_size = 1
            if category == "Index Put Option":
                strike_price = float(row.L_NAME.split("/")[1].replace(".", "").replace(",", "."))
            else:
                strike_price = None
            self.portfolio.transact_position(
                ticker=row.C_N_ID,
                quantity=Decimal(quantity),
                price=Decimal(price),
                date=row.D_NAV,
                category=retrieve_category(row.GTI),
                currency=row.Currency,
                action="BOT" if row.C_ACC_WAY == "CR" else "SLD",
                contract_size=Decimal(contract_size),
                strike=strike_price,
                history=True
            )

    def main(self, path, start_date, end_date):
        """
        This method will read the Excel file, then spawn multiple processes so that each file is processed very quickly.
        :param path: The path to the daily file.
        :param start_date: The start day for reading the files.
        :param end_date: The end day for reading the files
        :return:
        """
        start = datetime.datetime.strptime(start_date, "%m%d%Y")
        end = datetime.datetime.strptime(end_date, "%m%d%Y")

        def is_weekday(date):
            """
            Checks if date is a weekday or not. Returns True if date is a weekday, False otherwise.
            :param date:
            :return: bool
            """
            if date.weekday() < 5:
                return True
            else:
                return False

        not_available = []
        k = abs((start-end).days)
        print(f"The value  of k is: {k}")
        for i in tqdm(range(k)):
            file_date = start
            if is_weekday(file_date):
                pass
            else:
                start = start + datetime.timedelta(days=1)
                continue
            day = file_date.day
            month = file_date.month
            year = str(file_date.year)
            # Month and Day need to be in two digit format. i.e. dd/mm
            if month < 10:
                month = "0"+str(month)
            else:
                month = str(month)
            if day < 10:
                day = "0"+str(day)
            else:
                day = str(day)
            folder = os.path.join(path, f"{month}{year}")
            file = os.path.join(folder, f"Zobel {month}{day}{year}.xls")
            try:
                data = pd.read_excel(file, sheet_name=["HIS", "MVT", "SecuritiesIDs"])
                print(f"Now processing the file with path: {file}")
            except FileNotFoundError:
                print(f"1st Level FileNotFoundError {file}")
                try:
                    data = pd.read_excel(os.path.join(folder, f"Zobel {month}{day}{year}.xlsx"), sheet_name=["HIS", "MVT", "SecuritiesIDs"])
                except FileNotFoundError:
                    not_available.append(datetime.datetime.strftime(file_date, format="%m%d%Y"))
                    start = start + datetime.timedelta(days=1)
                    continue
            pos, mov, s_ids = data.values()
            self.read_ids(s_ids)
            self.read_movements(mov)
            self.read_positions(pos)
            start = start + datetime.timedelta(days=1)
            break

    def read_ids(self, file):
        """
        This method will read the "SecuritiesIDs" tab of the daily file and process the ID's. We will use the ID's to
            1) derive the underlying instrument for futures/options.
            2) Connect to bloomberg in the future to obtain more granular data
        :param path:
        :return:
        """
        # data = pd.read_excel(path, sheet_name="SecuritiesIDs").loc[:,["C_N_ID", "C_ID_TYPE", "G_ID_VALUE"]]
        data = file.loc[:, ["C_N_ID", "C_ID_TYPE", "G_ID_VALUE"]]
        self.portfolio.ids.update(data.groupby(["C_N_ID"]).agg(lambda x: list(x)).T.to_dict())
        # {C_N_ID: {"C_ID_TYPE": [List], "G_ID_VALUE":[List] }}

    def read_positions(self, pos):
        """
        This method reads the position tab "HIS" of the daily file to get the latest market quotes on existing positions


        :param pos: The daily position file.
        :return:
        """
        data = pos
        data = data.loc[~data["C_N_ID"].isna()].merge(data.loc[~(data["A_ACCRUED_INTEREST"] == 0) & (data["A_ACCRUED_INTEREST"].isna())])
        self.portfolio.wkn.update(data.loc[:, ["C_N_ID", "G_SORTING_KEY"]].set_index("C_N_ID").T.to_dict("list"))
        data["D_NAV"] = pd.to_datetime(data["D_NAV"])
        if self.trades.__len__() != 0:
            for _, trade in self.trades.items():
                self.portfolio.transact_position(
                    ticker=trade["ticker"],
                    quantity=Decimal(trade["quantity"]),
                    price=Decimal(data.loc[data["C_N_ID"] == trade["ticker"]]["P_COST_PRICE"].iloc[0]),
                    date=trade["date"],
                    category=retrieve_category(data.loc[data["C_N_ID"] == trade["ticker"]]["C_SOF_TYP"].iloc[0]),
                    currency=data.loc[data["C_N_ID"] == trade["ticker"]]["C_INVEST_CCY"],
                    action="BOT" if trade["action"] == "CR" else "SLD",
                    contract_size=Decimal(data.loc[data["C_N_ID"] == trade["ticker"]]["G_CONTRACT_SIZE"].iloc[0])
                )
            self.trades.clear()
        for row in data.itertuples():
            category = retrieve_category(row.C_SOF_TYP)
            date = row.D_NAV
            currency = row.C_INVEST_CCY
            if category == "Cash":
                market_value = row.A_MARKET_VALUE
                cost_basis = row.A_COST_VALUE_PTF
                self.portfolio.transact_cash(currency, market_value, cost_basis, date)
                continue
            self.portfolio.transact_position(ticker=row.C_N_ID,
                                             quantity=Decimal(row.Q_QTY),
                                             price=Decimal(row.P_VAL_PRICE),
                                             date=date,
                                             category=category,
                                             currency=currency,
                                             position=True)

    def read_movements(self, mov):
        """
        This  method  reads the Movements tab "MOV" of the daily file  to get the latest market quotes on existing
            positions. Since the Movement tab lacks some needed information such as currency, category, it will not
                directly call self.portfolio.transact_position() for buy orders. Rather it will just pass on information
                of that buy order and store it, the recording of the transaction can be done when we are processing other
                tabs and have access to the information missing from the  movement tab. (we call this in read_position)
        :param mov: The daily movement file.
        :return:
        """
        mov = mov.loc[~mov["C_N_ID"].isna()]
        if len(mov.index) == 0:  # No movements.
            return False
        data = mov
        data["D_TRADE"] = pd.to_datetime(data["D_TRADE"])
        for row in data.itertuples():
            if row.C_N_ID in self.portfolio.positions.keys():
                self.portfolio.transact_position(ticker=row.C_N_ID,
                                                 quantity=row.Q_QTY,
                                                 price=row.P_PRICE,
                                                 date=row.D_TRADE,
                                                 action="BOT" if row.C_ACC_WAY == "CR" else "SLD")
            else:
                self.trades[self.trades.__len__() + 1] = \
                    {"price": row.P_PRICE, "quantity": row.Q_QTY, "ticker": row.C_N_ID,
                        "date": row.D_TRADE, "action": row.C_ACC_WAY}


zobel = Portfolio()
read = Reader(zobel)
read.history_movements(r"/Users/vanessa/Desktop/Sigma/03.10.2020", "04/01/2017")
#analyzer = ana(zobel, title=["A","B"])
#analyzer.get_results()

##print(position.log)
for ticker, position in zobel.positions.items():
    print(f"Ticker: {ticker}\t {position.currency} \t {position}\t {position.log}")
#    #print(f"Ticker: {ticker}\t {analyzer.get_results()}")
#    print(pd.DataFrame(position.log, index=position.log["date"]))
    print("-"*100)
   # print(f"Ticker: {ticker}\t {position.currency} {position}\t {position.log}")
    
    
 
    #analyzer = ana(data, title=["A","B"])
    #analyzer.plot_results()
# read.main(path=r"C:\Users\Presentation\Desktop\CleaningData\Cash Data", start_date="03122019", end_date="01012020")
# zobel.transact_position(
#     ticker=168796,
#     quantity=Decimal(156507),
#     price=Decimal(20),
#     date=datetime.datetime.strptime("2019/09/11", "%Y/%m/%d"),
#     action="CR",
#     category="Fund",
#     currency="EUR",
# )
# zobel.transact_position(
#     ticker=4743,
#     quantity=Decimal(335000),
#     price=Decimal(5.45),
#     date=datetime.datetime.strptime("2018/08/01", "%Y/%m/%d"),
#     action="CR",
#     category="Stock",
#     currency="USD"
# )
# reader = Reader(zobel)
# reader.read_ids("toy_transactions.xlsx")
# reader.read_movements("toy_transactions.xlsx")
# reader.read_positions("toy_transactions.xlsx")
# print(zobel.positions)
# print(zobel.positions[102660].log)
# for ticker, position in zobel.positions.items():
#     print(f"Ticker {ticker}: ", position.log)
#     print(zobel.realized_pnl)
# s_id = pd.read_excel("toy_transactions.xlsx", sheet_name="SecuritiesIDs").loc[:, ["C_N_ID", "C_ID_TYPE", "G_ID_VALUE"]]
# # zobel.ids.update(s_id.set_index("C_N_ID").T.to_dict("list"))
# print(s_id.groupby(["C_N_ID"]).agg(lambda x: list(x)).T.to_dict())
# zobel.ids.update(s_id.groupby(["C_N_ID"]).agg(lambda x: list(x)).T.to_dict())
# print(zobel.ids)
# print(zobel.ids[73904]["G_ID_VALUE"][zobel.ids[73904]["C_ID_TYPE"].index(6)])

# All of the above worked for securities in the toy_transactions.xlsx  as of 29/02/2020 (LEAP DAY WOHOO!)

# Next I need to decide whether I should just read straight from the Position file ("HIS") or use the ("MVT") tab.
# As of 02/02/2020, the only real need to using the MVT tab would be to read closed positions. Whenever we add to an
# existing position, I can use the Position file given that the quantity will change but I would need to think about it.
# It would be a waste if I have to read the movement tab for every file I read, need to decide if it is possible to
# only read the movement tab if a position is closed or a position is added to.