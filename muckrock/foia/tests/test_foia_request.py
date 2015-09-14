"""
Tests using nose for the FOIA application
"""

from django.contrib import messages
from django.contrib.auth.models import User, AnonymousUser
from django.core.urlresolvers import reverse, resolve
from django.core import mail
from django.test import TestCase, Client
import nose.tools

import datetime
from datetime import date as real_date
import logging
from operator import attrgetter
import re

from muckrock.crowdfund.models import CrowdfundRequest
from muckrock.crowdfund.forms import CrowdfundRequestForm
from muckrock.foia import tasks
from muckrock.foia.models import FOIARequest, FOIACommunication, END_STATUS
from muckrock.foia.forms import FOIAEmbargoForm
from muckrock.agency.models import Agency
from muckrock.jurisdiction.models import Jurisdiction
from muckrock.task.models import SnailMailTask
from muckrock.tests import get_allowed, post_allowed, post_allowed_bad, get_post_unallowed, get_404

# MockDate breaks pylint-django
# pylint: skip-file

# allow methods that could be functions and too many public methods in tests
# pylint: disable=no-self-use
# pylint: disable=too-many-public-methods

class TestFOIARequestUnit(TestCase):
    """Unit tests for FOIARequests"""
    fixtures = ['holidays.json', 'jurisdictions.json', 'agency_types.json', 'test_users.json',
                'test_agencies.json', 'test_profiles.json', 'test_foiarequests.json',
                'test_foiacommunications.json']

    def setUp(self):
        """Set up tests"""
        # pylint: disable=C0103

        mail.outbox = []

        self.foia = FOIARequest.objects.get(pk=1)

    # models
    def test_foia_model_unicode(self):
        """Test FOIA Request model's __unicode__ method"""
        nose.tools.eq_(unicode(self.foia), 'Test 1')

    def test_foia_model_url(self):
        """Test FOIA Request model's get_absolute_url method"""

        nose.tools.eq_(self.foia.get_absolute_url(),
            reverse('foia-detail', kwargs={'idx': self.foia.pk, 'slug': 'test-1',
                                           'jurisdiction': 'massachusetts',
                                           'jidx': self.foia.jurisdiction.pk}))

    def test_foia_model_editable(self):
        """Test FOIA Request model's is_editable method"""

        foias = FOIARequest.objects.all().order_by('id')[:5]
        for foia in foias[:5]:
            if foia.status in ['started']:
                nose.tools.assert_true(foia.is_editable())
            else:
                nose.tools.assert_false(foia.is_editable())

    def test_foia_email(self):
        """Test FOIA sending an email to the user when a FOIA request is updated"""

        nose.tools.eq_(len(mail.outbox), 0)

        self.foia.status = 'submitted'
        self.foia.save()
        self.foia.submit()
        nose.tools.eq_(len(mail.outbox), 0)

        self.foia.status = 'processed'
        self.foia.save()
        self.foia.update()
        nose.tools.eq_(len(mail.outbox), 1)
        nose.tools.eq_(mail.outbox[0].to, [self.foia.user.email])

        # already updated, no additional email
        self.foia.status = 'fix'
        self.foia.save()
        self.foia.update()
        nose.tools.eq_(len(mail.outbox), 2)

        # if the user views it and clears the updated flag, we do get another email
        self.foia.updated = False
        self.foia.save()
        self.foia.status = 'rejected'
        self.foia.save()
        self.foia.update()
        nose.tools.eq_(len(mail.outbox), 3)

        foia = FOIARequest.objects.get(pk=6)
        foia.status = 'submitted'
        foia.save()
        foia.submit()
        nose.tools.eq_(mail.outbox[-1].from_email, '%s@requests.muckrock.com' % foia.get_mail_id())
        nose.tools.eq_(mail.outbox[-1].to, ['test@agency1.gov'])
        nose.tools.eq_(mail.outbox[-1].bcc,
                       ['other_a@agency1.gov', 'other_b@agency1.gov', 'diagnostics@muckrock.com'])
        nose.tools.eq_(mail.outbox[-1].subject,
                       'Mass Law Request: %s' % foia.title)
        nose.tools.eq_(foia.status, 'ack')
        nose.tools.eq_(foia.date_submitted, datetime.date.today())
        nose.tools.ok_(foia.date_due > datetime.date.today())

    def test_foia_viewable(self):
        """Test all the viewable and embargo functions"""

        user1 = User.objects.get(pk=1)
        user2 = User.objects.get(pk=2)

        foias = list(FOIARequest.objects.filter(id__in=[1, 5, 11, 12, 13, 14]).order_by('id'))
        # 0 = draft
        # 1 = completed, no embargo
        # 2 = completed, embargoed, no expiration
        # 3 = completed, embargoed, no expiration
        # 4 = completed, embargoed, no expiration
        foias[1].date_embargo = datetime.date.today() + datetime.timedelta(10)
        foias[2].date_embargo = datetime.date.today()
        foias[3].date_embargo = datetime.date.today() - datetime.timedelta(1)
        foias[3].embargo = False
        foias[4].date_embargo = datetime.date.today() - datetime.timedelta(10)
        foias[4].embargo = False

        # check manager get_viewable against models is_viewable
        viewable_foias = FOIARequest.objects.get_viewable(user1)
        for foia in FOIARequest.objects.all():
            if foia in viewable_foias:
                nose.tools.assert_true(foia.is_viewable(user1))
            else:
                nose.tools.assert_false(foia.is_viewable(user1))

        viewable_foias = FOIARequest.objects.get_viewable(user2)
        for foia in FOIARequest.objects.all():
            if foia in viewable_foias:
                nose.tools.assert_true(foia.is_viewable(user2))
            else:
                nose.tools.assert_false(foia.is_viewable(user2))

        viewable_foias = FOIARequest.objects.get_public()
        for foia in FOIARequest.objects.all():
            if foia in viewable_foias:
                nose.tools.assert_true(foia.is_viewable(AnonymousUser()))
            else:
                nose.tools.assert_false(foia.is_viewable(AnonymousUser()))

        nose.tools.assert_true(foias[0].is_viewable(user1))
        nose.tools.assert_true(foias[1].is_viewable(user1))
        nose.tools.assert_true(foias[2].is_viewable(user1))
        nose.tools.assert_true(foias[3].is_viewable(user1))
        nose.tools.assert_true(foias[4].is_viewable(user1))

        nose.tools.assert_false(foias[0].is_viewable(user2))
        nose.tools.assert_true (foias[1].is_viewable(user2))
        nose.tools.assert_false(foias[2].is_viewable(user2))
        nose.tools.assert_true (foias[3].is_viewable(user2))
        nose.tools.assert_true (foias[4].is_viewable(user2))

        nose.tools.assert_false(foias[0].is_viewable(AnonymousUser()))
        nose.tools.assert_true (foias[1].is_viewable(AnonymousUser()))
        nose.tools.assert_false(foias[2].is_viewable(AnonymousUser()))
        nose.tools.assert_true (foias[3].is_viewable(AnonymousUser()))
        nose.tools.assert_true (foias[4].is_viewable(AnonymousUser()))

    def test_foia_set_mail_id(self):
        """Test the set_mail_id function"""
        foia = FOIARequest.objects.get(pk=17)
        foia.set_mail_id()
        mail_id = foia.mail_id
        nose.tools.ok_(re.match(r'\d{1,4}-\d{8}', mail_id))

        foia.set_mail_id()
        nose.tools.eq_(mail_id, foia.mail_id)

    def test_foia_followup(self):
        """Make sure the follow up date is set correctly"""
        # pylint: disable=protected-access
        foia = FOIARequest.objects.get(pk=15)
        foia.followup()
        nose.tools.assert_in('I can expect', mail.outbox[-1].body)
        nose.tools.eq_(foia.date_followup,
                       datetime.date.today() + datetime.timedelta(foia._followup_days()))

        nose.tools.eq_(foia._followup_days(), 15)

        foia.date_estimate = datetime.date(2100, 1, 1)
        foia.followup()
        nose.tools.assert_in('I am still', mail.outbox[-1].body)
        nose.tools.eq_(foia._followup_days(), 183)

        foia.date_estimate = datetime.date(2000, 1, 1)
        foia.followup()
        nose.tools.assert_in('check on the status', mail.outbox[-1].body)
        nose.tools.eq_(foia._followup_days(), 15)

    def test_foia_followup_estimated(self):
        """If request has an estimated date, returns correct number of days"""
        # pylint: disable=protected-access
        foia = FOIARequest.objects.get(pk=15)
        foia.date_estimate = datetime.date.today() + datetime.timedelta(2)
        nose.tools.eq_(foia._followup_days(), 183)

     # manager
    def test_manager_get_submitted(self):
        """Test the FOIA Manager's get_submitted method"""

        submitted_foias = FOIARequest.objects.get_submitted()
        for foia in FOIARequest.objects.all():
            if foia in submitted_foias:
                nose.tools.ok_(foia.status != 'started')
            else:
                nose.tools.ok_(foia.status == 'started')

    def test_manager_get_done(self):
        """Test the FOIA Manager's get_done method"""

        done_foias = FOIARequest.objects.get_done()
        for foia in FOIARequest.objects.all():
            if foia in done_foias:
                nose.tools.ok_(foia.status == 'done')
            else:
                nose.tools.ok_(
                        foia.status in ['started', 'submitted', 'processed',
                                        'fix', 'rejected', 'payment'])


