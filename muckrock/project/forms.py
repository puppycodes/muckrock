"""
Forms for the project application
"""

from django import forms

from autocomplete_light import shortcuts as autocomplete_light
from autocomplete_light.contrib.taggit_field import TaggitField, TaggitWidget

from muckrock.project.models import Project

class ProjectCreateForm(forms.ModelForm):
    """Form for creating a new project"""

    tags = TaggitField(
        widget=TaggitWidget('TagAutocomplete', attrs={'placeholder': 'Search tags'}),
        help_text='Separate tags with commas.',
        required=False
    )

    class Meta:
        model = Project
        fields = ['title', 'summary', 'description', 'image', 'contributors', 'tags', 'private']
        widgets = {'contributors': autocomplete_light.MultipleChoiceWidget('UserAutocomplete')}
        help_texts = {
            'contributors': ('As the project creator, you are'
                            ' automatically listed as a contributor.'),
        }


class ProjectUpdateForm(forms.ModelForm):
    """Form for updating a project instance"""

    tags = TaggitField(
        widget=TaggitWidget('TagAutocomplete', attrs={'placeholder': 'Search tags'}),
        help_text='Separate tags with commas.',
        required=False
    )

    class Meta:
        model = Project
        fields = [
            'summary',
            'description',
            'image',
            'contributors',
            'tags',
            'requests',
            'articles',
            'private'
        ]
        widgets = {
            'contributors': autocomplete_light.MultipleChoiceWidget('UserAutocomplete'),
            'requests': autocomplete_light.MultipleChoiceWidget('FOIARequestAutocomplete'),
            'articles': autocomplete_light.MultipleChoiceWidget('ArticleAutocomplete'),
        }


class ProjectManagerForm(forms.Form):
    """Form for managing a list of projects"""
    projects = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Project.objects.all(),
        widget=autocomplete_light.MultipleChoiceWidget(
            'ProjectManagerAutocomplete',
            attrs={'placeholder': 'Search for a project'}))
