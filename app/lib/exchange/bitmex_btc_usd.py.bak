# -*- coding: utf-8 -*-
import base64
from collections import OrderedDict
import hashlib
import hmac
import json
import time

import cdecimal
from cdecimal import Decimal
from delorean import Delorean, parse

from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.exchange.exchange_order import Order
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money

import ccxt
from gryphon.lib.metrics import quote as quote_lib
import os

logger = get_logger(__name__)

class BitmexBTCUSDExchange(ExchangeAPIWrapper):
    def __init__(self, session=None, configuration=None):
        super(BitmexBTCUSDExchange, self).__init__(session, configuration)
        
        self.name = u'BITMEX_BTC_USD'
        self.friendly_name = u'Bitmex BTC-USD'
        self.volume_currency = u'BTC'
        self.currency = u'USD'
        self.bid_string = 'buy'
        self.ask_string = 'sell'

        self.load_creds()

        self.ccxt_exchange_id = 'bitmex'
        self.ccxt_symbol = "BTC/USD"
        ccxt_exchange_class = getattr(ccxt, self.ccxt_exchange_id)
        self.ccxt_exchange = ccxt_exchange_class({
            'apiKey': self.api_key,
            'secret': self.secret
            })

        # Configurables with defaults.
        self.market_order_fee = Decimal('0.00075')
        self.limit_order_fee = Decimal('0.000')
        self.fee = Decimal('0.00')
        self.fiat_balance_tolerance = Money('0.01', 'USD')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.max_tick_speed = 1
        self.min_order_size = Money('0.00', 'BTC')
        self.use_cached_orderbook = False

        if configuration:
            self.configure(configuration)


    def _load_env(self, key):
        return str(os.environ[key])

    def load_creds(self):
        try:
            self.api_key
            self.secret
        except AttributeError:
            self.api_key = self._load_env('BITMEX_BTC_USD_API_KEY')
            self.secret = self._load_env('BITMEX_BTC_USD_API_SECRET')


    def signature(self, params, secret):
        pass

    def auth_request(self) :
        '''Incorrect''' #!!!!
        path = 'instrument'
        signature = ccxt.python.bitmex.sign(path=path)
        return signature


    def req(self, req_method, url, **kwargs):
        req = super(BitmexBTCUSDExchange, self).req(req_method, url, **kwargs)
        return req

    def resp(self, req):
        response = super(BitmexBTCUSDExchange, self).resp(req)
        if 'message' in response:
            errors_string = str(response['message'])
            if 'not enough balance' in errors_string:
                raise exceptions.InsufficientFundsError()
            elif 'Order could not be cancelled' in errors_string:
                raise exceptions.CancelOrderNotFoundError()
            elif 'Nonce is too small' in errors_string:
                raise exceptions.NonceError()
            else:
                raise exceptions.ExchangeAPIErrorException(self, errors_string)

        return response

    def get_my_trades(self, since=None, limit=None, params={}):

        if self.ccxt_exchange.has['fetchMyTrades']:
            my_trades = self.ccxt_exchange.fetchMyTrades(
                symbol=self.ccxt_symbol,
                since=since,
                limit=limit,
                params=params
                )  
            return my_trades
        else:
            raise NotImplementedError


    def get_all_trades(self, since=None, limit=None, params={}):
        if self.ccxt_exchange.has['fetchTrades']:
            all_trades = self.ccxt_exchange.fetchTrades(
                symbol=self.ccxt_symbol,
                since=since,
                limit=limit,
                params=params
                )
            return all_trades
        else:
            raise NotImplementedError

    def get_status(self):
        if self.ccxt_exchange.has['fetchStatus']:
            status = self.ccxt_exchange.fetchStatus
            return status
        else:
            raise NotImplementedError


    def get_balance(self):
        if self.ccxt_exchange.has['fetchBalance']:
            raw_balance = self.ccxt_exchange.fetchBalance()

            btc_available = None
            usd_available = None
            if 'BTC' in raw_balance['free']: 
                btc_available = Money(raw_balance['free']['BTC'], 'BTC')
            else:
                btc_available = Money('0.0', 'BTC')
            
            if 'USD' in raw_balance['free']:
                usd_available = Money(raw_balance['free']['USD'], 'USD')
            else:
                usd_available = Money('0.0', 'USD')

            if btc_available == None and usd_available == None:
                raise exceptions.ExchangeAPIErrorException(
                    self,
                    'missing expected balances',
                )

            balance = Balance()
            balance['BTC'] = btc_available
            balance['USD'] = usd_available

            return balance

        else:
            raise NotImplementedError

    def get_ticker(self):
        if self.ccxt_exchange.has['fetchTicker']:
            ticker = self.ccxt_exchange.fetchTicker(self.ccxt_symbol)
            return ticker
        else:
            raise NotImplementedError

    def get_orderbook(self, limit=None, params={}, volume_limit=None):
        if self.ccxt_exchange.has['fetchOrderBook']:
            raw_orderbook = self.ccxt_exchange.fetchOrderBook(
                symbol=self.ccxt_symbol,
                limit=limit,
                params=params
                )
            parsed_orderbook = self.parse_orderbook(raw_orderbook, volume_limit)
            parsed_orderbook['time_parsed'] = Delorean().epoch
            return parsed_orderbook
        else:
            raise NotImplementedError


    def get_price_quote(self, mode, volume):
        open_orders = self.ccxt_exchange.fetchOpenOrders(
            symbol=self.ccxt_symbol,
            since=None,
            limit=None, 
            params={}
            )

        open_volume = sum([o['volume_remaining'] for o in open_orders])
        orderbook = self.get_orderbook(volume_limit=volume+open_volume)
    
        orderbook = self.remove_orders_from_orderbook(orderbook, open_orders)

        return quote_lib.price_quote_from_orderbook(orderbook, mode, volume)


    def market_order(self, mode, volume):
        if self.ccxt_exchange.has['createMarketBuyOrder', 'createMarketSellOrder']:
            if mode==Consts.BID:
                self.ccxt_exchange.createMarketBuyOrder(
                    symbol=self.ccxt_symbol,
                    amount=volume,
                    params={}
                    )
            elif mode==Consts.ASK:
                self.ccxt_exchange.createMarketSellOrder(
                    symbol=self.ccxt_symbol,
                    amount=volume,
                    params={}
                    )
        else:
            raise NotImplementedError
        

    def limit_order(self, mode, volume, price):
        if self.ccxt_exchange.has['createLimitBuyOrder', 'createLimitSellOrder']:
            if mode==Consts.BID:
                self.ccxt_exchange.createLimitBuyOrder(
                    symbol=self.ccxt_symbol,
                    amount=volume,
                    params={},
                    price=price
                    )
            elif mode==Consts.ASK:
                self.ccxt_exchange.createLimitSellOrder(
                    symbol=self.ccxt_symbol,
                    amount=volume,
                    params={},
                    price=price
                    )
        else:
            raise NotImplementedError

    def cancel_order(self, order_id, params={}):
        if self.ccxt_exchange.has['cancelOrder']:
            self.ccxt_exchange.cancelOrder(
                id=order_id,
                symbol=self.ccxt_symbol,
                params=params
                )
        else:
            raise NotImplementedError

    def get_open_orders(self, since=None, limit=None, params={}):
        if self.ccxt_exchange.has['fetchOpenOrders']:
            open_orders = self.ccxt_exchange.fetchOpenOrders(
                symbol=self.ccxt_symbol,
                since=since,
                limit=limit,
                params=params
                )
            return open_orders
        else:
            raise NotImplementedError


