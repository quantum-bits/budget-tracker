from common_models import *
from django.db import models
from itertools import chain
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.models import User
from django.db.models import Q
from decimal import *

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

    def dollar_format_parentheses(self, amount, include_zero):
        if amount>0:
            return "{0:.2f}".format(amount)
        elif amount<0:
            return "({0:.2f})".format(-amount)
        elif amount==0 and include_zero:
            return '0.00'
        else:
            return ''

    def subaccount_totals_summary(self, user_preferences):
        subaccount_summary_list = []
        total_share_remaining = 0
        for subaccount in self.subaccounts.filter(fiscal_year = user_preferences.fiscal_year_to_view):
            account_owner = subaccount.account_owners.filter(department_member=self)[0]
            remaining = subaccount.amount_remaining(user_preferences)
            amount_remaining_is_negative = False
            if remaining < 0:
                amount_remaining_is_negative = True
            subaccount_summary_list.append({
                    'subaccount': subaccount, 
                    'fraction': "{0:.0f}%".format(100*account_owner.fraction),
                    'available': self.dollar_format_parentheses(subaccount.amount_available, True),
                    'available_share': self.dollar_format_parentheses(subaccount.amount_available*Decimal(str(account_owner.fraction)), True),
                    'amount_remaining': self.dollar_format_parentheses(remaining,True),
                    'amount_remaining_share': self.dollar_format_parentheses(subaccount.amount_remaining(user_preferences)*Decimal(str(account_owner.fraction)), True),
                    'amount_remaining_is_negative': amount_remaining_is_negative
                    })
            total_share_remaining = total_share_remaining + subaccount.amount_remaining(user_preferences)*Decimal(str(account_owner.fraction))
        total_is_negative = False
        if total_share_remaining < 0:
            total_is_negative = True
        return subaccount_summary_list, self.dollar_format_parentheses(total_share_remaining, True),total_is_negative

    class Meta:
        ordering = ['last_name','first_name']



class SubAccount(models.Model):
    name = models.CharField(max_length=40)
    abbrev = models.CharField(max_length=30)
    amount_available = models.DecimalField(max_digits = 10, decimal_places=2)
    fiscal_year = models.ForeignKey(FiscalYear, related_name = 'subaccounts')
    owned_by = models.ManyToManyField(DepartmentMember, through='AccountOwner',
                                      blank=True, null=True,
                                      related_name = 'subaccounts')

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

    def debit_month(self, user_preferences, month, year):
        tot = 0
        for expense_budget_line in self.expense_budget_line.filter(Q(expense__date__month=month)
                                                                   &Q(expense__date__year=year)):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def credit_month(self, user_preferences, month, year):
        tot = 0
        for expense_budget_line in self.expense_budget_line.filter(Q(expense__date__month=month)
                                                                   &Q(expense__date__year=year)):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def retrieve_breakdown(self, user_preferences, month, year):
        text_block=''
        num_chars_expense = 11
        for expense_budget_line in self.expense_budget_line.filter(Q(expense__date__month=month)
                                                                   &Q(expense__date__year=year)):
            if expense_budget_line.expense.include_expense(user_preferences):
                date_string = expense_budget_line.expense.date.strftime("%m/%d/%y")
                is_credit = False
                if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                    is_credit = True
                amount_string = dollar_format_local(expense_budget_line.amount, is_credit)
                space_len = max(0,num_chars_expense-len(amount_string))
                filler = space_len*' '
                text_block=text_block+date_string+'   '+amount_string+filler+expense_budget_line.expense.description+'\n'
        return text_block


    def __unicode__(self):
        if self.abbrev == self.name:
            return self.abbrev
        else:
            return self.abbrev+' ('+self.name+')'

    class Meta:
        ordering = [ 'abbrev' ]

class Department(models.Model):
    name = models.CharField(max_length=80)

    def __unicode__(self):
        return self.name

    def total_for_month(self, user_preferences, month, year):
        tot = 0
        for budget_line in self.budget_lines.all():
            tot = tot+budget_line.credit_month(user_preferences, month, year)-budget_line.debit_month(user_preferences, month, year)
        return tot

class BudgetLine(models.Model):
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=40)
    has_subaccounts = models.BooleanField(default = False)
    department = models.ForeignKey(Department, null=True, related_name = 'budget_lines')
    fiscal_year = models.ForeignKey(FiscalYear, related_name = 'budget_lines')
    amount_available = models.DecimalField(max_digits = 10, decimal_places=2)

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

    def debit_month(self, user_preferences, month, year):
        tot = 0
        for expense_budget_line in self.expense_budget_line.filter(Q(expense__date__month=month)
                                                                   &Q(expense__date__year=year)):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def credit_month(self, user_preferences, month, year):
        tot = 0
        for expense_budget_line in self.expense_budget_line.filter(Q(expense__date__month=month)
                                                                   &Q(expense__date__year=year)):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def amount_remaining(self, user_preferences):
        return self.amount_available+self.total_credit(user_preferences)-self.total_debit(user_preferences)

    def retrieve_breakdown(self, user_preferences, month, year):
        text_block=''
        num_chars_expense = 11
        for expense_budget_line in self.expense_budget_line.filter(Q(expense__date__month=month)
                                                                   &Q(expense__date__year=year)):
            if expense_budget_line.expense.include_expense(user_preferences):
                date_string = expense_budget_line.expense.date.strftime("%m/%d/%y")
                is_credit = False
                if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                    is_credit = True
                amount_string = dollar_format_local(expense_budget_line.amount, is_credit)
                space_len = max(0,num_chars_expense-len(amount_string))
                filler = space_len*' '
                text_block=text_block+date_string+'   '+amount_string+filler+expense_budget_line.expense.description+'\n'
        return text_block

    def __unicode__(self):
        return '{0} ({1})'.format(self.code, self.name)

