from decimal import Decimal
from itertools import product
from multiprocessing import context
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from admin.forms import BtnBlockItemForm, BtnBlockSetupForm, CityForm, CustomCodeForm, ColorsForm, DoverCorpSetupForm, DoverCorpSliderForm, FAQForm, FAQSetupForm, GameCategoryForm, GameOrderForm, GamesCategorySetupForm, GamesForm, GamesPhotoForm, GamesSetupForm, HomeGamesSetupForm, SetupForm, StartCorpSetupForm, ThemeSettingsForm, SliderSetupForm, SliderForm, PageForm, WaitItemForm, WaitSetupForm, WhatCorpItemForm, WhatCorpItemSetupForm, WhatCorpSetupForm, WhatItemForm, WhatSetupForm, WhyWeCorpItemForm, WhyWeCorpSetupForm

from home.models import DoverCorpSetup, DoverCorpSlider, GameOrder, FAQ, BtnBlockItem, BtnBlockSetup, City, FAQSetup, GameCategory, Games, GamesCategorySetup, GamesPhoto, GamesSetup, HomeGamesSetup, Page, Slider, SliderSetup, StartCorpSetup, WaitItem, WaitSetup, WhatCorpItem, WhatCorpItemSetup, WhatCorpSetup, WhatItem, WhatSetup, WhyWeCorpItem, WhyWeCorpSetup




from setup.models import BaseSettings, Colors, CustomCode, EmailSettings, RecaptchaSettings, ThemeSettings


import subprocess
from main.settings import RESET_FILE

from django.contrib.auth import get_user_model
User = get_user_model()

from django.db.models import Q

from django.contrib.auth.decorators import user_passes_test

from django.db.models import Sum





@user_passes_test(lambda u: u.is_superuser)
def orders(request):

    oders = GameOrder.objects.all()
    games = Games.objects.all().order_by('city')

    context = {
        'oders': oders,
        'games': games
    }


    return render(request, 'orders/orders.html', context)




@user_passes_test(lambda u: u.is_superuser)
def order_add(request):

    if request.method == 'POST':
        form = GameOrderForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('orders')

        else:
            return render(request, 'orders/order_add.html', {'form': form})

    form = GameOrderForm()
    context = {
        'form': form
    }

    return render(request, 'orders/order_add.html', context)

@user_passes_test(lambda u: u.is_superuser)
def order_edit(request, pk):

    order = GameOrder.objects.get(id=pk)

    if request.method == 'POST':
        form = GameOrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return redirect('orders')

        else:
            return render(request, 'orders/order_edit.html', {'form': form})

    form = GameOrderForm(instance=order)
    context = {
        'form': form
    }

    return render(request, 'orders/order_edit.html', context)


@user_passes_test(lambda u: u.is_superuser)
def order_delete(request, pk):
    order = GameOrder.objects.get(id=pk)
    order.delete()
    return redirect('orders')


@user_passes_test(lambda u: u.is_superuser)
def subdomains(request):
    context = {
        'citys': City.objects.all()
    }

    return render(request, 'subdomains/subdomains.html', context)



@user_passes_test(lambda u: u.is_superuser)
def subdomains_add(request):

    form = CityForm()


    if request.method == 'POST':
        form = CityForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('subdomains')
        
        else:
            return render(request, 'subdomains/subdomains_add.html', {'form': form})
        
    context = {
        'form': form
    }

    return render(request, 'subdomains/subdomains_add.html', context)



@user_passes_test(lambda u: u.is_superuser)
def subdomains_edit(request, pk):

    form = CityForm(instance=City.objects.get(id=pk))

    if request.method == 'POST':
        form = CityForm(request.POST, instance=City.objects.get(id=pk))
        if form.is_valid():
            form.save()
            return redirect('subdomains')
        else:
            return render(request, 'subdomains/subdomains_edit.html', {'form': form})
        
    context = {
        'form': form
    }


    return render(request, 'subdomains/subdomains_edit.html', context)


@user_passes_test(lambda u: u.is_superuser)
def subdomains_delete(request, pk):

    City.objects.get(id=pk).delete()
    

    return redirect('subdomains')




# Сессия с хранением состояния сайдбара в админке
@user_passes_test(lambda u: u.is_superuser)
def sidebar_show(request): 
   
    request.session['sidebar'] = 'True' 
    
    return redirect('admin')

@user_passes_test(lambda u: u.is_superuser)
def sidebar_hide(request): 
    
    request.session['sidebar'] = 'False' 
    return redirect('admin')


