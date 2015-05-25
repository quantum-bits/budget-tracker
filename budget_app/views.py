from collections import namedtuple

from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.shortcuts import render, redirect
from django.template import RequestContext
from django.utils.functional import curry

from .models import *
from .forms import *

import json
import csv
from django.http import HttpResponse, HttpResponseRedirect
from os.path import expanduser
from datetime import date
from datetime import datetime

def home(request):
    return render(request, 'home.html')

# To Do:
# 0. New view(!) -- table with subaccounts down the side and years across
#    the top and budgeted amounts in the table itself.  The last column
#    can have a copy forward feature; there can also be a drop-down with
#    the different possibilities for the amounts (if there were different
#    options in different years)
# 0a. Same idea, but for budget lines.
# 0b. Make a (printable) "reports" view that shows each person's account
#     totals, along with the breakdown.  Need to talk to Bill a bit more
#     to see what he has in mind for this.  Dump to pdf?  Or generate a new
#     view and then attempt to print this out?  Not sure how well that will go.
# 0c. Do a summary of budget lines that lines up better with BANNER.  I think
#     the main thing will be to not include unchecked items in totals(?)  Need
#     to ask Bill for clarification.
# 1. Do a "freeze panes" thing like was done on iChair.  Do it for the budget entries page, and maybe other ones.
# 3. hint at the top of the budget lines page saying adj budget +/- expense = remaining
# Comments from Bill:
#   ==> Subacct page: summary line should show adj bud - spent + credits; otherwise you think haven't spent a lot
#   ==> Budget line entry allowed budget adjustment to get into 132020 without subaccount
#   x Checked/unchecked option in budget entries page
#   ==> When deleting unchecked item in budget lines page, check/unchecked option goes back to default


# on form for entering expenses, return an error if the date is not
# within the FY that is currently being viewed!!!!

# when displaying data, need to limit it to the current FY!!!

# NEXT:
# 0. new_budget_entry: look up how to do custom "cleaned data"...probably in the views documentation
#    for django



 
@login_required
def profile(request):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]

    # Note: to access the email address in the view, you could set it to
    # email = student.user.email

    context = {
                'fiscal_year': user_preferences.fiscal_year_to_view,
                'can_edit': user.is_superuser,
                'id': user_preferences.id,
                'username': user.username
                }
    return render(request, 'profile.html', context)

@login_required
def budget_entries(request, id = None):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    request.session["return_to_page"] = "/budget_app/budgetentries/"

    if request.method == 'POST':
        process_preferences_and_checked_form(request, user_preferences)

    month_list = list_of_months_in_fy(fiscal_year)
    budget_entry_list = ExpenseBudgetLine.create_budget_entries_list(user_preferences, month_list)

#    expense_list = []
#    for expense in Expense.objects.all():
#        if expense.date <= fiscal_year.end_on and expense.date >= fiscal_year.begin_on:
#            if expense.include_expense(user_preferences):
#                expense_list.append(expense)
#                print expense.abbrev_note()


    can_edit = False
    if user.is_superuser:
        can_edit = True

    if id == None:
        unchecked_only = False
    else:
        if user_preferences.view_checked_only:
            unchecked_only = False
        else:
            unchecked_only = True

    context = { 
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': fiscal_year,
        'expense_list': budget_entry_list,
        'unchecked_only': unchecked_only,
        'can_edit': can_edit
        }
    return render(request, 'budget_entries.html', context)






@login_required
def credit_card_entries(request):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    request.session["return_to_page"] = "/budget_app/credit_card_entries/"
    
    if request.method == 'POST':
        process_preferences_and_checked_form(request, user_preferences)

    credit_card_list = []
    for credit_card in CreditCard.objects.all():
        expense_list = []
        for expense in credit_card.expense.all():
            if expense.date <= fiscal_year.end_on and expense.date >= fiscal_year.begin_on:
                if expense.include_expense(user_preferences):
                    expense_list.append(expense)
#                    print expense
#                print expense_list
#                print expense.abbrev_note()
        credit_card_list.append({'credit_card': credit_card,
                                 'expense_list': expense_list})
#    print credit_card_list

    can_edit = False
    if user.is_superuser:
        can_edit = True

    context = {
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': fiscal_year,
        'credit_card_list': credit_card_list,
        'can_edit': can_edit
        }
    json_open_div_id_list = construct_json_open_div_id_list(request, 2)
    context['open_div_id_list']=json_open_div_id_list

    return render(request, 'credit_card_entries.html', context)