def dollar_format_local(amount,is_credit):
    if is_credit:
        return "{0:.2f}".format(amount)
    else:
        return "({0:.2f})".format(amount)

class AccountOwner(models.Model):
    """
    Relate a subaccount to one (of the possibly many) department members
    who 'own' this subaccount.  The primary purpose of this model is to 
    track how much of the subaccount is owned by the department member.
    """
    subaccount = models.ForeignKey(SubAccount, related_name = 'account_owners')
    department_member = models.ForeignKey(DepartmentMember, related_name = 'account_owners')
    fraction = models.FloatField(validators = [MinValueValidator(0.0), MaxValueValidator(1.0)])
    
    class Meta:
        ordering = [ 'subaccount' ]

class CreditCard(models.Model):
    person = models.ForeignKey(DepartmentMember, related_name='credit_card')

    def __unicode__(self):
        return '{0}, {1}'.format(self.person.last_name, self.person.first_name)


class Expense(models.Model):
#    amount = models.DecimalField(max_digits = 10, decimal_places=2)
    checked = models.BooleanField(default = False)
    encumbered = models.BooleanField(default = False)
    future_expense = models.BooleanField(default = False)
    description = models.CharField(max_length=50)
    charged_by = models.ForeignKey(DepartmentMember, blank=True, null=True, related_name='expense')

    date = models.DateField()
    credit_card = models.ForeignKey(CreditCard, blank=True, null=True, related_name='expense')
    extra_note = models.TextField(blank=True, null=True)

#    further action required (what?)

    def abbrev_note(self):
        num_slice = 15
        note = self.extra_note
        char_num = note.find(' ',num_slice,len(note))
        if char_num == -1:
            return note
        else:
            return note[:char_num].strip()+'....'

    def total_debit(self):
        total_amount = 0
        for expense_budget_line in self.expense_budget_line.all():
            if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                total_amount = total_amount+expense_budget_line.amount
        return total_amount

    def total_debit_string(self):
        return "{0:.2f}".format(self.total_debit())
#        return total_amount

    def total_credit(self):
        total_amount = 0
        for expense_budget_line in self.expense_budget_line.all():
            if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                total_amount = total_amount+expense_budget_line.amount
        return total_amount

    def total_credit_string(self):
        return "{0:.2f}".format(self.total_credit())
#        return total_amount

    def include_expense(self, user_preferences):
        if not(self.checked == False and user_preferences.view_checked_only == True) and not(self.encumbered == False and user_preferences.view_encumbrances_only == True) and not(self.future_expense == False and user_preferences.view_future_only == True):
            return True
        else:
            return False

    def total_credit_minus_debit_string(self):
        c_m_d = self.total_credit()-self.total_debit()
        if c_m_d >= 0:
            return "{0:.2f}".format(c_m_d)
        else:
            return "({0:.2f})".format(-c_m_d)

    def is_split_transaction(self):
        number_of_ebls = 0
        for expense_budget_line in self.expense_budget_line.all():
            number_of_ebls = number_of_ebls + 1
        if number_of_ebls > 1:
            return True
        else:
            return False

    def retrieve_split(self):
        text_block=''
        num_chars_expense = 11
        for expense_budget_line in self.expense_budget_line.all():
            date_string = expense_budget_line.expense.date.strftime("%m/%d/%y")
            is_credit = False
            if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                is_credit = True
            amount_string = dollar_format_local(expense_budget_line.amount, is_credit)
            space_len = max(0,num_chars_expense-len(amount_string))
            filler = space_len*' '
#            text_block=text_block+amount_string+filler+expense_budget_line.budget_line.name+' ('+expense_budget_line.budget_line.code+') '
            if expense_budget_line.subaccount:
                text_block = text_block+amount_string+filler+expense_budget_line.budget_line.name+' ('+expense_budget_line.budget_line.code+') - '
                if expense_budget_line.subaccount.abbrev == expense_budget_line.subaccount.name:
                    text_block = text_block+expense_budget_line.subaccount.abbrev+'\n'
                else:
                    text_block = text_block+expense_budget_line.subaccount.abbrev+' ('+expense_budget_line.subaccount.name+')'+'\n'
            else:
                text_block = text_block+amount_string+filler+expense_budget_line.budget_line.name+' ('+expense_budget_line.budget_line.code+') '+'\n'
        return text_block


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
    is_budget_adjustment = models.BooleanField(default = False)

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