# ============================================================================================================
# BITFINEX GRYPHON METHODS
# =================================================================================================
    
    
    
    @property
    def _orderbook_sort_key(self):
        return lambda o: float(o['price'])

    def parse_order(self, order):
        price = Money(order['price'], 'USD')
        volume = Money(order['amount'], 'BTC')
        return (price, volume)


    # returns an OrderedDict of order ids mapped to their filled volume (only include orders that have some trades)
    def audit(self, skip_recent=0):
        orders = OrderedDict()
        trades_to_audit = self.all_trades()
        # Trades from the same order aren't guaranteed to be next to each other, so we need to group them
        trades_to_audit.sort(key=lambda t:(t['order_id'], t['timestamp']), reverse=True)

        # we want to skip recent orders, but splitting between trades will give us incorrect volume_filled
        orders_to_skip = skip_recent

        while orders_to_skip > 0:
            try:
                trade = trades_to_audit.pop(0)
                # we found a boundary
                if trade['order_id'] != trades_to_audit[0]['order_id']:
                    orders_to_skip -= 1
            except IndexError:
                # if we run off the end of the list, we are trying to strip all trades
                trades_to_audit = []
                orders_to_skip = 0

        for trade in trades_to_audit:
            order_id = str(trade['order_id'])

            try:
                orders[order_id] += abs(Money(trade['amount'], 'BTC'))
            except KeyError:
                orders[order_id] = abs(Money(trade['amount'], 'BTC'))

        # Remove the oldest 2 orders, because its trades might be wrapped around a page
        # gap. This would give us an innacurate volume_filled number. We need to remove
        # 2, since there could be an ask and a bid.
        try:
            orders.popitem()
            orders.popitem()
        except KeyError:
            pass

        return orders