@login_required
def budget_line_entries(request, id = None):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    request.session["return_to_page"] = "/budget_app/budgetlineentries/"
    
    if request.method == 'POST':
        process_preferences_and_checked_form(request, user_preferences)

    department_list = []
    for department in Department.objects.all():
        budget_line_list = []
        for budget_line in BudgetLine.objects.filter(Q(fiscal_year__id=fiscal_year.id)&Q(department__id=department.id)):
            ebl_list = []
            bl_total_debit = 0
            bl_total_credit = 0
            bl_budget_adjustment = 0
            for expense_budget_line in budget_line.expense_budget_line.select_related('expense','subaccount').all():
                if expense_budget_line.expense.include_expense(user_preferences):
                    ebl_list.append(expense_budget_line)
                    if expense_budget_line.is_budget_adjustment == False:
                        if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                            bl_total_debit+=expense_budget_line.amount
                        else:
                            bl_total_credit+=expense_budget_line.amount
                    else:
                        if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                            bl_budget_adjustment-=expense_budget_line.amount
                        else:
                            bl_budget_adjustment+=expense_budget_line.amount                        
            total_debit_minus_credit = bl_total_debit-bl_total_credit
            bl_adjusted_budget = budget_line.amount_available + bl_budget_adjustment
            bl_amount_remaining = bl_adjusted_budget - total_debit_minus_credit
            if total_debit_minus_credit < 0:
                d_m_c_string = " + "+dollar_format(-total_debit_minus_credit)
            else:
                d_m_c_string = " - "+dollar_format(total_debit_minus_credit)

            budget_line_list.append({'budget_line': budget_line, 
                                     'expense_budget_line_list': ebl_list,
                                     'total_debit': dollar_format(bl_total_debit),
                                     'total_credit': dollar_format(bl_total_credit),
                                     'budget_adjustment': dollar_format_parentheses(bl_budget_adjustment, True),
                                     'total_debit_minus_credit': d_m_c_string,
                                     'budget_line_available': dollar_format_parentheses(budget_line.amount_available, True),
                                     'adjusted_budget': dollar_format_parentheses(bl_adjusted_budget, True),
                                     'budget_line_remaining': dollar_format_parentheses(bl_amount_remaining, True)})
        department_list.append({'department': department,
                                'budget_line_list': budget_line_list})

    if id == None:
        unchecked_only = False
    else:
        if user_preferences.view_checked_only:
            unchecked_only = False
        else:
            unchecked_only = True

    can_edit = False
    if user.is_superuser:
        can_edit = True

    context = {
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': fiscal_year,
        'department_list': department_list,
        'unchecked_only': unchecked_only,
        'can_edit': can_edit
        }

    json_open_div_id_list = construct_json_open_div_id_list(request, 0)
    context['open_div_id_list']=json_open_div_id_list

    return render(request, 'budget_line_entries.html', context)


@login_required
def copy_budget_lines(request):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    current_fiscal_year = user_preferences.fiscal_year_to_view

#    if request.method == 'POST':
#        process_preferences_and_checked_form(request, user_preferences)

    can_edit = False
    if user.is_superuser:
        can_edit = True

    if request.method == 'POST':
        budget_line_list = request.POST.getlist('budget_lines_to_copy')
# for each element in the list of budget lines, fetch the requested budget (which is in the drop-down list)
        for budget_line_id in budget_line_list:
            amount = request.POST.get('amount'+budget_line_id)
# now create a new budget line, with the requested parameters, etc.
# first, get one of the original budget line objects, so various properties can be copied....
            budget_line_object = BudgetLine.objects.get(pk=int(budget_line_id))
            new_budget_line = BudgetLine.objects.create(code = budget_line_object.code,
                                                        name = budget_line_object.name,
                                                        has_subaccounts = budget_line_object.has_subaccounts,
                                                        department = budget_line_object.department,
                                                        fiscal_year = current_fiscal_year,
                                                        amount_available = Decimal(amount)
                                                        )
            new_budget_line.save()


#        next = request.GET.get('next', 'profile')
#        return redirect(next)


    fiscal_year_reverse_dict = {}
    index = 0
    number_previous_years = 0
    previous_fy_list = []
    for fiscal_year in FiscalYear.objects.all():
        if fiscal_year.begin_on.year < current_fiscal_year.begin_on.year:
            fiscal_year_reverse_dict[fiscal_year.id] = index
            number_previous_years+=1
            index+=1
            previous_fy_list.append(fiscal_year)

    budget_lines_current_fy = []
    budget_lines_current_fy_amounts = {}
    for budget_line in BudgetLine.objects.filter(fiscal_year = current_fiscal_year):
        budget_lines_current_fy.append(budget_line.code)
        budget_lines_current_fy_amounts[budget_line.code]=budget_line.amount_available

# now construct an array that holds the previous years' budget amounts
        
    budget_line_dict = {}
    for budget_line in BudgetLine.objects.all():
        if budget_line.fiscal_year.begin_on.year < current_fiscal_year.begin_on.year:
            if budget_line.code not in budget_lines_current_fy:
                can_copy_forward = True
                amount_current_fy = '-'
            else:
                can_copy_forward = False
                amount_current_fy = budget_lines_current_fy_amounts[budget_line.code]