@user_passes_test(lambda u: u.is_superuser)
def admin(request):
    try:
        setup = BaseSettings.objects.get()
     
        
        email = EmailSettings.objects.get()
        theme = ThemeSettings.objects.get()
        colors = Colors.objects.get()
    except:
        setup = BaseSettings()
    
        
        email = EmailSettings()
        theme = ThemeSettings()
        colors = Colors()
        colors.save()
        theme.save()
        email.save()
        setup.save()
       
       


    
    
    
    
    context = {
        
        
    }

    return render(request, 'pages/index.html', context)



@user_passes_test(lambda u: u.is_superuser)
def general_settings(request):

    # Пытаемся выбрать модели настроек, если не получается - создаем новые. (для первого захода на сайт)
    try:
        setup = BaseSettings.objects.get()
        email = EmailSettings.objects.get()
        recaptcha = RecaptchaSettings.objects.get()
    except:
        setup = BaseSettings()
        email = EmailSettings()
        recaptcha = RecaptchaSettings()
        email.save()
        setup.save()
        recaptcha.save()

    # Сохранение основных настроек
    if request.method == 'POST':
        new_form = SetupForm(request.POST, request.FILES, instance=setup)
        if new_form.is_valid():
            new_form.save()

            subprocess.call(["touch", RESET_FILE])

            return redirect ('general_settings')

    # Заполнение форм значениями, для отображения уже сохраненных настроек
    setup = BaseSettings.objects.get()
    email = EmailSettings.objects.get()
    recaptcha = RecaptchaSettings.objects.get()
    
    form = SetupForm(instance=setup)
    
    
    context = {
        'form': form,
        'setup': setup,
        
        
    }
    return render(request, 'settings/general_settings.html', context)





# Настройки кастомных кодов POST/GET
@user_passes_test(lambda u: u.is_superuser)
def codes_settings(request):
    if request.method == 'POST':
        form = CustomCodeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('codes_settings')
        else:
            return render(request, 'settings/codes_settings.html', { 'form': form })
    codes = CustomCode.objects.all()
    form = CustomCodeForm()
    context = {
        'codes': codes,
        'form': form
    }
    return render(request, 'settings/codes_settings.html', context)


@user_passes_test(lambda u: u.is_superuser)
def codes_settings_edit(request, pk):
    codes = CustomCode.objects.get(pk=pk)
    if request.method == 'POST':
        form = CustomCodeForm(request.POST, instance=codes)
        if form.is_valid():
            form.save()
            return redirect('codes_settings')
        else:
            return render(request, 'settings/codes_edit.html', { 'form': form })
    
    form = CustomCodeForm(instance=codes)
    context = {
        'form': form
    }


    return render(request, 'settings/codes_edit.html', context)

@user_passes_test(lambda u: u.is_superuser)
def codes_settings_delete(request, pk):
    codes = CustomCode.objects.get(pk=pk)
    codes.delete()
    return redirect('codes_settings')


# Настройки цвета
@user_passes_test(lambda u: u.is_superuser)
def color_settings(request):

    if request.method == 'POST':
        form = ColorsForm(request.POST)
        if form.is_valid():
            form.save()

        return redirect('color_settings')
    try:
        color = Colors.objects.get()
        form = ColorsForm(instance=color)
    except:
        form = ColorsForm()
    context = {
        'form': form
    }

    return render(request, 'settings/color_settings.html', context)


# Настройка темы
@user_passes_test(lambda u: u.is_superuser)
def theme_settings(request):
    if request.method == 'POST':

        form = ThemeSettingsForm(request.POST)
        if form.is_valid():
            form.save()

        return redirect('theme_settings')

    try:
        theme = ThemeSettings.objects.get()
        form = ThemeSettingsForm(instance=theme)
    except:
        form = ThemeSettingsForm()
    
    context = {
        'form': form
    }

    return render(request, 'settings/theme_settings.html', context)




# !!! СТАТИКА !!!


@user_passes_test(lambda u: u.is_superuser)
def admin_slider(request):
    sliders = Slider.objects.all()
    try:
        slider_setup = SliderSetup.objects.get()
    except:
        slider_setup = SliderSetup()
        slider_setup.save()

    if request.method == 'POST':
        form = SliderSetupForm(request.POST, request.FILES, instance=slider_setup)
        if form.is_valid():
            form.save()
            return redirect('admin_slider')
        else:
            return render(request, 'static/slider.html', {'form': form})

    setup_form = SliderSetupForm(instance=slider_setup)
    context = {
        'setup_form': setup_form,
        'sliders': sliders
    }
    return render(request, 'static/slider.html', context)

