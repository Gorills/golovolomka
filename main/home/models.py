from django.db import models
from django.urls import reverse
from admin.singleton_model import SingletonModel



class City(models.Model):
    name = models.CharField(max_length=250, verbose_name='Название')
    slug = models.CharField(max_length=250, verbose_name='Слаг', unique=True)
    phone = models.CharField(max_length=250, verbose_name='Телефон')
    address = models.TextField(verbose_name='Адрес')
    email = models.EmailField(verbose_name='Email')
    vk = models.CharField(max_length=250, verbose_name='Вк')
    instagram = models.CharField(max_length=250, verbose_name='Инстаграм')
    telegram = models.CharField(max_length=250, verbose_name='Телеграм')
    whatsapp = models.CharField(max_length=250, verbose_name='Ватсап')


    def __str__(self):
        return self.name



# locations = City.objects.all()
# LOCATIONS_CHOICES = [(loc.slug, loc.name) for loc in locations]



# Create your models here.

class SliderSetup(SingletonModel):

    suptitle = models.CharField(max_length=250, verbose_name='Подзаголовок', null=True, blank=True)
    title = models.CharField(max_length=250, verbose_name='Заголовок', null=True, blank=True)
    text = models.TextField(verbose_name='Текст', null=True, blank=True)
    button_text = models.CharField(max_length=250, verbose_name='Текст кнопки', null=True, blank=True)
    link = models.CharField(max_length=250, verbose_name='Ссылка', null=True, blank=True)

    show_popup = models.BooleanField(default=False, verbose_name='Показывать всплывающее окно')

    bg = models.ImageField(upload_to='slider', verbose_name='Фоновое изображение', null=True, blank=True)

    class Meta:
        verbose_name = 'Настройки слайдера'
        verbose_name_plural = 'Настройки слайдера'




class Slider(models.Model):
    name = models.CharField(max_length=250, verbose_name='Название')
    image = models.ImageField(upload_to='slider', verbose_name='Изображение')

    def __str__(self):
        return self.name

    class Meta:
       
        verbose_name = 'Слайдер'
        verbose_name_plural = 'Слайдеры'




class GamesSetup(SingletonModel):
    title = models.CharField(max_length=250, verbose_name='Заголовок', null=True, blank=True)
    bg = models.ImageField(upload_to='slider', verbose_name='Фоновое изображение', null=True, blank=True)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = 'Настройки расписания игр'
        verbose_name_plural = 'Настройки расписания игр'




class GamesCategorySetup(SingletonModel):
    title = models.CharField(max_length=250, verbose_name='Заголовок', null=True, blank=True)
    bg = models.ImageField(upload_to='slider', verbose_name='Фоновое изображение', null=True, blank=True)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = 'Настройки формата игр'
        verbose_name_plural = 'Настройки формата игр'



class GamesPhoto(models.Model):
    image = models.ImageField(upload_to='games', verbose_name='Изображение')

    def __str__(self):
        return self.image.url
    
    class Meta:
        verbose_name = 'Фото'
        verbose_name_plural = 'Фото'


class GameCategory(models.Model):
    name = models.CharField(max_length=250, verbose_name='Название')
    show_to_home = models.BooleanField(default=True, verbose_name='Показывать на главной')
    description_short = models.TextField(verbose_name='Описание краткое')
    description = models.TextField(verbose_name='Описание полное')

    def __str__(self):
        return self.name
    

from django.db.models import Sum

class Games(models.Model):
    category = models.ForeignKey(GameCategory, on_delete=models.CASCADE, verbose_name='Категория')
    name = models.CharField(max_length=250, verbose_name='Название')
    date = models.CharField(max_length=250, verbose_name='Дата')
    time = models.CharField(max_length=250, verbose_name='Время')
    price = models.PositiveIntegerField(verbose_name='Цена', default=600)
    duration = models.CharField(max_length=250, verbose_name='Длительность', default='150 минут')
    comands = models.CharField(max_length=250, verbose_name='Чел в команде', default='2-12')

    number_of_seats = models.PositiveIntegerField(verbose_name='Количество мест', default=50)

    city = models.ForeignKey(City, on_delete=models.CASCADE, verbose_name='Город', related_name='games')
    location = models.CharField(max_length=250, verbose_name='Адрес (если нет, то адрес будет взят из города)', null=True, blank=True)

    description = models.TextField(verbose_name='Описание (если нет, то описание будет взято из короткого описания категории)', null=True, blank=True)

    bg = models.ImageField(upload_to='games/bg', verbose_name='Изображение')



    def __str__(self):
        return self.name + ' - ' + self.city.name + ' - ' + self.date
    


    def reverve(self):
        # Получаем все заказы, связанные с текущей игрой
        orders = GameOrder.objects.filter(game=self)

        # Суммируем количество людей из всех заказов
        command_number_count = orders.aggregate(Sum('command_number'))['command_number__sum']

        try:
            if command_number_count > self.number_of_seats:
                return False
            else:
                return True
            
        except:
            return True
        
    

    class Meta:
        verbose_name = 'Игра'
        verbose_name_plural = 'Игры'



class GameOrder(models.Model):
    game = models.ForeignKey(Games, on_delete=models.CASCADE, verbose_name='Игра', related_name='orders')
    command = models.CharField(max_length=250, verbose_name='Название команды')
    name = models.CharField(max_length=250, verbose_name='Имя')
    phone = models.CharField(max_length=250, verbose_name='Телефон')
    comment = models.TextField(verbose_name='Комментарий', null=True, blank=True)
    promo = models.CharField(max_length=250, verbose_name='Промокод', null=True, blank=True)
    how = models.CharField(max_length=250, verbose_name='Как вы узнали о нас', null=True, blank=True)
    command_number = models.PositiveIntegerField(verbose_name='Количество человек', default=2)
    reserve = models.BooleanField(default=False, verbose_name='Резерв')
    

    def __str__(self):
        return self.name


