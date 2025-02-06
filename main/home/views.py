from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpResponse


from .models import DoverCorpSetup, DoverCorpSlider, GameOrder, SliderSetup, Slider, Page, City, GamesSetup, GamesCategorySetup, GamesPhoto, GameCategory, Games, StartCorpSetup, WhatCorpItem, WhatCorpItemSetup, WhatCorpSetup, WhatSetup, WhatItem, WaitSetup, WaitItem, FAQSetup, FAQ, BtnBlockSetup, BtnBlockItem, HomeGamesSetup, WhyWeCorpItem, WhyWeCorpSetup
from setup.models import ThemeSettings, BaseSettings, EmailSettings

from .forms import CorpForm, GameOrderForm

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
    games = Games.objects.all().order_by('date_date')

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

def verify_yandex_captcha(token, user_ip):
    """Проверяет YaCaptcha через API Яндекса"""
    try:
        response = requests.get(
            "https://smartcaptcha.yandexcloud.net/validate",
            params={
                "secret": SMARTCAPTCHA_SERVER_KEY,
                "token": token,
                "ip": user_ip,  # Передаем IP пользователя
            },
            timeout=1  # Таймаут 1 секунда
        )
        server_output = response.content.decode()
        if response.status_code != 200:
            print(f"Ошибка проверки CAPTCHA: код={response.status_code}; ответ={server_output}")
            return False  # Если ошибка запроса, считаем капчу не пройденной
        
        return json.loads(server_output).get("status") == "ok"
    
    except requests.RequestException as e:
        print(f"Ошибка сети при проверке CAPTCHA: {e}")
        return False  # Если произошла ошибка запроса, не пропускаем пользователя

def game_callback(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)

    form = GameOrderForm(request.POST)
    form_data = request.POST.dict()
    captcha_token = request.POST.get("smart-token")
    user_ip = get_client_ip(request)  # Получаем IP пользователя

    # Проверяем капчу перед обработкой формы
    if not captcha_token or not verify_yandex_captcha(captcha_token, user_ip):
        return JsonResponse({'error': 'Вы не прошли проверку CAPTCHA'}, status=400)

    try:
        with transaction.atomic():
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
                    send_message(message)
                except Exception as e:
                    # Логирование ошибки отправки сообщения, если необходимо
                    pass
                

                reserve_bool = True if reserve else False
                return JsonResponse({'success': True, 'url': f"/?reserve={reserve_bool}"})

            else:

                # В случае невалидной формы используем исходные данные и ошибки валидации
                errors = form.errors.as_json()
                message = (
                    f"Новая заявка с ошибкой!\n"
                    f"Полученные данные: {form_data}\n"
                    f"Ошибки: {errors}"
                )
                try:
                    send_message(message)
                except Exception as e:
                    # Логирование ошибки отправки сообщения, если необходимо
                    pass
                
                return JsonResponse({'error': 'Некорректные данные', 'url': "/?error=true", 'errors': form.errors}, status=400)

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

        return JsonResponse({'error': f'Ошибка сервера: {str(e)}', 'url': "/?error=true"}, status=500)






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

def home(request):


    
    sliders_setup = SliderSetup.objects.all().first()
    sliders = Slider.objects.all()

    games_setup = GamesSetup.objects.all().first()
    games = Games.objects.all().order_by('date_date')

    


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