#            index = fiscal_year_reverse_dict[budget_line.fiscal_year.id]
            if budget_line.code not in budget_line_dict:
                budget_line_dict[budget_line.code] = {'name': budget_line.name,
                                                      'code': budget_line.code,
                                                      'amounts': {budget_line.fiscal_year.id: budget_line.amount_available},
                                                      'can_copy_forward': can_copy_forward,
                                                      'department': budget_line.department,
                                                      'id': budget_line.id,
                                                      'current_fy_amount': amount_current_fy}
            else:
                budget_line_dict[budget_line.code]['amounts'][budget_line.fiscal_year.id] = budget_line.amount_available

    # turn the dict into a sorted list
    budget_line_list = []
    for key in budget_line_dict:
        amount_array = []
        drop_down_list_array = [Decimal('0')]
        for year in range(number_previous_years):
            amount_array.append('-')
        for year_id in budget_line_dict[key]['amounts']:
            amount_array[fiscal_year_reverse_dict[year_id]]=budget_line_dict[key]['amounts'][year_id]
            if budget_line_dict[key]['amounts'][year_id] not in drop_down_list_array:
                drop_down_list_array.insert(0, budget_line_dict[key]['amounts'][year_id])
        # add a new element to the dict....
        budget_line_dict[key]['amount_array']=amount_array
        budget_line_dict[key]['drop_down_list']=drop_down_list_array
        budget_line_list.append(budget_line_dict[key])
    sorted_budget_line_list = sorted(budget_line_list, key=lambda k: k['code'])

    context = { 
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': current_fiscal_year,
        'can_edit': can_edit,
        'budget_line_list': sorted_budget_line_list,
        'previous_fy_list': previous_fy_list
        }
    return render(request, 'copy_budget_lines.html', context)

@login_required
def copy_subaccounts(request):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    current_fiscal_year = user_preferences.fiscal_year_to_view

#    if request.method == 'POST':
#        process_preferences_and_checked_form(request, user_preferences)

    can_edit = False
    if user.is_superuser:
        can_edit = True

    if request.method == 'POST':
        subaccounts_list = request.POST.getlist('subaccounts_to_copy')
# for each element in the list of subaccounts, fetch the requested budget (which is in the drop-down list)
        for subaccount_id in subaccounts_list:
            subaccount_object_id = request.POST.get('amount'+subaccount_id)

# now create a new subaccount, with the requested parameters, etc.
# first, get the particular subaccount object whose parameters will be copied
            subaccount_object = SubAccount.objects.get(pk=int(subaccount_object_id))

            new_subaccount = SubAccount.objects.create(name = subaccount_object.name,
                                                       abbrev = subaccount_object.abbrev,
                                                       fiscal_year = current_fiscal_year,
                                                       amount_available = subaccount_object.amount_available
                                                       )
            # now create the "through" object(s)
            for account_owner in AccountOwner.objects.filter(subaccount=subaccount_object):
                owner = AccountOwner(subaccount=new_subaccount,
                                     department_member = account_owner.department_member,
                                     fraction = account_owner.fraction
                                     )
                owner.save()

            new_subaccount.save()

    fiscal_year_reverse_dict = {}
    index = 0
    number_previous_years = 0
    previous_fy_list = []
    for fiscal_year in FiscalYear.objects.all():
        if fiscal_year.begin_on.year < current_fiscal_year.begin_on.year:
            fiscal_year_reverse_dict[fiscal_year.id] = index
            number_previous_years+=1
            index+=1
            previous_fy_list.append(fiscal_year)

    subaccounts_current_fy = []
    subaccounts_current_fy_amounts = {}
    for subaccount in SubAccount.objects.filter(fiscal_year = current_fiscal_year):
        subaccounts_current_fy.append(subaccount.name)
        subaccount_breakdown_string = str(subaccount.amount_available)+' '
        zero_owners = True
        for account_owner in AccountOwner.objects.filter(subaccount=subaccount):
            fraction_string="{0:.0f}%".format(100*account_owner.fraction)
            if zero_owners:
                subaccount_breakdown_string+= '['
                zero_owners = False
            else:
                subaccount_breakdown_string+= '; '
            subaccount_breakdown_string+= account_owner.department_member.last_name +'('+fraction_string+')'
        if not zero_owners:
            subaccount_breakdown_string+= ']'
        subaccounts_current_fy_amounts[subaccount.name]=subaccount_breakdown_string

