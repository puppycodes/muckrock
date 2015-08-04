"""
Views for tags
"""

from django.db.models import Count
from django.views.generic import TemplateView, DetailView

from . import models

from muckrock.foia.models import FOIARequest
from muckrock.news.models import Article
from muckrock.project.models import Project
from muckrock.qanda.models import Question

def list_all_tags():
    """Should list all tags that exist and that have at least one object"""
    tags = models.Tag.objects.all()
    tags = tags.annotate(num_times=Count('tags_taggeditembase_items'))
    tags = tags.exclude(num_times=0)
    return tags

class TagListView(TemplateView):
    """Presents a list of all tags"""
    template_name = 'tags/tag_list.html'

    def get_context_data(self, **kwargs):
        """Adds all tags to context data"""
        context = super(TagListView, self).get_context_data(**kwargs)
        context['tags'] = list_all_tags()
        context['popular_tags'] = list_all_tags().order_by('-num_times')[:10]
        return context

class TagDetailView(DetailView):
    """Presents the details of a tag"""
    model = models.Tag
    template_name = 'tags/tag_list.html'

    def get_context_data(self, **kwargs):
        """Adds all tags to context data"""
        context = super(TagDetailView, self).get_context_data(**kwargs)
        context['tags'] = list_all_tags()
        this_tag = self.get_object().name
        context['tagged_projects'] = Project.objects\
                                    .filter(tags__name__in=[this_tag], private=False)
        context['tagged_requests'] = FOIARequest.objects\
                                    .filter(tags__name__in=[this_tag])\
                                    .get_viewable(self.request.user)
        context['tagged_articles'] = Article.objects\
                                    .filter(tags__name__in=[this_tag], publish=True)
        context['tagged_questions'] = Question.objects.filter(tags__name__in=[this_tag])
        return context