@user_passes_test(lambda u: u.is_superuser)
def slider_add(request):

    if request.method == 'POST':
        form = SliderForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_slider')

        else:
            return render(request, 'static/slider_add.html', {'form': form})
        

    form = SliderForm()
    context = {
        'form': form,
    }

    return render(request, 'static/slider_add.html', context)



@user_passes_test(lambda u: u.is_superuser)
def slider_edit(request, pk):
    slider = Slider.objects.get(id=pk)
    if request.method == 'POST':
        form = SliderForm(request.POST, request.FILES, instance=slider)
        if form.is_valid():
            form.save()
            return redirect('admin_slider')

        else:
            return render(request, 'static/slider_edit.html', {'form': form})
    form = SliderForm(instance=slider)
    context = {
        'form': form,
    }

    return render(request, 'static/slider_edit.html', context)


@user_passes_test(lambda u: u.is_superuser)
def slider_delete(request, pk):
    slider = Slider.objects.get(id=pk)
    slider.delete()
    return redirect('admin_slider')


@user_passes_test(lambda u: u.is_superuser)
def admin_pages(request):

    context = {
        'pages': Page.objects.all()
    }

    return render(request, 'static/admin_pages.html', context)


@user_passes_test(lambda u: u.is_superuser)
def page_add(request):

    if request.method == 'POST':
        form = PageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_pages')

        else:
            return render(request, 'static/page_add.html', {'form': form})

    form = PageForm()
    context = {
        'form': form,
    }

    return render(request, 'static/page_add.html', context)

@user_passes_test(lambda u: u.is_superuser)
def page_edit(request, pk):
    page = Page.objects.get(id=pk)
    if request.method == 'POST':
        form = PageForm(request.POST, request.FILES, instance=page)
        if form.is_valid():
            form.save()
            return redirect('admin_pages')
        else:
            return render(request, 'static/page_edit.html', {'form': form})
            
    form = PageForm(instance=page)
    context = {
        'form': form,
    }
    return render(request, 'static/page_edit.html', context)






# !!! СТАТИКА !!!


# !!! Пользователи USERS !!!


@user_passes_test(lambda u: u.is_superuser)
def admin_users(request):

    users = User.objects.all()

    context = {
        'users': users
    }

    return render(request, 'users/admin_users.html', context)

@user_passes_test(lambda u: u.is_superuser)
def users_delete(request, pk):

    user = User.objects.get(id=pk)
    user.delete()

    return redirect('admin_users')


# !!! Пользователи USERS !!!






@user_passes_test(lambda u: u.is_superuser)
def games(request):
    # Получаем или создаем настройки игр
    gemes_setup, _ = GamesSetup.objects.get_or_create()
    category_setup, _ = GamesCategorySetup.objects.get_or_create()

    # Создаем формы
    setup_form = GamesSetupForm(instance=gemes_setup)
    category_setup_form = GamesCategorySetupForm(instance=category_setup)

    if request.method == 'POST':
        if 'setup_form_submit' in request.POST:  # Проверяем, какая форма была отправлена
            setup_form = GamesSetupForm(request.POST, request.FILES, instance=gemes_setup)
            if setup_form.is_valid():
                setup_form.save()
                return redirect('games')

        elif 'category_setup_form_submit' in request.POST:  # Проверяем вторую форму
            category_setup_form = GamesCategorySetupForm(request.POST, request.FILES, instance=category_setup)
            if category_setup_form.is_valid():
                category_setup_form.save()
                return redirect('games')
            


    categorys = GameCategory.objects.all()
    games = Games.objects.all().order_by('date_date')

    # Контекст для рендера страницы
    context = {
        'setup_form': setup_form,
        'category_setup_form': category_setup_form,
        'categorys': categorys,
        'photos': GamesPhoto.objects.all(),
        'games': games
    }

    return render(request, 'games/games.html', context)




@user_passes_test(lambda u: u.is_superuser)
def geme_cat_add(request):

    if request.method == 'POST':
        form = GameCategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('games')

        else:
            return render(request, 'games/geme_cat_add.html', {'form': form})

    form = GameCategoryForm()
    context = {
        'form': form,
    }

    return render(request, 'games/geme_cat_add.html', context)


@user_passes_test(lambda u: u.is_superuser)
def geme_cat_edit(request, pk):
    game_cat = GameCategory.objects.get(id=pk)
    if request.method == 'POST':
        form = GameCategoryForm(request.POST, request.FILES, instance=game_cat)
        if form.is_valid():
            form.save()
            return redirect('games')
        else:
            return render(request, 'games/geme_cat_edit.html', {'form': form})
            
    form = GameCategoryForm(instance=game_cat)
    context = {
        'form': form,
    }
    return render(request, 'games/geme_cat_edit.html', context)



