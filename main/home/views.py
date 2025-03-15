from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpResponse


from .models import DoverCorpSetup, DoverCorpSlider, GameOrder, SliderSetup, Slider, Page, City, GamesSetup, GamesCategorySetup, GamesPhoto, GameCategory, Games, StartCorpSetup, WhatCorpItem, WhatCorpItemSetup, WhatCorpSetup, WhatSetup, WhatItem, WaitSetup, WaitItem, FAQSetup, FAQ, BtnBlockSetup, BtnBlockItem, HomeGamesSetup, WhyWeCorpItem, WhyWeCorpSetup
from setup.models import ThemeSettings, BaseSettings, EmailSettings

from .forms import CorpForm, FranchForm, GameOrderForm

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



from .context_processors import get_subdomain


def schedule(request):
    
    games_setup = GamesSetup.objects.all().first()
    games = Games.objects.all().order_by('date_date')

    city = get_subdomain(request)
    if city:
        games = games.filter(city=city)

    context = {
        'games_setup': games_setup,
        'games': games,
    }



    return render(request, 'home/schedule.html', context)


from django.http import JsonResponse
import requests
from django.conf import settings
from .telegram import send_message
from django.db import transaction
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect
from django.core.exceptions import ObjectDoesNotExist
import json

from main.local_settings import SMARTCAPTCHA_SERVER_KEY




