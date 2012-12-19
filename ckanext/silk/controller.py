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
from ckanext.silk.model import LinkageRule, Restriction

log = getLogger(__name__)

class SilkController(BaseController):
          
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
        
        sparql_query = 'SELECT DISTINCT ?class WHERE { [] <%s> ?class }' % unquoted_property
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
        
        
    def restrictions(self, context, params): 
        log.info(request.params)        
        routes = request.environ.get('pylons.routes_dict')
        c.dataset_id = routes['id']
        c.orig_resource_id = params['resource_id']
        c.dest_resource_id = params['dest_resource_id']
        c.dest_dataset_id = params['dest_package_id']
        
        data_dict = {
                'q': '*:*',
                'facet.field': g.facets,
                'rows': 0,
                'start': 0,
                'fq': 'capacity:"public"',
                'id': c.dataset_id
            }
        
        package = ckan.logic.get_action('package_show')(
                    context, data_dict)
                    
        c.orig_dataset_name = package['title']
        
        data_dict = {
                'q': '*:*',
                'facet.field': g.facets,
                'rows': 0,
                'start': 0,
                'fq': 'capacity:"public"',
                'id': c.dest_dataset_id
        }
        
        dest_package = ckan.logic.get_action('package_show')(
                    context, data_dict)
                    
        c.dest_dataset_name = dest_package['title']
        
        
        c.form = render('silk/restrictions_form.html')
        
        return render('silk/restrictions.html')
        
    def register(self, data=None, errors=None, error_summary=None):
        log.info('register!!')
        return self.new(data, errors, error_summary)
        
    def new(self, data=None, errors=None, error_summary=None):
        log.info('new!!!')
        log.info(request.params)
        routes = request.environ.get('pylons.routes_dict')
        c.dataset_id = routes['id']
        
        context = { 'model': model, 
                    'session': model.Session,
                    'user': c.user or c.author,
                    'save': 'save' in request.params}
                       
        #### NEXT STEP
        if context['save'] and not data:
            return self.restrictions(context, request.params)
                       
        data_dict = {
            'q': '*:*',
            'facet.field': g.facets,
            'rows': 0,
            'start': 0,
            'fq': 'capacity:"public"'
        }
      
        query = ckan.logic.get_action('package_list')(
            context, data_dict)
        
        c.packages = []
        c.resources = []
        for package_id in query:
            data_dict = {
                'q': '*:*',
                'facet.field': g.facets,
                'rows': 0,
                'start': 0,
                'fq': 'capacity:"public"',
                'id': package_id
            }
            package = ckan.logic.get_action('package_show')(
                    context, data_dict)
            if package_id != c.dataset_id:
                c.packages.append((package['title'], package_id))
                
            else:
                c.orig_dataset_name = package['title']
                
                if package['resources'][0]['format'] in ['api/sparql', 'application/rdf+xml']:
                    for resource in package['resources']:
                        c.resources.append((resource['id'], resource['name']))
                                                
        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        
        c.form = render(self.new_user_form, extra_vars=vars)
        
        return render('silk/main.html')
        
    def properties(self, data=None, errors=None, error_summary=None):
        log.info('Request params %s' % request.params)
        req_params = request.params        
   
        context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author}
        
        data_dict = {
                'q': '*:*',
                'facet.field': g.facets,
                'rows': 0,
                'start': 0,
                'fq': 'capacity:"public"',
                'id': req_params['orig_dataset_id']
        }
        
        orig_dataset = ckan.logic.get_action('package_show')(
                    context, data_dict)
        
        c.orig_dataset_name = orig_dataset['title']
        
        data_dict = {
                'q': '*:*',
                'facet.field': g.facets,
                'rows': 0,
                'start': 0,
                'fq': 'capacity:"public"',
                'id': req_params['orig_resource_id']
        }
            
        orig_resource = ckan.logic.get_action('resource_show')(
                    context, data_dict)
        
        query = 'SELECT ?s WHERE { ?s <%s> <%s> } LIMIT 1' % (req_params['orig_restriction'], req_params['orig_class_select'])
        params = urllib.urlencode({'query': query, 'format': 'application/json'})
        f = urllib.urlopen(orig_resource['url'], params)
        json_result = json.loads(f.read())
        
        subject = json_result['results']['bindings'][0]['s']['value']
        
        query = 'SELECT DISTINCT ?p WHERE { <%s> ?p ?o }' % subject
        params = urllib.urlencode({'query': query, 'format': 'application/json'})
        f = urllib.urlopen(orig_resource['url'], params)
        json_result = json.loads(f.read())
                
        binding_list = json_result['results']['bindings']
        c.orig_property_list = []      
        
        for binding in binding_list:
            c.orig_property_list.append(binding['p']['value'])
        
        
        data_dict = {
                'q': '*:*',
                'facet.field': g.facets,
                'rows': 0,
                'start': 0,
                'fq': 'capacity:"public"',
                'id': req_params['dest_dataset_id']
        }
        
        dest_dataset = ckan.logic.get_action('package_show')(
                    context, data_dict)
        
        c.dest_dataset_name = dest_dataset['title']
        
        data_dict = {
                'q': '*:*',
                'facet.field': g.facets,
                'rows': 0,
                'start': 0,
                'fq': 'capacity:"public"',
                'id': req_params['dest_resource_id']
        }
            
        dest_resource = ckan.logic.get_action('resource_show')(
                    context, data_dict)
        
        query = 'SELECT ?s WHERE { ?s <%s> <%s> } LIMIT 1' % (req_params['dest_restriction'], req_params['dest_class_select'])
        params = urllib.urlencode({'query': query, 'format': 'application/json'})
        f = urllib.urlopen(dest_resource['url'], params)
        json_result = json.loads(f.read())
        
        subject = json_result['results']['bindings'][0]['s']['value']
        
        query = 'SELECT DISTINCT ?p WHERE { <%s> ?p ?o }' % subject
        params = urllib.urlencode({'query': query, 'format': 'application/json'})
        f = urllib.urlopen(dest_resource['url'], params)
        json_result = json.loads(f.read())
                
        binding_list = json_result['results']['bindings']
        c.dest_property_list = []     
        
        for binding in binding_list:
            c.dest_property_list.append(binding['p']['value'])
        
        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        
        c.form = render('silk/properties_form.html', extra_vars=vars)
        
        return render('silk/properties.html')
        
    # Aqui empieza lo bueno
    
    def _get_package_type(self, id):
        """
        Given the id of a package it determines the plugin to load
        based on the package's type name (type). The plugin found
        will be returned, or None if there is no plugin associated with
        the type.
        """
        pkg = model.Package.get(id)
        if pkg:
            return pkg.type or 'package'
        return None
        
    def _package_form(self, package_type=None):
        return lookup_package_plugin(package_type).package_form()
    
    def save(self, id, params):
        session = model.Session
        log.info(params['dest_package_id'])
        linkage_rule = LinkageRule(params['new_linkage_rule_name'], id, params['resource_id'], params['dest_package_id'], params['dest_resource_id'])
        session.add(linkage_rule)
        session.commit()
        pass
        
    
    def read(self, id, data=None, errors=None, error_summary=None):
        
        log.info(request.params)
        if (len(request.params) > 0):
            if request.params['save'] == 'Save':
                self.save(id, request.params)
        
        
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
        
        log.info(linkage_rules)
        
        return render('silk/read.html')
        
    def edit_linkage_rules(self, id, data=None, errors=None, error_summary=None):
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
        
        
        c.linkage_rules = None
        
        c.form = render('silk/linkage_rule_form.html')
        
        return render('silk/edit_linkage_rules.html')
        
    def resource_read(self, id, linkage_rule_id):
        
        log.info('Params: %s' % request.params)
        log.info(request)
        
        if len(request.params) > 0:
            if 'restriction-save' in request.params:
                if request.params['restriction-save'] == 'true':
                    self.save_restriction(request.params, linkage_rule_id)
                
        
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
        
        for restriction in restrictions:
            if restriction.resource_id == c.orig_resource['id']:
                c.orig_restrictions_list.append({'id': restriction.id, 'resource_id': restriction.resource_id, 'variable_name': restriction.variable_name, 'property': restriction.property, 'class_name': restriction.class_name, 'linkage_rule_id': restriction.linkage_rule_id})
            elif restriction.resource_id == c.dest_resource['id']:
                c.dest_restrictions_list.append({'id': restriction.id, 'resource_id': restriction.resource_id, 'variable_name': restriction.variable_name, 'property': restriction.property, 'class_name': restriction.class_name, 'linkage_rule_id': restriction.linkage_rule_id})
        
        c.restrictions_control = False
        
        if len(c.orig_restrictions_list) > 0 and len(c.dest_restrictions_list):
            c.restrictions_control = True

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
        
        linkage_rules = model.Session.query(LinkageRule).filter_by(orig_dataset_id=c.pkg_dict['name'])
        
        linkage_rules_list = []
        
        for linkage_rule in linkage_rules:
            linkage_rules_list.append({'id': linkage_rule.id, 'name': linkage_rule.name, 'orig_dataset_id': linkage_rule.orig_dataset_id, 'orig_resource_id': linkage_rule.orig_resource_id, 'dest_dataset_id': linkage_rule.dest_dataset_id, 'dest_resource_id': linkage_rule.dest_resource_id})
        
        c.pkg_dict['linkage_rules'] = linkage_rules_list
        
        c.form = render('silk/restrictions_form.html')
            
        return render('silk/restrictions.html')
