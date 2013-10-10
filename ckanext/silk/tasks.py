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
    
    return ()
        
def get_package_list():
    res = requests.post(
        API_URL + 'action/package_list', json.dumps({}),
        headers = {'Authorization': API_KEY,
                   'Content-Type': 'application/json'}
    )

    if res.status_code == 200:
        return json.loads(res.content)['result']
    
    return ()

def get_linkage_rules(package_id):
    res = requests.post(
        API_URL + 'silk/listlinkagerules', json.dumps({'package_id': package_id}),
        headers = {'Authorization': API_KEY,
                   'Content-Type': 'application/json'}
    )
    
    if res.status_code == 200:
        return json.loads(res.content)['result']
    
    return ()
    
def save_rule_output(linkage_rule_id, rule_output):
    data = {'linkage_rule_id': linkage_rule_id, 'rule_output': rule_output }
    res = requests.post(
        API_URL + 'silk/saveruleoutput', json.dumps(data),
        headers = {'Authorization': API_KEY,
                   'Content-Type': 'application/json'}
    )
    
    return res.status_code == 200
    
def get_package_info(package_id):
    res = requests.post(
        API_URL + 'action/package_show', json.dumps({'id': package_id}),
        headers = {'Authorization': API_KEY,
                   'Content-Type': 'application/json'}
    )

    if res.status_code == 200:
        return json.loads(res.content)['result']
    
    return ()
    
def get_task_status(package_id, linkage_rule_id):
    task_info = {'entity_id': package_id, 
        'task_type': u'ckanext-silk', 
        'key': u'%s' % linkage_rule_id
        }
    
    res = requests.post(
        API_URL + 'action/task_status_show', json.dumps(task_info),
        headers = {'Authorization': API_KEY,
                   'Content-Type': 'application/json'}
    )

    if res.status_code == 200:
        return json.loads(res.content)['result']
    
    return None

def delete_task_status(task_id):
    res = requests.post(
        API_URL + 'action/task_status_delete', json.dumps({'id': task_id}),
        headers = {'Authorization': API_KEY,
        'Content-Type': 'application/json'}
    )

    return res.status_code == 200

@beat_init.connect    
def clear_broken_status_tasks(sender=None, conf=None, **kwargs):
    print 'Clearing old task status'
    
    package_list = get_package_list()
    for package in package_list:
        package_info = get_package_info(package)
        
        linkage_rules = get_linkage_rules(package_info['name'])
        for linkage_rule_id in linkage_rules['rules']:
            task_status = get_task_status(package_info['name'], linkage_rule_id)

            if task_status is not None:
                delete_task_status(task_status['id'])
    
def create_task_info(package_id, linkage_rule_id, json_value):    
    task_info = {
            'entity_id': package_id,
            'entity_type': u'package',
            'task_type': u'ckanext-silk',
            'key': u'%s' % linkage_rule_id,
            'value': json_value,
            'error': u'',
            'last_updated': datetime.now().isoformat()
        }
        
    return task_info

@celery.task(name = "silk.launch")
def launch(package_id, linkage_rule_id, input_file_name, output_file_name):
    task_info = create_task_info(package_id, linkage_rule_id, json.dumps({'status': 'running'}))
    task_status = update_task_status(task_info)
    
    print 'Launching Silk...'
    
    command = 'java -DconfigFile=%s -jar %s/silk.jar' % (input_file_name, SILK_HOME)
    print 'Executing command', command
    os.system(command)    
    
    print 'Silk process finished. Output written to %s' % output_file_name
    
    data = open(output_file_name, 'r').read()
    
    print 'Saving output for rule %s' % linkage_rule_id
    if save_rule_output(linkage_rule_id, data):
        print 'Rule output correctly saved'
    else:
        print 'Some problem ocurred during rule output saving'
    
    task_info = create_task_info(package_id, linkage_rule_id, json.dumps({'status': 'finished'}))
    task_info['id'] = task_status['id']

    update_task_status(task_info)
