from django import forms
from django.contrib.auth.models import User
from django.db.models import Q
from models import *
from django.forms.widgets import RadioSelect
import decimal

class ExpenseModelForm(forms.ModelForm):

    class Meta:
        model = Expense
        exclude = ('date')
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
                    raise forms.ValidationError("Amounts must be great than zero.  Use Debit or Credit accordingly.")
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

"""
    def clean(self):
        if any(self.errors):
            return
        begin_times = []
        end_times = []

        day_schedules = {0:[], 1:[], 2:[], 3:[], 4:[]}
        for subform in self.forms:
# need to do a "try/except" here b/c the form could have some blank rows if the user skips
# down and enters data a few rows down....
            try:
                begin_time = subform.cleaned_data['begin_at']
                end_time = subform.cleaned_data['end_at']
                day = subform.cleaned_data['day']
                begin_time_decimal = convert_time_to_decimal(begin_time)
                end_time_decimal = convert_time_to_decimal(end_time)
                if end_time_decimal <= begin_time_decimal:
                    raise forms.ValidationError("Ending time must be after beginning time.")

                for time_block in day_schedules[day]:
                    if (begin_time_decimal < time_block[1] and begin_time_decimal > time_block[0]
                        ) or (end_time_decimal < time_block[1] and end_time_decimal > time_block[0]
                        ) or (begin_time_decimal <= time_block[0] and end_time_decimal >= time_block[1]):
                        raise forms.ValidationError("Time blocks for a given day within a course offering cannot overlap.")

                day_schedules[day].append([begin_time_decimal, end_time_decimal])
            except KeyError:
                pass
"""


"""
class RegistrationForm(forms.ModelForm):
    username = forms.CharField(label=(u'User Name'))
    email = forms.EmailField(label=(u'Email Address'))
    password = forms.CharField(label=(u'Password'),
                               widget=forms.PasswordInput(render_value=False))

    password1 = forms.CharField(label=(u'Verify Password'),
                                widget=forms.PasswordInput(render_value=False))

    class Meta:
        model = Student
        exclude = ('user',)

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError("That username is already taken; please select another.")

    def clean(self):
        password = self.cleaned_data.get('password')
        password1 = self.cleaned_data.get('password1')
        if password and password1 and password != password1:
            raise forms.ValidationError("The passwords did not match.  Please try again.")

        # something seems to be wrong here -- it doesn't associate the error with
        # password; it does throw the exception, I think (i.e., it returns an error), but
        # it doesn't specifically give the password error message....
        return self.cleaned_data
"""

class AddNoteForm(forms.ModelForm):

    class Meta:
        model = Note
        exclude = ('department', 'year')

"""
class BaseInstructorFormSet(forms.models.BaseInlineFormSet):

    def clean(self):
        if any(self.errors):
            return
        instructors = []
        for subform in self.forms:
# need to do a "try/except" here b/c the form could have some blank rows if the user skips
# down and enters data a few rows down....
            try:
                instructor = subform.cleaned_data['instructor']
#                delete = subform.cleaned_data['delete']
#                print delete
                if instructor in instructors:
                    raise forms.ValidationError("Each instructor can only be listed once.")
                instructors.append(instructor)
            except KeyError:
                pass


class InstructorForm(forms.ModelForm):

    def __init__(self, department_id, *args, **kwargs):
        super (InstructorForm,self).__init__(*args,**kwargs)
        self.fields['instructor'].queryset = FacultyMember.objects.filter(Q(department__id = department_id))

    class Meta:
        model = OfferingInstructor


class BaseClassScheduleFormset(forms.models.BaseInlineFormSet):

    def clean(self):
        if any(self.errors):
            return
        begin_times = []
        end_times = []

        day_schedules = {0:[], 1:[], 2:[], 3:[], 4:[]}
        for subform in self.forms:
# need to do a "try/except" here b/c the form could have some blank rows if the user skips
# down and enters data a few rows down....
            try:
                begin_time = subform.cleaned_data['begin_at']
                end_time = subform.cleaned_data['end_at']
                day = subform.cleaned_data['day']
                begin_time_decimal = convert_time_to_decimal(begin_time)
                end_time_decimal = convert_time_to_decimal(end_time)
                if end_time_decimal <= begin_time_decimal:
                    raise forms.ValidationError("Ending time must be after beginning time.")

                for time_block in day_schedules[day]:
                    if (begin_time_decimal < time_block[1] and begin_time_decimal > time_block[0]
                        ) or (end_time_decimal < time_block[1] and end_time_decimal > time_block[0]
                        ) or (begin_time_decimal <= time_block[0] and end_time_decimal >= time_block[1]):
                        raise forms.ValidationError("Time blocks for a given day within a course offering cannot overlap.")

                day_schedules[day].append([begin_time_decimal, end_time_decimal])
            except KeyError:
                pass

"""
def convert_time_to_decimal(time):

    decimal_time = time.hour+time.minute/60.0
    return decimal_time

class BaseCourseOfferingFormset(forms.models.BaseInlineFormSet):

# This can be used for future expansion -- e.g., for error trapping on field entries.


    def clean(self):
        if any(self.errors):
            return

#class OtherLoadForm(forms.ModelForm):

#    class Meta:
#        model = OtherLoad
#        exclude = ('load_type',)

#    def __init__(self, dept_id, *args, **kwargs):
#        department_id = dept_id
#        super (AddCourseForm,self).__init__(*args,**kwargs)
#        self.fields['subject'].queryset = Subject.objects.filter(Q(department__id = department_id))


class UpdateRoomsToViewForm(forms.ModelForm):

    class Meta:
        model = UserPreferences
        exclude = ('user','department_to_view','faculty_to_view','academic_year_to_view',
                   'permission_level','other_load_types_to_view',)

class UpdateYearToViewForm(forms.ModelForm):

    class Meta:
        model = UserPreferences
        exclude = ('user','department_to_view','faculty_to_view','rooms_to_view',
                   'permission_level','other_load_types_to_view',)

class UpdateLoadsToViewForm(forms.ModelForm):

    class Meta:
        model = UserPreferences
        exclude = ('user','department_to_view','faculty_to_view','rooms_to_view',
                   'permission_level','academic_year_to_view',)



class UpdateFacultyToViewForm(forms.ModelForm):

    class Meta:
        model = UserPreferences
        exclude = ('user','department_to_view','rooms_to_view','academic_year_to_view',
                   'permission_level','other_load_types_to_view',)

    def __init__(self, dept_id, *args, **kwargs):
        department_id = dept_id
        super (UpdateFacultyToViewForm,self).__init__(*args,**kwargs)
        self.fields['faculty_to_view'].queryset = FacultyMember.objects.filter(Q(department__id = department_id))

class UpdateDepartmentToViewForm(forms.ModelForm):

    class Meta:
        model = UserPreferences
        exclude = ('user','faculty_to_view','rooms_to_view','academic_year_to_view',
                   'permission_level','other_load_types_to_view',)


#class CoursesToCopyForm(forms.Form):
#    copy_this_course = forms.CheckboxMultiSelect(choices=['one','two'], required = False)

#    def __init__(self, name_list, *args, **kwargs):
#        super (CoursesToCopyForm,self).__init__(*args,**kwargs)
#        copy_this_course = forms.CheckboxMultiSelect(choices=choices, required = False)
