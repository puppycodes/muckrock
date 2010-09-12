"""
Sitemap for FOIA application
"""

from django.contrib.sitemaps import Sitemap

from foia.models import FOIARequest

class FoiaSitemap(Sitemap):
    """Sitemap for FOIA Requests"""

    def items(self):
        """Return all FOIA requests"""
        return FOIARequest.objects.all()

    #def lastmod(self, obj):
    # Is it worth storing a last_mod field on foia requests just for this?

    def changefreq(self, obj):
        """How often does this object change"""
        # pylint: disable-msg=R0201

        if obj.status in ['rejected', 'done']:
            return 'never'
        else:
            return 'weekly'

    def priority(self, obj):
        """How important is this object"""
        # pylint: disable-msg=R0201

        return {
            'started': 0.3,
            'submitted': 0.5,
            'processed': 0.6,
            'fix': 0.6,
            'payment': 0.6,
            'rejected': 0.1,
            'done': 0.8,
            'partial': 0.7,
        }[obj.status]
