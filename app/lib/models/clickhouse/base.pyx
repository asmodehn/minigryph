#!python
#cython: language_level=3
# -*- coding: utf-8 -*-

from builtins import str
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData

from clickhouse_sqlalchemy import Table, make_session, get_declarative_base, types, engines

Base = get_declarative_base()
metata = Base.metadata

def unicode_string(self):
    return str(self).encode('utf-8')

Base.__str__ == unicode_string   


# How to migrate a database

#   foreman run alembic revision --autogenerate -m "moved value to Text from String"
# This generates the change script
#
#   foreman run alembic upgrade head
# This Executes the latest change script.
