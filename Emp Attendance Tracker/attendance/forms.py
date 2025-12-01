from django import forms
from .models import Employee, Attendance, Leave
from django.contrib.auth.models import User

class EmployeeRegisterForm(forms.Form):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    employee_id = forms.CharField(max_length=20)
    department = forms.CharField(max_length=100, required=False)
    designation = forms.CharField(max_length=100, required=False)
    is_admin = forms.BooleanField(required=False, label="Administrator (check for admin privileges)", help_text="Leave unchecked for regular employee, check for administrator access")


class AttendanceMarkForm(forms.Form):
    employee_id = forms.CharField(max_length=20, help_text="Employee ID to mark attendance for")
    action = forms.ChoiceField(choices=(("IN", "Clock In"), ("OUT", "Clock Out")), help_text="Attendance action")
    # optional timezone-aware timestamp (server will use now() if not provided)
    timestamp = forms.DateTimeField(required=False, help_text="Optional timestamp (server uses current time if not provided)")


class LeaveApplyForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }



