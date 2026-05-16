from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Test, Question, CustomUser

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Código o Usuario",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 2024001'})
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'})
    )

class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = ['name', 'description', 'seconds_per_question', 'num_questions', 'max_attempts', 'is_active', 'questions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Test'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Instrucciones para el estudiante'}),
            'seconds_per_question': forms.NumberInput(attrs={'class': 'form-control'}),
            'num_questions': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_attempts': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'questions': forms.CheckboxSelectMultiple(),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'title', 'is_active', 'stimulus_image', 
            'option_1_image', 'option_2_image', 'option_3_image', 
            'option_4_image', 'option_5_image', 'option_6_image', 
            'correct_option'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'correct_option': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class StudentImportForm(forms.Form):
    csv_file = forms.FileField(label="Seleccionar archivo CSV", widget=forms.FileInput(attrs={'class': 'form-control'}))

class StudentForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
        required=False,
        help_text="Dejar en blanco para mantener la actual"
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código de estudiante'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.Role.STUDENT
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
