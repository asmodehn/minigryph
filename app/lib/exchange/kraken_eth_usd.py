# decimal import compatible with py2
try:
    from decimal import Decimal
except NameError:
    from cdecimal import Decimal

from lib.exchange.kraken_eth_eur import KrakenETHEURExchange
from lib.logger import get_logger
from lib.money import Money

logger = get_logger(__name__)


# ! NOT FUNCTIONAL YET


class KrakenETHUSDExchange(KrakenETHEURExchange):
    def __init__(self, session=None, configuration=None):
        super(KrakenETHUSDExchange, self).__init__(session)

        self.name = u'KRAKEN_ETH_USD'
        self.friendly_name = u'Kraken ETH-USD'
        self.currency = 'USD'
        self.volume_currency = 'ETH'
        self.price_decimal_precision = 1 # As of Feb 2018

        # Updated by Gareth on 2016-9-20
        self.market_order_fee = Decimal('0.0024')
        self.limit_order_fee = Decimal('0.0014')
        self.fee = self.market_order_fee
        self.fiat_balance_tolerance = Money('0.0001', 'USD')
        self.volume_balance_tolerance = Money('0.000001', 'ETH')
        self.min_order_size = Money('0.02', 'ETH')
        self.max_tick_speed = 5
        self.use_cached_orderbook = False

        if configuration:
            self.configure(configuration)

    def load_creds(self):
        try:
            self.api_key
            self.secret
        except AttributeError:
            self.api_key = self._load_env('KRAKEN_ETH_USD_API_KEY')
            self.secret = self._load_env('KRAKEN_ETH_USD_API_SECRET')

