from sqlalchemy import types, Column, Table
import vdm.sqlalchemy

## Our Domain Object Tables
linkage_rule_table = Table('package', meta.metadata,
        Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
        Column('name', types.UnicodeText, nullable=False),
        Column('orig_dataset_id', types.UnicodeText, nullable=False),
        Column('orig_resource_id', types.UnicodeText, nullable=False),
        Column('dest_dataset_id', types.UnicodeText, nullable=False),
        Column('dest_resource_id', types.UnicodeText, nullable=False),
)

vdm.sqlalchemy.make_table_stateful(package_table)
package_revision_table = core.make_revisioned_table(package_table)

#Mira en dictization
class Package(vdm.sqlalchemy.RevisionedObjectMixin, vdm.sqlalchemy.StatefulObjectMixin, domain_object.DomainObject):
    
    text_search_fields = ['name']

    def __init__(self, **kw):
        pass
