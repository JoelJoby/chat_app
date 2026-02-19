from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}))

    class Meta:
        model = CustomUser
        fields = ('username', 'email')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }
    
    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name == 'username':
                field.widget.attrs['placeholder'] = 'Username'
            elif field_name == 'email':
                field.widget.attrs['placeholder'] = 'Email Address'
            elif field_name.startswith('password'):
                 field.widget.attrs['placeholder'] = 'Password'
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email.lower()

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ("email", "username")

class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("email", "username", "is_active", "is_staff", "is_superuser")

class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))

    def clean_username(self):
        username = self.cleaned_data.get('username')
        return username.lower()
