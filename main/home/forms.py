from django import forms
from snowpenguin.django.recaptcha3.fields import ReCaptchaField

from home.models import GameOrder


class GameOrderForm(forms.ModelForm):
    captcha = ReCaptchaField()

    game_id = forms.CharField(
        label='',
        required=False,
        widget=forms.HiddenInput(attrs={
            'class': 'popup__input',
            'placeholder': 'Игра',
            'hidden': 'hidden',
            'id': ''
        })
        
    )  
    name = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'popup__input',
            'placeholder': 'Имя',
            'required': 'required',
            'id': ''
        })
    )
    phone = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'popup__input',
            'placeholder': '+7 (999) 999 99-99',
            'required': 'required',
            'id': ''
        })
    )
    command = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'popup__input',
            'placeholder': 'Название команды',
            'required': 'required',
            'id': ''
        })
    )
    comment = forms.CharField(
        label='',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'popup__input',
            'placeholder': 'Комментарий',
            'id': ''
        })
    )
    promo = forms.CharField(
        label='',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'popup__input',
            'placeholder': 'Промокод',
            'id': ''
        })
    )
    how = forms.ChoiceField(
        label='',
        required=False,  
        choices=[
            ('', 'Как вы узнали о нас?'),
            ('Уже был(а) на играх', 'Уже был(а) на играх'),
            ('Instagram', 'Instagram'),
            ('Telegram', 'Telegram'),
            ('VK', 'VK'),
            ('Рекомендация знакомых', 'Рекомендация знакомых'),
            ('Поисковик в интернете', 'Поисковик в интернете'),
            ('СМИ', 'СМИ'),
        ],
        widget=forms.Select(attrs={
            'class': 'popup__input',
            'name': 'how',
            'id': ''
            
        })
    )
    command_number = forms.IntegerField(
        label='Количество человек',
        min_value=2,
        max_value=12,
        widget=forms.NumberInput(attrs={
            'class': 'popup__input',
            'value': '2',
            'required': 'required',
            'id': ''
        })
    )

    class Meta:
        model = GameOrder
        fields = ['game_id', 'command', 'name', 'phone', 'comment', 'promo', 'how', 'command_number']


    def clean_game_id(self):
        # Добавьте свою логику очистки, если необходимо
        game_id = self.cleaned_data.get('game_id')
        return game_id

    def clean_date(self):
        # Добавьте свою логику очистки, если необходимо
        date = self.cleaned_data.get('date')
        return date