"""
FOIA Machine urls
"""

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

import debug_toolbar

from muckrock.foiamachine import views
from muckrock.forms import PasswordResetForm

urlpatterns = patterns(
    '',
    url(r'^$', views.Homepage.as_view(), name='index'),
    url(r'^accounts/signup/$', views.Signup.as_view(), name='signup'),
    url(r'^accounts/login/$',
        auth_views.login,
        {'template_name': 'foiamachine/views/registration/login.html'},
        name='login'),
    url(r'^accounts/logout/$',
        auth_views.logout,
        {'next_page': 'index'},
        name='logout'),
    url(r'^accounts/profile/$',
        views.Profile.as_view(),
        name='profile'),
    url(r'^accounts/password_change/$',
        auth_views.password_change,
        {'template_name': 'foiamachine/views/registration/password_change.html',
         'post_change_redirect': 'password-change-done'},
        name='password-change'),
    url(r'^accounts/password_change/done/$',
        auth_views.password_change_done,
        {'template_name': 'foiamachine/views/registration/password_change_done.html'},
        name='password-change-done'),
    url(r'^accounts/password_reset/$',
        auth_views.password_reset,
        {'template_name': 'foiamachine/views/registration/password_reset.html',
         'email_template_name': 'foiamachine/email/password_reset_email.html',
         'post_reset_redirect': 'password-reset-done',
         'password_reset_form': PasswordResetForm},
        name='password-reset'),
    url(r'^accounts/password_reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.password_reset_confirm,
        {'template_name': 'foiamachine/views/registration/password_reset_confirm.html',
         'post_reset_redirect': 'password-reset-complete'},
        name='password-reset-confirm'),
    url(r'^accounts/password_reset/done/$',
        auth_views.password_reset_done,
        {'template_name': 'foiamachine/views/registration/password_reset_done.html'},
        name='password-reset-done'),
    url(r'^accounts/password_reset/complete/$',
        auth_views.password_reset_complete,
        {'template_name': 'foiamachine/views/registration/password_reset_complete.html'},
        name='password-reset-complete'),
    url(r'^foi/create/$',
        views.FoiaMachineRequestCreateView.as_view(),
        name='foi-create'),
    url(r'^foi/(?P<slug>[\w-]+)-(?P<pk>\d+)/$',
        views.FoiaMachineRequestDetailView.as_view(),
        name='foi-detail'),
    url(r'^foi/(?P<slug>[\w-]+)-(?P<pk>\d+)/update/$',
        views.FoiaMachineRequestUpdateView.as_view(),
        name='foi-update'),
    url(r'^foi/(?P<slug>[\w-]+)-(?P<pk>\d+)/delete/$',
        views.FoiaMachineRequestDeleteView.as_view(),
        name='foi-delete'),
    url(r'^foi/(?P<slug>[\w-]+)-(?P<pk>\d+)/share/$',
        views.FoiaMachineRequestShareView.as_view(),
        name='foi-share'),
    url(r'^foi/(?P<foi_slug>[\w-]+)-(?P<foi_pk>\d+)/comms/create/$',
        views.FoiaMachineCommunicationCreateView.as_view(),
        name='comm-create'),
    url(r'^foi/(?P<foi_slug>[\w-]+)-(?P<foi_pk>\d+)/comms/(?P<pk>\d+)/update/$',
        views.FoiaMachineCommunicationUpdateView.as_view(),
        name='comm-update'),
    url(r'^foi/(?P<foi_slug>[\w-]+)-(?P<foi_pk>\d+)/comms/(?P<pk>\d+)/delete/$',
        views.FoiaMachineCommunicationDeleteView.as_view(),
        name='comm-delete'),
    url(r'^autocomplete/', include('autocomplete_light.urls')),
    url(r'^__debug__/', include(debug_toolbar.urls)),
)

if settings.DEBUG:
    urlpatterns += patterns(
        '',
        url(
            r'^media/(?P<path>.*)$',
            'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}
        ),
        url(r'^500/$', TemplateView.as_view(template_name='500.html')),
        url(r'^404/$', TemplateView.as_view(template_name='404.html')),
    )
