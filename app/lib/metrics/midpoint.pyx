"""
Simple functions to find the "midpoint" of an orderbook given various definitions.
"""
from __future__ import division

from past.utils import old_div
import lib.metrics.quote as quote_lib
from lib.exchange.consts import Consts                                      #pyx file
from lib.money import Money

DEFAULT_QUOTE_DEPTH = '10'


class OrderbookSizeException(Exception):
    pass


def get_midpoint_from_orderbook(orderbook, depth=None):
    """
    A simple function to find the midpoint at a given depth specified in the orderbook's
    volume currency.

    Returns a USD Money.
    """

    try:
        if depth is None:
            vol_currency = orderbook['asks'][0].volume.currency

            depth = Money(DEFAULT_QUOTE_DEPTH, vol_currency)

        bid_quote = old_div(quote_lib.price_quote_from_orderbook(
            orderbook,
            Consts.BID,
            depth,
        )['total_price'], depth.amount)

        ask_quote = old_div(quote_lib.price_quote_from_orderbook(
            orderbook,
            Consts.ASK,
            depth,
        )['total_price'], depth.amount)
    except:
        raise OrderbookSizeException

    return old_div((bid_quote + ask_quote), 2)
