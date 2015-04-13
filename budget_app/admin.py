from django.contrib import admin
from budget_app.models import *

class NoteAdmin(admin.ModelAdmin):
    list_display = ('note',)

class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user','fiscal_year_to_view',)

class ExpenseBudgetLineInline(admin.TabularInline):
    model = ExpenseBudgetLine

class ExpenseAdmin(admin.ModelAdmin):
    inlines = [
        ExpenseBudgetLineInline,
        ]

class AccountOwnerAdmin(admin.ModelAdmin):
    list_display = ('subaccount','department_member','fraction',)

class AccountOwnerInline(admin.TabularInline):
    model = AccountOwner

class SubAccountAdmin(admin.ModelAdmin):
    inlines = [
        AccountOwnerInline,
        ]
    list_display = ('name','abbrev', 'amount_available','fiscal_year',)

admin.site.register(FiscalYear)
admin.site.register(Note, NoteAdmin)
admin.site.register(DepartmentMember)
admin.site.register(UserPreferences, UserPreferencesAdmin)
admin.site.register(BudgetLine)
admin.site.register(Expense, ExpenseAdmin)
admin.site.register(SubAccount, SubAccountAdmin)
admin.site.register(CreditCard)
admin.site.register(ExpenseBudgetLine)
admin.site.register(Department)
admin.site.register(AccountOwner, AccountOwnerAdmin)
