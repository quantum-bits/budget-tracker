from common_models import *
from django.db import models
from itertools import chain
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.models import User


# user.is_superuser can be used to signal that someone can mess with the
# budget....  (it's boolean)
# ./manage.py dumpdata (put in fixture, etc.); can dump select classes, too.
#
# income versus expense lines....  have a boolean: is_expense_line in
# BudgetLine class...+ve #s on expense lines are expenses; -ve #s are credits;
# vice versa for revenue lines.
#

# add method to expense: is_split_transaction (true if there is more than
# one expense_budget_line for the expense

import logging
logger = logging.getLogger(__name__)
LOG_FILENAME = 'constraint.log'
logging.basicConfig(filename=LOG_FILENAME, level = logging.DEBUG, filemode = 'w')


class FiscalYear(models.Model):
    begin_on = models.DateField()
    end_on = models.DateField()

    class Meta:
        ordering = [ 'begin_on' ]

    def __unicode__(self):
        return '{0}-{1}'.format(self.begin_on.year, self.end_on.year)

class SubAccount(models.Model):
    name = models.CharField(max_length=40)
    abbrev = models.CharField(max_length=10)
    amount_available = models.DecimalField(max_digits = 10, decimal_places=2)
    fiscal_year = models.ForeignKey(FiscalYear, related_name = 'subaccounts')

    def total_debit(self, user_preferences):
        tot = 0
        for expense_budget_line in self.expense_budget_line.all():
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def total_credit(self, user_preferences):
        tot = 0
        for expense_budget_line in self.expense_budget_line.all():
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def amount_remaining(self, user_preferences):
        return self.amount_available+self.total_credit(user_preferences)-self.total_debit(user_preferences)

    def __unicode__(self):
        return self.abbrev

    class Meta:
        ordering = [ 'abbrev' ]


class BudgetLine(models.Model):
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=40)
    has_subaccounts = models.BooleanField(default = False)
#    department = models.ForeignKey(Department, related_name = 'budget_lines')
    fiscal_year = models.ForeignKey(FiscalYear, related_name = 'budget_lines')
    amount_available = models.DecimalField(max_digits = 10, decimal_places=2)
#    expense = models.ForeignKey(Expense, related_name='budget_line')
#    subaccount = models.ManyToManyField(SubAccount,
#                                 blank=True, null=True,
#                                 related_name='budget_line')
    class Meta:
        ordering = [ 'code' ]

    def total_debit(self, user_preferences):
        tot = 0
        for expense_budget_line in self.expense_budget_line.all():
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def total_credit(self, user_preferences):
        tot = 0
        for expense_budget_line in self.expense_budget_line.all():
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def amount_remaining(self, user_preferences):
        return self.amount_available+self.total_credit(user_preferences)-self.total_debit(user_preferences)


    def __unicode__(self):
        return '{0} ({1})'.format(self.code, self.name)



class DepartmentMember(Person):
    RANK_CHOICES = (('Inst', 'Instructor'),
                    ('Adj', 'Adjunct Professor'),
                    ('Asst', 'Assistant Professor'),
                    ('Assoc', 'Associate Professor'),
                    ('Full', 'Professor'),
                    ('Staff','Staff'))
#    faculty_id = models.CharField(max_length=25)
#    department = models.ForeignKey(Department, related_name='faculty')
    position = models.CharField(max_length=8, choices=RANK_CHOICES)

    class Meta:
        ordering = ['last_name','first_name']




class CreditCard(models.Model):
    person = models.ForeignKey(DepartmentMember, related_name='credit_card')

    def __unicode__(self):
        return '{0}, {1}'.format(self.person.last_name, self.person.first_name)


class Expense(models.Model):
#    amount = models.DecimalField(max_digits = 10, decimal_places=2)
    checked = models.BooleanField(default = False)
    encumbered = models.BooleanField(default = False)
    future_expense = models.BooleanField(default = False)

#    budget_code = models.ManyToManyField(BudgetLine, through='ExpenseBudgetLine',
#    budget_code = models.ManyToManyField(ExpenseBudgetLine,
#                                         blank=True, null=True,
#                                         related_name='expense')
    description = models.CharField(max_length=50)
    charged_by = models.ForeignKey(DepartmentMember, blank=True, null=True, related_name='expense')

    date = models.DateField()
    credit_card = models.ForeignKey(CreditCard, blank=True, null=True, related_name='expense')
    extra_note = models.TextField(blank=True, null=True)

#    further action required (what?)

    def total_debit(self):
        total_amount = 0
        for expense_budget_line in self.expense_budget_line.all():
            if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                total_amount = total_amount+expense_budget_line.amount
        return total_amount

    def total_credit(self):
        total_amount = 0
        for expense_budget_line in self.expense_budget_line.all():
            if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                total_amount = total_amount+expense_budget_line.amount
        return total_amount

    def include_expense(self, user_preferences):
        if not(self.checked == False and user_preferences.view_checked_only == True) and not(self.encumbered == False and user_preferences.view_encumbrances_only == True) and not(self.future_expense == False and user_preferences.view_future_only == True):
            return True
        else:
            return False

    def is_split_transaction(self):
        number_of_ebls = 0
        for expense_budget_line in self.expense_budget_line.all():
            number_of_ebls = number_of_ebls + 1
        if number_of_ebls > 1:
            return True
        else:
            return False

    def __unicode__(self):
        return '{0}'.format(self.description)

    class Meta:
        ordering = ['-date']

class ExpenseBudgetLine(models.Model):

    DEBIT = -1
    CREDIT = 1

    DEBIT_OR_CREDIT_CHOICES = (
        (DEBIT, 'Debit'),
        (CREDIT, 'Credit')
    )

    amount = models.DecimalField(max_digits = 10, decimal_places=2)
    debit_or_credit = models.IntegerField(choices = DEBIT_OR_CREDIT_CHOICES, default = DEBIT)
    expense = models.ForeignKey(Expense, related_name='expense_budget_line')
    budget_line = models.ForeignKey(BudgetLine, related_name='expense_budget_line')
    subaccount = models.ForeignKey(SubAccount, blank = True, null = True, related_name='expense_budget_line')

    def formattedprice(self):
        return "%01.2f" % self.amount

    def __unicode__(self):
        return '{0}: {1}'.format(self.budget_line, self.expense)

    class Meta:
        ordering = ['-expense__date']


class UserPreferences(models.Model):

    user = models.ForeignKey(User, related_name = 'user_preferences')
#    department_to_view = models.ManyToManyField(Department,
#                                        blank=True, null=True,
#                                        related_name='user_preferences')
    fiscal_year_to_view = models.ForeignKey(FiscalYear, related_name = 'user_preferences')
    view_checked_only = models.BooleanField(default = False)
    view_encumbrances_only = models.BooleanField(default = False)
    view_future_only = models.BooleanField(default = False)

    # move permission_level to django's permissions stuff....

    def __unicode__(self):
        return self.user.last_name

class Note(StampedModel):
#    department = models.ForeignKey(Department, related_name='notes')
    note = models.TextField()
    year = models.ForeignKey(FiscalYear, blank=True, null=True, related_name='notes')

    def __unicode__(self):
        return "{0} on {1}".format(self.department, self.updated_at)
