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
# 1. Do a "freeze panes" thing like was done on iChair.  Do it for the budget entries page, and maybe other ones.
# 2. Possible to speed this app up?!?  Check it out with the debug toolbar, etc.
# 3. hint at the top of the budget lines page saying adj budget +/- expense = remaining


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
def budget_entries(request):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    request.session["return_to_page"] = "/budget_app/budgetentries/"

    if request.method == 'POST':
        process_preferences_and_checked_form(request, user_preferences)

    expense_list = []
    for expense in Expense.objects.all():
        if expense.date <= fiscal_year.end_on and expense.date >= fiscal_year.begin_on:
            if expense.include_expense(user_preferences):
                expense_list.append(expense)
#                print expense.abbrev_note()


    can_edit = False
    if user.is_superuser:
        can_edit = True

    context = { 
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': fiscal_year,
        'expense_list': expense_list,
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
            for expense_budget_line in budget_line.expense_budget_line.all():
                if expense_budget_line.expense.include_expense(user_preferences):
                    ebl_list.append(expense_budget_line)
            total_debit_minus_credit = budget_line.total_debit(user_preferences)-budget_line.total_credit(user_preferences)
            if total_debit_minus_credit < 0:
                d_m_c_string = " + "+dollar_format(-total_debit_minus_credit)
            else:
                d_m_c_string = " - "+dollar_format(total_debit_minus_credit)

            budget_line_list.append({'budget_line': budget_line, 
                                     'expense_budget_line_list': ebl_list,
                                     'total_debit': dollar_format(budget_line.total_debit(user_preferences)),
                                     'total_credit': dollar_format(budget_line.total_credit(user_preferences)),
                                     'budget_adjustment': dollar_format_parentheses(budget_line.budget_adjustment(user_preferences), True),
                                     'total_debit_minus_credit': d_m_c_string,
                                     'budget_line_available': dollar_format_parentheses(budget_line.amount_available, True),
                                     'adjusted_budget': dollar_format_parentheses(budget_line.adjusted_budget(user_preferences), True),
                                     'budget_line_remaining': dollar_format_parentheses(budget_line.amount_remaining(user_preferences), True)})
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
        for expense_budget_line in subaccount.expense_budget_line.all():
            if expense_budget_line.expense.include_expense(user_preferences):
                ebl_list.append(expense_budget_line)
        
        total_debit_minus_credit = subaccount.total_debit(user_preferences)-subaccount.total_credit(user_preferences)
        if total_debit_minus_credit < 0:
            d_m_c_string = " + "+dollar_format(-total_debit_minus_credit)
        else:
            d_m_c_string = " - "+dollar_format(total_debit_minus_credit)
                
        subaccount_list.append({'subaccount': subaccount, 
                                'expense_budget_line_list': ebl_list,
                                'total_debit': dollar_format(subaccount.total_debit(user_preferences)),
                                'total_credit': dollar_format(subaccount.total_credit(user_preferences)),
                                'budget_adjustment': dollar_format_parentheses(subaccount.budget_adjustment(user_preferences), True),
                                'total_debit_minus_credit': d_m_c_string,
                                'subaccount_available': dollar_format_parentheses(subaccount.amount_available, True),
                                'adjusted_budget': dollar_format_parentheses(subaccount.adjusted_budget(user_preferences), True),
                                'subaccount_remaining': dollar_format_parentheses(subaccount.amount_remaining(user_preferences), True)})

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
def subaccount_summary2(request):
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

    subaccount_totals_list=[]
    all_subaccounts_credit_minus_debit = 0
    for month, year, year_name in month_list:
        total_for_month = 0
        for subaccount in SubAccount.objects.filter(fiscal_year__id=fiscal_year.id).prefetch_related('expense_budget_line__expense'):
            total_for_month = total_for_month + subaccount.credit_month(user_preferences, month, year)-subaccount.debit_month(user_preferences, month, year)
        all_subaccounts_credit_minus_debit = all_subaccounts_credit_minus_debit + total_for_month
        subaccount_totals_list.append(dollar_format_parentheses(total_for_month,True))

    subaccount_list = []
    all_subaccounts_total = 0
    all_subaccounts_adjusted_total = 0
    budget_total = 0
    credit_minus_debit_total = 0

    for subaccount in SubAccount.objects.filter(fiscal_year__id=fiscal_year.id):
        owned_by = []
        for account_owner in subaccount.account_owners.all():
            owned_by.append(account_owner.department_member.last_name+" ({0:.0f}%)".format(account_owner.fraction*100))
        data_entries = []
        all_subaccounts_total = all_subaccounts_total+subaccount.amount_available
        subaccount_adjusted_budget=subaccount.adjusted_budget(user_preferences)
        all_subaccounts_adjusted_total = all_subaccounts_adjusted_total+subaccount_adjusted_budget
        budget_adjustment_note = ''
        for month, year, year_name in month_list:
            note = subaccount.retrieve_breakdown(user_preferences,month, year)
            budget_adjustment_note = budget_adjustment_note+subaccount.retrieve_budget_adjustment_breakdown(user_preferences,month, year)
            entry = subaccount.credit_month(user_preferences,month, year)-subaccount.debit_month(user_preferences,month, year)
            data_entries.append({'amount': dollar_format_parentheses(entry,False), 'breakdown':note})
#            department_total = department_total + entry
            credit_minus_debit_total = credit_minus_debit_total + entry

        total_subaccount = subaccount.total_credit(user_preferences)-subaccount.total_debit(user_preferences)
        budget_remaining_subaccount = subaccount.amount_remaining(user_preferences)
        budget_remaining_is_negative = False
        if budget_remaining_subaccount < 0:
            budget_remaining_is_negative = True
        subaccount_list.append({'subaccount': subaccount,
                                'owned_by': owned_by,
                                'data_entries': data_entries,
                                'budget_adjustment_note': budget_adjustment_note,
                                'total_debit_minus_credit': dollar_format_parentheses(total_subaccount,True),
                                'subaccount_available': dollar_format_parentheses(subaccount.amount_available,True),
                                'adjusted_budget': dollar_format_parentheses(subaccount_adjusted_budget,True),
                                'subaccount_remaining': dollar_format_parentheses(budget_remaining_subaccount,True),
                                'remaining_negative': budget_remaining_is_negative})

    budget_remaining = all_subaccounts_adjusted_total+credit_minus_debit_total
    budget_remaining_is_negative = False
    if budget_remaining < 0:
        budget_remaining_is_negative = True
    subaccount_data = {'subaccount_list': subaccount_list,
                       'all_subaccounts_total': all_subaccounts_total,
                       'month_name_list': month_name_list,
                       'adjusted_budget_total': all_subaccounts_adjusted_total,
                       'budget_remaining_is_negative': budget_remaining_is_negative,
                       'budget_remaining': dollar_format_parentheses(budget_remaining, True),
                       'budget_total': all_subaccounts_total,
                       'subaccount_totals_list': subaccount_totals_list,
                       'all_subaccounts_credit_minus_debit':dollar_format_parentheses(all_subaccounts_credit_minus_debit, True)}

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
        print budget_remaining, adjusted_budget_total, department_total
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
    return render(request, 'budget_line_summary.html', context)



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



