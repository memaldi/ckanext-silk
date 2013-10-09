from ckan.lib.celery_app import celery
import os
import ConfigParser

#Configuration load
config = ConfigParser.ConfigParser()
config.read(os.environ['CKAN_CONFIG'])

SILK_HOME = config.get('plugin:silk', 'silk_home')

@celery.task(name = "silk.launch")
def launch(file_name):
    print 'Launching Silk...'
    
    command = 'java -DconfigFile=%s -jar %s/silk.jar' % (file_name, SILK_HOME)
    print 'Executing command', command
    os.system(command)    
    
    print 'Silk process finished'
