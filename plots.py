#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 21:33:50 2020

@author: vanessa
"""

from analysis import Analysis as ana
from reader import Reader
from portfolio import Portfolio
import pandas as pd

import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default = 'browser'

zobel = Portfolio()
read = Reader(zobel)
read.history_movements(r"/Users/vanessa/Desktop/Sigma/03.10.2020", "04/01/2017")
analyzer = ana(zobel,title='s') 

for ticker in analyzer.constituents.keys():
    """ Plot for the general plots, i.e. directly call the function from 
        ananlysis class. The next one I need to do is: form a automation 
        report more like the daily report.
    """
    print(pd.DataFrame(analyzer.constituents[ticker]))
    

    