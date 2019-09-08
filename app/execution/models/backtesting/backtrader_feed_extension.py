# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import division
from past.utils import old_div
import os
import datetime
from decimal import Decimal

import backtrader as bt 
import pandas as pd

from backtrader.feeds import PandasData
from lib.logger import get_logger
import termcolor as tc

logger = get_logger(__name__)


# ! We sometimes get problems when plotting cerebro
# TODO should also be able take pandas Series containing 'order_size' as param
# TODO change the logic for buy and sell orders, this is not flexible enough


class ExtendedFeed(PandasData):

    lines = ('buy', 'sell', 'order_size')

    # for params, None = column not present, -1 = autodetect

    params = (
        ('datetime', 0),
        ('open', 1),
        ('high', 2),
        ('low', 3),
        ('close', 4),
        ('volume', 5),
        ('buy', 6),
        ('sell', 7),
        ('order_size', 8),
        ('openinterest',None),
    )
    datafields = PandasData.datafields + (['buy','sell']) 


# Create a Stratey
class Strategy(bt.Strategy):

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.datetime(0)
        print('%s, %s' % (dt, txt))


    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None


    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'Executed, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('Executed, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        color = 'green' if trade.pnlcomm>0 else 'red'
        self.log(tc.colored('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm), color))

    def __next__(self):
        # Log the closing price of the series from the reference if we want to have every candle close 
        # self.log('Close, %.2f' % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Get commission info
        # comm = self.broker.getcommissioninfo(self.data)
        comm = 0.00

        # Size as a percentage of account - don't forget to deduct commission amount
        # We take one percentage point off the intended order size as a precaution
        # ! Formula below may be wrong, please check
        open_size = (old_div((old_div((self.data.order_size[0]-1), 100)) * self.stats.broker.value[0], self.data.close[0]))*(1-comm)
        close_size = self.position.size

        # Check if we are in the market
        # TODO if self.position should be inside the if.buy statement
        if not self.position:

            # Not yet ... we MIGHT BUY if ...
            if self.data.buy :                    # BUY, BUY, BUY!!! (with all possible default parameters)
                self.log('↗ OPENING LONG, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy(size=open_size)

            if self.data.sell :                    # BUY, BUY, BUY!!! (with all possible default parameters)
                self.log('↘ OPENING SHORT, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell(size=open_size)
            

        else:

            if self.data.sell :
                # Close long position 
                self.log('- CLOSING LONG, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell(size=close_size)

                # Opening a short at the same time
                self.log('↘ OPENING SHORT, %.2f' % self.dataclose[0])
                self.order = self.sell(size=open_size)

            if self.data.buy :
                # Close short position 
                self.log('- CLOSING SHORT, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy(size=close_size)

                # Opening a long at the same time
                self.log('↗ OPENING LONG, %.2f' % self.dataclose[0])
                self.order = self.buy(size=open_size)


def get_signals(gryphon_strategy_class, data_path, key):

     # Get data into a pandas dataframe
    file_extension = os.path.splitext(data_path)[1]

    if file_extension == '.csv':
        df = pd.read_csv(data_path, parse_dates=["datetime"])
        df["hl2"] = old_div((df["high"] + df["low"]), 2)

    elif file_extension == '.h5':
        
        with pd.HDFStore(data_path) as store:
            df = store[key]

    else:
        raise NameError('No file path specified or file type not supported')

    # Get signals dataframe from strategy file
    signals = gryphon_strategy_class.signals(data=df)
    signals = signals[["datetime", "open", "high", "low", "close", "volume", "buy", "sell", "order_size"]]

    return signals


def run(gryphon_strategy_class, data_path, commission=0, key=None):

    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Pass gryphon_strategy_class as superclass
    cerebro.addstrategy(Strategy)

    # Get the dataframe with buy and sell signals that we created in the strat file
    df = get_signals(gryphon_strategy_class, data_path, key)

    # Pass it to the backtrader datafeed and add to cerebro
    data = ExtendedFeed(dataname=df)

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(1000.0)

    # Add a FixedSize sizer according to the stake
    # TODO change this 
    # cerebro.addsizer(bt.sizers.FixedSize, stake=100)


    # Set the commission
    cerebro.broker.setcommission(commission=commission)

    s = '| Backtesting Strat : %s  |' % gryphon_strategy_class.__class__.__name__
    print('\n')
    print('-' * len(s))
    print(s)
    print('-' * len(s) + '\n')
    print('Starting Portfolio Value :{0}'.format(cerebro.broker.getvalue()))
    
    # Run over everything
    cerebro.run()

    print('Final Portfolio Value :{0}'.format(cerebro.broker.getvalue()))

    try:        
        cerebro.plot()
    except:
        print('Cerebro plotting failed')
        pass