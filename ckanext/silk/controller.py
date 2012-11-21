from ckan.plugins import SingletonPlugin, IPackageController, implements
from ckan.lib.base import BaseController, render
from logging import getLogger

log = getLogger(__name__)

class SilkController(BaseController):

    def main(self, id):
        log.info('main')
        return render('silk/main.html')
