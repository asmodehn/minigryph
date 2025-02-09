# -*- coding: utf-8 -*-
from lib.exchange import exceptions


ALL_EXCHANGE_KEYS = [
    # 'bitstamp_btc_eur',
    # 'bitstamp_btc_usd',
    # 'bitstamp_eth_eur',
    # 'bitstamp_eth_usd',
    # 'bitstamp_eth_btc',
    # 'bitstamp_bch_btc',
    # 'bitstamp_bch_eur',
    # 'bitstamp_bch_usd',
    # 'bitfinex_btc_usd',
    # 'bitfinex_bch_usd', #! via ccwt wrapper
    # 'bitfinex_eth_usd', #! via ccxt wrapper
    # 'bitfinex_ltc_usd', #! via ccxt wrapper
    # 'bitfinex_zec_usd', #! via ccxt wrapper
    # 'bitfinex_xrp_usd', #! via ccxt wrapper
    'kraken_btc_eur',
    'kraken_btc_usd',
    # 'kraken_btc_cad',
    # 'kraken_bch_usd',   #! via ccxt wrapper
    # 'kraken_bch_eur',   #! via ccxt wrapper
    'kraken_eth_eur',   #! not added yet in test 
    'kraken_eth_usd',   #! not added yet in test
    # 'kraken_ltc_usd',   #! via ccxt wrapper
    # 'kraken_ltc_eur',   #! via ccxt wrapper
    # 'kraken_zec_usd',   #! via ccxt wrapper
    # 'kraken_zec_eur',   #! via ccxt wrapper
    # 'kraken_xrp_usd',   #! via ccxt wrapper
    # 'kraken_xrp_eur',   #! via ccxt wrapper
    # 'krakenfutures_btc_usd',
    # 'bitmex_btc_usd',   #! own file, but uses ccxt lib 
    # 'bitmex_eth_usd',   #! via ccxt wrapper
    # 'itbit_btc_usd',
    # 'okcoin_btc_usd',
    # 'coinbase_btc_usd',
    # 'quadriga_btc_cad',
    # 'gemini_btc_usd',
    # 'gemini_eth_btc',
    # 'gemini_eth_usd',
    # 'gemini_ltc_usd',
    # 'gemini_zec_usd',
]

HISTORICAL_EXCHANGE_KEYS = [
    'vaultofsatoshi_btc_cad',
    'bitme_btc_usd',
    'buttercoin_btc_usd',
    'cavirtex_btc_cad',
    'coinsetter_btc_usd',
]

BANK_ACCOUNT_KEYS = ['BMO_USD', 'BMO_CAD', 'BMO_CAD_OPS', 'BOA_MAIN', 'BOA_INCOME']


def all_exchanges():
    return [make_exchange_from_key(key) for key in ALL_EXCHANGE_KEYS]


def all_exchange_datas(db):
    return make_exchange_datas_from_keys(ALL_EXCHANGE_KEYS, db)

def all_bank_accounts(db):
    return make_exchange_datas_from_keys(BANK_ACCOUNT_KEYS, db)

def historical_exchanges():
    return [make_exchange_from_key(key) for key in HISTORICAL_EXCHANGE_KEYS]


def historical_exchange_datas(db):
    return make_exchange_datas_from_keys(HISTORICAL_EXCHANGE_KEYS, db)


def all_current_and_historical_exchanges():
    current_exchanges = all_exchanges()
    current_exchanges.extend(historical_exchanges())

    return current_exchanges


def canonical_key(key):
    key = key.upper()
    if key == 'VAULT':
        key = 'VAULTOFSATOSHI'
    if key == 'BUTTER':
        key = 'BUTTERCOIN'

    return key


def map_pair_name_to_exchange_name(pair_name):
    """
    We're preparing to add the notion that exchanges can have multiple trading pairs
    into our system. Each exchange is going to have a single ExchangeData db object but
    have one wrapper for each pair. Order.exchange_name is going to refer to the pair,
    but most accounting functions take place on the ExchangeData object. Thus, we need
    a mapping of ExchangeWrapper -> ExchangeData. This function will serve that purpose
    for now.

    To add a master-slave relationship to a pair, add a line like this:
        if pair_name == 'GEMINI_ETH_USD':  # [slave pair]
            return 'GEMINI_BTC_USD'  # [master pair]
    """
    return pair_name


def make_exchange_from_key(key):
    key = canonical_key(key)

    api_wrapper_class = get_api_wrapper_class_by_name(key)

    return api_wrapper_class()


def make_exchange_data_from_key(key, db):
    keys = [key]
    exchange_datas = make_exchange_datas_from_keys(keys, db)

    assert len(exchange_datas) == 1

    return exchange_datas[0]


