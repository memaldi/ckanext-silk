from ckan.lib.celery_app import celery
import os
import ConfigParser
import json
from datetime import datetime
import requests
import urlparse

#Configuration load
config = ConfigParser.ConfigParser()
config.read(os.environ['CKAN_CONFIG'])

MAIN_SECTION = 'app:main'
PLUGIN_SECTION = 'plugin:silk'

SILK_HOME = config.get(PLUGIN_SECTION, 'silk_home')
SITE_URL = config.get(MAIN_SECTION, 'ckan.site_url')
API_URL = urlparse.urljoin(SITE_URL, 'api/')
API_KEY = config.get(PLUGIN_SECTION, 'api_key')

def update_task_status(task_info):
    print "Updating task status for linkage_rule_id %s" % task_info['entity_id']
    res = requests.post(
        API_URL + 'action/task_status_update', json.dumps(task_info),
        headers = {'Authorization': API_KEY,
                   'Content-Type': 'application/json'}
    )

    if res.status_code == 200:
        return json.loads(res.content)['result']
    else:
        print 'ckan failed to update task_status, status_code (%s), error %s' % (res.status_code, res.content)
        return None

@celery.task(name = "silk.launch")
def launch(linkage_rule_id, file_name):
    task_info = {
            'entity_id': linkage_rule_id,
            'entity_type': u'linkage_rule',
            'task_type': u'ckanext-silk',
            'key': u'celery_task_status',
            'value': json.dumps({'status': 'running'}),
            'error': u'',
            'last_updated': datetime.now().isoformat()
        }
        
    task_status = update_task_status(task_info)
    
    print 'Launching Silk...'
    
    command = 'java -DconfigFile=%s -jar %s/silk.jar' % (file_name, SILK_HOME)
    print 'Executing command', command
    os.system(command)    
    
    print 'Silk process finished'
    
    task_info = {
            'id': task_status['id'],
            'entity_id': linkage_rule_id,
            'entity_type': u'linkage_rule',
            'task_type': u'ckanext-silk',
            'key': u'celery_task_status',
            'value': json.dumps({'status': 'finished'}),
            'error': u'',
            'last_updated': datetime.now().isoformat()       
        }

    update_task_status(task_info)
