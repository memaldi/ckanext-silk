from ckan.plugins import SingletonPlugin, IPackageController, implements
from ckan.lib.base import BaseController, render, c, model, g, request
from logging import getLogger
from ckan.logic import NotAuthorized, check_access
import urllib
import ckan
import json
from rdflib import Graph
import ckanext.datastore.logic.action as action

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
        
    def get_classes(self, property, resource_id):
        unquoted_property = urllib.unquote(property)
        context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author}
        
        data_dict = {
                'q': '*:*',
                'facet.field': g.facets,
                'rows': 0,
                'start': 0,
                'fq': 'capacity:"public"',
                'id': resource_id
        }
            
        resource = ckan.logic.get_action('resource_show')(
                    context, data_dict)
        
        resource_url = resource['url']
        json_result = None
        if (resource['format'] == 'api/sparql'):
            sparql_query = 'SELECT DISTINCT ?class WHERE { [] <%s> ?class }' % unquoted_property
            params = urllib.urlencode({'query': sparql_query, 'format': 'application/json'})
            f = urllib.urlopen(resource_url, params)
            json_result = json.loads(f.read())
                
        output_html = '''
                            <label class="control-label" for="classes">Classes:</label>
                            <div class="controls">
                            <select id="orig_class_select" name="orig_class_select">
        '''
        
        if json_result != None:
            #log.info(type(json_result))
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
        log.info(request.params)
        
        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        
        c.form = render('silk/properties_form.html', extra_vars=vars)
        
        return render('silk/properties.html')
