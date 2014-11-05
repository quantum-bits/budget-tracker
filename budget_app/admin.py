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

admin.site.register(FiscalYear)
admin.site.register(Note, NoteAdmin)
admin.site.register(DepartmentMember)
admin.site.register(UserPreferences, UserPreferencesAdmin)
admin.site.register(BudgetLine)
admin.site.register(Expense, ExpenseAdmin)
admin.site.register(SubAccount)
admin.site.register(CreditCard)
admin.site.register(ExpenseBudgetLine)
admin.site.register(Department)