def initialized_ledgers(db):
    """
    Give us the names of the exchanges that have initialized ledgers in our trading
    database.
    """
    from lib.models.mysql.exchange import Exchange as ExchangeData

    exchange_account_names = db.query(ExchangeData.name).all()
    exchange_account_names = [e[0] for e in exchange_account_names]

    return exchange_account_names


def get_all_initialized_exchange_wrappers(db):
    from lib.models.mysql.exchange import Exchange as ExchangeData

    exchange_accounts = db.query(ExchangeData).all()

    exchange_wrappers = [
        make_exchange_from_key(e.name) for e in exchange_accounts
        if e.name.lower() in ALL_EXCHANGE_KEYS
    ]

    return exchange_wrappers


def make_exchange_datas_from_keys(pair_names, db):
    from lib.models.mysql.exchange import Exchange as ExchangeData

    canonical_pair_names = [canonical_key(k) for k in pair_names]
    exchange_names = [map_pair_name_to_exchange_name(p) for p in canonical_pair_names]

    exchange_datas = db.query(ExchangeData)\
        .filter(ExchangeData.name.in_(exchange_names))\
        .all()

    assert len(exchange_datas) == len(pair_names)

    return [exchange_datas[0]]


def get_api_wrapper_class_by_name(exchange_name):
    exchange_name = canonical_key(exchange_name)

    # if exchange_name == 'BITSTAMP_BTC_USD':
    #     from lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
    #     return BitstampBTCUSDExchange
    # elif exchange_name == 'BITSTAMP_ETH_EUR':
    #     from lib.exchange.bitstamp_eth_eur import BitstampETHEURExchange
    #     return BitstampETHEURExchange
    # elif exchange_name == 'BITSTAMP_ETH_USD':
    #     from lib.exchange.bitstamp_eth_usd import BitstampETHUSDExchange
    #     return BitstampETHUSDExchange
    # elif exchange_name == 'BITSTAMP_ETH_BTC':
    #     from lib.exchange.bitstamp_eth_btc import BitstampETHBTCExchange
    #     return BitstampETHBTCExchange
    # elif exchange_name == 'BITSTAMP_ETH_EUR':
    #     from lib.exchange.bitstamp_eth_eur import BitstampETHEURExchange
    #     return BitstampETHEURExchange
    # elif exchange_name == 'BITSTAMP_BTC_EUR':
    #     from lib.exchange.bitstamp_btc_eur import BitstampBTCEURExchange
    #     return BitstampBTCEURExchange
    # elif exchange_name == 'BITSTAMP_BCH_BTC':
    #     from lib.exchange.bitstamp_bch_btc import BitstampBCHBTCExchange
    #     return BitstampBCHBTCExchange
    # elif exchange_name == 'BITSTAMP_BCH_USD':
    #     from lib.exchange.bitstamp_bch_usd import BitstampBCHUSDExchange
    #     return BitstampBCHUSDExchange
    # elif exchange_name == 'BITSTAMP_BCH_EUR':
    #     from lib.exchange.bitstamp_bch_eur import BitstampBCHEURExchange
    #     return BitstampBCHEURExchange
    #! DONT FORGET TO CHANGE BELOW BACK TO ELIF
    if exchange_name == 'KRAKEN_BTC_EUR':
        from lib.exchange.kraken_btc_eur import KrakenBTCEURExchange
        return KrakenBTCEURExchange
    elif exchange_name == 'KRAKEN_BTC_USD':
        from lib.exchange.kraken_btc_usd import KrakenBTCUSDExchange
        return KrakenBTCUSDExchange
    # elif exchange_name == 'KRAKEN_BTC_CAD':
    #     from lib.exchange.kraken_btc_cad import KrakenBTCCADExchange
    #     return KrakenBTCCADExchange
    # elif exchange_name == 'KRAKEN_BCH_EUR':     
    #     from gryphon.lib.exchange.ccxt_wrapper import KrakenBCHEURExchange
    #     return KrakenBCHEURExchange
    # elif exchange_name == 'KRAKEN_BCH_USD':     
    #     from gryphon.lib.exchange.ccxt_wrapper import KrakenBCHUSDExchange
    #     return KrakenBCHUSDExchange
    # elif exchange_name == 'KRAKEN_LTC_EUR':     
    #     from gryphon.lib.exchange.ccxt_wrapper import KrakenLTCEURExchange
    #     return KrakenLTCEURExchange
    # elif exchange_name == 'KRAKEN_LTC_USD':     
    #     from gryphon.lib.exchange.ccxt_wrapper import KrakenLTCUSDExchange
    #     return KrakenLTCUSDExchange
    elif exchange_name == 'KRAKEN_ETH_EUR':     
        from lib.exchange.kraken_eth_eur import KrakenETHEURExchange
        return KrakenETHEURExchange
    elif exchange_name == 'KRAKEN_ETH_USD':     
        from lib.exchange.kraken_eth_usd import KrakenETHUSDExchange
        return KrakenETHUSDExchange
    # elif exchange_name == 'KRAKEN_ZEC_EUR':     
    #     from gryphon.lib.exchange.ccxt_wrapper import KrakenZECEURExchange
    #     return KrakenZECEURExchange
    # elif exchange_name == 'KRAKEN_ZEC_USD':     
    #     from lib.exchange.ccxt_wrapper import KrakenZECUSDExchange
    #     return KrakenZECUSDExchange
    # elif exchange_name == 'KRAKEN_XRP_EUR':     
    #     from gryphon.lib.exchange.ccxt_wrapper import KrakenXRPEURExchange
    #     return KrakenXRPEURExchange
    # elif exchange_name == 'KRAKEN_XRP_USD':     
    #     from lib.exchange.ccxt_wrapper import KrakenXRPUSDExchange
    #     return KrakenXRPUSDExchange
    # elif exchange_name == 'KRAKENFUTURES_BTC_USD':     
    #     from lib.exchange.krakenfutures_btc_usd import KrakenFuturesBTCUSDExchange
    #     return KrakenFuturesBTCUSDExchange
    # elif exchange_name == 'BITMEX_BTC_USD':     
    #     from lib.exchange.bitmex_btc_usd import BitmexBTCUSDExchange
    #     return BitmexBTCUSDExchange
    # elif exchange_name == 'BITMEX_ETH_USD':     
    #     from lib.exchange.ccxt_wrapper import BitmexETHUSDExchange
    #     return BitmexETHUSDExchange
    # elif exchange_name == 'BITFINEX_BTC_USD':
    #     from lib.exchange.bitfinex_btc_usd import BitfinexBTCUSDExchange
    #     return BitfinexBTCUSDExchange
    # # elif exchange_name == 'BITFINEX_BCH_USD':   
    # #     from gryphon.lib.exchange.ccxt_wrapper import BitfinexBCHUSDExchange
    # #     return BitfinexBCHUSDExchange
    # elif exchange_name == 'BITFINEX_ETH_USD':   
    #     from gryphon.lib.exchange.ccxt_wrapper import BitfinexETHUSDExchange
    #     return BitfinexETHUSDExchange
    # elif exchange_name == 'BITFINEX_LTC_USD':   
    #     from gryphon.lib.exchange.ccxt_wrapper import BitfinexLTCUSDExchange
    #     return BitfinexLTCUSDExchange
    # elif exchange_name == 'BITFINEX_ZEC_USD':
    #     from gryphon.lib.exchange.ccxt_wrapper import BitfinexZECUSDExchange
    #     return BitfinexZECUSDExchange
    # elif exchange_name == 'BITFINEX_XRP_USD':
    #     from gryphon.lib.exchange.ccxt_wrapper import BitfinexXRPUSDExchange
    #     return BitfinexXRPUSDExchange
    # elif exchange_name == 'ITBIT_BTC_USD':
    #     from lib.exchange.itbit_btc_usd import ItbitBTCUSDExchange
    #     return ItbitBTCUSDExchange
    # elif exchange_name == 'OKCOIN_BTC_USD':
    #     from lib.exchange.okcoin_btc_usd import OKCoinBTCUSDExchange
    #     return OKCoinBTCUSDExchange
    # elif exchange_name == 'QUADRIGA_BTC_CAD':
    #     from lib.exchange.quadriga_btc_cad import QuadrigaBTCCADExchange
    #     return QuadrigaBTCCADExchange
    # elif exchange_name == 'COINBASE_BTC_USD':
    #     from lib.exchange.coinbase_btc_usd import CoinbaseBTCUSDExchange
    #     return CoinbaseBTCUSDExchange
    # elif exchange_name == 'GEMINI_BTC_USD':
    #     from lib.exchange.gemini_btc_usd import GeminiBTCUSDExchange
    #     return GeminiBTCUSDExchange
    # elif exchange_name == 'GEMINI_ETH_USD':
    #     from lib.exchange.gemini_eth_usd import GeminiETHUSDExchange
    #     return GeminiETHUSDExchange
    # elif exchange_name == 'GEMINI_ETH_BTC':
    #     from lib.exchange.gemini_eth_btc import GeminiETHBTCExchange
    #     return GeminiETHBTCExchange
    # elif exchange_name == 'GEMINI_LTC_USD':
    #     from lib.exchange.gemini_ltc_usd import GeminiLTCUSDExchange
    #     return GeminiLTCUSDExchange
    # elif exchange_name == 'GEMINI_ZEC_USD':
    #     from lib.exchange.gemini_zec_usd import GeminiZECUSDExchange
    #     return GeminiZECUSDExchange
    # elif exchange_name == 'POLONIEX_ETH_BTC':
    #     from lib.exchange.poloniex_eth_btc import PoloniexETHBTCExchange
    #     return PoloniexETHBTCExchange
    else:
        raise exceptions.ExchangeNotIntegratedError(exchange_name)

