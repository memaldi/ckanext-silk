from sqlalchemy import types, Column, Table, MetaData, UnicodeText, create_engine, Integer, ForeignKey
import vdm.sqlalchemy
from sqlalchemy.orm import mapper, relationship
from pylons import config
import sqlalchemy

metadata = MetaData()

## Our Domain Object Tables
linkage_rule_table = Table('linkage_rule', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', UnicodeText, nullable=False),
        Column('orig_dataset_id', UnicodeText, nullable=False),
        Column('orig_resource_id', UnicodeText, nullable=False),
        Column('dest_dataset_id', UnicodeText, nullable=False),
        Column('dest_resource_id', UnicodeText, nullable=False),
)

class LinkageRule(object):
    
    def __init__(self, name, orig_dataset_id, orig_resource_id, dest_dataset_id, dest_resource_id):
        self.name = name
        self.orig_dataset_id = orig_dataset_id
        self.orig_resource_id = orig_resource_id
        self.dest_dataset_id = dest_dataset_id
        self.dest_resource_id = dest_resource_id


restriction_table = Table('restriction', metadata,
        Column('id', Integer, primary_key=True),
        Column('resource_id', UnicodeText, nullable=False),
        Column('property', UnicodeText, nullable=False),
        Column('linkage_rule_id', Integer, ForeignKey('linkage_rule.id')),
)

class Restriction(object):
    
    def __init__(self, id, resource_id, property, linkage_rule_id):
        self.id = id
        self.resource_id = resource_id
        self.property = property
        self.linkage_rule_id = linkage_rule_id

mapper(LinkageRule, linkage_rule_table, properties={'restrictions': relationship(Restriction, backref='linkage_rule', order_by=restriction_table.c.id)})
mapper(Restriction, restriction_table)


#engine = create_engine('postgresql://ckanuser:pass@localhost/ckantest')
#metadata.create_all(engine)
