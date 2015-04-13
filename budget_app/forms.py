from django import forms
from django.contrib.auth.models import User
from django.db.models import Q
from models import *
from django.forms.widgets import RadioSelect
import decimal

class ExpenseModelForm(forms.ModelForm):

    class Meta:
        model = Expense
        exclude = ('date',)
        widgets = {
          'extra_note': forms.Textarea(attrs={'rows':2, 'cols':15})
        }

class ExpenseBudgetLineForm(forms.ModelForm):

    def __init__(self, fiscal_year_id, *args, **kwargs):
        super (ExpenseBudgetLineForm,self).__init__(*args,**kwargs)
        self.fields['budget_line'].queryset = BudgetLine.objects.filter(Q(fiscal_year__id = fiscal_year_id))
        self.fields['subaccount'].queryset = SubAccount.objects.filter(Q(fiscal_year__id = fiscal_year_id))

    class Meta:
        model = ExpenseBudgetLine


class BaseExpenseBudgetLineFormset(forms.models.BaseInlineFormSet):

    def clean(self):
        if any(self.errors):
            return
        budget_line_id_list = []
        number_to_delete = 0
        for subform in self.forms:
            try:
                amount = subform.cleaned_data['amount']
                if decimal.Decimal(amount) <=0:
                    raise forms.ValidationError("Amounts must be greater than zero.  Use Debit or Credit accordingly.")
                budgetline = subform.cleaned_data['budget_line']
#                if budgetline.id in budget_line_id_list:
#                   raise forms.ValidationError("Each budget line may only be used once for a given transaction.")
                budget_line_id_list.append(budgetline.id)
                delete_this = subform.cleaned_data[u'DELETE']
                if delete_this:
                    number_to_delete = number_to_delete+1
            except KeyError:
                pass
        if len(budget_line_id_list) == 0:
            raise forms.ValidationError("Each transaction must use at least one budget line.")
        if number_to_delete >= len(budget_line_id_list):
            raise forms.ValidationError("Each transaction must use at least one budget line.  You cannot delete the last one(s).")


class AddNoteForm(forms.ModelForm):

    class Meta:
        model = Note
        exclude = ('department', 'year')


class UpdateYearToViewForm(forms.ModelForm):

    class Meta:
        model = UserPreferences
        exclude = ('user','view_checked_only','view_encumbrances_only','view_future_only',)