def get_client_ip(request):
    """Определяет реальный IP пользователя, учитывая возможные прокси."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



def game_callback(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)

    form = GameOrderForm(request.POST)
    form_data = request.POST.dict()
    
    city = get_subdomain(request)
    if city:
        telegram_group = city.telegram_group
        if not telegram_group:
            telegram_group = '-1002487695898'
    else:
        telegram_group = '-1002487695898'


    try:
        
        if form.is_valid():
            

            game_id = form.cleaned_data.get('game_id')
            command = form.cleaned_data.get('command')
            name = form.cleaned_data.get('name')
            phone = form.cleaned_data.get('phone')
            comment = form.cleaned_data.get('comment')
            promo = form.cleaned_data.get('promo')
            how = form.cleaned_data.get('how')
            command_number = form.cleaned_data.get('command_number')

            
            try:
                game = Games.objects.get(id=game_id)
            except ObjectDoesNotExist:
                error_message = (
                    f"Игра с id {game_id} не найдена.\n"
                    f"Полученные данные: {form_data}"
                )
                try:
                    send_message(error_message)
                except Exception as send_err:
                    # Здесь можно добавить логирование ошибки отправки сообщения
                    pass
                return JsonResponse({'error': 'Игра не найдена'}, status=404)

            # Предполагаем, что метод называется reserve(), исправляем опечатку, если она была
            try:
                # Если метод возвращает bool, то можно использовать:
                reserve = not game.reserve()
            except AttributeError:
                # Если метода reserve() нет, установить значение по умолчанию или обработать иначе
                reserve = False

            GameOrder.objects.create(
                game=game,
                name=form.cleaned_data.get('name'),
                phone=form.cleaned_data.get('phone'),
                command=form.cleaned_data.get('command'),
                comment=form.cleaned_data.get('comment'),
                promo=form.cleaned_data.get('promo'),
                how=form.cleaned_data.get('how'),
                command_number=form.cleaned_data.get('command_number'),
            )

            # Формируем сообщение для Telegram
            message = (
                f"Новая заявка на игру ***{game}***\n"
                f"Команда: {command}\n"
                f"Имя: {name}\n"
                f"Телефон: {phone}\n"
                f"Количество человек: {command_number}\n"
                f"Комментарий: {comment}\n"
                f"Промокод: {promo}\n"
                f"Как вы узнали о нас: {how}"
            )
            try:
                send_message(message, telegram_group)
            except Exception as e:
                # Логирование ошибки отправки сообщения, если необходимо
                pass
            

            reserve_bool = "true" if reserve else "false"
            return redirect(f"/?reserve={reserve_bool}")
        
            

        else:

            # В случае невалидной формы используем исходные данные и ошибки валидации
            errors = form.errors.as_json()
            message = (
                f"Новая заявка с ошибкой!\n"
                f"Полученные данные: {form_data}\n"
                f"Ошибки: {errors}"
            )
            try:
                send_message(message, )
            except Exception as e:
                # Логирование ошибки отправки сообщения, если необходимо
                pass

            return redirect(f"/?error=true")
                
                

    except Exception as e:
        # Ловим любые непредвиденные ошибки, отправляем информацию в Telegram
        error_message = (
            f"Ошибка при обработке заявки.\n"
            f"Полученные данные: {form_data}\n"
            f"Ошибка: {str(e)}"
        )
        try:
            send_message(error_message)
        except Exception:
            pass

        return redirect(f"/?error=true")






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



def corp(request):

    if request.method == 'POST':
        form = CorpForm(request.POST)
        
        if form.is_valid():
            name = form.cleaned_data.get('name')
            email = form.cleaned_data.get('email')
            phone = form.cleaned_data.get('phone')
            data = form.cleaned_data.get('data')
            city = form.cleaned_data.get('city')
            numbers = form.cleaned_data.get('numbers')
            how_call = form.cleaned_data.get('how_call')
            how = form.cleaned_data.get('how')
            place = form.cleaned_data.get('place')

            
            message = f'''
Новая заявка на корпоратив
Имя: {name}
Email: {email}
Телефон: {phone}
Дата: {data}
Город: {city}
Количество человек: {numbers}
Как вы узнали о нас: {how_call}
Как вы узнали о нас: {how}
Место проведения: {place}
'''

            # print(message)
            send_message(message)


            return redirect('/?reserve=false')

    

    what_setup = WhatCorpSetup.objects.all().first()

    what_corp_items_setup = WhatCorpItemSetup.objects.all().first()
    what_corp_items = WhatCorpItem.objects.all()

    wht_we_corp_setup = WhyWeCorpSetup.objects.all().first()
    wht_we_corp_items = WhyWeCorpItem.objects.all()

    dover_corp_setup = DoverCorpSetup.objects.all().first()
    dover_corp_slider = DoverCorpSlider.objects.all()

    faq_setup = FAQSetup.objects.all().first()
    faq = FAQ.objects.all()
    games_photo = GamesPhoto.objects.all()
    games_category_setup = GamesCategorySetup.objects.all().first()
    form = CorpForm()


    context = {
        'start': StartCorpSetup.objects.all().first(),
        'what_setup': what_setup,
        'what_corp_items_setup': what_corp_items_setup,
        'what_corp_items': what_corp_items,

        'wht_we_corp_setup': wht_we_corp_setup,
        'wht_we_corp_items': wht_we_corp_items,

        'dover_corp_setup': dover_corp_setup,
        'dover_corp_slider': dover_corp_slider,



        'faq_setup': faq_setup,
        'faq': faq,
        'games_photo': games_photo,
        'games_category_setup': games_category_setup,
        'form': form
    }


    return render(request, 'home/corp.html', context)



from .models import StartFranchSetup, WhatFranchSetup, WhatFranchBtn, AboutFranchSetup, WhatFranchItem, WhatOtlItem, FotmatFranchSetup, FormatFranchItem, FiveFranchSetup, FiveFranchItem, WhatYouGetSetup, WhatYouGetItem, YourPaySetup, YourPayItem, NumbersFranchSetup, NumbetsTableItem, NumbersFranchItem, DirectorWordsSetup, CallbackFranchSetup

def franchise(request):
    if request.method == 'POST':
        form = FranchForm(request.POST)
        
        if form.is_valid():
            name = form.cleaned_data.get('name')
            phone = form.cleaned_data.get('phone')
            city = form.cleaned_data.get('city')
            
            how = form.cleaned_data.get('how')
            comment = form.cleaned_data.get('comment')

            
            message = f'''
Новая заявка на франшизу
Имя: {name}
Телефон: {phone}
Город: {city}
Как вы узнали о нас: {how}
Комментарий: {comment}
'''

            # print(message)
            send_message(message)


            return redirect('/?reserve=false')
        

    form = FranchForm()
    context = {
        'start_serup': StartFranchSetup.objects.all().first(),
        'what_setup': WhatFranchSetup.objects.all().first(),
        'what_btn': WhatFranchBtn.objects.all(),
        'about_setup': AboutFranchSetup.objects.all().first(),
        'what_items': WhatFranchItem.objects.all(),
        'what_otl': WhatOtlItem.objects.all(),
        'fotmat_setup': FotmatFranchSetup.objects.all().first(),
        'fotmat_items': FormatFranchItem.objects.all(),
        'five_setup': FiveFranchSetup.objects.all().first(),
        'five_items': FiveFranchItem.objects.all(),
        'what_you_get_setup': WhatYouGetSetup.objects.all().first(),
        'what_you_get_items': WhatYouGetItem.objects.all(),
        'your_pay_setup': YourPaySetup.objects.all().first(),
        'your_pay_items': YourPayItem.objects.all(),
        'numbers_setup': NumbersFranchSetup.objects.all().first(),
        'numbers_items': NumbetsTableItem.objects.all(),
        'numbers_items_2': NumbersFranchItem.objects.all(),
        'director_setup': DirectorWordsSetup.objects.all().first(),
        'callback_setup': CallbackFranchSetup.objects.all().first(),
        'form': form
    }

    
    return render(request, 'home/franchise.html', context)


def home(request):

    city = get_subdomain(request)

    
    sliders_setup = SliderSetup.objects.all().first()
    sliders = Slider.objects.all()

    games_setup = GamesSetup.objects.all().first()
    games = Games.objects.all().order_by('date_date')

    if city:
        games = games.filter(city=city)


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