class TestFOIAFunctional(TestCase):
    """Functional tests for FOIA"""
    fixtures = ['holidays.json', 'jurisdictions.json', 'agency_types.json', 'test_users.json',
                'test_profiles.json', 'test_foiarequests.json', 'test_foiacommunications.json',
                'test_agencies.json']

    # views
    def test_foia_list(self):
        """Test the foia-list view"""

        response = get_allowed(self.client, reverse('foia-list'),
                ['lists/request_list.html', 'lists/base_list.html'])
        nose.tools.eq_(set(response.context['object_list']),
            set(FOIARequest.objects.get_viewable(AnonymousUser()).order_by('-date_submitted')[:12]))

    def test_foia_list_user(self):
        """Test the foia-list-user view"""

        for user_pk in [1, 2]:
            response = get_allowed(self.client,
                                   reverse('foia-list-user', kwargs={'user_pk': user_pk}),
                                   ['lists/request_list.html', 'lists/base_list.html'])
            user = User.objects.get(pk=user_pk)
            nose.tools.eq_(set(response.context['object_list']),
                           set(FOIARequest.objects.get_viewable(AnonymousUser()).filter(user=user)))
            nose.tools.ok_(all(foia.user == user for foia in response.context['object_list']))

    def test_foia_sorted_list(self):
        """Test sorting on foia-list view"""

        for field in ['title', 'date_submitted', 'status']:
            for order in ['asc', 'desc']:
                response = get_allowed(self.client, reverse('foia-list') +
                                       '?sort=%s&order=%s' % (field, order),
                                       ['lists/request_list.html', 'lists/base_list.html'])
                nose.tools.eq_([f.title for f in response.context['object_list']],
                               [f.title for f in sorted(response.context['object_list'],
                                                        key=attrgetter(field),
                                                        reverse=order=='desc')])

    def test_foia_detail(self):
        """Test the foia-detail view"""

        foia = FOIARequest.objects.get(pk=2)
        get_allowed(self.client,
                    reverse('foia-detail', kwargs={'idx': foia.pk, 'slug': foia.slug,
                                                   'jurisdiction': foia.jurisdiction.slug,
                                                   'jidx': foia.jurisdiction.pk}),
                    ['foia/detail.html', 'base.html'],
                    context = {'foia': foia})

    def test_feeds(self):
        """Test the RSS feed views"""

        get_allowed(self.client, reverse('foia-submitted-feed'))
        get_allowed(self.client, reverse('foia-done-feed'))

    def test_404_views(self):
        """Test views that should give a 404 error"""

        get_404(self.client, reverse('foia-detail', kwargs={'idx': 1, 'slug': 'test-c',
                                                       'jurisdiction': 'massachusetts',
                                                       'jidx': 1}))
        get_404(self.client, reverse('foia-detail', kwargs={'idx': 2, 'slug': 'test-c',
                                                       'jurisdiction': 'massachusetts',
                                                       'jidx': 1}))

    def test_unallowed_views(self):
        """Test private views while not logged in"""

        foia = FOIARequest.objects.get(pk=2)
        get_post_unallowed(self.client, reverse('foia-draft',
                                           kwargs={'jurisdiction': foia.jurisdiction.slug,
                                                   'jidx': foia.jurisdiction.pk,
                                                   'idx': foia.pk, 'slug': foia.slug}))

    def test_auth_views(self):
        """Test private views while logged in"""

        foia = FOIARequest.objects.get(pk=1)
        self.client.login(username='adam', password='abc')

        # get authenticated pages
        get_allowed(self.client, reverse('foia-create'),
                    ['forms/foia/create.html'])

        get_allowed(self.client, reverse('foia-draft',
                                    kwargs={'jurisdiction': foia.jurisdiction.slug,
                                            'jidx': foia.jurisdiction.pk,
                                            'idx': foia.pk, 'slug': foia.slug}),
                    ['forms/foia/draft.html', 'forms/base_form.html'])

        get_404(self.client, reverse('foia-draft',
                                kwargs={'jurisdiction': foia.jurisdiction.slug,
                                        'jidx': foia.jurisdiction.pk,
                                        'idx': foia.pk, 'slug': 'bad_slug'}))


    def test_foia_submit_views(self):
        """Test submitting a FOIA request"""

        foia = FOIARequest.objects.get(pk=1)
        agency = Agency.objects.get(pk=3)
        self.client.login(username='adam', password='abc')

        # test for submitting a foia request for enough credits
        # tests for the wizard

        foia_data = {'title': 'test a', 'request': 'updated request', 'submit': 'Submit',
                     'agency': agency.pk, 'combo-name': agency.name}

        kwargs = {'jurisdiction': foia.jurisdiction.slug,
                  'jidx': foia.jurisdiction.pk,
                  'idx': foia.pk, 'slug': foia.slug}
        draft = reverse('foia-draft', kwargs=kwargs)
        kwargs = {'jurisdiction': foia.jurisdiction.slug,
                  'jidx': foia.jurisdiction.pk,
                  'idx': foia.pk, 'slug': 'test-a'}
        detail = reverse('foia-detail', kwargs=kwargs)
        post_allowed(self.client, draft, foia_data, detail)

        foia = FOIARequest.objects.get(title='test a')
        nose.tools.ok_(foia.first_request().startswith('updated request'))
        nose.tools.eq_(foia.status, 'submitted')

    def test_foia_save_views(self):
        """Test saving a FOIA request"""

        foia = FOIARequest.objects.get(pk=6)
        self.client.login(username='bob', password='abc')

        foia_data = {'title': 'Test 6', 'request': 'saved request', 'submit': 'Save'}

        kwargs = {'jurisdiction': foia.jurisdiction.slug,
                  'jidx': foia.jurisdiction.pk,
                  'idx': foia.pk, 'slug': foia.slug}
        draft = reverse('foia-draft', kwargs=kwargs)
        detail = reverse('foia-detail', kwargs=kwargs)
        chain = [('http://testserver' + url, 302) for url in (detail, draft)]
        response = self.client.post(draft, foia_data, follow=True)
        nose.tools.eq_(response.status_code, 200)
        nose.tools.eq_(response.redirect_chain, chain)

        foia = FOIARequest.objects.get(title='Test 6')
        nose.tools.ok_(foia.first_request().startswith('saved request'))
        nose.tools.eq_(foia.status, 'started')

    def test_action_views(self):
        """Test action views"""

        foia = FOIARequest.objects.get(pk=1)
        self.client.login(username='adam', password='abc')

        foia = FOIARequest.objects.get(pk=18)
        get_allowed(self.client, reverse('foia-pay',
                                    kwargs={'jurisdiction': foia.jurisdiction.slug,
                                            'jidx': foia.jurisdiction.pk,
                                            'idx': foia.pk, 'slug': foia.slug}),
                    ['foia/detail.html', 'base.html'])