# now construct an array that holds the previous years' budget amounts
        
    subaccount_dict = {}
    for subaccount in SubAccount.objects.all():
        if subaccount.fiscal_year.begin_on.year < current_fiscal_year.begin_on.year:
            if subaccount.name not in subaccounts_current_fy:
                can_copy_forward = True
                amount_current_fy = '-'
            else:
                can_copy_forward = False
                amount_current_fy = subaccounts_current_fy_amounts[subaccount.name]
#            index = fiscal_year_reverse_dict[subaccount.fiscal_year.id]

            subaccount_breakdown_string = str(subaccount.amount_available)+' '
            zero_owners = True
            for account_owner in AccountOwner.objects.filter(subaccount=subaccount):
                fraction_string="{0:.0f}%".format(100*account_owner.fraction)
                if zero_owners:
                    subaccount_breakdown_string+= '['
                    zero_owners = False
                else:
                    subaccount_breakdown_string+= '; '
                subaccount_breakdown_string+= account_owner.department_member.last_name +'('+fraction_string+')'
            if not zero_owners:
                subaccount_breakdown_string+= ']'

            if subaccount.name not in subaccount_dict:
                subaccount_dict[subaccount.name] = {'name': subaccount.name,
                                                    'abbrev': subaccount.abbrev,
                                                    'amounts': {subaccount.fiscal_year.id: {'id': subaccount.id, 
                                                                                            'description': subaccount_breakdown_string}},
                                                    'can_copy_forward': can_copy_forward,
                                                    'id': subaccount.id,
                                                    'current_fy_amount': amount_current_fy}
            else:
                subaccount_dict[subaccount.name]['amounts'][subaccount.fiscal_year.id] = {'id': subaccount.id,
                                                                                          'description': subaccount_breakdown_string}

    # turn the dict into a sorted list
    subaccount_list = []
    for key in subaccount_dict:
        amount_array = []
        drop_down_dict = {}
        for year in range(number_previous_years):
            amount_array.append({'id':0,'description':'-'})
        for year_id in subaccount_dict[key]['amounts']:
            amount_array[fiscal_year_reverse_dict[year_id]]=subaccount_dict[key]['amounts'][year_id]
            if subaccount_dict[key]['amounts'][year_id]['description'] not in drop_down_dict.values():
                drop_down_dict[subaccount_dict[key]['amounts'][year_id]['id']] = subaccount_dict[key]['amounts'][year_id]['description']
        # add a new element to the dict....
        subaccount_dict[key]['amount_array']=amount_array
        subaccount_dict[key]['drop_down_dict']=drop_down_dict
        subaccount_list.append(subaccount_dict[key])
    sorted_subaccount_list = sorted(subaccount_list, key=lambda k: k['name'])

    context = { 
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': current_fiscal_year,
        'can_edit': can_edit,
        'subaccount_list': sorted_subaccount_list,
        'previous_fy_list': previous_fy_list
        }
    return render(request, 'copy_subaccounts.html', context)

def dollar_format(amount):
    return "{0:.2f}".format(amount)

def dollar_format_parentheses(amount, include_zero):
    if amount>0:
        return "{0:.2f}".format(amount)
    elif amount<0:
        return "({0:.2f})".format(-amount)
    elif amount==0 and include_zero:
        return '0.00'
    else:
        return ''

@login_required
def subaccount_entries(request):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    request.session["return_to_page"] = "/budget_app/subaccountentries/"

    if request.method == 'POST':
        process_preferences_and_checked_form(request, user_preferences)

    subaccount_list = []
    for subaccount in SubAccount.objects.filter(fiscal_year__id=fiscal_year.id):
        ebl_list = []

        sa_total_debit = 0
        sa_total_credit = 0
        sa_budget_adjustment = 0
        for expense_budget_line in subaccount.expense_budget_line.select_related('expense','budget_line').all():
            if expense_budget_line.expense.include_expense(user_preferences):
                ebl_list.append(expense_budget_line)
                if expense_budget_line.is_budget_adjustment == False:
                    if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                        sa_total_debit+=expense_budget_line.amount
                    else:
                        sa_total_credit+=expense_budget_line.amount
                else:
                    if expense_budget_line.debit_or_credit == expense_budget_line.DEBIT:
                        sa_budget_adjustment-=expense_budget_line.amount
                    else:
                        sa_budget_adjustment+=expense_budget_line.amount                        
        total_debit_minus_credit = sa_total_debit-sa_total_credit
        sa_adjusted_budget = subaccount.amount_available + sa_budget_adjustment
        sa_amount_remaining = sa_adjusted_budget - total_debit_minus_credit

        if total_debit_minus_credit < 0:
            d_m_c_string = " + "+dollar_format(-total_debit_minus_credit)
        else:
            d_m_c_string = " - "+dollar_format(total_debit_minus_credit)
                
        subaccount_list.append({'subaccount': subaccount, 
                                'expense_budget_line_list': ebl_list,
                                'total_debit': dollar_format(sa_total_debit),
                                'total_credit': dollar_format(sa_total_credit),
                                'budget_adjustment': dollar_format_parentheses(sa_budget_adjustment, True),
                                'total_debit_minus_credit': d_m_c_string,
                                'subaccount_available': dollar_format_parentheses(subaccount.amount_available, True),
                                'adjusted_budget': dollar_format_parentheses(sa_adjusted_budget, True),
                                'subaccount_remaining': dollar_format_parentheses(sa_amount_remaining, True)})

    can_edit = False
    if user.is_superuser:
        can_edit = True

    context = { 
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': fiscal_year,
        'subaccount_list': subaccount_list,
        'can_edit': can_edit
        }
    json_open_div_id_list = construct_json_open_div_id_list(request, 1)
    context['open_div_id_list']=json_open_div_id_list

    return render(request, 'subaccount_entries.html', context)

