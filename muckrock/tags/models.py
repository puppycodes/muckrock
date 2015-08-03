"""
Models for the tags application
"""

from django.db import models

import autocomplete_light
from taggit.models import Tag as TaggitTag, GenericTaggedItemBase

# pylint: disable=model-missing-unicode

class Tag(TaggitTag):
    """Custom Tag Class"""

    def save(self, *args, **kwargs):
        """Normalize name before saving"""
        self.name = Tag.normalize(self.name)
        super(Tag, self).save(*args, **kwargs)

    @staticmethod
    def normalize(name):
        """Normalize tag name"""
        html_remove = dict((ord(c), None) for c in ['<', '>', '&', '"', "'"])
        return name.translate(html_remove).strip().lower()

    class Meta:
        # pylint: disable=too-few-public-methods
        ordering = ['name']

class TaggedItemBase(GenericTaggedItemBase):
    """Custom Tagged Item Base Class"""
    tag = models.ForeignKey(Tag, related_name="%(app_label)s_%(class)s_items")

autocomplete_light.register(Tag)
