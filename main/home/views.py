from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpResponse


from .models import GameOrder, SliderSetup, Slider, Page, City, GamesSetup, GamesCategorySetup, GamesPhoto, GameCategory, Games, WhatSetup, WhatItem, WaitSetup, WaitItem, FAQSetup, FAQ, BtnBlockSetup, BtnBlockItem, HomeGamesSetup
from setup.models import ThemeSettings, BaseSettings, EmailSettings

from .forms import GameOrderForm

try:
    theme_address = ThemeSettings.objects.get().name
except:
    theme_address = 'default'

from django.views.generic import TemplateView, ListView

from django.core.mail import send_mail


try:
    email_from = EmailSettings.objects.get().host_from
except:
    email_from = ''

try:
    email_to = BaseSettings.objects.get().email_for_order.split(',')
except:
    email_to = ['gorivanickiy@gmail.com']





def schedule(request):
    
    games_setup = GamesSetup.objects.all().first()
    games = Games.objects.all()

    context = {
        'games_setup': games_setup,
        'games': games,
    }



    return render(request, 'home/schedule.html', context)



from .telegram import send_message

def game_callback(request):
    if request.method == 'POST':
        form = GameOrderForm(request.POST)  
        if form.is_valid():
            game_id = form.cleaned_data.get('game_id')
            command = form.cleaned_data.get('command')
            name = form.cleaned_data.get('name')
            phone = form.cleaned_data.get('phone')
            comment = form.cleaned_data.get('comment')
            promo = form.cleaned_data.get('promo')
            how = form.cleaned_data.get('how')
            command_number = form.cleaned_data.get('command_number')

            game = Games.objects.get(id=game_id)
            if game.reverve() == False:
                reserve=True
            else:
                reserve=False


            GameOrder.objects.create(
                game=game,
                name=name,
                phone=phone,
                command=command,
                comment=comment,
                promo=promo,
                how=how,
                command_number=command_number,
                reserve=reserve
                
            )
            

            message = f'Новая заявка на игру {game} \n Команда: {command} \n Имя: {name} \n Телефон: {phone} \n Комментарий: {comment}'
            send_message(message)
            
            
            if reserve == True:
                return redirect('/?reserve=true')
            else:
                return redirect('/?reserve=false')


        else:
            print('not valid')

    return redirect('home')







@require_GET
def robots_txt(request):
    try:
        setup = BaseSettings.objects.get()
        if setup.active == True:
            lines = [
                "User-Agent: *",
                "Disallow: /admin/",
                "Disallow: /order/",
                
                "Disallow: *utm=",
                "Disallow: /accounts/",

                "Allow: /core/theme/default/*.css",
                "Allow: /core/theme/default/*.js",
                "Allow: /core/theme/default/*.png",
                "Allow: /core/theme/default/*.jpg",
                "Allow: /core/theme/default/*.gif",

                "User-Agent: Yandex",
                "Disallow: /admin/",
                "Disallow: /order/",
                "Disallow: /accounts/",
            
                "Disallow: *utm=",
                "Allow: /core/theme/default/*.css",
                "Allow: /core/theme/default/*.js",
                "Allow: /core/theme/default/*.png",
                "Allow: /core/theme/default/*.jpg",
                "Allow: /core/theme/default/*.gif",

                "Clean-Param: utm_source&utm_medium&utm_campaign",
                "Host: https://agency-profit.ru",
                "Sitemap: https://agency-profit.ru//sitemap.xml",
            ]
        else:
            lines = [
                "User-Agent: *",
                "Disallow: /",
                
            ]

    except:
        lines = [
            "User-Agent: *",
            "Disallow: /",
            
        ]
        
    return HttpResponse("\n".join(lines), content_type="text/plain")




def page_not_found_view(request, exception):
    return render(request, '404.html', status=404)

import datetime

def home(request):


    
    sliders_setup = SliderSetup.objects.all().first()
    sliders = Slider.objects.all()

    games_setup = GamesSetup.objects.all().first()
    games = Games.objects.all()

    


    games_category_setup = GamesCategorySetup.objects.all().first()
    games_category = GameCategory.objects.filter(show_to_home=True)
    games_photo = GamesPhoto.objects.all()


    what_setup = WhatSetup.objects.all().first()
    what = WhatItem.objects.all()

    wait_setup = WaitSetup.objects.all().first()
    wait = WaitItem.objects.all()

    faq_setup = FAQSetup.objects.all().first()
    faq = FAQ.objects.all()

    btn_block_setup = BtnBlockSetup.objects.all().first()
    btn_block_items = BtnBlockItem.objects.all()

    home_games = HomeGamesSetup.objects.all().first()

    
    
    

   
    
    context = {
        'sliders_setup': sliders_setup,
        'sliders': sliders,
        'games_setup': games_setup,
        'games': games,
        'games_category_setup': games_category_setup,
        'games_category': games_category,
        'games_photo': games_photo,
        'what_setup': what_setup,
        'what': what,
        'wait': wait,
        'wait_setup': wait_setup,
        'faq_setup': faq_setup,
        'faq': faq,
        'btn_block_setup': btn_block_setup,
        'btn_block_items': btn_block_items,
        'home_games': home_games,

       
        
        
    }
    
    return render(request, 'home/home.html', context)


def page_detail(request, slug):
    page = get_object_or_404(Page, type=slug)
    
    
    

    context = {
        'page': page,
    }
    return render(request, 'home/page_detail.html', context)
