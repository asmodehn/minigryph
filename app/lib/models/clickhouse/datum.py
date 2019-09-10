from __future__ import division
from builtins import str
from builtins import object
from past.utils import old_div
from collections import defaultdict
from datetime import datetime
import json
import uuid

# decimal import compatible with py2
try:
    from decimal import Decimal
except NameError:
    from cdecimal import Decimal

from sqlalchemy import Table, ForeignKey, Column, Integer, Unicode, DateTime, UnicodeText, Numeric, desc

from clickhouse_sqlalchemy import types, engines

from lib.models.base import Base                                                    #pyx file
from lib import session
from lib.singleton import Singleton
from future.utils import with_metaclass

metadata = Base.metadata


# clickhouse favours few but very wide tables 
# so we put all mysql tables from OG gryphon into one giant table
# we use arrays to replace tables, see : https://www.altinity.com/blog/2019/5/23/handling-variable-time-series-efficiently-in-clickhouse


# clickhouse also does not support foreign keys

class Wide(Base):

    # Basic Order
    # Datum 
    unique_id = Column(types.UUID, primary_key=True)
    time_created = Column(types.DateTime)
    datum_type = Column(types.String)
    numeric_value = Column(types.Float32)
    string_value = Column(types.Nullable(types.String))
    meta_data = Column(types.Nullable(types.String))
    order_id = Column(types.Nullable(types.Int32)) 
    # Event
    unique_id = Column(Unicode(64), nullable=False)
    event_id = Column(Integer, primary_key=True)
    time_created = Column(DateTime, nullable=False)
    exchange_name = Column(Unicode(256), nullable=False)
    event_type = Column(Unicode(256), nullable=False)
    data = Column(UnicodeText(length=2**31))
    # Exchange
    # Flag
    # Liability
    # Market Data
    # Order
    # Orderbook Snapshot
    # Ticker
    # Trade
    # Transaction





    # constructor style
    datum = Table('datum', metadata,
            Column('unique_id', types.UUID, primary_key=True), 
            Column('time_created', types.DateTime),
            Column('datum_type', types.String),
            Column('numeric_value', types.Float32),
            Column('string_value', types.Nullable(types.String)),
            Column('meta_data', types.Nullable(types.String)),
            Column('order_id', types.Nullable(types.Int32), foreign_key='order.order_id'),
            engines.Memory()


    )
    # end 
    

    __tablename__ = 'datum'

    unique_id = Column(Unicode(64), nullable=False)
    datum_id = Column(Integer, primary_key=True)
    time_created = Column(DateTime, nullable=False)
    datum_type = Column(Unicode(256), nullable=False)
    numeric_value = Column(Numeric(precision=20, scale=10))
    string_value = Column(Unicode(256))
    meta_data = Column(UnicodeText(length=2**31))

    order_id = Column(Integer, ForeignKey('order.order_id'), nullable=True)

    def __init__(self, datum_type, numeric_value=None, string_value=None, meta_data={}, order=None):
        self.time_created = datetime.utcnow()
        self.datum_type = datum_type
        self.numeric_value = numeric_value
        self.string_value = string_value
        self.unique_id = u'dat_%s' % str(uuid.uuid4().hex)
        self.meta_data = json.dumps(meta_data)
        self.order = order

    def __unicode__(self):
        return str(repr(self))

    def __repr__(self):
        d = {
            'datum_type': self.datum_type,
            'time_created': str(self.time_created),
            'meta_data': json.loads(self.meta_data),
        }
        if self.numeric_value:
            d.update({'numeric_value': str(self.numeric_value)})
        if self.string_value:
            d.update({'string_value': self.string_value})

        return json.dumps(d, ensure_ascii=False)


class DatumRecorder(with_metaclass(Singleton, object)):
    def create(self, db=None, logger=None):
        self.db = db
        self.external_logger = logger
        self.data_for_mean = defaultdict(list)

    def record(self, datum_type, numeric_value=None, string_value=None, meta_data={}, order=None):
        datum = Datum(
            datum_type,
            numeric_value=numeric_value,
            string_value=string_value,
            meta_data=meta_data,
            order=order,
        )

        if not hasattr(self, 'db') and not hasattr(self, 'external_logger'):
            raise Exception('DatumRecorder must be created before you can record')

        if self.db:
            self.db.add(datum)
            session.commit_mysql_session(self.db)
        elif self.external_logger:
            self.external_logger.info(datum)
        else:
            # we aren't recording events.
            pass

    def record_mean(self, datum_type, numeric_value, sample_size):
        """
        Store a datum with the mean of every <sample_size> data points.

        This has weird behaviour if two places call it with different sample_sizes.
        We should only have one DatumRecorder line per datum_type
        """
        if not hasattr(self, 'data_for_mean'):
            raise Exception('DatumRecorder must be created before you can record')

        data = self.data_for_mean[datum_type]
        data.append(numeric_value)

        if len(data) >= sample_size:
            mean = old_div(Decimal(sum(data)), Decimal(len(data)))
            self.record(datum_type, numeric_value=mean)
            # Clear the content of a referenced list
            del data[:]


class DatumRetriever(with_metaclass(Singleton, object)):
    @staticmethod
    def get(datum_type):
        db = session.get_a_trading_db_mysql_session()
        data = db.query(Datum).filter_by(
            datum_type=datum_type).order_by(
            desc(Datum.time_created)).all()
        return data
        
