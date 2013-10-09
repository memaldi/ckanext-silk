from ckan.lib.celery_app import celery
from celery.signals import beat_init
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
        return None
        
def get_package_list():
    res = requests.post(
        API_URL + 'action/package_list', json.dumps({}),
        headers = {'Authorization': API_KEY,
                   'Content-Type': 'application/json'}
    )

    if res.status_code == 200:
        return json.loads(res.content)['result']
    else:
        return {}
        
def get_package_info(package_name):
    res = requests.post(
        API_URL + 'action/package_show', json.dumps({'id': package_name}),
        headers = {'Authorization': API_KEY,
                   'Content-Type': 'application/json'}
    )

    if res.status_code == 200:
        return json.loads(res.content)['result']
    else:
        return {}
        
def get_pending_tasks():
    pending_tasks = []
    
    packages = get_package_list()

    for package in packages:
        package_info = get_package_info(package)

        tasks_status = get_tasks_status(package_info['id'])
        if len(tasks_status) > 0:
            print tasks_status            

    return pending_tasks

@beat_init.connect    
def clear_broken_status_tasks(sender=None, conf=None, **kwargs):
    print 'Clearing pending task status'

    pending_tasks = get_pending_tasks()

    print pending_tasks

    for task_id in pending_tasks.items():
        print 'Deleting task id %s' % task_id
        delete_task_status(task_id)

@celery.task(name = "silk.launch")
def launch(package_id, linkage_rule_id, input_file_name, output_file_name):
    task_info = {
            'entity_id': package_id,
            'entity_type': u'linkage_rule',
            'task_type': u'ckanext-silk',
            'key': u'%s' % linkage_rule_id,
            'value': json.dumps({'status': 'running'}),
            'error': u'',
            'last_updated': datetime.now().isoformat()
        }
        
    task_status = update_task_status(task_info)
    
    print 'Launching Silk...'
    
    command = 'java -DconfigFile=%s -jar %s/silk.jar' % (input_file_name, SILK_HOME)
    print 'Executing command', command
    os.system(command)    
    
    print 'Silk process finished'
    
    data = open(output_file_name, 'r').read()
    
    task_info = {
            'id': task_status['id'],
            'entity_id': package_id,
            'entity_type': u'linkage_rule',
            'task_type': u'ckanext-silk',
            'key': u'%s' % linkage_rule_id,
            'value': json.dumps({'status': 'finished', 'data' : data}),
            'error': u'',
            'last_updated': datetime.now().isoformat()       
        }

    update_task_status(task_info)
