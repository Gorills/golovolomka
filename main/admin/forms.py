from django import forms

from setup.models import BaseSettings, Colors, ThemeSettings, CustomCode


from home.models import GameOrder, SliderSetup, Slider, Page, City, GamesSetup, GamesCategorySetup, GamesPhoto, GameCategory, Games, WhatSetup, WhatItem, WaitSetup, WaitItem, FAQSetup, FAQ, BtnBlockSetup, BtnBlockItem, HomeGamesSetup

from ckeditor_uploader.widgets import CKEditorUploadingWidget



class GamesSetupForm(forms.ModelForm):
    class Meta:
        model = GamesSetup
        fields = "__all__"



class GamesCategorySetupForm(forms.ModelForm):  
    class Meta:
        model = GamesCategorySetup
        fields = "__all__"




class GameCategoryForm(forms.ModelForm):  
    description = forms.CharField(label='Описание', required=False, widget=CKEditorUploadingWidget())
    class Meta:
        model = GameCategory
        fields = "__all__"



class GamesPhotoForm(forms.ModelForm):  
    class Meta:
        model = GamesPhoto
        fields = "__all__"



class GamesForm(forms.ModelForm):  
    class Meta:
        model = Games
        fields = "__all__"

        widgets = {
            "date_date": forms.DateInput(attrs={'type': 'date'})
        }

class WhatSetupForm(forms.ModelForm):
    text = forms.CharField(label='Описание', required=False, widget=CKEditorUploadingWidget())
    class Meta:
        model = WhatSetup
        fields = "__all__"


class WhatItemForm(forms.ModelForm):
    class Meta:
        model = WhatItem
        fields = "__all__"


class WaitSetupForm(forms.ModelForm):
    
    class Meta:
        model = WaitSetup
        fields = "__all__"


class WaitItemForm(forms.ModelForm):
    class Meta:
        model = WaitItem
        fields = "__all__"



class FAQSetupForm(forms.ModelForm):
    class Meta:
        model = FAQSetup
        fields = "__all__"



class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = "__all__"


class BtnBlockSetupForm(forms.ModelForm):
    class Meta:
        model = BtnBlockSetup
        fields = "__all__"


class BtnBlockItemForm(forms.ModelForm):
    class Meta:
        model = BtnBlockItem
        fields = "__all__"



class HomeGamesSetupForm(forms.ModelForm):
    text = forms.CharField(label='Текст', required=False, widget=CKEditorUploadingWidget())
    class Meta:
        model = HomeGamesSetup
        fields = "__all__"



class CityForm(forms.ModelForm):
    class Meta:
        model = City
        fields = "__all__"
        



class GameOrderForm(forms.ModelForm):
    class Meta:
        model = GameOrder
        fields = "__all__"




class CustomCodeForm(forms.ModelForm):
    class Meta:
        model = CustomCode
        fields = '__all__'

        widgets = { 
            'code' : forms.Textarea(attrs={
                'class': 'input',
            }),
            'name': forms.TextInput(attrs={
                'class': 'input',
            }),
            'subdomain': forms.Select(attrs={
                'class': 'input',
            }),
        }




# Услуги



# Страницы 
class PageForm(forms.ModelForm):
    text = forms.CharField(label='Текст страницы', required=False, widget=CKEditorUploadingWidget())
    class Meta:
        model = Page
        fields = "__all__"
        
        widgets = {
           
            'type': forms.Select(attrs={
                'class': 'input',
            }),
            'name': forms.TextInput(attrs={
                'class': 'input',
            }),
            'meta_h1': forms.TextInput(attrs={
                'class': 'input',
            }),
           
            'meta_title': forms.TextInput(attrs={
                'class': 'input',
            }),
            'meta_description': forms.Textarea(attrs={
                'class': 'input',
            }),
            'meta_keywords': forms.TextInput(attrs={
                'class': 'input',
            }),
            'page_order': forms.NumberInput(attrs={
                'class': 'input',
            }),
        }



# Cлайдер