@user_passes_test(lambda u: u.is_superuser)
def game_cat_delete(request, pk):   

    game_cat = GameCategory.objects.get(id=pk)
    game_cat.delete()
    return redirect('games')


@user_passes_test(lambda u: u.is_superuser)
def game_add(request):

    if request.method == 'POST':
        form = GamesForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('games')

        else:
            return render(request, 'games/game_add.html', {'form': form})

    form = GamesForm()
    context = {
        'form': form,
    }

    return render(request, 'games/game_add.html', context)


@user_passes_test(lambda u: u.is_superuser)
def game_edit(request, pk):
    game = Games.objects.get(id=pk)
    if request.method == 'POST':
        form = GamesForm(request.POST, request.FILES, instance=game)
        if form.is_valid():
            form.save()
            return redirect('games')
        else:
            return render(request, 'games/game_edit.html', {'form': form})
            
    form = GamesForm(instance=game)
    context = {
        'form': form,
    }
    return render(request, 'games/game_edit.html', context)

@user_passes_test(lambda u: u.is_superuser)
def game_delete(request, pk):

    game = Games.objects.get(id=pk)
    game.delete()

    return redirect('games')



@user_passes_test(lambda u: u.is_superuser)
def photo_add(request):

    if request.method == 'POST':
        form = GamesPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('games')

        else:
            return render(request, 'games/photo_add.html', {'form': form})

    form = GamesPhotoForm()
    context = {
        'form': form,
    }

    return render(request, 'games/photo_add.html', context)


@user_passes_test(lambda u: u.is_superuser)
def photo_edit(request, pk):
    photo = GamesPhoto.objects.get(id=pk)
    if request.method == 'POST':
        form = GamesPhotoForm(request.POST, request.FILES, instance=photo)
        if form.is_valid():
            form.save()
            return redirect('games')
        else:
            return render(request, 'games/photo_edit.html', {'form': form})
            
    form = GamesPhotoForm(instance=photo)
    context = {
        'form': form,
    }
    return render(request, 'games/photo_edit.html', context)

@user_passes_test(lambda u: u.is_superuser)
def photo_delete(request, pk):

    photo = GamesPhoto.objects.get(id=pk)
    photo.delete()

    return redirect('games')


@user_passes_test(lambda u: u.is_superuser)
def what(request):

    what_setup = WhatSetup.objects.all().first()
    form = WhatSetupForm(instance=what_setup)

    if request.method == 'POST':    
        form = WhatSetupForm(request.POST, request.FILES, instance=what_setup)
        if form.is_valid():
            form.save()
            return redirect('what')
        else:
            return render(request, 'what/what.html', {'form': form})


    what = WhatItem.objects.all()

    context = {
        'what_setup': what_setup,
        'what': what,
        'form': form
    }

    return render(request, 'what/what.html', context)



@user_passes_test(lambda u: u.is_superuser)
def what_add(request):

    if request.method == 'POST':
        form = WhatItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('what')

        else:
            return render(request, 'what/what_add.html', {'form': form})

    form = WhatItemForm()
    context = {
        'form': form,
    }

    return render(request, 'what/what_add.html', context)
            

@user_passes_test(lambda u: u.is_superuser)
def what_edit(request, pk):
    what = WhatItem.objects.get(id=pk)
    if request.method == 'POST':
        form = WhatItemForm(request.POST, request.FILES, instance=what)
        if form.is_valid():
            form.save()
            return redirect('what')
        else:
            return render(request, 'what/what_edit.html', {'form': form})
            
    form = WhatItemForm(instance=what)
    context = {
        'form': form,
    }
    return render(request, 'what/what_edit.html', context)


@user_passes_test(lambda u: u.is_superuser)
def what_delete(request, pk):

    what = WhatItem.objects.get(id=pk)
    what.delete()

    return redirect('what')



@user_passes_test(lambda u: u.is_superuser)
def wait(request):

    wait_setup = WaitSetup.objects.all().first()

    form = WaitSetupForm(instance=wait_setup)
    wait = WaitItem.objects.all()

    if request.method == 'POST':    
        form = WaitSetupForm(request.POST, request.FILES, instance=wait_setup)
        if form.is_valid():
            form.save()
            return redirect('wait')
        else:
            return render(request, 'wait/wait.html', {'form': form})

    context = {
        'wait_setup': wait_setup,
        'form': form,
        'wait': wait
    }

    return render(request, 'wait/wait.html', context)


@user_passes_test(lambda u: u.is_superuser)
def wait_add(request):

    if request.method == 'POST':
        form = WaitItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('wait')

        else:
            return render(request, 'wait/wait_add.html', {'form': form})

    form = WaitItemForm()
    context = {
        'form': form,
    }

    return render(request, 'wait/wait_add.html', context)


