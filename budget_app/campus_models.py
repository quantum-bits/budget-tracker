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
                    'adjusted_available': self.dollar_format_parentheses(subaccount.adjusted_budget(user_preferences), True),
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
        for expense_budget_line in self.expense_budget_line.filter(is_budget_adjustment = False):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def total_credit(self, user_preferences):
        tot = 0
        for expense_budget_line in self.expense_budget_line.filter(is_budget_adjustment = False):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def debit_month(self, user_preferences, month, year):
        tot = 0
        for expense_budget_line in self.expense_budget_line.filter(Q(expense__date__month=month)
                                                                   &Q(expense__date__year=year)
                                                                   &Q(is_budget_adjustment = False)):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def credit_month(self, user_preferences, month, year):
        tot = 0
        for expense_budget_line in self.expense_budget_line.filter(expense__date__month=month, expense__date__year=year, is_budget_adjustment = False):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def budget_adjustment(self, user_preferences):
        tot = 0
        for expense_budget_line in self.expense_budget_line.filter(is_budget_adjustment = True):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                    tot = tot + expense_budget_line.amount
                else:
                    tot = tot - expense_budget_line.amount
        return tot

    def adjusted_budget(self, user_preferences):
        return self.amount_available + self.budget_adjustment(user_preferences)

    def amount_remaining(self, user_preferences):
        return self.amount_available+self.budget_adjustment(user_preferences)+self.total_credit(user_preferences)-self.total_debit(user_preferences)

    def retrieve_breakdown(self, user_preferences, month, year):
        text_block=''
        num_chars_expense = 11
        for expense_budget_line in self.expense_budget_line.filter(Q(expense__date__month=month)
                                                                   &Q(expense__date__year=year)
                                                                   &Q(is_budget_adjustment = False)):
            if expense_budget_line.expense.include_expense(user_preferences):
                date_string = expense_budget_line.expense.date.strftime("%m/%d/%y")
                is_credit = False
                if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                    is_credit = True
                amount_string = dollar_format_local(expense_budget_line.amount, is_credit)
                space_len = max(0,num_chars_expense-len(amount_string))
                filler = space_len*' '
                text_block=text_block+date_string+'   '+amount_string+filler+expense_budget_line.expense.description+'\n'
        print "text block", text_block
        return text_block

    def retrieve_budget_adjustment_breakdown(self, user_preferences, month, year):
        text_block=''
        num_chars_expense = 11
        for expense_budget_line in self.expense_budget_line.filter(Q(expense__date__month=month)
                                                                   &Q(expense__date__year=year)
                                                                   &Q(is_budget_adjustment = True)):
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
        for expense_budget_line in self.expense_budget_line.filter(is_budget_adjustment = False):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def total_credit(self, user_preferences):
        tot = 0
        for expense_budget_line in self.expense_budget_line.filter(is_budget_adjustment = False):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def debit_month(self, user_preferences, month, year):
        tot = 0
        for expense_budget_line in self.expense_budget_line.filter(Q(expense__date__month=month)
                                                                   &Q(expense__date__year=year)
                                                                   &Q(is_budget_adjustment = False)):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def credit_month(self, user_preferences, month, year):
        tot = 0
        for expense_budget_line in self.expense_budget_line.filter(Q(expense__date__month=month)
                                                                   &Q(expense__date__year=year)
                                                                   &Q(is_budget_adjustment = False)):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                    tot = tot + expense_budget_line.amount
        return tot

    def budget_adjustment(self, user_preferences):
        tot = 0
        for expense_budget_line in self.expense_budget_line.filter(is_budget_adjustment = True):
            if expense_budget_line.expense.include_expense(user_preferences):
                if expense_budget_line.debit_or_credit == expense_budget_line.CREDIT:
                    tot = tot + expense_budget_line.amount
                else:
                    tot = tot - expense_budget_line.amount
        return tot

    def adjusted_budget(self, user_preferences):
        return self.amount_available + self.budget_adjustment(user_preferences)

    def amount_remaining(self, user_preferences):
        return self.amount_available+self.budget_adjustment(user_preferences)+self.total_credit(user_preferences)-self.total_debit(user_preferences)

    def retrieve_breakdown(self, user_preferences, month, year):
        text_block=''
        num_chars_expense = 11
        for expense_budget_line in self.expense_budget_line.filter(Q(expense__date__month=month)
                                                                   &Q(expense__date__year=year)
                                                                   &Q(is_budget_adjustment = False)):
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

    def retrieve_budget_adjustment_breakdown(self, user_preferences, month, year):
        text_block=''
        num_chars_expense = 11
        for expense_budget_line in self.expense_budget_line.filter(Q(expense__date__month=month)
                                                                   &Q(expense__date__year=year)
                                                                   &Q(is_budget_adjustment = True)):
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

