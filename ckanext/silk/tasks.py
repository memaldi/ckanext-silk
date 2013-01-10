from ckan.lib.celery_app import celery

@celery.task(name = "silk.launch")
def launch(file_name):
    print 'OLA KE ASE'
