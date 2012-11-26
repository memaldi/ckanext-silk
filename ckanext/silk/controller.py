from ckan.plugins import SingletonPlugin, IPackageController, implements
from ckan.lib.base import BaseController, render, c, model, g
from logging import getLogger
import ckan
import ckanext.datastore.logic.action as action

log = getLogger(__name__)

class SilkController(BaseController):

    def main(self, id):
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
        return render('silk/main.html')
        
    def get_resources(self, value):
        
        data_dict = {
                'q': '*:*',
                'facet.field': g.facets,
                'rows': 0,
                'start': 0,
                'fq': 'capacity:"public"',
                'id': value
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
