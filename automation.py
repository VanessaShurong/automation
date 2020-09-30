#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 11:29:25 2020

@author: vanessa
"""

from portfolio import Portfolio
import performance as perf

from matplotlib import cm
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
import os
import seaborn as sns
from matplotlib.ticker import FuncFormatter

class Analysis:
    def __init__(self,portfolio,title=None,benchmark=None,periods=252,rolling_sharpe=False):
        self.portfolio = portfolio
        self.constituents= {}
        self.periods = periods
        self.benchmark = benchmark
        self.rolling_sharpe = rolling_sharpe
        self.security = {}
        self.security_benchmark = {} 
        self.title = '\n'.join(title)
        self.get_results()
        
    def get_results(self):
        for ticker in self.portfolio.positions:
            daily_return = pd.DataFrame(self.portfolio.positions[ticker].log)["price"].astype(float).pct_change().fillna(0.0)
            cum_return = np.exp(np.log(1+daily_return).cumsum())         
            drawdown,max_drawdown,drawdown_duration = perf.create_drawdowns(cum_return)
            
            statistics = {}
            statistics["sharpe"] = perf.create_sharpe_ratio(daily_return,self.periods)
            statistics["drawdowns"] = drawdown
            statistics["max_drawdown"] = max_drawdown
            statistics["max_drawdown_pct"] = max_drawdown
            statistics["max_drawdown_duration"] = drawdown_duration
            statistics["daily_returns"] = daily_return
            statistics["cum_returns"] = cum_return
            statistics["date"] = pd.DataFrame(self.portfolio.positions[ticker].log)["date"]
            
            self.constituents[ticker] = statistics
            
        if self.benchmark is not None:
            "Need to change the benchamrk here"
            daily_return_b = pd.DataFrame(self.portfolio.positions[ticker].log)["price"].astype(float).pct_change().fillna(0.0)
            cum_returns_b = np.exp(np.log(1 + daily_return_b).cumsum())
            dd_b, max_dd_b, dd_dur_b = perf.create_drawdowns(cum_returns_b)
            statistics["sharpe_b"] = perf.create_sharpe_ratio(returns_b)
            
            statistics["drawdowns_b"] = dd_b
            statistics["max_drawdown_pct_b"] = max_dd_b
            statistics["max_drawdown_duration_b"] = dd_dur_b
            statistics["security_b"] = security_b
            statistics["returns_b"] = returns_b
            statistics["rolling_sharpe_b"] = rolling_sharpe_b
            statistics["cum_returns_b"] = cum_returns_b
            self.constituents[ticker] = statistics

 def _plot_txt_curve(self, stats, ax=None, **kwargs):
        """
        Outputs the statistics for the security curve.
        """
        def format_perc(x, pos):
                return '%.0f%%' % x

        stats = pd.DataFrame(stats)
        stats['date']=pd.to_datetime(stats['date'])
        stats.set_index('date',inplace=True)
        returns = stats["daily_returns"]
        cum_returns = stats['cum_returns']

        y_axis_formatter = FuncFormatter(format_perc)
        ax.yaxis.set_major_formatter(FuncFormatter(y_axis_formatter))
            
        tot_ret = cum_returns[-1] - 1.0
        cagr = perf.create_cagr(cum_returns, self.periods)
        sharpe = perf.create_sharpe_ratio(returns, self.periods)
        rsq = perf.rsuqare(range(cum_returns.shape[0]), cum_returns)
        dd, dd_max, dd_dur = perf.create_drawdowns(cum_returns)

        ax.text(0.25, 7.9, 'Total Return', fontsize=8)
        ax.text(7.50, 7.9, '{:.0%}'.format(tot_ret), fontweight='bold', horizontalalignment='right', fontsize=8)
            
        ax.text(0.25, 6.9, 'CAGR', fontsize=8)
        ax.text(7.50, 6.9, '{:.2%}'.format(cagr), fontweight='bold', horizontalalignment='right', fontsize=8)

        ax.text(0.25, 5.9, 'Sharpe Ratio', fontsize=8)
        ax.text(7.50, 5.9, '{:.2f}'.format(sharpe), fontweight='bold', horizontalalignment='right', fontsize=8)
            
        ax.text(0.25, 4.9, 'Annual Volatility', fontsize=8)
        ax.text(7.50, 4.9, '{:.2%}'.format(returns.std() * np.sqrt(252)), fontweight='bold', horizontalalignment='right', fontsize=8)
            
        ax.text(0.25, 3.9, 'R-Squared', fontsize=8)
        ax.text(7.50, 3.9, '{:.2f}'.format(rsq), fontweight='bold', horizontalalignment='right', fontsize=8)

        ax.text(0.25, 2.9, 'Max Daily Drawdown', fontsize=8)
        ax.text(7.50, 2.9, '{:.2%}'.format(dd_max), color='red', fontweight='bold', horizontalalignment='right', fontsize=8)

        ax.text(0.25, 1.9, 'Max Drawdown Duration', fontsize=8)
        ax.text(7.50, 1.9, '{:.0f}'.format(dd_dur), fontweight='bold', horizontalalignment='right', fontsize=8)

        ax.set_title('Curve', fontweight='bold')

        if self.benchmark is not None:
            returns_b = stats['returns_b']
            security_b = stats['cum_returns_b']
            tot_ret_b = security_b[-1] - 1.0
            cagr_b = perf.create_cagr(security_b)
            sharpe_b = perf.create_sharpe_ratio(returns_b)
            rsq_b = perf.rsquared(range(security_b.shape[0]), security_b)
            dd_b, dd_max_b, dd_dur_b = perf.create_drawdowns(security_b)

            ax.text(9.75, 8.9, '{:.0%}'.format(tot_ret_b), fontweight='bold', horizontalalignment='right', fontsize=8)
            ax.text(9.75, 7.9, '{:.2%}'.format(cagr_b), fontweight='bold', horizontalalignment='right', fontsize=8)
            ax.text(9.75, 6.9, '{:.2f}'.format(sharpe_b), fontweight='bold', horizontalalignment='right', fontsize=8)
            ax.text(9.75, 5.9, '{:.2%}'.format(returns_b.std() * np.sqrt(252)), fontweight='bold', horizontalalignment='right', fontsize=8)
            ax.text(9.75, 4.9, '{:.2f}'.format(rsq_b), fontweight='bold', horizontalalignment='right', fontsize=8)
            ax.text(9.75, 3.9, '{:.2%}'.format(dd_max_b), color='red', fontweight='bold', horizontalalignment='right', fontsize=8)
            ax.text(9.75, 2.9, '{:.0f}'.format(dd_dur_b), fontweight='bold', horizontalalignment='right', fontsize=8)

            ax.set_title('Curve vs. Benchmark', fontweight='bold')

        ax.grid(False)
        ax.spines['top'].set_linewidth(2.0)
        ax.spines['bottom'].set_linewidth(2.0)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.get_xaxis().set_visible(False)
        ax.set_ylabel('')
        ax.set_xlabel('')
            
        ax.axis([0, 10, 0, 10]) 
        return ax
              
