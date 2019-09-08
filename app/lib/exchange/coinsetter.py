# -*- coding: utf-8 -*-
from future import standard_library
standard_library.install_aliases()
import base64
import datetime
import hashlib
import hmac
import json
import math
import os
import requests
import time
import urllib.request, urllib.parse, urllib.error

# decimal import compatible with py2
try:
    from decimal import Decimal
except NameError:
    from cdecimal import Decimal

from collections import OrderedDict
from delorean import Delorean, parse
from urllib.parse import urlencode

from lib.exchange.consts import Consts
from lib.exchange.exchange_api_wrapper import ExchangeAPIWrapper
from lib.exchange.exceptions import *
from lib.exchange.exchange_order import Order
from lib.logger import get_logger
from lib.models.exchange import Balance
from lib.money import Money

logger = get_logger(__name__)


class CoinsetterExchange(ExchangeAPIWrapper):
    def __init__(self, session=None, use_cached_orderbook=False):
        super(CoinsetterExchange, self).__init__(session)
        self.name = u'COINSETTER'
        self.friendly_name = u'Coinsetter'
        self.base_url = 'https://api.coinsetter.com/v1'
        self.currency = "USD"
        self.fee = Decimal("0.002")
        self.market_order_fee = self.fee
        self.limit_order_fee = self.fee
        self.bid_string = "BUY"
        self.ask_string = "SELL"
        self.use_cached_orderbook = use_cached_orderbook
