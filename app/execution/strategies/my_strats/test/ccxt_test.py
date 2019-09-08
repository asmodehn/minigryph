
from gryphon.execution.strategies.base import Strategy
from cdecimal import Decimal
from gryphon.lib.money import Money
from gryphon.lib.exchange.consts import Consts
import gryphon.lib.metrics.quote as quote
from gryphon.lib import market_making as mm
from gryphon.lib.metrics import midpoint as midpoint_lib
from gryphon.lib.analysis.backtrader_indicators import test_indicator

import talib
import pandas as pd

from gryphon.lib.models import datum_indicators



class CcxtTest(Strategy):

    def __init__(self, db, harness, strategy_configuration, backtest_configuration):
        super(CcxtTest, self).__init__(db, harness)

        self.spread = Decimal("0.01")
        self.base_volume = Money("0.5", "ETH")
        self.exchange = None
        self.slip_volume = Money("10", "ETH")
        self.volume_currency = "ETH"

        self.configure(strategy_configuration)

        self.localslist = locals()
        self.localslist.pop('self')

        # print 'self.kwargs', self.localslist

    def configure(self, strategy_configuration):
        super(CcxtTest, self).configure(strategy_configuration) 

        self.init_configurable("spread", strategy_configuration)
        self.init_configurable("base_volume", strategy_configuration)
        self.init_configurable("exchange", strategy_configuration)

        self.init_target_exchange()

    def set_up(self):
        pass

    def init_target_exchange(self):
        self.target_exchange = self.harness.exchange_from_key(self.exchange)
        self.target_exchanges = [self.target_exchange.name]


    def tick(self, current_orders):  
        ob = self.target_exchange.get_orderbook()
        ticker = self.target_exchange.get_ticker()
        balance = self.target_exchange.get_balance()

        price_quote = self.target_exchange.get_price_quote(mode=Consts.BID, volume=Money(100000, 'ETH'))

        self.harness.log('price quote : {0}'.format(price_quote))
        self.harness.log('ticker last: {0:.2f}'.format(ticker["last"]))
        
        bid_volume = mm.simple_position_responsive_sizing(self.base_volume, self.position)[0]
        bid_price = mm.midpoint_centered_fixed_spread(ob, self.spread)[0]

        if bid_volume > 0:
            self.target_exchange.limit_order(Consts.BID, bid_volume, bid_price)