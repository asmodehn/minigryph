"""
Simple function to get the quote for a desired market order from an orderbook. This is
useful in a variety of ways and places.
"""


from lib.money import Money
from lib.exchange.consts import Consts                                      #pyx file


def price_quote_from_orderbook(orderbook, mode, volume):
    if mode == Consts.BID:
        orders = orderbook.get('asks', [])
    elif mode == Consts.ASK:
        orders = orderbook.get('bids', [])
    else:
        raise ValueError('mode must be one of ask/bid')

    if not isinstance(volume, Money):
        raise ValueError('Volume must be a Money() object')

    if volume.currency != orders[0].volume.currency:
        raise ValueError('Volume currency does not match orderbook currency! %s != %s' % (
            volume.currency,
            orders[0].volume.currency,
        ))

    if not orders:
        raise Exception('no orders on one side of the book.')

    price = 0
    volume_remaining = volume

    for order in orders:
        volume_from_this_order = order.volume

        if order.volume > volume_remaining:
            volume_from_this_order = volume_remaining

        volume_remaining -= volume_from_this_order
        price += (volume_from_this_order.amount * order.price)

        if volume_remaining <= 0:
            break

    last_order = order  # Because the loop broke.

    if volume_remaining > 0:
        raise Exception('not enough liquidity for a %s %s' % (volume, mode))

    response = {
        'total_price': price,
        'price_for_order': last_order.price,
    }

    return response