@user_passes_test(lambda u: u.is_superuser)
def wait_edit(request, pk):
    wait = WaitItem.objects.get(id=pk)
    if request.method == 'POST':
        form = WaitItemForm(request.POST, request.FILES, instance=wait)
        if form.is_valid():
            form.save()
            return redirect('wait')
        else:
            return render(request, 'wait/wait_edit.html', {'form': form})
            
    form = WaitItemForm(instance=wait)
    context = {
        'form': form,
    }
    return render(request, 'wait/wait_edit.html', context)


@user_passes_test(lambda u: u.is_superuser)
def wait_delete(request, pk):

    wait = WaitItem.objects.get(id=pk)
    wait.delete()

    return redirect('wait')





@user_passes_test(lambda u: u.is_superuser)
def faq(request):

    faq_setup = FAQSetup.objects.all().first()

    form = FAQSetupForm(instance=faq_setup)

    if request.method == 'POST':    
        form = FAQSetupForm(request.POST, request.FILES, instance=faq_setup)
        if form.is_valid():
            form.save()
            return redirect('faq')
        else:
            return render(request, 'faq/faq.html', {'form': form})


    faq = FAQ.objects.all()

    context = {
        'faq': faq,
        'form': form,
    }

    return render(request, 'faq/faq.html', context)


@user_passes_test(lambda u: u.is_superuser)
def faq_add(request):

    if request.method == 'POST':
        form = FAQForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('faq')

        else:
            return render(request, 'faq/faq_add.html', {'form': form})

    form = FAQForm()
    context = {
        'form': form,
    }

    return render(request, 'faq/faq_add.html', context)


@user_passes_test(lambda u: u.is_superuser)
def faq_edit(request, pk):
    faq = FAQ.objects.get(id=pk)
    if request.method == 'POST':
        form = FAQForm(request.POST, instance=faq)
        if form.is_valid():
            form.save()
            return redirect('faq')
        else:
            return render(request, 'faq/faq_edit.html', {'form': form})
            
    form = FAQForm(instance=faq)
    context = {
        'form': form,
    }
    return render(request, 'faq/faq_edit.html', context)


@user_passes_test(lambda u: u.is_superuser)
def faq_delete(request, pk):

    faq = FAQ.objects.get(id=pk)
    faq.delete()

    return redirect('faq')




@user_passes_test(lambda u: u.is_superuser)
def btn_block(request):

    try:
        btn_block = BtnBlockSetup.objects.all().first()
    except:
        btn_block = BtnBlockSetup()
        btn_block.save()

    form = BtnBlockSetupForm(instance=btn_block)

    if request.method == 'POST':    
        form = BtnBlockSetupForm(request.POST, request.FILES, instance=btn_block)
        if form.is_valid():
            form.save()
            return redirect('btn_block')
        else:
            return render(request, 'btn_block/btn_block.html', {'form': form})

    context = {
        'form': form,
        'btn_block': BtnBlockItem.objects.all(),
    }

    return render(request, 'btn_block/btn_block.html', context)


@user_passes_test(lambda u: u.is_superuser)
def btn_block_add(request):

    if request.method == 'POST':
        form = BtnBlockItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('btn_block')

        else:
            return render(request, 'btn_block/btn_block_add.html', {'form': form})

    form = BtnBlockItemForm()
    context = {
        'form': form,
    }

    return render(request, 'btn_block/btn_block_add.html', context)


@user_passes_test(lambda u: u.is_superuser)
def btn_block_edit(request, pk):
    btn_block = BtnBlockItem.objects.get(id=pk)
    if request.method == 'POST':
        form = BtnBlockItemForm(request.POST, request.FILES, instance=btn_block)
        if form.is_valid():
            form.save()
            return redirect('btn_block')
        else:
            return render(request, 'btn_block/btn_block_edit.html', {'form': form})
            
    form = BtnBlockItemForm(instance=btn_block)
    context = {
        'form': form,
    }
    return render(request, 'btn_block/btn_block_edit.html', context)


@user_passes_test(lambda u: u.is_superuser)
def btn_block_delete(request, pk):

    btn_block = BtnBlockItem.objects.get(id=pk)
    btn_block.delete()

    return redirect('btn_block')


