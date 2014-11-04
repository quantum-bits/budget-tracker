from collections import namedtuple

from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.shortcuts import render, redirect
from django.template import RequestContext
from django.utils import simplejson
from django.utils.functional import curry

from .models import *
from .forms import *

import csv
from django.http import HttpResponse, HttpResponseRedirect
import xlwt
from os.path import expanduser
from datetime import date
from datetime import datetime

def home(request):
    return render(request, 'home.html')



# on form for entering expenses, return an error if the date is not
# within the FY that is currently being viewed!!!!

# when displaying data, need to limit it to the current FY!!!

# NEXT:
# 0. new_budget_entry: look up how to do custom "cleaned data"...probably in the views documentation
#    for django
# 1. if is_split_transaction: put something on the budget_line_entries page and the subaccount page as a 
#    warning if the person is about to check off the transaction...!
# 2. on budget_line_entries and subaccount pages -- put totals in headings 
#    for divs(?); compare to amount remaining in account

 
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

    if request.method == 'POST':
        process_preferences_and_checked_form(request, user_preferences)

    expense_list = []
    for expense in Expense.objects.all():
        if expense.date <= fiscal_year.end_on and expense.date >= fiscal_year.begin_on:
            if expense.include_expense(user_preferences):
                expense_list.append(expense)
                print expense.abbrev_note()

    context = { 
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': fiscal_year,
        'expense_list': expense_list
        }
    return render(request, 'budget_entries.html', context)

@login_required
def budget_line_entries(request):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    if request.method == 'POST':
        process_preferences_and_checked_form(request, user_preferences)

    budget_line_list = []
    for budget_line in BudgetLine.objects.filter(fiscal_year__id=fiscal_year.id):
        ebl_list = []
        for expense_budget_line in budget_line.expense_budget_line.all():
            if expense_budget_line.expense.include_expense(user_preferences):
                ebl_list.append(expense_budget_line)
        budget_line_list.append({'budget_line': budget_line, 
                                 'expense_budget_line_list': ebl_list,
                                 'total_debit': dollar_format(budget_line.total_debit(user_preferences)),
                                 'total_credit': dollar_format(budget_line.total_credit(user_preferences)),
                                 'budget_line_available': dollar_format(budget_line.amount_available),
                                 'budget_line_remaining': dollar_format(budget_line.amount_remaining(user_preferences))})

    context = {
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': fiscal_year,
        'budget_line_list': budget_line_list
        }
    return render(request, 'budget_line_entries.html', context)


def dollar_format(amount):
    return "{0:.2f}".format(amount)

@login_required
def subaccount_entries(request):
    user = request.user
# assumes that users each have exactly ONE UserPreferences object
    user_preferences = user.user_preferences.all()[0]
    fiscal_year = user_preferences.fiscal_year_to_view

    if request.method == 'POST':
        process_preferences_and_checked_form(request, user_preferences)

    subaccount_list = []
    for subaccount in SubAccount.objects.filter(fiscal_year__id=fiscal_year.id):
        ebl_list = []
        for expense_budget_line in subaccount.expense_budget_line.all():
            if expense_budget_line.expense.include_expense(user_preferences):
                ebl_list.append(expense_budget_line)
        subaccount_list.append({'subaccount': subaccount, 
                                'expense_budget_line_list': ebl_list,
                                'total_debit': dollar_format(subaccount.total_debit(user_preferences)),
                                'total_credit': dollar_format(subaccount.total_credit(user_preferences)),
                                'subaccount_available': dollar_format(subaccount.amount_available),
                                'subaccount_remaining': dollar_format(subaccount.amount_remaining(user_preferences))})

    context = { 
        'user_preferences': user_preferences,
        'user': user,
        'fiscal_year': fiscal_year,
        'subaccount_list': subaccount_list
        }
    return render(request, 'subaccount_entries.html', context)

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

    json_bls_with_sas = simplejson.dumps(budget_lines_with_subaccounts)

    budget_line_labels = []
    subaccount_labels = []
    for form in formset:
        budget_line_labels.append(form['budget_line'].id_for_label)
        subaccount_labels.append(form['subaccount'].id_for_label)

    json_budget_line_labels = simplejson.dumps(budget_line_labels)
    json_subaccount_labels = simplejson.dumps(subaccount_labels)
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
    context ={'expense': expense}
    return render(request, 'delete_expense_confirmation.html', context)

@login_required
def delete_expense(request, id):
    instance = Expense.objects.get(pk = id)

    instance.delete()
    return redirect('budget_entries')


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

