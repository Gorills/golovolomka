from django import forms
# from snowpenguin.django.recaptcha3.fields import ReCaptchaField

from home.models import GameOrder, Games


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
            'placeholder': 'Иван Иванов',
            'required': 'required',
            'id': 'id_name',
        })
    )
    phone = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'corp-form__input',
            'placeholder': '+7 (999) 999-99-99',
            'required': 'required',
            'id': 'id_phone',
            'inputmode': 'tel',
        })
    )
    email = forms.EmailField(
        label='',
        widget=forms.EmailInput(attrs={
            'class': 'corp-form__input',
            'placeholder': 'you@example.com',
            'required': 'required',
            'id': 'id_email',
        })
    )
    data = forms.CharField(
        label='',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'corp-form__input corp-form__input--date',
            'placeholder': 'ДД.ММ.ГГГГ',
            'id': 'id_data',
            'inputmode': 'numeric',
            'autocomplete': 'off',
        })
    )

    city = forms.CharField(
        label='',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'corp-form__input',
            'placeholder': 'Краснодар',
            'id': 'id_city',
        })
    )
    numbers = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'corp-form__input',
            'placeholder': 'Например, 25',
            'required': 'required',
            'id': 'id_numbers',
            'inputmode': 'numeric',
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
            'class': 'corp-form__input corp-form__input--select',
            'id': 'id_how_call',
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
            'class': 'corp-form__input corp-form__input--select',
            'id': 'id_how',
        })
    )

    place = forms.ChoiceField(
        label='',
        required=False,
        choices=[
            ('', 'Выберите вариант'),
            ('Уже известно', 'Уже известно'),
            ('Еще неизвестно', 'Ещё неизвестно'),
            ('Можете посоветовать?', 'Можете посоветовать?'),
        ],
        widget=forms.Select(attrs={
            'class': 'corp-form__input corp-form__input--select',
            'id': 'id_place',
        })
    )




class GameOrderForm(forms.ModelForm):
    


    game_id = forms.CharField(
        label='',
        required=True,
        error_messages={'required': 'Не выбрана игра'},
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
        initial=2,
        widget=forms.HiddenInput(attrs={
            'id': 'id_command_number',
        }),
    )
    # Не model-поля: в game_callback дублируем в agree_privacy_policy + agree_personal_data
    consent_privacy_and_rules = forms.BooleanField(
        label='',
        required=True,
        error_messages={
            'required': 'Необходимо согласие с правилами и политикой персональных данных',
        },
        widget=forms.CheckboxInput(attrs={
            'class': 'popup__checkbox',
            'id': 'id_consent_privacy_and_rules',
            'required': 'required',
        }),
    )
    consent_info_messages = forms.BooleanField(
        label='',
        required=True,
        error_messages={
            'required': 'Необходимо согласие на получение информационных сообщений',
        },
        widget=forms.CheckboxInput(attrs={
            'class': 'popup__checkbox',
            'id': 'id_consent_info_messages',
            'required': 'required',
        }),
    )

    class Meta:
        model = GameOrder
        fields = [
            'game_id', 'command', 'name', 'phone', 'comment', 'promo', 'how',
            'command_number',
        ]


    def clean_game_id(self):
        game_id = (self.cleaned_data.get('game_id') or '').strip()
        if not game_id:
            return game_id
        if not str(game_id).isdigit():
            raise forms.ValidationError('Некорректный идентификатор игры')
        if not Games.objects.filter(pk=game_id).exists():
            raise forms.ValidationError('Игра не найдена')
        return game_id

    def clean_date(self):
        # Добавьте свою логику очистки, если необходимо
        date = self.cleaned_data.get('date')
        return date