@login_required
def subaccount_summary(request):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    if request.method == 'POST':
        process_preferences_and_checked_form(request, user_preferences)

    month_list = list_of_months_in_fy(fiscal_year)
    month_name_list = []
    for month, year, year_name in month_list:
        month_name_list.append(year_name)

    subaccount_data = ExpenseBudgetLine.create_subaccount_summary(user_preferences, month_list)

    can_edit = False
    if user.is_superuser:
        can_edit = True

    context = {
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': fiscal_year,
        'subaccount_data': subaccount_data,
        'can_edit': can_edit
        }
    return render(request, 'subaccount_summary.html', context)


@login_required
def budget_line_summary(request):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    if request.method == 'POST':
        process_preferences_and_checked_form(request, user_preferences)

    month_list = list_of_months_in_fy(fiscal_year)
    month_name_list = []
    for month, year, year_name in month_list:
        month_name_list.append(year_name)


    department_list = ExpenseBudgetLine.create_budget_line_summary(user_preferences, month_list)

    can_edit = False
    if user.is_superuser:
        can_edit = True

    context = {
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': fiscal_year,
        'department_list': department_list,
        'can_edit': can_edit
        }
    return render(request, 'budget_line_summary.html', context)

@login_required
def budget_line_summary2(request):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    if request.method == 'POST':
        process_preferences_and_checked_form(request, user_preferences)

    month_list = list_of_months_in_fy(fiscal_year)
    month_name_list = []
    for month, year, year_name in month_list:
        month_name_list.append(year_name)

    department_list = []
    for department in Department.objects.all():
        budget_line_list = []
        department_totals_list=[]
        department_total = 0
        budget_total = 0
        adjusted_budget_total = 0
        for month, year, year_name in month_list:
            department_totals_list.append(dollar_format_parentheses(department.total_for_month(user_preferences, month, year),True))
        for budget_line in BudgetLine.objects.filter(Q(fiscal_year__id=fiscal_year.id)&Q(department__id=department.id)):
            data_entries = []
            budget_total = budget_total+budget_line.amount_available
            adjusted_budget_total = adjusted_budget_total+budget_line.adjusted_budget(user_preferences)
            budget_adjustment_note = ''
            for month, year, year_name in month_list:
                note = budget_line.retrieve_breakdown(user_preferences,month, year)
                budget_adjustment_note = budget_adjustment_note+budget_line.retrieve_budget_adjustment_breakdown(user_preferences,month, year)
                entry = budget_line.credit_month(user_preferences,month, year)-budget_line.debit_month(user_preferences,month, year)
                data_entries.append({'amount': dollar_format_parentheses(entry,False), 'breakdown':note})
                department_total = department_total + entry

            total_budget_line = budget_line.total_credit(user_preferences)-budget_line.total_debit(user_preferences)

            budget_remaining_in_line = budget_line.amount_remaining(user_preferences)
            budget_remaining_is_negative = False
            if budget_remaining_in_line < 0:
                budget_remaining_is_negative = True

            budget_line_list.append({'budget_line': budget_line,
                                     'data_entries': data_entries,
                                     'budget_adjustment_note': budget_adjustment_note,
                                     'total_debit_minus_credit': dollar_format_parentheses(total_budget_line,True),
                                     'budget_line_available': dollar_format_parentheses(budget_line.amount_available,True),
                                     'adjusted_budget': dollar_format_parentheses(budget_line.adjusted_budget(user_preferences),True),
                                     'budget_line_remaining': dollar_format_parentheses(budget_remaining_in_line,True),
                                     'remaining_negative': budget_remaining_is_negative})
        budget_remaining = adjusted_budget_total+department_total
