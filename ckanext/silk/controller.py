from ckan.plugins import SingletonPlugin, IPackageController, implements
from ckan.lib.base import BaseController, render, c, model, g, request
from logging import getLogger
from ckan.logic import NotAuthorized, check_access
import ckan
import ckanext.datastore.logic.action as action

log = getLogger(__name__)

class SilkController(BaseController):

    '''def main(self, id):
        c.dataset_id = id
        context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author}
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
            if package_id != id:
                c.packages.append((package['title'], package_id))
            else:
                c.dataset_name = package['title']
                if package['resources'][0]['format'] in ['api/sparql', 'application/rdf+xml']:
                    #log.info(package['resources'][0])
                    for resource in package['resources']:
                        c.resources.append((resource['id'], resource['name']))
                    #c.resources.append((package['resources'][0]['id'], package['resources'][0]['name']))
        return render('silk/main.html')'''
        
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
        
        
    def register(self, data=None, errors=None, error_summary=None):
        return self.new(data, errors, error_summary)
        
    def new(self, data=None, errors=None, error_summary=None):
        log.info(request.params)
        
        routes = request.environ.get('pylons.routes_dict')
        c.dataset_id = routes['id']
        
        context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author}
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
                c.dataset_name = package['title']
                
                if package['resources'][0]['format'] in ['api/sparql', 'application/rdf+xml']:
                    #log.info(package['resources'][0])
                    for resource in package['resources']:
                        c.resources.append((resource['id'], resource['name']))
                    #c.resources.append((package['resources'][0]['id'], package['resources'][0]['name']))
        log.info(c.packages)
        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        
        c.form = render(self.new_user_form, extra_vars=vars)
        
        return render('silk/main.html')
