from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    'budget_app.views',

    url(r'^home/$', 'home'),

    url(r'^profile/$', 'profile', name='profile'),
    url(r'^budgetentries/$', 'budget_entries', name='budget_entries'),
    url(r'^budgetlineentries/$', 'budget_line_entries', name='budget_line_entries'),
    url(r'^subaccountentries/$', 'subaccount_entries', name='subaccount_entries'),
    url(r'^summary/$', 'summary', name='summary'),
    url(r'^newbudgetentry/$', 'new_budget_entry', name='new_budget_entry'),
    url(r'^newbudgetentry/(\d+)/$', 'new_budget_entry', name='new_budget_entry'),
    url(r'^deleteexpense/(\d+)/$', 'delete_expense', name='delete_expense'),
    url(r'^deleteexpenseconfirmation/(\d+)/$', 'delete_expense_confirmation', name='delete_expense_confirmation'),

    url(r'^updateyeartoview/(\d+)/$', 'update_year_to_view', name='update_year_to_view'),

    url(r'^notes/', 'display_notes', name='display_notes'),
    url(r'^addnote/', 'add_new_note', name='add_new_note'),
    url(r'^updateNote/(\d+)/$', 'update_note', name='update_note'),
    url(r'^deleteNote/(\d+)/$', 'delete_note', name='delete_note'),

)