#        print budget_remaining, adjusted_budget_total, department_total
        budget_remaining_is_negative = False
        if budget_remaining < 0:
            budget_remaining_is_negative = True
        department_list.append({'department': department,
                                'budget_line_list': budget_line_list,
                                'month_name_list': month_name_list,
                                'department_totals_list': department_totals_list,
                                'department_total': dollar_format_parentheses(department_total,True),
                                'budget_total': dollar_format_parentheses(budget_total,True),
                                'adjusted_budget_total': dollar_format_parentheses(adjusted_budget_total,True),
                                'budget_remaining':dollar_format_parentheses(budget_remaining,True),
                                'budget_remaining_is_negative': budget_remaining_is_negative})

    can_edit = False
    if user.is_superuser:
        can_edit = True

    context = {
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': fiscal_year,
        'department_list': department_list,
        'can_edit': can_edit
        }
    return render(request, 'budget_line_summary2.html', context)



@login_required
def owner_summary(request):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    if request.method == 'POST':
        process_preferences_and_checked_form(request, user_preferences)

    data_list = []
    for department_member in DepartmentMember.objects.all():
        summary_list, total, total_is_negative = department_member.subaccount_totals_summary(user_preferences)
        data_list.append({
                'department_member': department_member,
                'subaccount_summary': summary_list, 
                'total': total, 
                'total_is_negative': total_is_negative
                })

    can_edit = False
    if user.is_superuser:
        can_edit = True

    context = { 
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': fiscal_year,
        'can_edit': can_edit,
        'data_list': data_list
        }
    return render(request, 'owner_summary.html', context)












def list_of_months_in_fy(fy):
    begin_month = fy.begin_on.month
    begin_year = fy.begin_on.year
    end_month = fy.end_on.month
    end_year = fy.end_on.year

    month_dict={1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun',
                7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
    if begin_year > end_year:
        return []
    if (begin_year == end_year) and (begin_month>end_month):
        return []
    month_list = []
    month = begin_month
    year = begin_year
    end_reached = False
    while not end_reached:
        month_list.append([month, year, month_dict[month]+" '"+str(year%100)])
        month = month+1
        if month == 13:
            month = 1
            year = year+1
        if (year > end_year) or ((year == end_year) and (month > end_month)):
            end_reached = True
    return month_list







@login_required
def new_budget_entry(request, id = None):
# if id == None (i.e., if no argument is passed and id gets the default setting of None) create a new 
# budget entry; otherwise, edit the entry with the id that gets passed    
    user = request.user
    user_preferences = user.user_preferences.all()[0]
    fy_id = user_preferences.fiscal_year_to_view.id

    ExpenseBudgetLineFormset = inlineformset_factory(Expense, ExpenseBudgetLine, formset = BaseExpenseBudgetLineFormset, extra=3)
    ExpenseBudgetLineFormset.form = staticmethod(curry(ExpenseBudgetLineForm, fiscal_year_id = fy_id))
    fiscal_year = FiscalYear.objects.get(pk=fy_id)

    if id:
        expense = Expense.objects.get(pk=id)
        form_date = expense.date.strftime('%m/%d/%Y')
    else:
        expense = Expense()
        form_date = ''

    date_error = ''
    if request.method == 'POST':
        expense_form = ExpenseModelForm(request.POST, instance=expense, prefix='expenses')
        formset = ExpenseBudgetLineFormset(request.POST, instance = expense, prefix='expensebudgetlines')
        formset.is_valid()
        try:
            form_date = request.POST.getlist('inputdate')[0]
            date_new_format = datetime.strptime(form_date, '%m/%d/%Y').strftime('%Y-%m-%d')
            date_date_format = datetime.strptime(form_date, '%m/%d/%Y').date()
            if date_date_format < fiscal_year.begin_on or date_date_format > fiscal_year.end_on:
                date_error = 'Date must fall within the current FY ('+fiscal_year.begin_on.strftime('%m/%d/%Y')+' - '+fiscal_year.end_on.strftime('%m/%d/%Y')+')'
        except ValueError:
            date_error = 'Dates must be entered in the format mm/dd/yyyy.'

        if expense_form.is_valid() and formset.is_valid() and not formset.non_form_errors() and not date_error:
            r = expense_form.save(commit=False)
            r.date = date_new_format
            r.save()
            formset.save()
            next = request.GET.get('next','profile')
            return redirect(next)
        else:
            form_date = request.POST.getlist('inputdate')[0]
    else:
        expense_form = ExpenseModelForm(instance=expense, prefix='expenses')
        formset = ExpenseBudgetLineFormset(instance = expense, prefix='expensebudgetlines')
    
    budget_line_objects = BudgetLine.objects.filter(Q(fiscal_year__id = fy_id))

    budget_lines_with_subaccounts = []
    for bl in budget_line_objects:
        if bl.has_subaccounts:
            budget_lines_with_subaccounts.append(str(bl.id))

    json_bls_with_sas = json.dumps(budget_lines_with_subaccounts)

    budget_line_labels = []
    subaccount_labels = []
    for form in formset:
        budget_line_labels.append(form['budget_line'].id_for_label)
        subaccount_labels.append(form['subaccount'].id_for_label)

    json_budget_line_labels = json.dumps(budget_line_labels)
    json_subaccount_labels = json.dumps(subaccount_labels)
    errordict={}
    dict = {"formset": formset,
            "date": form_date,
            "date_error": date_error,
            "expense_form": expense_form,
            "json_budget_line_labels": json_budget_line_labels,
            "json_subaccount_labels": json_subaccount_labels,
            "json_bls_with_sas": json_bls_with_sas
            }
    return render(request, 'new_budget_entry.html', dict)

def process_preferences_and_checked_form(request, user_preferences):
    expenses_to_check_list= request.POST.getlist('expense_check_flag')

    for expense_id in expenses_to_check_list:
        expense = Expense.objects.get(pk = expense_id)
        expense.checked = True
        expense.save()
    checked_only = request.POST.getlist('checked')[0]
    encumbered_only = request.POST.getlist('encumbered')[0]
    future_only = request.POST.getlist('future')[0]
    if checked_only == 'checked_only':
        user_preferences.view_checked_only = True
    else:
        user_preferences.view_checked_only = False
    if encumbered_only == 'encumbered_only':
        user_preferences.view_encumbrances_only = True
    else:
        user_preferences.view_encumbrances_only = False
    if future_only == 'future_only':
        user_preferences.view_future_only = True
    else:
        user_preferences.view_future_only = False
    user_preferences.save()
    return



@login_required
def delete_expense_confirmation(request, id):
    expense = Expense.objects.get(pk = id)
    if "return_to_page" in request.session:
        sending_page = request.session["return_to_page"]
    else:
        sending_page = "home"

    context ={'expense': expense, 'sending_page': sending_page}
    return render(request, 'delete_expense_confirmation.html', context)

@login_required
def delete_expense(request, id):
    instance = Expense.objects.get(pk = id)

    instance.delete()

    if "return_to_page" in request.session:
        next = request.session["return_to_page"]
    else:
        next = "home"

    return redirect(next)


@login_required
def update_year_to_view(request, id):

    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]

    instance = UserPreferences.objects.get(pk = id)

    if request.method == 'POST':
        form = UpdateYearToViewForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            next = request.GET.get('next', 'profile')
            return redirect(next)
        else:
            return render(request, 'update_year_to_view.html', {'form': form})
    else:
        form = UpdateYearToViewForm(instance=instance)
        context = {'form': form}
        return render(request, 'update_year_to_view.html', context)