class WhatSetup(SingletonModel):
    title = models.CharField(max_length=250, verbose_name='Заголовок', null=True, blank=True)
    bg = models.ImageField(upload_to='what', verbose_name='Фоновое изображение', null=True, blank=True)
    link = models.CharField(max_length=250, verbose_name='Ссылка', default="/pravila")

    video = models.FileField(upload_to='what', verbose_name='Видео', null=True, blank=True)
    embedded_video = models.TextField(null=True, blank=True, verbose_name='Встроенное видео (код для вставки)')

    text = models.TextField(verbose_name='Текст', null=True, blank=True)

    def __str__(self):  
        return self.title
    
    class Meta:
        verbose_name = 'Настройки блока что такое головоломка?'
        verbose_name_plural = 'Настройки блока что такое головоломка?'


class WhatItem(models.Model):
    title = models.CharField(max_length=250, verbose_name='Заголовок')
    text = models.TextField(verbose_name='Текст')

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = 'Блоки что такое головоломка?'
        verbose_name_plural = 'Блоки что такое головоломка?'




class WaitSetup(SingletonModel):
    title = models.CharField(max_length=250, verbose_name='Заголовок', null=True, blank=True)
    bg = models.ImageField(upload_to='wait', verbose_name='Фоновое изображение', null=True, blank=True)
    image = models.ImageField(upload_to='wait', verbose_name='Изображение', null=True, blank=True)

    def __str__(self):  
        return self.title
    
    class Meta:
        verbose_name = 'Настройки что тебя ждет'
        verbose_name_plural = 'Настройки что тебя ждет'



class WaitItem(models.Model):
    text = models.TextField(verbose_name='Текст')

    def __str__(self):  
        return self.text
    
    class Meta:
        verbose_name = 'Что тебя ждет'
        verbose_name_plural = 'Что тебя ждет'




class FAQSetup(SingletonModel):
    title = models.CharField(max_length=250, verbose_name='Заголовок', null=True, blank=True)
    bg = models.ImageField(upload_to='faq', verbose_name='Фоновое изображение', null=True, blank=True)

    def __str__(self):  
        return self.title
    
    class Meta:
        verbose_name = 'Настройки вопрос-ответ'
        verbose_name_plural = 'Настройки вопрос-ответ'


class FAQ(models.Model):
    question = models.CharField(max_length=250, verbose_name='Вопрос')
    answer = models.TextField(verbose_name='Ответ')

    def __str__(self):  
        return self.question
    
    class Meta:
        verbose_name = 'Вопрос-ответ'
        verbose_name_plural = 'Вопрос-ответ'



class BtnBlockSetup(SingletonModel):
    bg = models.ImageField(upload_to='btn', verbose_name='Фоновое изображение', null=True, blank=True)

    class Meta:
        verbose_name = 'Настройки блока с кнопками'
        verbose_name_plural = 'Настройки блока с кнопками'



class BtnBlockItem(models.Model):
    title = models.CharField(max_length=250, verbose_name='Заголовок')
    link = models.CharField(max_length=250, verbose_name='Ссылка')
    link_text = models.CharField(max_length=250, verbose_name='Текст ссылки')
    bg = models.ImageField(upload_to='btn', verbose_name='Фоновое изображение')

    def __str__(self):  
        return self.title
    
    class Meta:
        verbose_name = 'Кнопка в блоке с кнопками'
        verbose_name_plural = 'Кнопка в блоке с кнопками'





class HomeGamesSetup(SingletonModel):
    title = models.CharField(max_length=250, verbose_name='Заголовок', null=True, blank=True)
    bg = models.ImageField(upload_to='games', verbose_name='Фоновое изображение', null=True, blank=True)
    image = models.ImageField(upload_to='games', verbose_name='Изображение', null=True, blank=True)
    text = models.TextField(verbose_name='Текст', null=True, blank=True)
    link = models.CharField(max_length=250, verbose_name='Ссылка', null=True, blank=True)
    link_text = models.CharField(max_length=250, verbose_name='Текст ссылки', null=True, blank=True)

    def __str__(self):  
        return self.title

    class Meta:
        verbose_name = 'Настройки блока с домашними играми'






class Page(models.Model):
    
    
    PAGE_CLASS = (
       ('privacy', 'Политика конфиденциальности'),
       ('soglashenie', 'Пользовательское соглашение'),
       ('pravila', 'Правила'),
       
      
    )
    type = models.CharField(max_length=200, choices=PAGE_CLASS, verbose_name='Тип страницы', unique=True)
    name = models.CharField(max_length=350, null=True, blank=True, verbose_name='Название страницы')
    meta_h1 = models.CharField(max_length=350, null=True, blank=True, verbose_name='h1')
    text = models.TextField(verbose_name='Текст страницы')
    meta_title = models.CharField(max_length=350, null=True, blank=True, verbose_name='Мета тайтл')
    meta_description = models.TextField(null=True, blank=True, verbose_name='Мета описание')
    meta_keywords = models.TextField(null=True, blank=True, verbose_name='Ключевые слова через запятую')
    image = models.ImageField(upload_to='catalog', null=True, blank=True, verbose_name='Изображение')
    page_order = models.PositiveIntegerField(default=0, verbose_name='Сортировка')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("page_detail", kwargs={"slug": self.type})
    

    class Meta:
        verbose_name = 'Страница'
        verbose_name_plural = 'Страницы'