@user_passes_test(lambda u: u.is_superuser)
def home_games(request):

    try:
        home_games_setup = HomeGamesSetup.objects.all().first()
    except:
        home_games_setup = HomeGamesSetup()
        home_games_setup.save()
    

    form = HomeGamesSetupForm(instance=home_games_setup)

    if request.method == 'POST':    
        form = HomeGamesSetupForm(request.POST, request.FILES, instance=home_games_setup)
        if form.is_valid():
            form.save()
            return redirect('home_games')
        else:
            return render(request, 'home_games/home_games.html', {'form': form})

   

    context = {
       
        'form': form,
    }

    return render(request, 'home_games/home_games.html', context)







@user_passes_test(lambda u: u.is_superuser)
def admin_corp(request):

    try:
        start_corp_setup = StartCorpSetup.objects.all().first()
    except:
        start_corp_setup = StartCorpSetup()
        start_corp_setup.save()

    form = StartCorpSetupForm(instance=start_corp_setup)

    if request.method == 'POST':    
        form = StartCorpSetupForm(request.POST, request.FILES, instance=start_corp_setup)
        if form.is_valid():
            form.save()
            return redirect('admin_corp')
        else:
            return render(request, 'corp/admin_corp.html', {'form': form})
    

    context = {
        'form': form

    }


    return render(request, 'corp/admin_corp.html', context)


@user_passes_test(lambda u: u.is_superuser)
def admin_what_corp(request):

    try:
        what_corp_setup = WhatCorpSetup.objects.all().first()
    except:
        what_corp_setup = WhatCorpSetup()
        what_corp_setup.save()


    form = WhatCorpSetupForm(instance=what_corp_setup)

    if request.method == 'POST':    
        form = WhatCorpSetupForm(request.POST, request.FILES, instance=what_corp_setup)
        if form.is_valid():
            form.save()
            return redirect('admin_what_corp')
        else:
            return render(request, 'corp/admin_what_corp.html', {'form': form})
        

    context = {
        'form': form
    }

    return render(request, 'corp/admin_what_corp.html', context)


@user_passes_test(lambda u: u.is_superuser)
def admin_what_corp_items(request):

    try:
        what_corp_items_setup = WhatCorpItemSetup.objects.all().first()
    except:
        what_corp_items_setup = WhatCorpItemSetup()
        what_corp_items_setup.save()

    form = WhatCorpItemSetupForm(instance=what_corp_items_setup)

    if request.method == 'POST':    
        form = WhatCorpItemSetupForm(request.POST, request.FILES, instance=what_corp_items_setup)
        if form.is_valid():
            form.save()
            return redirect('admin_what_corp_items')
        else:
            return render(request, 'corp/admin_what_corp_items.html', {'form': form})
        


    context = {
        'form': form,
        'items': WhatCorpItem.objects.all()
    }

    return render(request, 'corp/admin_what_corp_items.html', context)


@user_passes_test(lambda u: u.is_superuser)
def admin_what_corp_items_add(request):

    if request.method == 'POST':
        form = WhatCorpItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_what_corp_items_add')
        else:
            return render(request, 'corp/admin_what_corp_items_add.html', {'form': form})

    form = WhatCorpItemForm()
    context = {
        'form': form,
    }

    return render(request, 'corp/admin_what_corp_items_add.html', context)


@user_passes_test(lambda u: u.is_superuser)
def admin_what_corp_items_edit(request, pk):
    what_corp_item = WhatCorpItem.objects.get(id=pk)
    if request.method == 'POST':
        form = WhatCorpItemForm(request.POST, request.FILES, instance=what_corp_item)
        if form.is_valid():
            form.save()
            return redirect('admin_what_corp_items')
        else:
            return render(request, 'corp/admin_what_corp_items_add.html', {'form': form})
            
    form = WhatCorpItemForm(instance=what_corp_item)
    context = {
        'form': form

    }

    return render(request, 'corp/admin_what_corp_items_add.html', context)



@user_passes_test(lambda u: u.is_superuser)
def admin_what_corp_items_delete(request, pk):
    what_corp_item = WhatCorpItem.objects.get(id=pk)
    what_corp_item.delete()
    return redirect('admin_what_corp_items')



@user_passes_test(lambda u: u.is_superuser)
def admin_why_we_corp(request):

    try:
        why_we_corp_setup = WhyWeCorpSetup.objects.all().first()
    except:
        why_we_corp_setup = WhyWeCorpSetup()
        why_we_corp_setup.save()

    form = WhyWeCorpSetupForm(instance=why_we_corp_setup)

    if request.method == 'POST':    
        form = WhyWeCorpSetupForm(request.POST, request.FILES, instance=why_we_corp_setup)
        if form.is_valid():
            form.save()
            return redirect('admin_why_we_corp')
        else:
            return render(request, 'corp/admin_why_we_corp.html', {'form': form})
        


    context = {
        'form': form,
        'items': WhyWeCorpItem.objects.all()
    }

    return render(request, 'corp/admin_why_we_corp.html', context)