def dollar_format_parentheses(amount, include_zero):
    if amount>0:
        return "{0:.2f}".format(amount)
    elif amount<0:
        return "({0:.2f})".format(-amount)
    elif amount==0 and include_zero:
        return '0.00'
    else:
        return ''


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

    def includes_budget_adjustment(self):
        includes_budget_adjustment_bool = False
        for expense_budget_line in self.expense_budget_line.all():
            if expense_budget_line.is_budget_adjustment == True:
                includes_budget_adjustment_bool = True
        return includes_budget_adjustment_bool

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

    @classmethod
    def create_budget_line_summary(cls, user_preferences, month_list):
        """
        fetches and formats the data used to create the budget line summary page
        """

        fiscal_year = user_preferences.fiscal_year_to_view
        num_chars_expense = 11

        month_name_list = []
        for month, year, year_name in month_list:
            month_name_list.append(year_name)

        department_data = []
        for department in Department.objects.all():
            budget_line_summary = {}
            all_budget_lines_total = 0
            credit_minus_debit_total = 0
            budget_remaining = 0
            for budget_line in BudgetLine.objects.filter(fiscal_year__id=fiscal_year.id, department = department):
                all_budget_lines_total = all_budget_lines_total+budget_line.amount_available

                budget_line_summary[budget_line.id]={
                    'budget_line': budget_line,
                    'code': budget_line.code,
                    'data_list': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    'note_list': ['','','','','','','','','','','',''],
                    'data_entries':[],
                    'budget_adjustment_note': '',
#                    'owned_by': owned_by,
                    'original_budget': dollar_format_parentheses(budget_line.amount_available, True),
                    'adjusted_budget': budget_line.amount_available,
                    'remaining': '',
                    'remaining_negative': False,
                    'total_credit_minus_debit': ''
                    }

            all_budget_lines_adjusted_total = all_budget_lines_total
            data_list_index = 0
            budget_line_totals_list=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            for month, year, year_name in month_list:
                total_for_month = 0
