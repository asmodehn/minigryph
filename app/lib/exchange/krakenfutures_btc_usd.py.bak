# -*- coding: utf-8 -*-
import base64
from collections import OrderedDict
import hashlib
import hmac
import os
import time
import urllib

from cdecimal import Decimal
from delorean import Delorean
from more_itertools import chunked

from gryphon.lib.exchange import exceptions
from gryphon.lib.exchange import order_types
from gryphon.lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money

import pandas as pd

logger = get_logger(__name__)


class LedgerSizeException(Exception):
    pass


class KrakenFuturesBTCUSDExchange(ExchangeAPIWrapper):
    '''
    This is only intended for use with perps
    '''
    # TODO : implement Dead Mans switch : "cancelallordersafter" endpoint
    # To accommodate downtime issues, you can use the "cancelallordersafter" REST endpoint to 
    # specify a timeout period which, if a new request is not sent before that period, will result 
    # in all orders being cancelled.


    #! =================================
    #! NOT ADDED YET TO EXCHANGE FACTORY
    #! =================================

    def __init__(self, session=None, configuration=None):
        super(KrakenFuturesBTCUSDExchange, self).__init__(session, configuration)

        # Immutable properties and endpoints.
        self.name = u'KRAKENFUTURES_BTC_USD'
        self.friendly_name = u'KrakenFutures BTC-USD'
        self.base_url = 'https://futures.kraken.com/derivatives/api/v3'
        self.price_decimal_precision = 1
        self.currency = u'USD'
        self.volume_currency = u'BTC'
        self.bid_string = 'buy'
        self.ask_string = 'sell'

        self.orderbook_depth = 100000

        # Configurables with defaults.
        self.market_order_fee = Decimal('0.00075')
        self.limit_order_fee = Decimal('-0.0002')
        self.fee = self.market_order_fee
        self.fiat_balance_tolerance = Money('0.0001', 'USD')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.min_order_size = Money('0.002', 'BTC')
        self.max_tick_speed = 5
        self.use_cached_orderbook = False

        # TODO: Unclear if these should be configurable or not.
        self.withdrawal_fee = Money('0.001', 'BTC')
        self.btc_credit_limit = Money('0', 'BTC')

        if configuration:
            self.configure(configuration)

    @property
    def pair(self):
        return self.construct_pair(self.currency)

    def req(self, req_method, url, **kwargs):
        req = super(KrakenFuturesBTCUSDExchange, self).req(req_method, url, **kwargs)

        if not kwargs.get('no_auth'):
            time.sleep(0.1)  # For nonces.

        return req

    def resp(self, req):
        response = super(KrakenFuturesBTCUSDExchange, self).resp(req)

        if response.get('error'):
            errors_string = str(response['error'])

            if 'Insufficient funds' in errors_string:
                raise exceptions.InsufficientFundsError()
            elif 'Unknown order' in errors_string:
                raise exceptions.CancelOrderNotFoundError()
            elif 'Invalid nonce' in errors_string:
                raise exceptions.NonceError()
            else:
                raise exceptions.ExchangeAPIErrorException(self, errors_string)

        try:
            return response['result']
        except KeyError:
            raise exceptions.ExchangeAPIFailureException(self, response)

    def get_trades_public(self):
        '''will return last 100 trades (public endpoint)'''
        
        req = self.get_trades_public_req()
        return self.get_trades_public_resp(req)

    def get_trades_public_req(self):
        # https://support.kraken.com/hc/en-us/articles/360022839511-History
        
        payload = {'symbol': 'pi_xbtusd'}
        req = self.req('get', '/history', data=payload)

        return req

    def get_trades_public_resp(self, req):
        # https://support.kraken.com/hc/en-us/articles/360022839511-History

        response = self.resp(req)
        return response['history']


    def get_trades_private(self):
        '''will return last 100 trades (private endpoint)'''

        req = self.get_trades_private_req()
        return self.get_trades_private_resp(req)

    def get_trades_private_req(self):
        # https://support.kraken.com/hc/en-us/articles/360028921891-Recent-Orders

        payload = {'symbol': 'pi_xbtusd'}
        req = self.req('get', '/recentorders', data=payload)
        return req

    def get_trades_private_resp(self, req):
        # https://support.kraken.com/hc/en-us/articles/360028921891-Recent-Orders

        response = self.resp(req)
        return response['orderEvents']


    def get_trades_info_from_ledger(self, trade_ids, order_open_timestamp, order_close_timestamp):
        # ! not done yet

        """
        Check the ledger entries to get accurate numbers for how much our balance was
        changed.

        The ledger is Kraken's only real source of truth, the trades/order endpoints
        lie to us.
        """

        # We add a 0.1s buffer to make sure we get entries right on the boundary
        # timestamps.
        ledger_start = order_open_timestamp - Decimal('0.1')
        # We add a 1s buffer because it takes Kraken a bit of time to write to the
        # ledger.
        ledger_end = order_close_timestamp + Decimal('1')

        entries = self.get_ledger_entries(
            start=ledger_start,
            end=ledger_end,
        )

        trades_info = {}

        for trade_id in trade_ids:
            trades_info[trade_id] = {
                'btc': Money.loads('BTC 0'),
                'btc_fee': Money.loads('BTC 0'),
                'fiat': Money(0, self.currency),
                'fiat_fee': Money(0, self.currency),
            }

        for ledger_id, entry in entries.iteritems():
            trade_id = entry['refid']

            if trade_id not in trade_ids:
                continue

            amount = Decimal(entry['amount'])

            if entry['type'] == 'credit':
                # Credit ledger entries show up when we dip into our line of credit.
                # They have opposite signs, and need to be included along side the
                # trade ledger entries to get accurate trade amounts.
                amount = -amount
            elif entry['type'] == 'trade':
                pass
            else:
                raise exceptions.ExchangeAPIErrorException(
                    self,
                    'Unexpected ledger entry type "%s"' % entry['type'],
                )

            currency = self.convert_from_kraken_currency(entry['asset'])

            if currency == 'BTC':
                trades_info[trade_id]['btc'] += Money(amount, 'BTC')
                trades_info[trade_id]['btc_fee'] += Money(entry['fee'], 'BTC')
            else:
                trades_info[trade_id]['fiat'] += Money(amount, currency)
                trades_info[trade_id]['fiat_fee'] += Money(entry['fee'], currency)

            # There are multiple ledger entries per trade, but they should all be going
            #through at the same time, so we can just take the timestamp of the last
            # one.
            trades_info[trade_id]['time'] = entry['time']

        return trades_info

    def ledger_entry(self, ledger_id):
        # ! not done yet
        req = self.ledger_entry_req(ledger_id)
        return self.ledger_entry_resp(req)

    def ledger_entry_req(self, ledger_id):
        # ! not done yet

        payload = {
            'id': ledger_id,
        }

        return self.req('post', '/private/QueryLedgers', data=payload)

    def ledger_entry_resp(self, req):
        # ! not done yet
        return self.resp(req)

    def get_ledger_entries(self, type=None, start=None, end=None):
        # ! not done yet

        try:
            req = self.get_ledger_entries_req(type, start, end)
            return self.get_ledger_entries_resp(req)
        except LedgerSizeException:
            # If there were too many ledger entries for this time period, split the
            # period in half and run each one seperately.
            # It's a bit of a hack but this is a rare edge case.
            mid = (start + end) / 2
            first_half = self.get_ledger_entries(type, start, mid)
            second_half = self.get_ledger_entries(type, mid, end)

            full_ledger = first_half
            full_ledger.update(second_half)

            return full_ledger

    def get_ledger_entries_req(self, type=None, start=None, end=None):
        # ! not done yet

        payload = {}

        if type:
            payload['type'] = type

        if start:
            payload['start'] = '%.3f' % start

        if end:
            payload['end'] = '%.3f' % end

        return self.req('post', '/private/Ledgers', data=payload)

    def get_ledger_entries_resp(self, req):
        # ! not done yet

        response = self.resp(req)
        count = int(response['count'])

        entries = response['ledger']

        if count > len(entries):
            raise LedgerSizeException('More entries than fit on one page of results')

        return entries

    def closed_orders(self, start=None, end=None, offset=0):
        # ! not done yet
         
        req = self.closed_orders_req(start, end, offset)
        return self.closed_orders_resp(req)

    def closed_orders_req(self, start=None, end=None, offset=0):
        # ! not done yet

        payload = {}

        if start:
            payload['start'] = start

        if end:
            payload['end'] = end

        if offset:
            payload['ofs'] = str(offset)

        return self.req('post', '/private/ClosedOrders', data=payload)

    def closed_orders_resp(self, req):
        # ! not done yet

        response = self.resp(req)
        count = int(response['count'])
        closed_orders = []

        for order_id, raw_order in response['closed'].iteritems():
            raw_order['order_id'] = order_id
            closed_orders.append(raw_order)

        return count, closed_orders

    ######## Common Exchange Methods ########

    def load_creds(self):
        try:
            self.api_key
            self.secret
        except AttributeError:
            self.api_key = self._load_env('KRAKENFUTURES_BTC_USD_API_KEY')
            self.secret = self._load_env('KRAKENFUTURES_BTC_USD_API_SECRET')

    def auth_request(self, req_method, url, request_args):
        """
        This modifies the request_args.
        """
        self.load_creds()

        endpoint = url.replace(self.base_url, '')
        endpoint = '/0' + endpoint

        nonce = unicode(int(round(time.time() * 1000)))

        try:
            payload = request_args['data']
        except KeyError:
            payload = request_args['data'] = {}

        payload.update({
            'nonce': nonce,
        })

        post_data = urllib.urlencode(payload)
        message = endpoint + hashlib.sha256(nonce + post_data).digest()
        sig = base64.b64encode(hmac.new(base64.b64decode(self.secret), message, hashlib.sha512).digest())

        try:
            headers = request_args['headers']
        except KeyError:
            headers = request_args['headers'] = {}

        headers.update({
            'API-Key': self.api_key,
            'API-Sign': sig,
        })

    def get_balance_req(self):
        # https://support.kraken.com/hc/en-us/articles/360022635792-Accounts

        return self.req('post', 'accounts')

    def get_balance_resp(self, req):
        # https://support.kraken.com/hc/en-us/articles/360022635792-Accounts

        response = self.resp(req)["accounts"]["balances"]["xbt"]
        total_balance = Balance()
        total_balance['btc'] = Money(Decimal(response), 'btc')    

        return total_balance

    def get_ticker_req(self, verify=True):
        # https://support.kraken.com/hc/en-us/articles/360022839531-Tickers

        url = 'tickers'
        return self.req('get', url, no_auth=True, verify=verify)["tickers"]

    def get_ticker_resp(self, req):
        # https://support.kraken.com/hc/en-us/articles/360022839531-Tickers

        response = self.resp(req)
        ticker = filter(lambda ticker : ticker["symbol"] == "pi_xbtusd", response)

        return {
            'mark': Money(ticker['markPrice'], self.currency),
            'ask' : Money(ticker['ask'], self.currency),
            'bid' : Money(ticker['bid'], self.currency),
            'oi': Money(ticker['openInterest'], self.currency),
            'last': Money(ticker['last'], self.currency),
            'volume': Money(ticker['vol24h'], self.currency),
        }



    def get_open_positions(self):
        '''returns size and average entry price of all open positions'''

        req = self.get_open_position_req()
        return self.get_open_position_resp(req)

    def get_open_positions_req(self, verify=True):
        # https://support.kraken.com/hc/en-us/articles/360022635832-Open-Positions

        url = '/openpositions'
        return self.req('get', url, verify=verify)

    def get_open_positions_resp(self, req):
        # https://support.kraken.com/hc/en-us/articles/360022635832-Open-Positions

        response = self.resp(req)
        return response['openPositions']



    def _get_orderbook_from_api_req(self, verify=True):
        # https://support.kraken.com/hc/en-us/articles/360022839551-Order-Book

        url = '/orderbook/?symbol=pi_xbtusd'
        return self.req('get', url, no_auth=True, verify=verify)["orderBook"]

    def _get_raw_bids(self, raw_orderbook):
        return raw_orderbook['bids']

    def _get_raw_asks(self, raw_orderbook):
        return raw_orderbook['asks']

    def place_order_req(self, mode, volume, price, order_type=order_types.LIMIT_ORDER):
        # https://support.kraken.com/hc/en-us/articles/360022839691-Send-Order

        mode = self._order_mode_from_const(mode)
        try:
            payload = {
                'orderType': 'lmt',
                'symbol': 'pi_xbtusd',
                'side':mode,
                'size': unicode(volume.amount),
                'limitPrice': unicode(price.amount)
                # 'stopPrice': optional
                }

        except AttributeError:
            raise TypeError('volume and price must be Money objects')

        return self.req('post', '/sendorder', data=payload)

    def place_order_resp(self, req):
        # https://support.kraken.com/hc/en-us/articles/360022839691-Send-Order
        
        response = self.resp(req)

        try:
            return {'success': True, 'order_id': unicode(response['order_id'])}
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'response does not contain an order_id',
            )

    def get_open_orders_req(self):
        # https://support.kraken.com/hc/en-us/articles/360022839631-Open-Orders

        payload = {}
        return self.req('get', '/openorders', data=payload)

    def get_open_orders_resp(self, req):
        # https://support.kraken.com/hc/en-us/articles/360022839631-Open-Orders
        
        response = self.resp(req)
        open_orders = []

        try:
            raw_open_orders = response['openOrders']

            for raw_order in raw_open_orders.iteritems():
                if raw_order['status'] in ('untouched', 'partiallyFilled'):
                    mode = self._order_mode_to_const(raw_order["side"])
                    volume_filled = Money(raw_order['filledSize'], self.currency)
                    volume_unfilled = Money(raw_order['unfilledSize'], self.currency)
                    price = Money(raw_order['limitPrice'], self.currency)
                    order_id = raw_order['order_id']

                    order = {
                        'mode': mode,
                        'id': order_id,
                        'price': price,
                        'volume_filled': volume_filled, 
                        'volume_remaining': volume_unfilled,
                    }

                    open_orders.append(order)
        except KeyError:
            raise exceptions.ExchangeAPIErrorException(
                self,
                'Open orders format incorrect',
            )

        return open_orders

    def get_order_details(self, order_id):
        # ! not done yet

        req = self.get_order_details_req(order_id)
        return self.get_order_details_resp(req, order_id)

    def get_order_details_req(self, order_id):
        # ! not done yet

        return self.get_multi_order_details_req([order_id])

    def get_order_details_resp(self, req, order_id):
        #! not done yet

        return self.get_multi_order_details_resp(req, [order_id])[order_id]
            
    def get_multi_order_details(self, order_ids):
        # ! not done yt

        req = self.get_multi_order_details_req(order_ids)
        return self.get_multi_order_details_resp(req, order_ids)
 
    def get_multi_order_details_req(self, order_ids):
        # ! not done yet

        order_ids = [unicode(o) for o in order_ids]

        payload = {
            'trades': True,
            'txid': ','.join(order_ids),
        }

        return self.req('post', '/private/QueryOrders', data=payload)

    def get_multi_order_details_resp(self, req, order_ids):
        # ! not done yet

        multi_trades = self.resp(req)
        data = {}

        for order_id in order_ids:
            total_fiat = Money('0', self.currency)
            total_btc = Money('0', 'BTC')
            our_trades = []

            if order_id in multi_trades:
                order = multi_trades[order_id]
                trade_ids = order.get('trades', [])

                if trade_ids:
                    opentm = order['opentm']

                    # Partially-executed orders haven't "closed" yet so they don't
                    # have a closetm. We only need the already executed trades, so we
                    # end the interval at NOW().
                    if 'closetm' in order:
                        closetm = order['closetm']
                    else:
                        closetm = Decimal(Delorean().epoch)

                    trades = self.get_trades_info_from_ledger(
                        trade_ids,
                        opentm,
                        closetm,
                    )

                    for t_id, t in trades.iteritems():
                        fiat = abs(t['fiat'])
                        btc = abs(t['btc'])

                        if t['btc_fee'] and t['fiat_fee']:
                            raise exceptions.ExchangeAPIErrorException(
                                self,
                                '#%s charged fees in both fiat (%s) and BTC (%s)' % (
                                order_id,
                                t['fiat_fee'],
                                t['btc_fee'],
                            ))
                        elif t['btc_fee']:
                            fee = t['btc_fee']
                        else:
                            fee = t['fiat_fee']

                        total_fiat += fiat
                        total_btc += btc

                        our_trades.append({
                            'time': int(t['time']),
                            'trade_id': unicode(t_id),
                            'fee': fee,
                            'btc': btc,
                            'fiat': fiat,
                        })

            data[order_id] = {
                'time_created': int(order['opentm']),
                'type': self._order_mode_to_const(order['descr']['type']),
                'btc_total': total_btc,
                'fiat_total': total_fiat,
                'trades': our_trades,
            }

        return data

    def cancel_order_req(self, order_id):
        # https://support.kraken.com/hc/en-us/articles/360022635872-Cancel-Order

        payload = {
            'order_id': unicode(order_id),
        }

        return self.req('post', '/cancelorder', data=payload)

    def cancel_order_resp(self, req):
        response = self.resp(req)

        if response['status'] == 'cancelled':
            return {'success': True}
        elif response['status'] == "filled":
            return {'order was filled before it could get cancelled'}
        elif response['status'] == "notFound":
            raise exceptions.CancelOrderNotFoundError(self)
        else:
            raise exceptions.ExchangeAPIErrorException(self, message="unexpected status")
    
            



    def transfer(self, amount, to):
        '''
        transfer funds between two margin accounts with the same collateral currency, 
        or between a margin account and your cash account 
        '''

        req = self.transfer_req(amount, to)
        return self.transfer_resp(req)

    def transfer_req(self, volume, to):
        # https://support.kraken.com/hc/en-us/articles/360022635852-Transfer
        
        payload = {
            'fromAccount': 'pi_xbtusd',
            'toAccount': to,
            'unit': 'xbt',
            'amount' : volume.amount 
            }
        req = self.req('post', '/transfer', data=payload)
        return req

    def transfer_resp(self, req):
        # https://support.kraken.com/hc/en-us/articles/360022635852-Transfer

        response = self.resp(req)
        return response


    def withdraw(self, volume):

        req = self.withdraw_req(volume)
        return self.withdraw_resp(req)

    def withdraw_req(self, volume):
        # https://support.kraken.com/hc/en-us/articles/360028105972-Withdrawal-to-Spot-Wallet
        '''will send btc to kraken spot wallet, we dont need to specify an adress'''

        if not isinstance(volume, Money) or volume.currency != self.volume_currency:
            raise TypeError('Withdrawal volume must be in %s' % self.volume_currency)

        volume += self.withdrawal_fee
        payload = {
            'currency': 'XBT',
            'amount': volume.amount,
            }
        return self.req('post', '/withdrawal', data=payload)

    def withdraw_resp(self, req):
        # https://support.kraken.com/hc/en-us/articles/360028105972-Withdrawal-to-Spot-Wallet

        response = self.resp(req)
        return response



    def get_order_audit_data(self, skip_recent=0, lookback_hours=2):
        # ! not done yet

        """
        Returns an OrderedDict of order ids mapped to their filled volume (including
        only orders that have some trades).
        """
        raw_orders = []
        start = Delorean().last_hour(lookback_hours).epoch

        offset = 0
        count, raw_chunk = self.closed_orders(start)
        raw_orders += raw_chunk
        offset += len(raw_chunk)

        while offset < count:
            logger.info('%s orders fetched, %s remaining' % (offset, count - offset))
            _, raw_chunk = self.closed_orders(start, offset=offset)
            raw_orders += raw_chunk
            offset += len(raw_chunk)

        raw_orders = raw_orders[skip_recent:]

        orders = OrderedDict()

        for raw_order in raw_orders:
            volume_executed = Money(raw_order['vol_exec'], 'BTC')

            if volume_executed > 0:
                order_id = raw_order['order_id']
                orders[order_id] = volume_executed

        return orders

    def fiat_deposit_fee(self, deposit_amount):
        # ! not done yet

        return Money('5', 'EUR')



# ===================================================================================================================================
# ===== Below code should not be needed

    @classmethod
    def construct_pair(cls, fiat_currency):
        btc_currency_code = cls.convert_to_kraken_currency('BTC')
        fiat_currency_code = cls.convert_to_kraken_currency(fiat_currency)

        return btc_currency_code + fiat_currency_code

    @classmethod
    def convert_from_kraken_currency(cls, kraken_currency):
        if kraken_currency == 'XBT':
            currency = 'BTC'
        elif kraken_currency[0] == 'Z':
            currency = kraken_currency[1:]

        if currency not in Money.CURRENCIES:
            raise ValueError('invalid currency value: \'%s\'' % currency)

        return currency

    @classmethod
    def convert_to_kraken_currency(cls, currency):
        # symbol of kraken perps for btc/usd => pi_xbtusd

        if currency == 'BTC':
            kraken_currency = 'XBT'
        else:
            kraken_currency = 'Z' + currency

        return kraken_currency
