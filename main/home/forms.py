from django import forms
# from snowpenguin.django.recaptcha3.fields import ReCaptchaField

from home.models import GameOrder


class FranchForm(forms.Form):
    name = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'control__input',
            'placeholder': 'ИМЯ',
            'required': 'required',
            'id': ''
        })
    )
    phone = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'control__input',
            'placeholder': 'ТЕЛЕФОН',
            'required': 'required',
            'id': ''
        })
    )
    city = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'control__input',
            'placeholder': 'ГОРОД',
            'required': 'required',
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
            'class': 'control__input',
            'name': 'how',
            'id': ''
            
        })
    )
    comment = forms.CharField(
        label='',
        widget=forms.Textarea(attrs={
            'class': 'control__input control__input--textarea',
            'placeholder': 'Комментарий',
            'required': 'required',
            'id': ''
        })
    )   





class CorpForm(forms.Form):
    

    name = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'corp-form__input',
            'placeholder': 'Имя',
            'required': 'required',
            'id': ''
        })
    )
    phone = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'corp-form__input',
            'placeholder': '+7 (999) 999 99-99',
            'required': 'required',
            'id': ''
        })
    )
    email = forms.EmailField(
        label='',
        widget=forms.EmailInput(attrs={
            'class': 'corp-form__input',
            'placeholder': 'Email',
            'required': 'required',
            'id': ''
        })
    )
    data = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'corp-form__input',
            'placeholder': 'Дата',
            'id': '',
            'type': 'date'
        })
    )

    city = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'corp-form__input',
            'placeholder': 'Город',
        
            'id': '',
            'value': 'Краснодар'
        })
    )
    numbers = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'corp-form__input',
            'placeholder': 'Количество человек',
            'required': 'required',
            'id': ''
        })
    )

    how_call = forms.ChoiceField(
        label='',
        required=False,  
        choices=[
            ('', 'Удобный способ связи'),
            ('Звонок', 'Звонок'),
            ('Telegram', 'Telegram'),
            ('Viber', 'Viber'),
            ('WhatsApp', 'WhatsApp'),
            ('Email', 'Email'),
       
        ],
        widget=forms.Select(attrs={
            'class': 'corp-form__input',
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
            'class': 'corp-form__input',
            'name': 'how',
            'id': ''
            
        })
    )

    place = forms.ChoiceField(
        label='',
        required=False,  
        choices=[
            ('', 'Место проведения'),
            ('', 'Уже известно'),
            ('', 'Еще неизвестно'),
            ('', 'Можете посоветовать?'),
           
            
        ],
        widget=forms.Select(attrs={
            'class': 'corp-form__input',
            'name': 'place',
            'id': ''
            
        })
    )




class GameOrderForm(forms.ModelForm):
    


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
        min_value=1,
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