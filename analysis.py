#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 13 13:33:23 2020

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
        self.security_b = {} 
        self.title = '\n'.join(title)
        self.get_results()
        
    def get_results(self):
        for ticker in self.portfolio.positions:
            daily_return = pd.DataFrame(self.portfolio.positions[ticker].log)["price"].astype(float).pct_change().fillna(0.0)
            cum_return = np.exp(np.log(1+daily_return).cumsum())         
            drawdown,max_drawdown,drawdown_duration = perf.create_drawdowns(cum_return)
            
            statistics = {}
#            statistics["ticker"] = ticker
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
            statistics["sharpe_b"] = perf.create_sharpe_ratio(daily_return_b)
            
            statistics["drawdowns_b"] = dd_b
            statistics["max_drawdown_pct_b"] = max_dd_b
            statistics["max_drawdown_duration_b"] = dd_dur_b
#            statistics["security_b"] = security_b
            statistics["returns_b"] = daily_return_b
#            statistics["rolling_sharpe_b"] = rolling_sharpe_b
            statistics["cum_returns_b"] = cum_returns_b
            self.constituents[ticker] = statistics
            
            
    
    def _plot_security(self,stats,ax=None,**kwargs):
        def format_two_dec(x,pos):
            return '%.2f' % x
        
        stats = pd.DataFrame(stats)
        stats["date"] = pd.to_datetime(stats["date"])
        stats.set_index("date",inplace=True)
        
        y_axis_formatter = FuncFormatter(format_two_dec)
        ax.yaxis.set_major_formatter(FuncFormatter(y_axis_formatter))
        ax.xaxis.set_tick_params(reset=True)
        ax.yaxis.grid(linestyle=':')
        ax.xaxis.set_major_locator(mdates.YearLocator(1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.grid(linestyle=':')
        
        if self.benchmark is not None:
            benchmark = stats['cum_returns_b']
            benchmark.plot(lw=2, color='gray', label=self.benchmark, 
                           alpha=0.60,ax=ax, **kwargs)
        
        stats["cum_returns"].plot(lw=2,color="green",x_compat=False,
                                  label="Backtest",ax=ax,**kwargs)
        
        ax.axhline(1.0,linestyle="--",color="black",lw=1)
        ax.set_ylabel("Cumulative Returns")
        ax.set_xlabel("")
        plt.setp(ax.get_xticklabels(),visible=True,rotation=0,ha="center")
        ax.set_title("Cumulative Returns",fontweight="bold")

        return ax

    def _plot_rolling_sharpe(self, stats, ax=None, **kwargs):
        """
        Plots the curve of rolling Sharpe ratio.
        """
        def format_two_dec(x, pos):
            return '%.2f' % x


        y_axis_formatter = FuncFormatter(format_two_dec)
        ax.yaxis.set_major_formatter(FuncFormatter(y_axis_formatter))
        ax.xaxis.set_tick_params(reset=True)
        ax.yaxis.grid(linestyle=':')
        ax.xaxis.set_major_locator(mdates.YearLocator(1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.grid(linestyle=':')
        
        if self.benchmark is not None:
            benchmark = stats['rolling_sharpe_b']
            benchmark.plot(lw=2, color='gray', label=self.benchmark, 
                           alpha=0.60,ax=ax, **kwargs)

        stats['rolling_sharpe'].plot(lw=2, color='green', alpha=0.6, x_compat=False,
                    label='Backtest', ax=ax, **kwargs)

        ax.axvline(stats['rolling_sharpe'].index[252], linestyle="dashed", c="gray", lw=2)
        ax.set_ylabel('Rolling Annualised Sharpe')
        ax.legend(loc='best')
        ax.set_xlabel('')
        plt.setp(ax.get_xticklabels(), visible=True, rotation=0, ha='center')

        return ax
    
    def _plot_drawdown(self,stats,ax=None,**kwargs):
        def format_perc(x,pos):
            return '%.0f%%' % x
        
        stats = pd.DataFrame(stats)
        stats["date"] = pd.to_datetime(stats["date"])
        stats.set_index("date",inplace=True)
        
        y_axis_formatter = FuncFormatter(format_perc)
        ax.yaxis.set_major_formatter(FuncFormatter(y_axis_formatter))
        ax.yaxis.grid(linestyle=":")
        
        underwater = -100 * stats["drawdowns"]
        underwater.plot(ax=ax,lw=2,kind="area",color="red",alpha=0.3,**kwargs)
        ax.set_ylabel("")
        ax.set_xlabel("")
        plt.setp(ax.get_xticklabels(),visible=True,rotation=0,ha="center")
        ax.set_title("Drawdown(%)",fontweight="bold")
        
        return ax
            
    def _plot_monthly_returns(self,stats,ax=None,**kwargs):
        stats = pd.DataFrame(stats)
        stats["date"] = pd.to_datetime(stats["date"])
        stats.set_index("date",inplace=True)
        returns = stats["daily_returns"]
        
        monthly_ret = perf.aggregate_returns(returns,"monthly")
        monthly_ret = monthly_ret.unstack()
        monthly_ret = np.round(monthly_ret,3)
        monthly_ret.rename(columns={1:"Jan",2:"Feb",3:"Mar",4:"Apr",
                                    5:"May",6:"Jun",7:"Jul",8:"Aug",
                                    9:"Sep",10:"Oct",11:"Nov",12:"Dec"},
                           inplace = True)
        
        sns.heatmap(monthly_ret.fillna(0)*100.0,annot=True,fmt="0.1f",
                    annot_kws={"size":8},alpha=1.0,center=0.0,cbar=False,
                    cmap=cm.RdYlGn,ax=ax,**kwargs)
        
        ax.set_title('Monthly Returns (%)', fontweight='bold')
        ax.set_ylabel('')
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
        ax.set_xlabel('')
    
        return ax
        
    def _plot_yearly_returns(self,stats,ax=None,**kwargs):
        def format_perc(x,pos):
            return '%.0f%%' % x
        
        stats = pd.DataFrame(stats)
        stats["date"] = pd.to_datetime(stats["date"])
        stats.set_index("date",inplace=True)
        returns = stats["daily_returns"]
        
        y_axis_formatter = FuncFormatter(format_perc)
        ax.yaxis.set_major_formatter(FuncFormatter(y_axis_formatter))
        ax.yaxis.grid(linestyle=":")
        
        yly_ret = perf.aggregate_returns(returns,"yearly")*100.0
        yly_ret.plot(ax=ax,kind="bar")
        ax.set_title("yearly Returns(%)",fontweight="bold")
        ax.set_ylabel("")
        ax.set_xlabel("")
        plt.setp(ax.get_xticklabels(),rotation=45)
        ax.xaxis.grid(False)
        
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
              
        
    def plot_results(self, ticker):
                        
        """
        Plot the Tearsheet
        """
        rc = {
                'lines.linewidth': 1.0,
                'axes.facecolor': '0.995',
                'figure.facecolor': '0.97',
                'font.family': 'serif',
                'font.serif': 'Ubuntu',
                'font.monospace': 'Ubuntu Mono',
                'font.size': 10,
                'axes.labelsize': 10,
                'axes.labelweight': 'bold',
                'axes.titlesize': 10,
                'xtick.labelsize': 8,
                'ytick.labelsize': 8,
                'legend.fontsize': 10,
                'figure.titlesize': 12
            }
        sns.set_context(rc)
        sns.set_style("whitegrid")
        sns.set_palette("deep", desat=.6)
    
        if self.rolling_sharpe:
            offset_index = 1
        else:
            offset_index = 0
        vertical_sections = 5 + offset_index
        fig = plt.figure(figsize=(10, vertical_sections * 3.5))
        fig.suptitle(self.title, y=0.94, weight='bold')
        gs = gridspec.GridSpec(vertical_sections, 3, wspace=0.25, hspace=0.5)
    
        stats = self.constituents[ticker]
        ax_security = plt.subplot(gs[:2, :])
                
        if self.rolling_sharpe:
                ax_sharpe = plt.subplot(gs[2, :])
        ax_drawdown = plt.subplot(gs[2 + offset_index, :])
        ax_monthly_returns = plt.subplot(gs[3 + offset_index, :2])
        ax_yearly_returns = plt.subplot(gs[3 + offset_index, 2])
        ax_txt_curve = plt.subplot(gs[4 + offset_index, 0])
#                    ax_txt_time = plt.subplot(gs[4 + offset_index, 2])
    
        self._plot_security(stats, ax=ax_security)
                
        if self.rolling_sharpe:
            self._plot_rolling_sharpe(stats, ax=ax_sharpe)
        self._plot_drawdown(stats, ax=ax_drawdown)
        self._plot_monthly_returns(stats, ax=ax_monthly_returns)
        self._plot_yearly_returns(stats, ax=ax_yearly_returns)
        self._plot_txt_curve(stats, ax=ax_txt_curve)
#                    self._plot_txt_time(stats, ax=ax_txt_time)
    
            # Plot the figure
        plt.show(block=False)


