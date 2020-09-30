import pandas as pd
import numpy as np
import collections
from position import Stock
from decimal import Decimal
import datetime

def retrieve_category(c_sof) -> str:
    """
    This method will store a dictionary of C_SOF_TYP codes found in Column T of the daily position file (tab HIS).
        We will use it to assign a category for securities when they are being read by  Reader.read_positions.

    A design decision that was made is that we don't necessarily want to retrieve the Category assigned to the code
        by DZ. Instead, we will assign to each code a category depending on how much level of granularity we are aiming
        for.

    :param c_sof: 3 digit code in C_SOF_TYP column..
    :return: str: The corresponding category.
    """
    codes = {
        100: "Stock",           # Equities in the DZ file
        130: "Certificate",     # Participation Certificate in the DZ file
        174: "Fund",            # Equity Fund in the DZ file.
        175: "Fund",            # Balanced Fund in the  DZ file.
        176: "Fund",            # Other Funds in the DZ file.
        184: "ETF",             # Equity Fund ETF in the DZ file.
        186: "ETF",             # Other Funds ETF in the DZ file.
        161: "ETF",             # Exchange-traded Fund in the DZ file
        431: "Index Put Option",     # Put Options on Indices in the  DZ file.
        620: "Futures",         # Futures on Indices
    }
    if pd.isna(c_sof):  # must be first if statement.
        return "Cash"
    if c_sof not in codes.keys():
        return "Unknown"
    else:
        return codes[c_sof]

#
# mappings = {}
# data = pd.DataFrame({
#     "ticker": [122, 115, 984, 445, 320, 893],
#     "identifier": ["futes1907", "ISIN00001", "futes1912", "option5556", "tsla", "futzvg1907"],
#     "other_col_1": [1, 1, 1, 1, 1, 1],
#     "other_col_2": [2, 2, 2, 2, 2, 2]
# })
# mappings.update(data.loc[:,  ["ticker", "identifier"]].set_index("ticker").T.to_dict("list"))
# print(mappings)
# data = pd.DataFrame({
#     "ticker": [122, 115, 984, 445, 320, 3998],
#     "identifier": ["futes1907", "ISIN00001", "futes1912", "option5556", "tsla", "Bonds"]
# })
# mappings.update(data.set_index("ticker").T.to_dict("list"))
# print(mappings)
#

# desc = "Put on Euro Stoxx 50 Price Index Juni 2020/3.000,00"
# strike = desc.split("/")[1].replace(".","").replace(",",".")
# print(float(strike))
