from ckanext.silk.model.__init__ import Configuration

from sqlalchemy import create_engine

USER = 'ckanuser'
PASS = 'pass'

from ckanext.silk.model.__init__ import Configuration

Configuration.create_db(USER, PASS)
