from django import forms


class loginForm(forms.Form):
    email = forms.EmailField(label='email', max_length=200)
    password = forms.CharField(widget=forms.PasswordInput(), label="Password", max_length=200)


class SignUpForm(forms.Form):
    Firstname = forms.CharField(label='First Name')
    Lastname = forms.CharField(label='Last name')
    email = forms.CharField(widget=forms.EmailField(), label='Email')
    Address = forms.CharField(widget=forms.Textarea(), label='Address')
    password = forms.CharField(widget=forms.PasswordInput(), label="Password")

