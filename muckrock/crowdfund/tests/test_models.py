# -*- coding: utf-8 -*-
"""
Tests for crowdfunding models
"""

from django.test import TestCase

from datetime import date, timedelta
from decimal import Decimal
from mock import patch, Mock
from nose.tools import eq_, ok_

from muckrock.crowdfund import models
from muckrock.foia.models import FOIARequest
from muckrock.project.models import Project
from muckrock.task.models import GenericCrowdfundTask

def create_project_crowdfund():
    """Helper function to create a project crowdfund"""
    crowdfund = models.CrowdfundProject.objects.create(
        name='Cool project please help',
        payment_required=Decimal(50),
        date_due=(date.today() + timedelta(30)),
        project=Project.objects.create(title='Test Project')
    )
    crowdfund.save()
    return crowdfund


class TestCrowdfundAbstract(TestCase):
    """Test methods on the abstract base class"""

    def setUp(self):
        self.crowdfund = create_project_crowdfund()

    def test_close_crowdfund(self):
        """Closing a crowdfund should raise a flag and create a task."""
        crowdfund_task_count = GenericCrowdfundTask.objects.count()
        self.crowdfund.close_crowdfund()
        updated_crowdfund = models.CrowdfundProject.objects.get(pk=self.crowdfund.pk)
        ok_(updated_crowdfund.closed, 'The closed flag should be raised.')
        eq_(GenericCrowdfundTask.objects.count(), crowdfund_task_count + 1,
            'A new crowdfund task should be created.')


class TestCrowdfundRequest(TestCase):
    """Test crowdfund a request"""

    fixtures = ['holidays.json', 'jurisdictions.json', 'agency_types.json', 'test_users.json',
                'test_agencies.json', 'test_profiles.json', 'test_foiarequests.json',
                'test_foiacommunications.json']

    def setUp(self):
        self.crowdfund = models.CrowdfundRequest()
        self.foia = FOIARequest.objects.get(pk=1)
        self.crowdfund.foia = self.foia

    def test_unicode(self):
        """The crowdfund should express itself concisely."""
        eq_('%s' % self.crowdfund, 'Crowdfunding for %s' % self.foia)
        self.crowdfund.foia.title = u'Test¢Unicode'
        self.crowdfund.foia.save()
        eq_('%s' % self.crowdfund, 'Crowdfunding for %s' % self.foia)


class TestCrowdfundProject(TestCase):
    """Test crowdfunding a project"""

    def setUp(self):
        self.crowdfund = create_project_crowdfund()
        self.project = self.crowdfund.project

    def test_unicode(self):
        """The crowdfund should express itself concisely."""
        eq_('%s' % self.crowdfund, 'Crowdfunding for Test Project')

    def test_unicode_characters(self):
        """The unicode method should support unicode characters"""
        project_title = u'Test¢s Request'
        self.project = Project.objects.create(title=project_title)
        self.crowdfund.project = self.project
        ok_('%s' % self.crowdfund)

    def test_get_crowdfund_object(self):
        """The crowdfund should have a project being crowdfunded."""
        eq_(self.crowdfund.get_crowdfund_object(), self.project)

@patch('stripe.Charge', Mock())
class TestCrowdfundPayment(TestCase):
    """Test making a payment to a crowdfund"""

    def setUp(self):
        self.crowdfund = create_project_crowdfund()
        self.token = Mock()

    def test_make_payment(self):
        """Should make and return a payment object"""
        amount = Decimal(100)
        payment = self.crowdfund.make_payment(self.token, amount)
        ok_(isinstance(payment, models.CrowdfundProjectPayment),
            'Making a payment should create and return a payment object')

    def test_unlimit_amount(self):
        """The amount paid should be able to exceed the amount required."""
        amount = Decimal(100)
        payment = self.crowdfund.make_payment(self.token, amount)
        eq_(payment.amount, amount,
            'The payment should be made in full despite exceeding the amount required.')

    def test_limit_amount(self):
        """No more than the amount required should be paid if the crowdfund is capped."""
        self.crowdfund.payment_capped = True
        self.crowdfund.save()
        amount = Decimal(100)
        payment = self.crowdfund.make_payment(self.token, amount)
        eq_(payment.amount, self.crowdfund.payment_required,
            'The amount should be capped at the crowdfund\'s required payment.')
        ok_(self.crowdfund.closed,
            'Once the cap has been reached, the crowdfund should close.')
