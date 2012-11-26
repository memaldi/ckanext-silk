from ckan.plugins import SingletonPlugin, IGenshiStreamFilter, implements, IConfigurer, IRoutes
from logging import getLogger
from pylons import request
from genshi.input import HTML
from genshi.filters.transform import Transformer
import os

log = getLogger(__name__)

class SilkExtension(SingletonPlugin):
    
    implements(IConfigurer, inherit=True)
    implements(IGenshiStreamFilter, inherit=True)
    implements(IRoutes, inherit=True)
    
    def update_config(self, config):
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))
        our_public_dir = os.path.join(rootdir, 'ckanext',
                                      'silk', 'theme', 'public')
        template_dir = os.path.join(rootdir, 'ckanext',
                                    'silk', 'theme', 'templates')
        # set our local template and resource overrides
        config['extra_public_paths'] = ','.join([our_public_dir,
                config.get('extra_public_paths', '')])
        config['extra_template_paths'] = ','.join([template_dir,
                config.get('extra_template_paths', '')])
    
    def filter(self, stream):
        routes = request.environ.get('pylons.routes_dict')
        log.info(routes)
        if routes.get('controller') == 'package':

                stream = stream | Transformer('//ul[@class="nav nav-pills"]').append(HTML(
                    
                    '''<li class>
                        <a class href="/silk/main/%s">
                            <img src="/icons/rdf_flyer.24" height="16px" width="16px" alt="None" class="inline-icon ">
                            Silk
                        </a>
                    </li>''' % routes.get('id')
                    
                ))

        return stream
        
    def before_map(self, map):
        map.connect('/silk/main', controller='ckanext.silk.controller:SilkController', action='error')
        map.connect('/silk/main/{id}', controller='ckanext.silk.controller:SilkController', action='main')
        map.connect('/silk/get_resources/{value}', controller='ckanext.silk.controller:SilkController', action='get_resources')
        return map
    