@login_required
def display_notes(request):

    user = request.user
    user_preferences = user.user_preferences.all()[0]

    fiscal_year = user_preferences.fiscal_year_to_view.begin_on.year
    fiscal_year_string = str(fiscal_year)+'-'+str(fiscal_year+1)

    temp_data = Note.objects.all().filter(Q(year__begin_on__year=fiscal_year))

    can_edit = False
    if user.is_superuser:
        can_edit = True

    datablock = []
    ii = 0
    for adv_notes in temp_data:
        ii = ii + 1
        datablock.append([adv_notes.updated_at, adv_notes.note, adv_notes.id, ii])

#    print datablock

    context = {
        'datablock': datablock,
        'can_edit': can_edit,
        'year': fiscal_year_string
        }
    return render(request, 'notes.html', context)


@login_required
def add_new_note(request):
    # The following list should just have one element(!)...hence "listofstudents[0]" is
    # used in the following....

    user = request.user
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    if request.method == 'POST':
        form = AddNoteForm(request.POST)
        if form.is_valid():
            p1 = Note.objects.create(
                                     year=fiscal_year
                                     )
            p1.note = form.cleaned_data['note']
            p1.save()
            return redirect('display_notes')
        else:
            return render(request, 'addNote.html', {'form': form})
    else:
        # user is not submitting the form; show them the blank add semester form
        form = AddNoteForm()
        context = {'form': form}
        return render(request, 'addNote.html', context)


@login_required
def update_note(request, id):

    instance = Note.objects.get(pk = id)
#    print instance.note
#    print instance.department
#    print instance.year

    if request.method == 'POST':
        form = AddNoteForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect('display_notes')
        else:
            return render(request, 'addNote.html', {'form': form})
    else:
        form = AddNoteForm(instance=instance)
        context = {'form': form}
        return render(request, 'addNote.html', context)

@login_required
def delete_note(request, id):
    instance = Note.objects.get(pk = id)

    instance.delete()
    return redirect('display_notes')

@login_required
def open_close_div_tracker(request,sending_page,id):
    """
    called by ajax; tracks which divs should be open and closed on the sending page
    """