@user_passes_test(lambda u: u.is_superuser)
def admin_why_we_corp_add(request):

    if request.method == 'POST':
        form = WhyWeCorpItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_why_we_corp')
        else:
            return render(request, 'corp/admin_why_we_corp_add.html', {'form': form})

    form = WhyWeCorpItemForm()
    context = {
        'form': form,
    }

    return render(request, 'corp/admin_why_we_corp_add.html', context)



@user_passes_test(lambda u: u.is_superuser)
def admin_why_we_corp_edit(request, pk):
    why_we_corp_item = WhyWeCorpItem.objects.get(id=pk)
    if request.method == 'POST':
        form = WhyWeCorpItemForm(request.POST, request.FILES, instance=why_we_corp_item)
        if form.is_valid():
            form.save()
            return redirect('admin_why_we_corp')
        else:
            return render(request, 'corp/admin_why_we_corp_add.html', {'form': form})
            
    form = WhyWeCorpItemForm(instance=why_we_corp_item)
    context = {
        'form': form

    }

    return render(request, 'corp/admin_why_we_corp_add.html', context)



@user_passes_test(lambda u: u.is_superuser)
def admin_why_we_corp_delete(request, pk):
    why_we_corp_item = WhyWeCorpItem.objects.get(id=pk)
    why_we_corp_item.delete()
    return redirect('admin_why_we_corp')



@user_passes_test(lambda u: u.is_superuser)
def admin_dover_corp(request):

    try:
        dover_corp_setup = DoverCorpSetup.objects.all().first()
    except:
        dover_corp_setup = DoverCorpSetup()
        dover_corp_setup.save()

    form = DoverCorpSetupForm(instance=dover_corp_setup)

    if request.method == 'POST':    
        form = DoverCorpSetupForm(request.POST, request.FILES, instance=dover_corp_setup)
        if form.is_valid():
            form.save()
            return redirect('admin_dover_corp')
        else:
            return render(request, 'corp/admin_dover_corp.html', {'form': form})


    context = {
        'form': form,
        'items': DoverCorpSlider.objects.all()
    }

    return render(request, 'corp/admin_dover_corp.html', context)


@user_passes_test(lambda u: u.is_superuser)
def admin_dover_corp_add(request):

    if request.method == 'POST':
        form = DoverCorpSliderForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_dover_corp')
        else:
            return render(request, 'corp/admin_dover_corp_add.html', {'form': form})

    form = DoverCorpSliderForm()
    context = {
        'form': form,
    }

    return render(request, 'corp/admin_dover_corp_add.html', context)


@user_passes_test(lambda u: u.is_superuser)
def admin_dover_corp_edit(request, pk): 
    dover_corp_slider = DoverCorpSlider.objects.get(id=pk)
    if request.method == 'POST':
        form = DoverCorpSliderForm(request.POST, request.FILES, instance=dover_corp_slider)
        if form.is_valid():
            form.save()
            return redirect('admin_dover_corp')
        else:
            return render(request, 'corp/admin_dover_corp_add.html', {'form': form})
            
    form = DoverCorpSliderForm(instance=dover_corp_slider)
    context = {
        'form': form

    }

    return render(request, 'corp/admin_dover_corp_add.html', context)   


@user_passes_test(lambda u: u.is_superuser)
def admin_dover_corp_delete(request, pk):
    dover_corp_slider = DoverCorpSlider.objects.get(id=pk)
    dover_corp_slider.delete()
    return redirect('admin_dover_corp')



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from django.forms import modelform_factory
from django.contrib import messages
from django.http import HttpResponseNotAllowed
from django.apps import apps
from django import forms
from django.db import models
from ckeditor.widgets import CKEditorWidget  # ✅ Импортируем CKEditor

def custom_formfield_callback(field):
    """ Используем CKEditor только для полей `text` """
    if field.name == "text":  # ✅ Только для полей с именем `text`
        return field.formfield(widget=CKEditorWidget())
    return field.formfield()

