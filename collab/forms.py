from django import forms
from django.contrib.auth.models import User
from .models import Project, Task

class ProjectForm(forms.ModelForm):
    team_members = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Team Members"
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True,
        label="Due Date"
    )

    class Meta:
        model = Project
        fields = ['title', 'description', 'due_date', 'status', 'team_members']



class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['name', 'description', 'due_date', 'assigned_to', 'status', 'priority']



# class ProjectForm(forms.ModelForm):
#     team_members = forms.ModelMultipleChoiceField(
#         queryset=User.objects.all(),
#         widget=forms.CheckboxSelectMultiple,
#         required=False
#     )

#     class Meta:
#         model = Project
#         fields = ['title', 'description', 'status', 'due_date', 'team_members']