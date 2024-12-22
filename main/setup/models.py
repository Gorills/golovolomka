from venv import create
from django.db import models
from admin.singleton_model import SingletonModel

# Create your models here.

class BaseSettings(SingletonModel):
    name = models.CharField(max_length=350, blank=True, null=True)
    phone = models.CharField(max_length=250, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    vk = models.CharField(max_length=250, verbose_name='Вк')
    instagram = models.CharField(max_length=250, verbose_name='Инстаграм')
    telegram = models.CharField(max_length=250, verbose_name='Телеграм')
    whatsapp = models.CharField(max_length=250, verbose_name='Ватсап')
    copy_year = models.CharField(max_length=350, blank=True, null=True)
    copy = models.CharField(max_length=350, blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    meta_title = models.CharField(max_length=350, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=350, blank=True, null=True)
    social_image = models.FileField(upload_to="social_image", blank=True, null=True)
    
    logo_dark = models.FileField(upload_to="logo", blank=True, null=True, verbose_name='Логотип')
    icon_ico = models.FileField(upload_to="fav", blank=True, null=True)
    icon_png = models.FileField(upload_to="fav", blank=True, null=True)
    icon_svg = models.FileField(upload_to="fav", blank=True, null=True)
    theme_color = models.CharField(max_length=250, blank=True, null=True)
    active = models.BooleanField(default=False)
    debugging_mode = models.BooleanField(default=True)
    create_at = models.DateField(auto_now_add=True)
    update_at = models.DateField(auto_now=True)

    def get_phone(self):

        phone = self.phone

        try:
            res = phone.replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
        except:
            res = ''

        return res
    
    def get_whatsapp(self):
        phone = self.phone

        try:
            res = phone.replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
            if len(res) > 0 and res[0] == '8':
                res = '7' + res[1:]
        except:
            res = ''

        return res
    
    def get_telegram(self):
        phone = self.phone

        try:
            res = phone.replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
            if len(res) > 0 and res[0] == '8':
                res = '+7' + res[1:]
        except:
            res = ''

        return res


# {{ person.get_engine_display }}
# ENGINE_CHOICES = (
#     ("SQLite", "SQLite"),
#     ("PostgreSQL", "PostgreSQL"),
#     ("MySQL", "MySQL"),
# )

# class DBSettings(models.Model):
#     engine = models.CharField(max_length=250, choices=ENGINE_CHOICES, default='SQLite')
#     name = models.CharField(max_length=250)
#     user = models.CharField(max_length=250)
#     password = models.CharField(max_length=250)
#     host = models.CharField(max_length=250)



class RecaptchaSettings(SingletonModel):
    recaptcha_private_key = models.CharField(max_length=250, blank=True, null=True)
    recaptcha_public_key = models.CharField(max_length=250, blank=True, null=True)
    recaptcha_default_action = models.CharField(max_length=250, default='generic', blank=True, null=True)
    recaptcha_score_threshold = models.CharField(max_length=250, default='0.5', blank=True, null=True)
    recaptcha_language = models.CharField(max_length=250, default='ru', blank=True, null=True)



class EmailSettings(SingletonModel):
    host = models.CharField(max_length=250, blank=True, null=True)
    host_user = models.CharField(max_length=250, blank=True, null=True)
    host_password = models.CharField(max_length=250, blank=True, null=True)
    host_from = models.CharField(max_length=250, blank=True, null=True)
    host_port = models.CharField(max_length=250, default='465', blank=True, null=True)
    use_ssl = models.BooleanField(default=True)
    use_tls = models.BooleanField(default=False)



class CustomCode(models.Model):
    name = models.CharField(max_length=250, verbose_name='Название')
    code = models.TextField(verbose_name='Код')
    h_f = models.BooleanField(verbose_name='Шапка/Подвал')




class ThemeSettings(SingletonModel):
    THEME_CLASS = (
       ('default', 'default'),
       
    )
    name = models.CharField(max_length=250, choices=THEME_CLASS, default='default')
    


class Colors(SingletonModel):
    primary = models.CharField(max_length=50)
    secondary = models.CharField(max_length=50)
    success = models.CharField(max_length=50, default='#198754')
    danger = models.CharField(max_length=50, default='#dc3545')
    warning = models.CharField(max_length=50, default='#ffc107')
    info = models.CharField(max_length=50, default='#0dcaf0')