@user_passes_test(lambda u: u.is_superuser)
def admin_franch(request, model_name, items1_model_name=None, items2_model_name=None):
    """ Универсальное представление для работы с франшизными моделями + 2 необязательных списка объектов """

    # Получаем основную модель
    model = apps.get_model('home', model_name)
    if not model:
        return render(request, 'franch/admin_error.html', {"error": "Основная модель не найдена"})

    # ✅ Проверяем, что items1_model_name и items2_model_name не равны 'None' (строка) или None (объект)
    items1_model = None
    items1 = None
    if items1_model_name and items1_model_name.lower() != "none":
        try:
            items1_model = apps.get_model('home', items1_model_name)
            items1 = items1_model.objects.all()
        except LookupError:
            items1 = None

    items2_model = None
    items2 = None
    if items2_model_name and items2_model_name.lower() != "none":
        try:
            items2_model = apps.get_model('home', items2_model_name)
            items2 = items2_model.objects.all()
        except LookupError:
            items2 = None

    # Загружаем Singleton, если модель поддерживает `get_solo`
    instance = model.get_solo() if hasattr(model, 'get_solo') else None

    # Запоминаем текущие файлы перед обработкой формы
    old_files = {field.name: getattr(instance, field.name) for field in model._meta.fields if isinstance(field, models.FileField)} if instance else {}

    # ✅ Применяем CKEditor только для `text`
    FormClass = modelform_factory(model, exclude=[], formfield_callback=custom_formfield_callback)

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=instance)

        if form.is_valid():
            updated_instance = form.save(commit=False)

            # ✅ Если установлен чекбокс очистки файла, удаляем файл
            for field_name, old_file in old_files.items():
                if request.POST.get(f"{field_name}-clear"):  # Django использует `-clear` для чекбокса очистки
                    setattr(updated_instance, field_name, None)  # Удаляем файл

                elif not request.FILES.get(field_name):  # Если новый файл не загружен, оставляем старый
                    setattr(updated_instance, field_name, old_file)

            updated_instance.save()
            messages.success(request, f'Настройки {model._meta.verbose_name} обновлены!')

            # ✅ Исправленный редирект
            if items1_model_name and items2_model_name and items1_model_name.lower() != "none" and items2_model_name.lower() != "none":
                return redirect(reverse('admin_franch_with_two_items', args=[model_name, items1_model_name, items2_model_name]))
            elif items1_model_name and items1_model_name.lower() != "none":
                return redirect(reverse('admin_franch_with_items', args=[model_name, items1_model_name]))
            else:
                return redirect(reverse('admin_franch', args=[model_name]))
    else:
        form = FormClass(instance=instance)

    return render(request, 'franch/admin_franch.html', {
        'form': form,
        'items1': items1,
        'items2': items2,
        'items1_model_name': items1_model_name if items1_model_name and items1_model_name.lower() != "none" else None,
        'items2_model_name': items2_model_name if items2_model_name and items2_model_name.lower() != "none" else None,
        'model_name': model_name,
        'verbose_name': model._meta.verbose_name,
        'verbose_name_plural': model._meta.verbose_name_plural
    })


@user_passes_test(lambda u: u.is_superuser)
def admin_franch_delete(request, model_name, item_id):
    """ Удаление записи """
    model = apps.get_model('home', model_name)
    instance = get_object_or_404(model, id=item_id)
    instance.delete()
    messages.success(request, f'Запись {instance} удалена!')

    # ✅ Получаем URL, с которого пришли
    previous_url = request.META.get('HTTP_REFERER')

    if previous_url:
        # ✅ Извлекаем первую модель из пути URL
        path_parts = previous_url.strip('/').split('/')
        if len(path_parts) > 1 and path_parts[0] == "franch":
            primary_model_name = path_parts[1]  # Первая модель в пути
            return redirect(reverse('admin_franch', args=[primary_model_name]))

    # Если `HTTP_REFERER` нет или путь неверный → редиректим на `admin_franch`
    return redirect(reverse('admin_franch', args=[model_name]))



@user_passes_test(lambda u: u.is_superuser)
def admin_franch_edit(request, model_name, item_id):
    """ Редактирование записи """
    model = apps.get_model('home', model_name)
    instance = get_object_or_404(model, id=item_id)

    FormClass = modelform_factory(model, exclude=[])

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f'Запись {instance} обновлена!')

            # ✅ Получаем URL, с которого пришли
            previous_url = request.META.get('HTTP_REFERER')

            if previous_url:
                # ✅ Извлекаем первую модель из пути URL
                path_parts = previous_url.strip('/').split('/')
                if len(path_parts) > 1 and path_parts[0] == "franch":
                    primary_model_name = path_parts[1]  # Первая модель в пути
                    return redirect(reverse('admin_franch', args=[primary_model_name]))

            # Если `HTTP_REFERER` нет или путь неверный → редиректим на `admin_franch`
            return redirect(reverse('admin_franch', args=[model_name]))
    else:
        form = FormClass(instance=instance)

    return render(request, 'franch/admin_franch.html', {
        'form': form,
        'model_name': model_name,
        'verbose_name': model._meta.verbose_name
    })