class SliderSetupForm(forms.ModelForm):
    
    class Meta:
        model = SliderSetup
        fields = "__all__"
        widgets = {
            'speed': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Значение',
            })
        }



class SliderForm(forms.ModelForm):
    
    class Meta:
        model = Slider
        fields = "__all__"
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Название',
            }),
            'title': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Заголовок (не обязательно)',
            }),
            'text': forms.Textarea(attrs={
                'class': 'input',
                'placeholder': 'Текст (не обязательно)',
            }),
            'button_text': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Текст кнопки (не обязательно)',
            }),
            'link': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Ссылка (не обязательно)',
            }),
        }





class ThemeSettingsForm(forms.ModelForm):
    class Meta:
        model = ThemeSettings
        fields = [
            'name'
        ]
        widgets = {
            'name': forms.Select(attrs={
                'placeholder': 'Тема',
                'class': 'input'
            }),
        }
        labels = {
            'name': 'Выбрать тему',
        
        }

class ColorsForm(forms.ModelForm):
    class Meta:
        model = Colors
        fields = [
            'primary',
            'secondary',
            'success',
            'danger',
            'warning',
            'info',
        ]
        widgets = {
            'primary': forms.TextInput(attrs={
                
                'placeholder': 'Основной цвет',
                'type': 'color'
            }),
            'secondary': forms.TextInput(attrs={
                
                'placeholder': 'Дополнительный цвет',
                'type': 'color'
            }),
            'success': forms.TextInput(attrs={
                
                'placeholder': 'Цвет успеха',
                'type': 'color'
            }),
            'danger': forms.TextInput(attrs={
                
                'placeholder': 'Цвет ошибки',
                'type': 'color'
            }),
            'warning': forms.TextInput(attrs={
                
                'placeholder': 'Цвет предупреждения',
                'type': 'color'
            }),
            'info': forms.TextInput(attrs={
                
                'placeholder': 'Цвет инфо',
                'type': 'color'
            }),
        }
        labels = {
            'primary': 'Основной цвет',
            'secondary': 'Дополнительный цвет',
            'success': 'Цвет успеха',
            'danger': 'Цвет ошибки',
            'warning': 'Цвет предупреждения',
            'info': 'Цвет инфо',
        }





class SetupForm(forms.ModelForm):
    class Meta:
        model = BaseSettings
        fields = "__all__"
            
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Название сайта',
                
            }),
            'phone': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Телефон',
                
            }),
            'vk': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'vk',
                
            }),
            'instagram': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'instagram',
            }),
            'telegram': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'telegram',
            }),
            'whatsapp': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'whatsapp',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input',
                'placeholder': 'Email для клиентов'
            }),
           
            'copy_year': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Год копирайта',
                
            }),
            'copy': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Копирайт',
                
            }),
            'address': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Адрес',
                
            }),
            'meta_title': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Мета заголовок',
                
            }),
            'meta_description': forms.Textarea(attrs={
                'class': 'input',
                'placeholder': 'Мета описание',
                
            }),
            'meta_keywords': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Ключевые слова',
                
            }),
            'theme_color': forms.TextInput(attrs={
                
                'placeholder': 'Основной цвет',
                'type': 'color'
                
            }),
           
           
        }
        labels = {
            'name': 'Название сайта',
            'phone': 'Телефон',
            'email': 'Email для клиентов',
    
            'copy_year': 'Год копирайта',
            'copy': 'Копирайт',
            'address': 'Адрес',
            
            'meta_title': 'Мета заголовок',
            'meta_description': 'Мета описание',
            'meta_keywords': 'Ключевые слова',
            'social_image': 'Изображение для соц.сетей',
           
            'logo_dark': 'Логотип темный',
            'icon_ico': 'Иконка .ico',
            'icon_png': 'Иконка .png',
            'icon_svg': 'Иконка .svg',
            'theme_color': 'Основной цвет',
            'active': 'Разрешить индексацию',
            'debugging_mode': 'Режим разработки (вывод текстовой информации об ошибках)',
           
        }