class TestFOIAIntegration(TestCase):
    """Integration tests for FOIA"""

    fixtures = ['holidays.json', 'jurisdictions.json', 'agency_types.json', 'test_users.json',
                'test_agencies.json', 'test_profiles.json', 'test_foiarequests.json',
                'test_foiacommunications.json']

    def setUp(self):
        """Set up tests"""
        # pylint: disable=C0103
        # pylint: disable=bad-super-call
        # pylint: disable=C0111

        mail.outbox = []

        import muckrock.foia.models.request

        # Replace real date and time with mock ones so we can control today's/now's value
        # Unfortunately need to monkey patch this a lot of places, and it gets rather ugly
        #http://tech.yunojuno.com/mocking-dates-with-django
        class MockDate(datetime.date):
            def __add__(self, other):
                d = super(MockDate, self).__add__(other)
                return MockDate(d.year, d.month, d.day)
            class MockDateType(type):
                "Used to ensure the FakeDate returns True to function calls."
                def __instancecheck__(self, instance):
                    return isinstance(instance, real_date)
            # this forces the FakeDate to return True to the isinstance date check
            __metaclass__ = MockDateType
        class MockDateTime(datetime.datetime):
            def date(self):
                return MockDate(self.year, self.month, self.day)

        self.orig_date = datetime.date
        self.orig_datetime = datetime.datetime
        datetime.date = MockDate
        datetime.datetime = MockDateTime
        muckrock.foia.models.request.date = datetime.date
        muckrock.foia.models.request.datetime = datetime.datetime
        def save(self, *args, **kwargs):
            if self.date_followup:
                self.date_followup = MockDateTime(self.date_followup.year,
                                                  self.date_followup.month,
                                                  self.date_followup.day)
            if self.date_done:
                self.date_done = MockDateTime(self.date_done.year,
                                              self.date_done.month,
                                              self.date_done.day)
            super(FOIARequest, self).save(*args, **kwargs)
        self.FOIARequest_save = muckrock.foia.models.FOIARequest.save
        muckrock.foia.models.FOIARequest.save = save
        self.set_today(datetime.date(2010, 1, 1))

    def tearDown(self):
        """Tear down tests"""
        # pylint: disable=C0103

        import muckrock.foia.models

        # restore the original date and datetime for other tests
        datetime.date = self.orig_date
        datetime.datetime = self.orig_datetime
        muckrock.foia.models.request.date = datetime.date
        muckrock.foia.models.request.datetime = datetime.datetime
        muckrock.foia.models.FOIARequest.save = self.FOIARequest_save

    def set_today(self, date):
        """Set what datetime thinks today is"""
        datetime.date.today = classmethod(lambda cls: cls(date.year, date.month, date.day))
        datetime.datetime.now = classmethod(lambda cls: cls(date.year, date.month, date.day))

    def test_request_lifecycle_no_email(self):
        """Test a request going through the full cycle as if we had to physically mail it"""
        # pylint: disable=too-many-statements
        # pylint: disable=protected-access

        user = User.objects.get(username='adam')
        agency = Agency.objects.get(pk=3)
        jurisdiction = Jurisdiction.objects.get(pk=1)
        cal = jurisdiction.get_calendar()

        self.set_today(datetime.date(2010, 2, 1))
        nose.tools.eq_(len(mail.outbox), 0)

        ## create and submit request
        foia = FOIARequest.objects.create(
            user=user, title='Test with no email', slug='test-with-no-email',
            status='submitted', jurisdiction=jurisdiction, agency=agency)
        comm = FOIACommunication.objects.create(
            foia=foia, from_who='Muckrock', to_who='Test Agency', date=datetime.datetime.now(),
            response=False, communication=u'Test communication')
        foia.submit()

        # check that a snail mail task was created
        nose.tools.ok_(
            SnailMailTask.objects.filter(
                communication=comm, category='n').exists())

        ## two days pass, then the admin mails in the request
        self.set_today(datetime.date.today() + datetime.timedelta(2))
        foia.status = 'processed'
        foia.update_dates()
        foia.save()

        # make sure dates were set correctly
        nose.tools.eq_(foia.date_submitted, datetime.date(2010, 2, 3))
        nose.tools.eq_(foia.date_due, cal.business_days_from(datetime.date.today(),
                                                             jurisdiction.get_days()))
        nose.tools.eq_(foia.date_followup.date(),
                       max(foia.date_due, foia.last_comm().date.date() +
                                          datetime.timedelta(foia._followup_days())))
        nose.tools.ok_(foia.days_until_due is None)
        # no more mail should have been sent
        nose.tools.eq_(len(mail.outbox), 0)

        old_date_due = foia.date_due

        ## after 5 days agency replies with a fix needed
        self.set_today(datetime.date.today() + datetime.timedelta(5))
        comm = FOIACommunication.objects.create(
            foia=foia, from_who='Test Agency', to_who='Muckrock', date=datetime.datetime.now(),
            response=True, communication='Test communication')
        foia.status = 'fix'
        foia.save()
        foia.update(comm.anchor())

        # check that a notification has been sent to the user
        nose.tools.eq_(len(mail.outbox), 1)
        nose.tools.ok_(mail.outbox[-1].subject.startswith('[MuckRock]'))
        nose.tools.eq_(mail.outbox[-1].to, ['adam@example.com'])
        # make sure dates were set correctly
        nose.tools.eq_(foia.date_submitted, datetime.date(2010, 2, 3))
        nose.tools.ok_(foia.date_due is None)
        nose.tools.ok_(foia.date_followup is None)
        nose.tools.eq_(foia.days_until_due, cal.business_days_between(datetime.date(2010, 2, 8),
                                                                      old_date_due))

        old_days_until_due = foia.days_until_due

        ## after 10 days the user submits the fix and the admin submits it right away
        self.set_today(datetime.date.today() + datetime.timedelta(10))
        comm = FOIACommunication.objects.create(
            foia=foia, from_who='Muckrock', to_who='Test Agency', date=datetime.datetime.now(),
            response=False, communication='Test communication')
        foia.status = 'submitted'
        foia.save()
        foia.submit()

        # check that another snail mail task is created
        nose.tools.ok_(
            SnailMailTask.objects.filter(
                communication=comm, category='u').exists())

        foia.status = 'processed'

        foia.update_dates()
        foia.save()

        # make sure dates were set correctly
        nose.tools.eq_(foia.date_submitted, datetime.date(2010, 2, 3))
        nose.tools.eq_(foia.date_due, cal.business_days_from(datetime.date.today(),
                                                             old_days_until_due))
        nose.tools.eq_(foia.date_followup.date(),
                       max(foia.date_due, foia.last_comm().date.date() +
                                          datetime.timedelta(foia._followup_days())))
        nose.tools.ok_(foia.days_until_due is None)

        old_date_due = foia.date_due

        ## after 4 days agency replies with the documents
        self.set_today(datetime.date.today() + datetime.timedelta(4))
        comm = FOIACommunication.objects.create(
            foia=foia, from_who='Test Agency', to_who='Muckrock', date=datetime.date.today(),
            response=True, communication='Test communication')
        foia.status = 'done'
        foia.save()
        foia.update(comm.anchor())

        # check that a notification has not been sent to the user since they habe not
        # cleared the updated flag yet by viewing it
        nose.tools.eq_(len(mail.outbox), 2)
        # make sure dates were set correctly
        nose.tools.eq_(foia.date_submitted, datetime.date(2010, 2, 3))
        nose.tools.eq_(foia.date_due, old_date_due)
        nose.tools.ok_(foia.date_followup is None)
        nose.tools.ok_(foia.days_until_due is None)


