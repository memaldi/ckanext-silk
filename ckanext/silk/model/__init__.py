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
        Column('variable_name', UnicodeText, nullable=False),
        Column('property', UnicodeText, nullable=False),
        Column('class_name', UnicodeText, nullable=False),
        Column('linkage_rule_id', Integer, ForeignKey('linkage_rule.id')),
)

class Restriction(object):
    
    def __init__(self, resource_id, variable_name, property, class_name, linkage_rule_id):
        self.resource_id = resource_id
        self.variable_name = variable_name
        self.property = property
        self.class_name = class_name
        self.linkage_rule_id = linkage_rule_id

path_input_table = Table('path_input', metadata,
        Column('id', Integer, primary_key=True),
        Column('restriction_id', Integer,ForeignKey('restriction.id')),
        Column('path_input', UnicodeText, nullable=False),
)

class PathInput(object):
    
    def __init__(self, restriction_id, path_input):
        self.restriction_id = restriction_id
        self.path_input = path_input
        
transformation_table = Table('transformation', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', UnicodeText, nullable=False),
)

class Transformation(object):
    
    def __init__(self, name):
        self.name = name
        
parameter_table = Table('parameter', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', UnicodeText, nullable=False),
        Column('value', UnicodeText, nullable=False),
        Column('transformation_id', Integer, ForeignKey('transformation.id')),
)        

class Parameter(object):
    
    def __init__ (self, name, value, transformation_id):
        self.name = name
        self.value = value
        self.transformation_id = transformation_id
        
transformation_path_inputs_association_table = Table('association_t_p', metadata,
        Column('transformation_id', Integer, ForeignKey('transformation.id')),
        Column('path_input_id', Integer, ForeignKey('path_input.id')),
)

mapper(PathInput, path_input_table)
mapper(Parameter, parameter_table)
mapper(Transformation, transformation_table, properties={'path_inputs': relationship(PathInput, secondary=transformation_path_inputs_association_table, backref='transformations'), 'parameters': relationship(Parameter, backref='transformation', order_by=parameter_table.c.id)})
mapper(Restriction, restriction_table, properties={'path_inputs': relationship(PathInput, backref='restriction', order_by=path_input_table.c.id)})
mapper(LinkageRule, linkage_rule_table, properties={'restrictions': relationship(Restriction, backref='linkage_rule', order_by=restriction_table.c.id)})



#engine = create_engine('postgresql://ckanuser:pass@localhost/ckantest')
#metadata.drop_all(engine)
#metadata.create_all(engine)