# I should probably add a method to expense budget line to append a note or something.  
# even better -- make the notes their own class, and then I can mess around with them at will, define a unicode method for displaying them, etc.
                for ebl in cls.objects.select_related('expense', 'budget_line', 'subaccount').filter(expense__date__month=month,
                                              expense__date__year=year,
                                              budget_line__department=department):
                    date_string = ebl.expense.date.strftime("%m/%d/%y")
                    if ebl.expense.include_expense(user_preferences):
                        if ebl.is_budget_adjustment == False:
                            if ebl.debit_or_credit == ebl.CREDIT:
                                budget_line_summary[ebl.budget_line.id]['data_list'][data_list_index]+=ebl.amount
                                credit_minus_debit_total+=ebl.amount
                                budget_line_totals_list[data_list_index]+=ebl.amount
                                is_credit = True
                            else:
                                budget_line_summary[ebl.budget_line.id]['data_list'][data_list_index]-=ebl.amount
                                credit_minus_debit_total-=ebl.amount
                                budget_line_totals_list[data_list_index]-=ebl.amount
                                is_credit = False
                        else:
                            if ebl.debit_or_credit == ebl.CREDIT:
                                budget_line_summary[ebl.budget_line.id]['adjusted_budget']+=ebl.amount
                                all_budget_lines_adjusted_total+=ebl.amount
                                is_credit = True
                            else:
                                budget_line_summary[ebl.budget_line.id]['adjusted_budget']-=ebl.amount
                                all_budget_lines_adjusted_total-=ebl.amount
                                is_credit = False
                        amount_string = dollar_format_local(ebl.amount, is_credit)
                        space_len = max(0,num_chars_expense-len(amount_string))
                        filler = space_len*' '
                        addition_to_note = date_string+'   '+amount_string+filler+ebl.expense.description+'\n'
                        if ebl.is_budget_adjustment == False:
                            budget_line_summary[ebl.budget_line.id]['note_list'][data_list_index]+=addition_to_note
                        else:
                            budget_line_summary[ebl.budget_line.id]['budget_adjustment_note']+=addition_to_note

                data_list_index+=1

            budget_remaining = all_budget_lines_adjusted_total+credit_minus_debit_total

            for key in budget_line_summary:
                # calculate totals; convert things to the approprate dollar format
                total=sum(budget_line_summary[key]['data_list'])
                budget_line_summary[key]['total_credit_minus_debit']=dollar_format_parentheses(total,True)
                budget_line_summary[key]['total']=dollar_format_parentheses(total,True)
                remaining = budget_line_summary[key]['adjusted_budget']+total
                budget_line_summary[key]['remaining']=dollar_format_parentheses(remaining,True)
                if remaining < 0:
                    budget_line_summary[key]['remaining_negative'] = True
                budget_line_summary[key]['adjusted_budget']=dollar_format_parentheses(budget_line_summary[key]['adjusted_budget'],True)
                data_entries_list = []
    # there must be a nicer way to do this...!
                for ii in range(len(budget_line_summary[key]['data_list'])):
                    entry = budget_line_summary[key]['data_list'][ii]
                    note = budget_line_summary[key]['note_list'][ii]
                    data_entries_list.append({'amount':dollar_format_parentheses(entry,False),'breakdown': note})
                budget_line_summary[key]['data_entries']=data_entries_list
    # turn the dict into a sorted list
            budget_line_summary_list = []
            for key in budget_line_summary:
                budget_line_summary_list.append(budget_line_summary[key])
            sorted_budget_line_summary_list = sorted(budget_line_summary_list, key=lambda k: k['code'])

            budget_remaining_is_negative = False
            if budget_remaining < 0:
                budget_remaining_is_negative = True
            budget_line_totals_list_formatted=[]
            for subtotal in budget_line_totals_list:
                budget_line_totals_list_formatted.append(dollar_format_parentheses(subtotal, True)),
            budget_line_data = {'budget_line_list': sorted_budget_line_summary_list,
                                'all_budget_lines_total': dollar_format_parentheses(all_budget_lines_total, True),
                                'month_name_list': month_name_list,
                                'adjusted_budget_total': dollar_format_parentheses(all_budget_lines_adjusted_total, True),
                                'budget_remaining_is_negative': budget_remaining_is_negative,
                                'budget_remaining': dollar_format_parentheses(budget_remaining, True),
                                'budget_total': dollar_format_parentheses(all_budget_lines_total, True),
                                'budget_line_totals_list': budget_line_totals_list_formatted,
                                'all_budget_lines_credit_minus_debit':dollar_format_parentheses(credit_minus_debit_total, True)}

            department_data.append({'department': department,
                                    'budget_line_data': budget_line_data
                                    })
#            if expense_budget_line.expense.include_expense(user_preferences):
#                if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
#                    tot = tot + expense_budget_line.amount
        return department_data


    @classmethod
    def create_subaccount_summary(cls, user_preferences, month_list):
        """
        fetches and formats the data used to create the subaccount summary page
        """

        fiscal_year = user_preferences.fiscal_year_to_view
        subaccount_summary = {}
        num_chars_expense = 11

        month_name_list = []
        for month, year, year_name in month_list:
            month_name_list.append(year_name)

        all_subaccounts_total = 0
        credit_minus_debit_total = 0
        budget_remaining = 0

        for subaccount in SubAccount.objects.filter(fiscal_year__id=fiscal_year.id):
            owned_by = []
            for account_owner in subaccount.account_owners.all():
                owned_by.append(account_owner.department_member.last_name+" ({0:.0f}%)".format(account_owner.fraction*100))
            all_subaccounts_total = all_subaccounts_total+subaccount.amount_available
#            budget_adjustment_note = ''
#            for month, year, year_name in month_list:
#                budget_adjustment_note+=subaccount.retrieve_budget_adjustment_breakdown(user_preferences,month, year)
            subaccount_summary[subaccount.id]={
                'subaccount': subaccount,
                'abbrev': subaccount.abbrev,
                'data_list': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                'note_list': ['','','','','','','','','','','',''],
                'data_entries':[],
                'budget_adjustment_note': '',
                'owned_by': owned_by,
                'original_budget': dollar_format_parentheses(subaccount.amount_available, True),
                'adjusted_budget': subaccount.amount_available,
                'remaining': '',
                'remaining_negative': False,
                'total_credit_minus_debit': ''
                }

        all_subaccounts_adjusted_total = all_subaccounts_total
        data_list_index = 0
        subaccount_totals_list=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        for month, year, year_name in month_list:
            total_for_month = 0