class FOIAEmbargoTests(TestCase):
    """Embargoing a request hides it from public view."""
    fixtures = ['holidays.json', 'jurisdictions.json', 'agency_types.json', 'test_users.json',
                'test_agencies.json', 'test_profiles.json', 'test_foiarequests.json',
                'test_foiacommunications.json']

    def setUp(self):
        self.foia = FOIARequest.objects.get(pk=3)
        self.user = self.foia.user
        self.client = Client()
        self.client.login(username=self.user.username, password='abc')
        self.url = reverse('foia-embargo', kwargs={
            'jurisdiction': self.foia.jurisdiction.slug,
            'jidx': self.foia.jurisdiction.pk,
            'idx': self.foia.pk,
            'slug': self.foia.slug
        })

    def test_basic_embargo(self):
        """The embargo should be accepted if the owner can embargo and edit the request."""
        nose.tools.ok_(self.foia.editable_by(self.user),
            'The request should be editable by the user.')
        nose.tools.ok_(self.user.profile.can_embargo(),
            'The user should be allowed to embargo.')
        nose.tools.ok_(self.foia.status not in END_STATUS,
            'The request should not be closed.')
        data = {'embargo': 'create'}
        response = self.client.post(self.url, data, follow=True)
        self.foia.refresh_from_db()
        nose.tools.eq_(response.status_code, 200)
        nose.tools.ok_(self.foia.embargo, 'An embargo should be set on the request.')

    def test_no_permission_to_edit(self):
        """Users without permission to edit the request should not be able to change the embargo"""
        user_without_permission = User.objects.get(pk=2)
        nose.tools.ok_(not self.foia.editable_by(user_without_permission))
        nose.tools.ok_(user_without_permission.profile.can_embargo())
        data = {'embargo': 'create'}
        client_without_permission = Client()
        client_without_permission.login(username=user_without_permission.username, password='abc')
        response = client_without_permission.post(self.url, data, follow=True)
        self.foia.refresh_from_db()
        nose.tools.eq_(response.status_code, 200)
        nose.tools.ok_(not self.foia.embargo, 'The embargo should not be set on the request.')

    def test_no_permission_to_embargo(self):
        """Users without permission to embargo the request should not be allowed to do so."""
        user_without_permission = User.objects.get(pk=5)
        self.foia.user = user_without_permission
        self.foia.save()
        nose.tools.ok_(self.foia.editable_by(user_without_permission))
        nose.tools.ok_(not user_without_permission.profile.can_embargo())
        data = {'embargo': 'create'}
        client_without_permission = Client()
        client_without_permission.login(username=user_without_permission.username, password='abc')
        response = client_without_permission.post(self.url, data, follow=True)
        self.foia.refresh_from_db()
        nose.tools.eq_(response.status_code, 200)
        nose.tools.ok_(not self.foia.embargo, 'The embargo should not be set on the request.')

    def test_unembargo(self):
        """
        The embargo should be removable by editors of the request.
        Any user should be allowed to remove an embargo, even if they cannot apply one.
        """
        user_without_permission = User.objects.get(pk=5)
        self.foia.user = user_without_permission
        self.foia.embargo = True
        self.foia.save()
        nose.tools.assert_true(self.foia.embargo)
        nose.tools.assert_true(self.foia.editable_by(user_without_permission))
        nose.tools.assert_false(user_without_permission.profile.can_embargo())
        data = {'embargo': 'delete'}
        client_without_permission = Client()
        client_without_permission.login(username=user_without_permission.username, password='abc')
        response = client_without_permission.post(self.url, data, follow=True)
        self.foia.refresh_from_db()
        nose.tools.eq_(response.status_code, 200)
        nose.tools.assert_false(self.foia.embargo,
            'The embargo should be removed from the request.')

    def test_embargo_details(self):
        """
        If the request is in a closed state, it needs a date to be applied.
        If the user has permission, apply a permanent embargo.
        """
        self.foia.status = 'rejected'
        self.foia.save()
        default_expiration_date = datetime.date.today() + datetime.timedelta(1)
        embargo_form = FOIAEmbargoForm({
            'permanent_embargo': True,
            'date_embargo': default_expiration_date
        })
        nose.tools.assert_true(embargo_form.is_valid(), 'Form should validate.')
        nose.tools.assert_true(self.user.profile.can_embargo_permanently())
        data = {'embargo': 'create'}
        data.update(embargo_form.data)
        response = self.client.post(self.url, data, follow=True)
        self.foia.refresh_from_db()
        nose.tools.eq_(response.status_code, 200)
        nose.tools.assert_true(self.foia.embargo,
            'An embargo should be set on the request.')
        nose.tools.eq_(self.foia.date_embargo, default_expiration_date,
            'An expiration date should be set on the request.')
        nose.tools.assert_true(self.foia.permanent_embargo,
            'A permanent embargo should be set on the request.')

    def test_cannot_permanent_embargo(self):
        """Users who cannot set permanent embargoes shouldn't be able to."""
        user_without_permission = User.objects.get(pk=2)
        self.foia.user = user_without_permission
        self.foia.save()
        embargo_form = FOIAEmbargoForm({'permanent_embargo': True})
        nose.tools.assert_true(user_without_permission.profile.can_embargo())
        nose.tools.assert_false(user_without_permission.profile.can_embargo_permanently())
        nose.tools.assert_true(embargo_form.is_valid(), 'Form should validate.')
        data = {'embargo': 'create'}
        data.update(embargo_form.data)
        client_without_permission = Client()
        client_without_permission.login(username=user_without_permission.username, password='abc')
        response = client_without_permission.post(self.url, data, follow=True)
        self.foia.refresh_from_db()
        nose.tools.eq_(response.status_code, 200)
        nose.tools.assert_true(self.foia.embargo,
            'An embargo should be set on the request.')
        nose.tools.assert_false(self.foia.permanent_embargo,
            'A permanent embargo should not be set on the request.')

    def test_update_embargo(self):
        """The embargo should be able to be updated."""
        self.foia.embargo = True
        self.foia.embargo_permanent = True
        self.foia.date_embargo = datetime.date.today() + datetime.timedelta(5)
        self.foia.status = 'rejected'
        self.foia.save()
        self.foia.refresh_from_db()
        nose.tools.assert_true(self.foia.embargo)
        expiration = datetime.date.today() + datetime.timedelta(15)
        embargo_form = FOIAEmbargoForm({
            'date_embargo': expiration
        })
        data = {'embargo': 'update'}
        data.update(embargo_form.data)
        response = self.client.post(self.url, data, follow=True)
        self.foia.refresh_from_db()
        nose.tools.eq_(response.status_code, 200)
        nose.tools.assert_true(self.foia.embargo,
            'The embargo should stay applied to the request.')
        nose.tools.assert_false(self.foia.permanent_embargo,
            'The permanent embargo should be repealed.')
        nose.tools.eq_(self.foia.date_embargo, expiration,
            'The embargo expiration date should be updated.')

    def test_expire_embargo(self):
        """Any requests with an embargo date before today should be unembargoed"""
        self.foia.embargo = True
        self.foia.date_embargo = datetime.date.today() - datetime.timedelta(1)
        self.foia.status = 'rejected'
        self.foia.save()
        tasks.embargo_expire()
        self.foia.refresh_from_db()
        nose.tools.assert_false(self.foia.embargo,
            'The embargo should be repealed.')

    def test_do_not_expire_permanent(self):
        """A request with a permanent embargo should stay embargoed."""
        self.foia.embargo = True
        self.foia.permanent_embargo = True
        self.foia.date_embargo = datetime.date.today() - datetime.timedelta(1)
        self.foia.status = 'rejected'
        self.foia.save()
        tasks.embargo_expire()
        self.foia.refresh_from_db()
        nose.tools.assert_true(self.foia.embargo,
            'The embargo should remain embargoed.')

    def test_do_not_expire_no_date(self):
        """A request without an expiration date should not expire."""
        self.foia.embargo = True
        self.foia.save()
        tasks.embargo_expire()
        self.foia.refresh_from_db()
        nose.tools.assert_true(self.foia.embargo,
            'The embargo should remain embargoed.')

    def test_expire_after_date(self):
        """Only after the date_embargo passes should the embargo expire."""
        self.foia.embargo = True
        self.foia.date_embargo = datetime.date.today()
        self.foia.status = 'rejected'
        self.foia.save()
        tasks.embargo_expire()
        self.foia.refresh_from_db()
        nose.tools.assert_true(self.foia.embargo,
            'The embargo should remain embargoed.')

    def test_set_date_on_status_change(self):
        """
        If the request status is changed to an end status and it is embargoed,
        set the embargo expiration date to 30 days from today.
        """
        default_expiration_date = datetime.date.today() + datetime.timedelta(30)
        self.foia.embargo = True
        self.foia.save()
        self.foia.status = 'rejected'
        self.foia.save()
        self.foia.refresh_from_db()
        nose.tools.assert_true(self.foia.embargo and self.foia.status in END_STATUS)
        nose.tools.eq_(self.foia.date_embargo, default_expiration_date,
            'The embargo should be given an expiration date.')

    def test_set_date_exception(self):
        """
        If the request is changed to an inactive state, it is embargoed, and there is no
        previously set expiration date, then set the embargo expiration to its default value.
        """
        extended_expiration_date = datetime.date.today() + datetime.timedelta(15)
        self.foia.embargo = True
        self.foia.date_embargo = extended_expiration_date
        self.foia.status = 'rejected'
        self.foia.save()
        self.foia.refresh_from_db()
        nose.tools.assert_true(self.foia.embargo and self.foia.status in END_STATUS)
        nose.tools.eq_(self.foia.date_embargo, extended_expiration_date,
            'The embargo should not change the extended expiration date.')

    def test_remove_date(self):
        """The embargo date should be removed if the request is changed to an active state."""
        default_expiration_date = datetime.date.today() + datetime.timedelta(30)
        self.foia.embargo = True
        self.foia.save()
        self.foia.status = 'rejected'
        self.foia.save()
        self.foia.refresh_from_db()
        nose.tools.assert_true(self.foia.embargo and self.foia.status in END_STATUS)
        nose.tools.eq_(self.foia.date_embargo, default_expiration_date,
            'The embargo should be given an expiration date.')
        self.foia.status = 'appealing'
        self.foia.save()
        self.foia.refresh_from_db()
        nose.tools.assert_false(self.foia.embargo and self.foia.status in END_STATUS)
        nose.tools.ok_(not self.foia.date_embargo,
            'The embargo date should be removed.')
