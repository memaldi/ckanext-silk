from ckanext.silk.model.__init__ import Configuration

from sqlalchemy import create_engine

USER = 'ckanuser'
PASS = 'pass'

print 'Creating table for silk storage'
engine = create_engine('postgresql://%s:%s@localhost/ckantest' % (USER, PASS), echo=True)
property_model.metadata.drop_all(engine)
property_model.metadata.create_all(engine)