# I should probably add a method to expense budget line to append a note or something.  
# even better -- make the notes their own class, and then I can mess around with them at will, define a unicode method for displaying them, etc.
            for ebl in cls.objects.select_related('expense', 'budget_line', 'subaccount').filter(expense__date__month=month,
                                          expense__date__year=year,
                                          subaccount__isnull=False):
                date_string = ebl.expense.date.strftime("%m/%d/%y")
                if ebl.expense.include_expense(user_preferences):
                    if ebl.is_budget_adjustment == False:
                        if ebl.debit_or_credit == ebl.CREDIT:
                            subaccount_summary[ebl.subaccount.id]['data_list'][data_list_index]+=ebl.amount
                            credit_minus_debit_total+=ebl.amount
                            subaccount_totals_list[data_list_index]+=ebl.amount
                            is_credit = True
                        else:
                            subaccount_summary[ebl.subaccount.id]['data_list'][data_list_index]-=ebl.amount
                            credit_minus_debit_total-=ebl.amount
                            subaccount_totals_list[data_list_index]-=ebl.amount
                            is_credit = False
                    else:
                        if ebl.debit_or_credit == ebl.CREDIT:
                            subaccount_summary[ebl.subaccount.id]['adjusted_budget']+=ebl.amount
                            all_subaccounts_adjusted_total+=ebl.amount
                            is_credit = True
                        else:
                            subaccount_summary[ebl.subaccount.id]['adjusted_budget']-=ebl.amount
                            all_subaccounts_adjusted_total-=ebl.amount
                            is_credit = False
                    amount_string = dollar_format_local(ebl.amount, is_credit)
                    space_len = max(0,num_chars_expense-len(amount_string))
                    filler = space_len*' '
                    addition_to_note = date_string+'   '+amount_string+filler+ebl.expense.description+'\n'
                    if ebl.is_budget_adjustment == False:
                        subaccount_summary[ebl.subaccount.id]['note_list'][data_list_index]+=addition_to_note
                    else:
                        subaccount_summary[ebl.subaccount.id]['budget_adjustment_note']+=addition_to_note

            data_list_index+=1

        budget_remaining = all_subaccounts_adjusted_total+credit_minus_debit_total

        for key in subaccount_summary:
            # calculate totals; convert things to the approprate dollar format
            total=sum(subaccount_summary[key]['data_list'])
            subaccount_summary[key]['total_credit_minus_debit']=dollar_format_parentheses(total,True)
            subaccount_summary[key]['total']=dollar_format_parentheses(total,True)
            remaining = subaccount_summary[key]['adjusted_budget']+total
            subaccount_summary[key]['remaining']=dollar_format_parentheses(remaining,True)
            if remaining < 0:
                subaccount_summary[key]['remaining_negative'] = True
            subaccount_summary[key]['adjusted_budget']=dollar_format_parentheses(subaccount_summary[key]['adjusted_budget'],True)
            data_entries_list = []
# there must be a nicer way to do this...!
            for ii in range(len(subaccount_summary[key]['data_list'])):
                entry = subaccount_summary[key]['data_list'][ii]
                note = subaccount_summary[key]['note_list'][ii]
                data_entries_list.append({'amount':dollar_format_parentheses(entry,False),'breakdown': note})
            subaccount_summary[key]['data_entries']=data_entries_list
# turn the dict into a sorted list
        subaccount_summary_list = []
        for key in subaccount_summary:
            subaccount_summary_list.append(subaccount_summary[key])
        sorted_subaccount_summary_list = sorted(subaccount_summary_list, key=lambda k: k['abbrev'])

        budget_remaining_is_negative = False
        if budget_remaining < 0:
            budget_remaining_is_negative = True
        subaccount_totals_list_formatted=[]
        for subtotal in subaccount_totals_list:
            subaccount_totals_list_formatted.append(dollar_format_parentheses(subtotal, True)),
        subaccount_data = {'subaccount_list': sorted_subaccount_summary_list,
                           'all_subaccounts_total': dollar_format_parentheses(all_subaccounts_total, True),
                           'month_name_list': month_name_list,
                           'adjusted_budget_total': dollar_format_parentheses(all_subaccounts_adjusted_total, True),
                           'budget_remaining_is_negative': budget_remaining_is_negative,
                           'budget_remaining': dollar_format_parentheses(budget_remaining, True),
                           'budget_total': dollar_format_parentheses(all_subaccounts_total, True),
                           'subaccount_totals_list': subaccount_totals_list_formatted,
                           'all_subaccounts_credit_minus_debit':dollar_format_parentheses(credit_minus_debit_total, True)}

