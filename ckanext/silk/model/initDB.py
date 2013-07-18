import integration_model
from sqlalchemy import create_engine

USER = 'ckanuser'
PASS = 'pass'

print 'Creating table for metadata property storage'
engine = create_engine('postgresql://%s:%s@localhost/ckantest' % (USER, PASS), echo=True)
integration_model.metadata.drop_all(engine)
integration_model.metadata.create_all(engine)
