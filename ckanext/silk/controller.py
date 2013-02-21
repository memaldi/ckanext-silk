from pylons import config
from ckan.plugins import SingletonPlugin, IPackageController, implements
from ckan.lib.base import BaseController, render, c, model, g, request
from logging import getLogger
from ckan.logic import NotAuthorized, check_access, get_action
import urllib
import ckan
import json
from rdflib import Graph
import ckanext.datastore.logic.action as action
from ckan.lib.plugins import lookup_package_plugin
from ckanext.silk.model import LinkageRule, Restriction, PathInput, Transformation, Parameter, Comparison, ComparisonParameters
from xml.dom.minidom import Document
import uuid
from ckan.lib.celery_app import celery

log = getLogger(__name__)

class SilkController(BaseController):
          
    prefixes = {}
          
    def __before__(self, action, **env):
        BaseController.__before__(self, action, **env)
        try:
            context = {'model': model, 'user': c.user or c.author}
            check_access('site_read', context)
        except NotAuthorized:
            if c.action not in ('login', 'request_reset', 'perform_reset',):
                abort(401, _('Not authorized to see this page'))

    ## hooks for subclasses
    new_user_form = 'silk/main_form.html'
    #edit_user_form = 'user/edit_user_form.html'
        
    def get_resources(self, value):
        c.dest_package_id = value
        data_dict = {
                'q': '*:*',
                'facet.field': g.facets,
                'rows': 0,
                'start': 0,
                'fq': 'capacity:"public"',
                'id': c.dest_package_id
            }
        context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author}
        package = ckan.logic.get_action('package_show')(
                    context, data_dict)
        
        return_html = ''
        if len(package['resources']) > 0:
            if package['resources'][0]['format'] in ['api/sparql', 'application/rdf+xml']:
                for resource in package['resources']:
                    return_html += '<option value="%s">%s</option>' % (resource['id'], resource['name'])
        
        return return_html
        
    def get_classes(self, property, resource_url):
        unquoted_property = urllib.unquote(property)
        resource_url = urllib.unquote(resource_url)
        json_result = None
        
        sparql_query = 'SELECT DISTINCT ?class WHERE { [] <%s> ?class } ORDER BY ?class' % unquoted_property
        params = urllib.urlencode({'query': sparql_query, 'format': 'application/json'})
        f = urllib.urlopen(resource_url, params)
        json_result = json.loads(f.read())
        output_html = '''
                            <label class="control-label" for="classes">Classes:</label>
                            <div class="controls">
                            <select id="class_select" name="class_select">
        '''
        
        if json_result != None:
            bindings = json_result['results']['bindings']
            for binding in bindings:
                value = binding['class']['value']
                output_html += '<option value="%s">%s</option>' % (value, value)
        output_html += '''</select>
                    </div>'''        
        return output_html
        
    def get_linkage_rules(self, id):
        linkage_rules = model.Session.query(LinkageRule).filter_by(orig_dataset_id=id).order_by('id').all()
        
        linkage_rules_list= []
        
        for linkage_rule in linkage_rules:
            linkage_rules_list.append({'id': linkage_rule.id, 'name': linkage_rule.name, 'orig_dataset_id': linkage_rule.orig_dataset_id, 'orig_resource_id': linkage_rule.orig_resource_id, 'dest_dataset_id': linkage_rule.dest_dataset_id, 'dest_resource_id': linkage_rule.dest_resource_id})
        
        return linkage_rules, linkage_rules_list
       
        
    # Aqui empieza lo bueno
    
    def save(self, id, params, linkage_rule_id=None):
        session = model.Session
        log.info(params)
        if linkage_rule_id == -1:
            linkage_rule = LinkageRule(params['new_linkage_rule_name'], id, params['resource_id'], params['dest_package_id'], params['dest_resource_id'], params['link_type'])
            session.add(linkage_rule)
        else:
            linkage_rule = session.query(LinkageRule).filter_by(id=linkage_rule_id).first()
            linkage_rule.name = params['new_linkage_rule_name']
            linkage_rule.orig_resource_id = params['resource_id']
            linkage_rule.dest_dataset_id = params['dest_package_id']
            linkage_rule.dest_resource_id = params['dest_resource_id']
            linkage_rule.link_type = params['link_type']
            #session.update(linkage_rule)
            
        session.commit()
        
    
    def read(self, id):
        #TODO: arreglar esto con params
        log.info(request.params)
       
        if (len(request.params) > 0):
            if request.params['save'] == 'Save':
                self.save(id, request.params, request.params['linkage_rule_id'])
                

        
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
                   
        data_dict = {'id': id}
        
        c.pkg_dict = get_action('package_show')(context, data_dict)
        c.pkg = context['package']
                
        linkage_rules, linkage_rules_list = self.get_linkage_rules(c.pkg_dict['name'])
        
        c.pkg_dict['linkage_rules'] = linkage_rules_list
        c.id = id
                
        return render('silk/read.html')
        
    def edit_linkage_rules(self, id, linkage_rule_id=None):
        '''Hook method made available for routing purposes.'''

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
        
        data_dict = {'id': id}
        
        c.pkg_dict = get_action('package_show')(context, data_dict)
        c.pkg = context['package']
                
        c.valid_resources = []
        
        for resource in c.pkg_dict['resources']:
            if resource['format'] in ['api/sparql']:
                c.valid_resources.append((resource['id'], resource['name']))
        
        data_dict = {}
        
        package_list = ckan.logic.get_action('package_list')(
            context, data_dict)
            
        c.dest_packages = []
        
        for package_id in package_list:
            data_dict = {'id': package_id}
            package = get_action('package_show')(context, data_dict)
            resources = package['resources']
            valid = False
            
            for resource in resources:
                if resource['format'] in ['api/sparql']:
                    valid = True
                    break
                    
            if valid:
                c.dest_packages.append((package['title'], package['name']))
        
        
        linkage_rules, linkage_rules_list = self.get_linkage_rules(c.pkg_dict['name'])
        
        c.linkage_rule_dict = {'id': '', 'name': '', 'orig_dataset_id': '', 'orig_resource_id': '', 'dest_dataset_id': '', 'dest_resource_id': ''}
        
        if linkage_rule_id != 'new':
            linkage_rule = model.Session.query(LinkageRule).filter_by(id=linkage_rule_id).first()
            c.linkage_rule_dict = {'id': linkage_rule.id, 'name': linkage_rule.name, 'orig_dataset_id': linkage_rule.orig_dataset_id, 'orig_resource_id': linkage_rule.orig_resource_id, 'dest_dataset_id': linkage_rule.dest_dataset_id, 'dest_resource_id': linkage_rule.dest_resource_id, 'link_type': linkage_rule.link_type}
            c.dest_resources = []
            data_dict = {'id': linkage_rule.dest_dataset_id}
            dest_package = get_action('package_show')(context, data_dict)
            for resource in dest_package['resources']:
                c.dest_resources.append((resource['id'], resource['name']))            
        
        c.pkg_dict['linkage_rules'] = linkage_rules_list
        
        c.form = render('silk/linkage_rule_form.html')
        
        return render('silk/edit_linkage_rules.html')
        
    def resource_read(self, id, linkage_rule_id, object=None, object_id=None):
        
        log.info('Params: %s' % request.params)
        
        #TODO: Seguro que hay una manera mas elegante
        if len(request.params) > 0:
            if 'restriction-save' in request.params:
                if request.params['restriction-save'] == 'true':
                    self.save_restriction(request.params, linkage_rule_id)
            elif 'pathinput-save' in request.params:
                if request.params['pathinput-save'] == 'true':
                    self.save_path_input(request.params, linkage_rule_id)
            elif 'transformation-save' in request.params:
                if request.params['transformation-save'] == 'true':
                    self.save_transformation(request.params, linkage_rule_id)
            elif 'comparison-save' in request.params:
                if request.params['comparison-save'] == 'true':
                    self.save_comparison(request.params, linkage_rule_id)
            elif 'aggregation-save' in request.params:
                if request.params['aggregation-save'] == 'true':
                    self.save_aggregation(request.params, linkage_rule_id)
                    
        log.info('Object id %s' % object_id)
        if object == 'deletepathinput':
            self.path_input_delete(object_id)
        elif object == 'deletecomparison':
            self.comparison_delete(object_id)
        
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
                   
        data_dict = {'id': id}
        
        c.pkg_dict = get_action('package_show')(context, data_dict)
        c.pkg = context['package']

        linkage_rules = model.Session.query(LinkageRule).filter_by(orig_dataset_id=c.pkg_dict['name'])
        
        linkage_rules_list = []
        
        for linkage_rule in linkage_rules:
            linkage_rules_list.append({'id': linkage_rule.id, 'name': linkage_rule.name, 'orig_dataset_id': linkage_rule.orig_dataset_id, 'orig_resource_id': linkage_rule.orig_resource_id, 'dest_dataset_id': linkage_rule.dest_dataset_id, 'dest_resource_id': linkage_rule.dest_resource_id})
                
        c.pkg_dict['linkage_rules'] = linkage_rules_list

        linkage_rule = model.Session.query(LinkageRule).filter_by(id=linkage_rule_id).first()
        log.info(linkage_rule.dest_dataset_id)
        c.linkage_rule_dict = {'id': linkage_rule.id, 'name': linkage_rule.name, 'orig_dataset_id': linkage_rule.orig_dataset_id, 'orig_resource_id': linkage_rule.orig_resource_id, 'dest_dataset_id': linkage_rule.dest_dataset_id, 'dest_resource_id': linkage_rule.dest_resource_id}

        data_dict = {'id': linkage_rule.orig_resource_id}
        c.orig_resource = ckan.logic.get_action('resource_show')(context, data_dict)
                    
        data_dict = {'id': linkage_rule.dest_dataset_id}
        c.dest_pkg_dict = get_action('package_show')(context, data_dict)
        
        data_dict = {'id': linkage_rule.dest_resource_id}
        c.dest_resource = ckan.logic.get_action('resource_show')(context, data_dict)

        c.orig_restrictions_list = []
        c.dest_restrictions_list = []
        restrictions = linkage_rule.restrictions
        
        orig_path_inputs = []
        dest_path_inputs = []
        
        #TODO: arreglar esto
        for restriction in restrictions:
            if restriction.resource_id == c.orig_resource['id']:
                c.orig_restrictions_list.append({'id': restriction.id, 'resource_id': restriction.resource_id, 'variable_name': restriction.variable_name, 'property': restriction.property, 'class_name': restriction.class_name, 'linkage_rule_id': restriction.linkage_rule_id})
                orig_path_inputs = restriction.path_inputs
                c.orig_variable_name = restriction.variable_name
            elif restriction.resource_id == c.dest_resource['id']:
                c.dest_restrictions_list.append({'id': restriction.id, 'resource_id': restriction.resource_id, 'variable_name': restriction.variable_name, 'property': restriction.property, 'class_name': restriction.class_name, 'linkage_rule_id': restriction.linkage_rule_id})
                dest_path_inputs = restriction.path_inputs
                c.dest_variable_name = restriction.variable_name
                
        c.orig_path_inputs_list = []
        c.dest_path_inputs_list = []
        c.transformation_list = []
        c.comparison_list = []
        
        for path_input in orig_path_inputs:
            path_input_comparisons = path_input.comparisons
            path_input_comparison_list = []
            for comparison in path_input_comparisons:
                comparison_dict = {'id': comparison.id, 'distance_measure': comparison.distance_measure, 'threshold': comparison.threshold, 'required': comparison.required, 'weight': comparison.weight}
                c.comparison_list.append(comparison_dict)
                
            transformations = path_input.transformations
            for transformation in transformations:
                
                transformation_comparisons = transformation.comparisons
                for comparison in transformation_comparisons:
                    comparison_dict = {'id': comparison.id, 'distance_measure': comparison.distance_measure, 'threshold': comparison.threshold, 'required': comparison.required, 'weight': comparison.weight}
                    if comparison_dict not in c.comparison_list:
                        c.comparison_list.append(comparison_dict)
                
                parameters = transformation.parameters
                transformation_dict = {'id': transformation.id, 'name': transformation.name}
                #transformation_dict['comparisons'] = path_input_comparison_list
                parameter_list = []
                for parameter in parameters:
                    parameter_list.append({'id': parameter.id, 'name': parameter.name, 'value': parameter.value})
                transformation_dict['parameters'] = parameter_list
                
                transformation_path_inputs = transformation.path_inputs
                transformation_path_input_list = []
                for path_input in transformation_path_inputs:
                    path_input_dict = {'id': path_input.id, 'path_input': path_input.path_input, 'variable_name': c.orig_variable_name}
                    transformation_path_input_list.append(path_input_dict)
                transformation_dict['path_inputs'] = transformation_path_input_list
                
                c.transformation_list.append(transformation_dict)
                
            #log.info('Transformation: %s' % transformations)
            log.info('Comparisons: %s' % c.comparison_list)
            c.orig_path_inputs_list.append({'id': path_input.id, 'restriction_id': path_input.restriction_id, 'path_input': path_input.path_input})
        
        for path_input in dest_path_inputs:
            path_input_comparisons = path_input.comparisons
            path_input_comparison_list = []
            for comparison in path_input_comparisons:
                comparison_dict = {'id': comparison.id, 'distance_measure': comparison.distance_measure, 'threshold': comparison.threshold, 'required': comparison.required, 'weight': comparison.weight}
                if comparison_dict not in c.comparison_list:
                    c.comparison_list.append(comparison_dict)
                
            transformations = path_input.transformations
            for transformation in transformations:
                
                transformation_comparisons = transformation.comparisons
                for comparison in transformation_comparisons:
                    comparison_dict = {'id': comparison.id, 'distance_measure': comparison.distance_measure, 'treshold': comparison.treshold, 'required': comparison.required, 'weight': comparison.weight}
                    if comparison_dict not in c.comparison_list:
                        c.comparison_list.append(comparison_dict)
                
                transformation_dict = {'id': transformation.id, 'name': transformation.name}
                #transformation_dict['comparisons'] = path_input_comparison_list
                parameters = transformation.parameters
                parameter_list = []
                for parameter in parameters:
                    parameter_list.append({'id': parameter.id, 'name': parameter.name, 'value': parameter.value})
                transformation_dict['parameters'] = parameter_list
                
                transformation_path_inputs = transformation.path_inputs
                transformation_path_input_list = []
                for path_input in transformation_path_inputs:
                    path_input_dict = {'id': path_input.id, 'path_input': path_input.path_input, 'variable_name': c.dest_variable_name}
                    transformation_path_input_list.append(path_input_dict)
                transformation_dict['path_inputs'] = transformation_path_input_list
                
                if transformation_dict not in c.transformation_list:
                    c.transformation_list.append(transformation_dict)
            
            #log.info('Transformation: %s' % transformations)
            c.dest_path_inputs_list.append({'id': path_input.id, 'restriction_id': path_input.restriction_id, 'path_input': path_input.path_input})
        
        new_comparison_list = []
        for comparison in c.comparison_list:
            log.info('Comparison: %s' % comparison)
            comparison_object = model.Session.query(Comparison).filter_by(id=comparison['id']).first()
            params = comparison_object.parameters
            param_list = []
            for param in params:
                 param_dict = {'id': param.id, 'name': param.name, 'value': param.value}
                 param_list.append(param_dict)
            comparison['params'] = param_list
            new_comparison_list.append(comparison)
            
        
        c.comparison_list = new_comparison_list
        #log.info(c.transformation_list)
        
        c.aggregation_list = []
        
        if linkage_rule.aggregation != None:
            c.aggregation_list.append(linkage_rule.aggregation)
        
        c.restrictions_control = False
        c.path_inputs_control = False
        
        c.launch_control = False
        
        if (len(c.comparison_list) > 0 and len(c.comparison_list) <= 1) or (len(c.comparison_list) > 1 and len(c.aggregation_list) >= 1):
            c.launch_control = True
            
        if len(c.orig_restrictions_list) > 0 and len(c.dest_restrictions_list) > 0:
            c.restrictions_control = True

        if len(c.orig_path_inputs_list) > 0 and len(c.dest_path_inputs_list) > 0:
            c.path_inputs_control = True        

        return render('silk/read_linkage_rule.html')
        
    def save_restriction(self, params, linkage_rule_id):
        restriction = Restriction(params['resource_id'], params['variable_name'], params['restriction'], params['class_select'], linkage_rule_id)
        linkage_rule = model.Session.query(LinkageRule).filter_by(id=linkage_rule_id).first()
        
        linkage_rule.restrictions.append(restriction)
        model.Session.add(restriction)
        model.Session.commit()
        
    def restriction_edit(self, linkage_rule_id, dataset):
          
        c.dataset = dataset
        linkage_rule = model.Session.query(LinkageRule).filter_by(id=linkage_rule_id).first()
        c.linkage_rule_dict = {'id': linkage_rule.id, 'name': linkage_rule.name, 'orig_dataset_id': linkage_rule.orig_dataset_id, 'orig_resource_id': linkage_rule.orig_resource_id, 'dest_dataset_id': linkage_rule.dest_dataset_id, 'dest_resource_id': linkage_rule.dest_resource_id}

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
                   
        if dataset == 'orig':
            pkg_id = linkage_rule.orig_dataset_id
            resource_id = linkage_rule.orig_resource_id
        else:
            pkg_id = linkage_rule.dest_dataset_id
            resource_id = linkage_rule.dest_resource_id
            
        data_dict = {'id': pkg_id}
        c.pkg_dict = get_action('package_show')(context, data_dict)
        c.pkg = context['package']
        
        data_dict = {'id': resource_id}
        c.resource_dict = get_action('resource_show')(context, data_dict)
        
        linkage_rules, linkage_rules_list = self.get_linkage_rules(linkage_rule.orig_dataset_id)
        c.id = linkage_rule.orig_dataset_id
        
        c.pkg_dict['linkage_rules'] = linkage_rules_list
        
        c.form = render('silk/restrictions_form.html')
            
        return render('silk/restrictions.html')

    def path_input_new(self, linkage_rule_id, dataset):
        c.dataset = dataset
        linkage_rule = model.Session.query(LinkageRule).filter_by(id=linkage_rule_id).first()
        c.linkage_rule_dict = {'id': linkage_rule.id, 'name': linkage_rule.name, 'orig_dataset_id': linkage_rule.orig_dataset_id, 'orig_resource_id': linkage_rule.orig_resource_id, 'dest_dataset_id': linkage_rule.dest_dataset_id, 'dest_resource_id': linkage_rule.dest_resource_id}

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
                   
        if dataset == 'orig':
            pkg_id = linkage_rule.orig_dataset_id
            resource_id = linkage_rule.orig_resource_id
        else:
            pkg_id = linkage_rule.dest_dataset_id
            resource_id = linkage_rule.dest_resource_id
            
        data_dict = {'id': pkg_id}
        c.pkg_dict = get_action('package_show')(context, data_dict)
        c.pkg = context['package']
        
        data_dict = {'id': resource_id}
        c.resource_dict = get_action('resource_show')(context, data_dict)
        
        resource_url = c.resource_dict['url']
        
        restrictions = linkage_rule.restrictions
        
        for restriction in restrictions:
            if restriction.resource_id == c.resource_dict['id']:
                selected_restriction = restriction
                
        c.restriction_id = selected_restriction.id
        c.variable_name =selected_restriction.variable_name
        
        query = 'SELECT DISTINCT ?s WHERE { ?s <%s> <%s> } LIMIT 1' % (selected_restriction.property, selected_restriction.class_name)
        params = urllib.urlencode({'query': query, 'format': 'application/json'})
        f = urllib.urlopen(resource_url, params)
        json_result = json.loads(f.read())
        
        binding_list = json_result['results']['bindings']
        
        subject = binding_list[0]['s']['value']
        
        query = 'SELECT DISTINCT ?p WHERE { <%s> ?p ?o }' % subject
        
        params = urllib.urlencode({'query': query, 'format': 'application/json'})
        f = urllib.urlopen(resource_url, params)
        json_result = json.loads(f.read())
        
        binding_list = json_result['results']['bindings']
        
        c.property_list = []
        
        path_input = ''
        if c.path_input_dict != '':
            log.info('path input new: %s', c.path_input_dict)
            path_input == c.path_input_dict['path_input']
        
        c.match = False
        for binding in binding_list:
            c.property_list.append(binding['p']['value'])
            if binding['p']['value'] == path_input:
               c.match = True
        
        linkage_rules, linkage_rules_list = self.get_linkage_rules(linkage_rule.orig_dataset_id)
        c.id = linkage_rule.orig_dataset_id
        
        c.pkg_dict['linkage_rules'] = linkage_rules_list
        c.form = render('silk/path_input_form.html')
        return render('silk/path_input.html')


    def path_input_edit(self, linkage_rule_id, dataset, path_input_id):
        path_input = model.Session.query(PathInput).filter_by(id=path_input_id).first()
        c.path_input_dict = {'id': path_input_id, 'path_input': path_input.path_input, 'restriction_id': path_input.restriction_id}
        log.info('path input edit %s', c.path_input_dict)
        c.edit = True
        return self.path_input_new(linkage_rule_id, dataset)

    def save_path_input(self, params, linkage_rule_id):
        log.info(request.params)
        path_input_str = ''
        if request.params['input_path'] == 'custom_input_path':
            path_input_str = request.params['custom_input_path_value']
        else:
            path_input_str = request.params['input_path']
        if 'path-input-id' in request.params:            
            path_input = model.Session.query(PathInput).filter_by(id=request.params['path-input-id']).first()
            path_input.path_input = path_input_str
        else:
            path_input = PathInput(request.params['restriction-id'], path_input_str)
            restriction = model.Session.query(Restriction).filter_by(id=request.params['restriction-id']).first()
            restriction.path_inputs.append(path_input)
            model.Session.add(path_input)
        model.Session.commit()

    def path_input_delete(self, path_input_id):
        
        path_input = model.Session.query(PathInput).filter_by(id=path_input_id).first()
        model.Session.delete(path_input)
        model.Session.commit()
        
    def comparison_delete(self, comparison_id):
        comparison = model.Session.query(Comparison).filter_by(id=comparison_id).first()
        model.Session.delete(comparison)
        model.Session.commit()
        
    def transformation_edit(self, linkage_rule_id):
        
        linkage_rule = model.Session.query(LinkageRule).filter_by(id=linkage_rule_id).first()
        c.linkage_rule_dict = {'id': linkage_rule.id, 'name': linkage_rule.name, 'orig_dataset_id': linkage_rule.orig_dataset_id, 'orig_resource_id': linkage_rule.orig_resource_id, 'dest_dataset_id': linkage_rule.dest_dataset_id, 'dest_resource_id': linkage_rule.dest_resource_id}

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
                   
        data_dict = {'id': linkage_rule.orig_dataset_id}
        
        c.pkg_dict = get_action('package_show')(context, data_dict)
        c.pkg = context['package']
        
        restrictions = linkage_rule.restrictions
        
        c.path_input_options = ''
        
        for restriction in linkage_rule.restrictions:
            path_inputs = restriction.path_inputs
            for path_input in path_inputs:
                c.path_input_options += '<option value="%s">%s/%s</option>' % (path_input.id, restriction.variable_name, path_input.path_input)
                        
        linkage_rules, linkage_rules_list = self.get_linkage_rules(linkage_rule.orig_dataset_id)
        c.id = linkage_rule.orig_dataset_id
        
        c.pkg_dict['linkage_rules'] = linkage_rules_list                
        
        c.form = render('silk/transformation_form.html')
        return render('silk/transformation.html')
        
    def save_transformation(self, params, linkage_rule_id):
        
        transformation_id = params['transformation_id']
        transformation = Transformation(transformation_id)
        
        model.Session.add(transformation)
        model.Session.commit()
        
        input_1_id = params['input_1_id']
        path_input_1 = model.Session.query(PathInput).filter_by(id=input_1_id).first()
        
        model.Session.add(path_input_1)
        
        transformation.path_inputs.append(path_input_1)
        
        if transformation_id == 'concatenate':
            input_2_id = params['input_2_id']
            path_input_2 = model.Session.query(PathInput).filter_by(id=input_2_id).first()
            model.Session.add(path_input_2)
            transformation.path_inputs.append(path_2_id)
                
        if transformation_id == 'capitalize':
            parameter = Parameter('allWords', params['allWords'], transformation.id)
            model.Session.add(parameter)
            transformation.parameters.append(parameter)
        elif transformation_id == 'replace':
            parameter_1 = Parameter('search', params['search'], transformation.id)
            parameter_2 = Parameter('replace', params['replace'], transformation.id)
            model.Session.add(parameter_1)
            model.Session.add(parameter_2)
            transformation.parameters.append(parameter_1)
            transformation.parameters.append(parameter_2)
        elif transformation_id == 'regexReplace':
            parameter_1 = Parameter('regex', params['regex'], transformation.id)
            parameter_2 = Parameter('replace', params['replace'], transformation.id)
            model.Session.add(parameter_1)
            model.Session.add(parameter_2)
            transformation.parameters.append(parameter_1)
            transformation.parameters.append(parameter_2)
        elif transformation_id == 'logarithm':
            parameter = Parameter('base', params['base'], transformation.id)
            model.Session.add(parameter)
            transformation.parameters.append(parameter)
        elif transformation_id == 'convert':
            parameter_1 = Parameter('sourceCharset', params['sourceCharset'], transformation.id)
            parameter_2 = Parameter('targetCharset', params['targetCharset'], transformation.id)
            model.Session.add(parameter_1)
            model.Session.add(parameter_2)
            transformation.parameters.append(parameter_1)
            transformation.parameters.append(parameter_2)
        elif transformation_id == 'tokenize':
            parameter = Parameter('regex', params['regex'], transformation.id)
            model.Session.add(parameter)
            transformation.parameters.append(parameter)
        elif transformation_id == 'removeValues':
            parameter = Parameter('blacklist', params['blacklist'], transformation.id)
            model.Session.add(parameter)
            transformation.parameters.append(parameter)

        model.Session.commit()

    def comparison_edit(self, linkage_rule_id):
        
        linkage_rule = model.Session.query(LinkageRule).filter_by(id=linkage_rule_id).first()
        c.linkage_rule_dict = {'id': linkage_rule.id, 'name': linkage_rule.name, 'orig_dataset_id': linkage_rule.orig_dataset_id, 'orig_resource_id': linkage_rule.orig_resource_id, 'dest_dataset_id': linkage_rule.dest_dataset_id, 'dest_resource_id': linkage_rule.dest_resource_id}

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
                   
        data_dict = {'id': linkage_rule.orig_dataset_id}
        
        c.pkg_dict = get_action('package_show')(context, data_dict)
        c.pkg = context['package']
        
        restrictions = linkage_rule.restrictions
        
        c.path_inputs = []
        c.transformations = []
        
        for restriction in restrictions:
            path_inputs = restriction.path_inputs
            for path_input in path_inputs:
                #c.option += '<option value="path-%s">%s/%s</option>' % (path_input.id, restriction.variable_name, path_input.path_input)
                c.path_inputs.append({'id': path_input.id, 'variable_name': restriction.variable_name, 'path_input': path_input.path_input})
                transformations = path_input.transformations
                for transformation in transformations:
                    #c.option += '<option value="transformation-%s">Transformation #%s</option>' % (transformation.id, transformation.id)
                    c.transformations.append({'id': transformation.id})
        
        linkage_rules, linkage_rules_list = self.get_linkage_rules(linkage_rule.orig_dataset_id)
        c.id = linkage_rule.orig_dataset_id
        
        c.pkg_dict['linkage_rules'] = linkage_rules_list
        
        c.form = render('silk/comparison_form.html')
        return render('silk/comparison.html')

    def save_comparison(self, params, linkage_rule_id):
        
        required = False
        if 'required' in params:
            required = True
            
        comparison = Comparison(params['distanceMeasure'], params['threshold'], required, params['weight'])
        model.Session.add(comparison)
        
        input_1 = None
        input_2 = None
        
        input_type = params['input_1'].split('-')[0]
        if input_type == 'path':
            input_1 = model.Session.query(PathInput).filter_by(id=params['input_1'].split('-')[1]).first()
        else:
            input_1 = model.Session.query(Transformation).filter_by(id=params['input_1'].split('-')[1]).first()
        
        input_type = params['input_2'].split('-')[0]
        if input_type == 'path':
            input_2 = model.Session.query(PathInput).filter_by(id=params['input_2'].split('-')[1]).first()
        else:
            input_2 = model.Session.query(Transformation).filter_by(id=params['input_2'].split('-')[1]).first()

        input_1.comparisons.append(comparison)
        input_2.comparisons.append(comparison)
        
        model.Session.commit()
        
        if (params['distanceMeasure'] == 'num'):
            param_1 = ComparisonParameters('minValue', params['minValue'], comparison.id)
            param_2 = ComparisonParameters('maxValue', params['maxValue'], comparison.id)
            model.Session.add(param_1)
            model.Session.add(param_2)
            comparison.parameters.append(param_1)
            comparison.parameters.append(param_2)
        elif (params['distanceMeasure'] == 'wgs84'):
            param = ComparisonParameters('unit', params['unit'], comparison.id)
            model.Session.add(param)
            comparison.parameters.append(param)

        model.Session.commit()

    def aggregation_edit(self, linkage_rule_id):
        
        linkage_rule = model.Session.query(LinkageRule).filter_by(id=linkage_rule_id).first()
        c.linkage_rule_dict = {'id': linkage_rule.id, 'name': linkage_rule.name, 'orig_dataset_id': linkage_rule.orig_dataset_id, 'orig_resource_id': linkage_rule.orig_resource_id, 'dest_dataset_id': linkage_rule.dest_dataset_id, 'dest_resource_id': linkage_rule.dest_resource_id}

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
                   
        data_dict = {'id': linkage_rule.orig_dataset_id}
        
        c.pkg_dict = get_action('package_show')(context, data_dict)
        c.pkg = context['package']
        
        linkage_rule, linkage_rules_list = self.get_linkage_rules(linkage_rule.orig_dataset_id)
        c.pkg_dict['linkage_rules'] = linkage_rules_list
        
        c.form = render('silk/aggregation_form.html')
        return render('silk/aggregation.html')
        
    def save_aggregation(self, params, linkage_rule_id):
        linkage_rule = model.Session.query(LinkageRule).filter_by(id=linkage_rule_id).first()
        linkage_rule.aggregation = params['aggregation']
        model.Session.commit()
        
    def launch(self, linkage_rule_id):
        linkage_rule = model.Session.query(LinkageRule).filter_by(id=linkage_rule_id).first()
        c.linkage_rule_dict = {'id': linkage_rule.id, 'name': linkage_rule.name, 'orig_dataset_id': linkage_rule.orig_dataset_id, 'orig_resource_id': linkage_rule.orig_resource_id, 'dest_dataset_id': linkage_rule.dest_dataset_id, 'dest_resource_id': linkage_rule.dest_resource_id}

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
        
        data_dict = {'id': linkage_rule.orig_dataset_id}
        
        c.pkg_dict = get_action('package_show')(context, data_dict)
        c.pkg = context['package']        
        
        data_dict = {'id': linkage_rule.orig_resource_id}
        orig_resource = ckan.logic.get_action('resource_show')(context, data_dict)
        data_dict = {'id': linkage_rule.dest_resource_id}
        dest_resource = ckan.logic.get_action('resource_show')(context, data_dict)
        
        orig_restriction = model.Session.query(Restriction).filter_by(resource_id=orig_resource['id'], linkage_rule_id=linkage_rule.id).first()
        dest_restriction = model.Session.query(Restriction).filter_by(resource_id=dest_resource['id'], linkage_rule_id=linkage_rule.id).first()
        
        orig_path_inputs = orig_restriction.path_inputs
        dest_path_inputs = dest_restriction.path_inputs
        
        orig_transformations = []
        
        for path_input in orig_path_inputs:
            transformations = path_input.transformations
            for transformation in transformations:
                if transformation not in orig_transformations:
                    orig_transformations.append(transformation)
        
        dest_transformations = []
        
        for path_input in dest_path_inputs:
            transformations = path_input.transformations
            for transformation in transformations:
                if transformation not in dest_transformations:
                    dest_transformations.append(transformation)
        
        comparison_list = []
        #TODO: mejorar!
        for path_input in orig_path_inputs:
            comparisons = path_input.comparisons
            for comparison in comparisons:
                comparison_list.append(comparison)
        for path_input in dest_path_inputs:
            comparisons = path_input.comparisons
            for comparison in comparisons:
                comparison_list.append(comparison)
        for transformation in orig_transformations:
            comparisons = transformation.comparisons
            for comparison in comparisons:
                comparison_list.append(comparison)
        for transformation in dest_transformations:
            comparisons = transformation.comparisons
            for comparison in comparisons:
                comparison_list.append(comparison)
            
        comparison_dict = {}
        for comparison in comparison_list:
            log.info(comparison)
            comparison_dict[comparison.id] = comparison
            
        log.info(comparison_dict)
            
        document = Document()
        silk = document.createElement('Silk') 
        
        prefixesNode = document.createElement('Prefixes')
        
        
        datasources = document.createElement('DataSources')
        
        orig_datasource = document.createElement('DataSource')
        orig_datasource.setAttribute('id', linkage_rule.orig_dataset_id)
        orig_datasource.setAttribute('type', 'sparqlEndpoint')
        param = document.createElement('Param')
        param.setAttribute('name', 'endpointURI')
        param.setAttribute('value', orig_resource['url'])
        orig_datasource.appendChild(param)
        
        dest_datasource = document.createElement('DataSource')
        dest_datasource.setAttribute('id', linkage_rule.dest_dataset_id)
        dest_datasource.setAttribute('type', 'sparqlEndpoint')
        param = document.createElement('Param')
        param.setAttribute('name', 'endpointURI')
        param.setAttribute('value', dest_resource['url'])
        dest_datasource.appendChild(param)
        
        datasources.appendChild(orig_datasource)
        datasources.appendChild(dest_datasource)
        
        interlinks = document.createElement('Interlinks')
        
        interlink = document.createElement('Interlink')
        interlink.setAttribute('id', linkage_rule.name)
        
        linktype = document.createElement('LinkType')
        text = document.createTextNode(self.get_prefix(linkage_rule.link_type))
        linktype.appendChild(text)
        
        sourcedataset = document.createElement('SourceDataset')
        sourcedataset.setAttribute('dataSource', linkage_rule.orig_dataset_id)
        sourcedataset.setAttribute('var', orig_restriction.variable_name.lstrip('?'))
        
        restricto = document.createElement('RestrictTo')
        text = document.createTextNode('%s %s %s' % (orig_restriction.variable_name, self.get_prefix(orig_restriction.property), self.get_prefix(orig_restriction.class_name)))
        restricto.appendChild(text)
        sourcedataset.appendChild(restricto)
        
        targetdataset = document.createElement('TargetDataset')
        targetdataset.setAttribute('dataSource', linkage_rule.dest_dataset_id)
        targetdataset.setAttribute('var', dest_restriction.variable_name.lstrip('?'))
        
        restricto = document.createElement('RestrictTo')
        text = document.createTextNode('%s %s %s' % (dest_restriction.variable_name, self.get_prefix(dest_restriction.property), self.get_prefix(dest_restriction.class_name)))
        restricto.appendChild(text)
        targetdataset.appendChild(restricto)
        
        interlink.appendChild(linktype)
        interlink.appendChild(sourcedataset)
        interlink.appendChild(targetdataset)
        
        
        
        linkagerule = document.createElement('LinkageRule')
                
        for key in comparison_dict.keys():
            comparison = comparison_dict[key]
            compare = document.createElement('Compare')
            compare.setAttribute('metric', comparison.distance_measure)
            path_inputs = comparison.path_inputs
            for path_input in path_inputs:
                input = document.createElement('Input')
                prefixed_path = self.get_prefix(path_input.path_input)
                input.setAttribute('path', '%s/%s' % (path_input.restriction.variable_name, prefixed_path))
                compare.appendChild(input)
            for transformation in comparison.transformations:
                for path_input in transformation.path_inputs:
                    input = document.createElement('Input')
                    prefixed_path = self.get_prefix(path_input.path_input)
                    input.setAttribute('path', '%s/%s' % (path_input.restriction.variable_name, prefixed_path))
                    transforminput = document.createElement('TransformInput')
                    transforminput.setAttribute('function', transformation.name)
                    transforminput.appendChild(input)
                    for parameter in transformation.parameters:
                        param = document.createElement('Param')
                        param.setAttribute('name', parameter.name)
                        param.setAttribute('value', parameter.value)
                        transforminput.appendChild(param)
                    compare.appendChild(transforminput)
                    
            linkagerule.appendChild(compare)
        
        filter = document.createElement('Filter')
            
        interlink.appendChild(linkagerule)
        interlink.appendChild(filter)
        
        interlinks.appendChild(interlink)
        
        
        log.info(self.prefixes)
        for key in self.prefixes.keys():
            
            namespace = self.prefixes[key]
            prefix = document.createElement('Prefix')
            prefix.setAttribute('id', key)
            prefix.setAttribute('namespace', namespace)
            prefixesNode.appendChild(prefix)
        
        task_id=str(uuid.uuid4())
        
        outputs = document.createElement('Outputs')
        
        output = document.createElement('Output')
        output.setAttribute('type', 'file')
        param = document.createElement('Param')
        param.setAttribute('name', 'file')
        param.setAttribute('value', '/tmp/output-%s.xml' % task_id)
        output.appendChild(param)
        param = document.createElement('Param')
        param.setAttribute('name', 'format')
        param.setAttribute('value', 'ntriples')
        output.appendChild(param)
        
        outputs.appendChild(output)
        
        silk.appendChild(prefixesNode)
        silk.appendChild(datasources)
        silk.appendChild(interlinks)
        silk.appendChild(outputs)
        document.appendChild(silk)
        
        log.info(document.toprettyxml())
        
        
        file_name = '/tmp/input-%s.xml' % task_id
        fl = open(file_name, 'w')
        fl.write(document.toprettyxml())
        fl.close()
        
        celery.send_task("silk.launch", args=[file_name], task_id=task_id)
        
        return render('silk/silk_launched.html')

    def get_prefix(self, uri):
        if '#' in uri:
            namespace = uri.split('#')[0] + '#'
            postfix = uri.split('#')[1]
        else:
            splitted_uri = uri.split('/')
            namespace = ''
            for i in range(0, len(splitted_uri) - 1):
                namespace += splitted_uri[i] + '/'
            postfix = splitted_uri[len(splitted_uri) - 1]
                
        params = urllib.urlencode({'uri': namespace, 'format': 'json'})
        f = urllib.urlopen('http://prefix.cc/reverse?%s' % params)
        result = f.read()
        log.info(result)
        json_result = json.loads('[%s]' % result)
        log.info(json_result)
        for key in json_result[0].keys():
            prefix = key
        self.prefixes[prefix] = namespace
        return '%s:%s' % (prefix, postfix)
        