#            if expense_budget_line.expense.include_expense(user_preferences):
#                if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
#                    tot = tot + expense_budget_line.amount
        return subaccount_data

    @classmethod
    def create_budget_entries_list(cls, user_preferences, month_list):
        """
        fetches and formats the data used to create the budget entries page.
        """
        fiscal_year = user_preferences.fiscal_year_to_view
        expense_dict={}

        for month, year, year_name in month_list:
            for ebl in cls.objects.select_related('expense','subaccount','budget_line').filter(expense__date__month=month,
                                          expense__date__year=year):
                date_string = ebl.expense.date.strftime("%m/%d/%y")
                if ebl.expense.include_expense(user_preferences):
                    if ebl.expense.id in expense_dict:
                        expense_dict[ebl.expense.id]['expense_budget_lines'].append({'budget_line_code': ebl.budget_line.code,
                                                                                     'subaccount': ebl.subaccount,
                                                                                     'debit_or_credit': ebl.debit_or_credit,
                                                                                     'formattedprice': ebl.formattedprice,
                                                                                     'is_budget_adjustment': ebl.is_budget_adjustment
                                                                                     }
                                                                                    )
                    else:
                        expense_dict[ebl.expense.id]={'date': ebl.expense.date,
                                                      'extra_note': ebl.expense.extra_note,
                                                      'description': ebl.expense.description,
                                                      'abbrev_note': ebl.expense.abbrev_note,
                                                      'date_numeric': ebl.expense.date.year*10000+ebl.expense.date.month*100+ebl.expense.date.day,
                                                      'id': ebl.expense.id,
                                                      'DEBIT': ebl.DEBIT,
                                                      'total_debit': 0,
                                                      'total_credit': 0,
                                                      'total_debit_string': '',
                                                      'total_credit_string': '',
                                                      'checked': ebl.expense.checked,
                                                      'encumbered': ebl.expense.encumbered,
                                                      'includes_budget_adjustment': False,
                                                      'future_expense': ebl.expense.future_expense,
                                                      'expense_budget_lines': [{'budget_line_code': ebl.budget_line.code,
                                                                                'subaccount': ebl.subaccount,
                                                                                'debit_or_credit': ebl.debit_or_credit,
                                                                                'formattedprice': ebl.formattedprice,
                                                                                'is_budget_adjustment': ebl.is_budget_adjustment
                                                                                }
                                                                               ]
                                                      }
                    if ebl.is_budget_adjustment:
                        expense_dict[ebl.expense.id]['includes_budget_adjustment'] = True
                    if ebl.debit_or_credit == ebl.DEBIT:
                        expense_dict[ebl.expense.id]['total_debit'] += ebl.amount
                        expense_dict[ebl.expense.id]['total_debit_string'] = "{0:.2f}".format(expense_dict[ebl.expense.id]['total_debit'])                    
                    else:
                        expense_dict[ebl.expense.id]['total_credit'] += ebl.amount
                        expense_dict[ebl.expense.id]['total_credit_string'] = "{0:.2f}".format(expense_dict[ebl.expense.id]['total_credit'])

# NEXT: fix total_debit, total_debit_string, etc., so that they are not looping backwards along foreign keys!  currently down to 1400 queries

        budget_entry_list = []
        for key in expense_dict:
            budget_entry_list.append(expense_dict[key])
        sorted_budget_entry_list = sorted(budget_entry_list, key=lambda k: k['date_numeric'], reverse=True)

        return sorted_budget_entry_list


    def formattedprice(self):
        return "%01.2f" % self.amount

    def formattedprice_parentheses(self):
        if self.debit_or_credit == self.CREDIT:
            return "%01.2f" % self.amount
        else:
            return "(%01.2f)" % self.amount

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