# sending_page: 
#  0: budget_line_entries
#  1: subaccount_entries
#  2: credit_card_entries

    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    if int(sending_page) == 0:
        base_key = "budget_line_entries-"
        incoming_budget_line = BudgetLine.objects.get(pk=int(id))
        for budget_line in BudgetLine.objects.filter(Q(fiscal_year__id=fiscal_year.id)&Q(department__id=incoming_budget_line.department.id)):
            key = base_key+str(budget_line.id)
            if budget_line.id == int(id): # this is the one that just got clicked
                if key in request.session:
                    if request.session[key] == 'closed':
                        request.session[key] = 'open'
                    else:
                        request.session[key] = 'closed'
                else:
                    request.session[key] = 'open'
            else:
                request.session[key] = 'closed'
    elif int(sending_page) == 1:
        base_key = "subaccount_entries-"
        for subaccount in SubAccount.objects.filter(Q(fiscal_year__id=fiscal_year.id)):
            key = base_key+str(subaccount.id)
            if subaccount.id == int(id): # this is the one that just got clicked
                if key in request.session:
                    if request.session[key] == 'closed':
                        request.session[key] = 'open'
                    else:
                        request.session[key] = 'closed'
                else:
                    request.session[key] = 'open'
            else:
                request.session[key] = 'closed'
    elif int(sending_page) == 2:
        base_key = "credit_card_entries-"
        for credit_card in CreditCard.objects.all():
            key = base_key+str(credit_card.id)
            if credit_card.id == int(id): # this is the one that just got clicked
                if key in request.session:
                    if request.session[key] == 'closed':
                        request.session[key] = 'open'
                    else:
                        request.session[key] = 'closed'
                else:
                    request.session[key] = 'open'
            else:
                request.session[key] = 'closed'

#    print "list of keys:"
#    for key in request.session.keys():
#        print key, request.session[key]
    return_string = ""

    return HttpResponse(return_string)

def construct_json_open_div_id_list(request, sending_page):
    """
    constructs a json-formatted list of ids for the divs that should be open upon loading a given page
    """
# sending_page: 
#  0: budget_line_entries
#  1: subaccount_entries
#  2: credit_card_entries
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    open_div_list = []
    if int(sending_page) == 0:
        base_key = "budget_line_entries-"
        close_all_ids = False
        for department in Department.objects.all():
            all_ids_this_dept_closed = True
            for budget_line in BudgetLine.objects.filter(Q(fiscal_year__id=fiscal_year.id)&Q(department__id=department.id)):
                key = base_key+str(budget_line.id)
                if key in request.session:
                    if request.session[key]=='open':
                        if all_ids_this_dept_closed == False: #apparently there are more than one div within a given department that are marked as open; oops! close them all
                            close_all_ids = True
                        else:
                            all_ids_this_dept_closed = False
                            open_div_list.append(budget_line.id)
        
        if close_all_ids: # there has been an irregularity; close all the divs; reset the session variables, too
            open_div_list = []
            for department in Department.objects.all():
                for budget_line in BudgetLine.objects.filter(Q(fiscal_year__id=fiscal_year.id)&Q(department__id=department.id)):
                    key = base_key+str(budget_line.id)
                    request.session[key]='closed'

    elif int(sending_page) == 1:
        base_key = "subaccount_entries-"
        close_all_ids = False
        all_ids_closed = True
        for subaccount in SubAccount.objects.filter(Q(fiscal_year__id=fiscal_year.id)):
            key = base_key+str(subaccount.id)
            if key in request.session:
                if request.session[key]=='open':
                    if all_ids_closed == False: #apparently there are more than one div that are marked as open; oops! close them all
                        close_all_ids = True
                    else:
                        all_ids_closed = False
                        open_div_list.append(subaccount.id)
        
        if close_all_ids: # there has been an irregularity; close all the divs; reset the session variables, too
            open_div_list = []
            for subaccount in SubAccount.objects.filter(Q(fiscal_year__id=fiscal_year.id)):
                key = base_key+str(subaccount.id)
                request.session[key]='closed'

    elif int(sending_page) == 2:
        base_key = "credit_card_entries-"
        close_all_ids = False
        all_ids_closed = True
        for credit_card in CreditCard.objects.all():
            key = base_key+str(credit_card.id)
            if key in request.session:
                if request.session[key]=='open':
                    if all_ids_closed == False: #apparently there are more than one div that are marked as open; oops! close them all
                        close_all_ids = True
                    else:
                        all_ids_closed = False
                        open_div_list.append(credit_card.id)
        
        if close_all_ids: # there has been an irregularity; close all the divs; reset the session variables, too
            open_div_list = []
            for credit_card in CreditCard.objects.all():
                key = base_key+str(credit_card.id)
                request.session[key]='closed'

    json_open_div_id_list = json.dumps(open_div_list)

    return json_open_div_id_list



