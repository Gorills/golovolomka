import unicodedata
from datetime import datetime

from django.shortcuts import get_object_or_404, render, redirect
from django.db import transaction
from django.db.models import F, Sum
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


def _text_needle(s):
    """Нормализация + регистронезависимое сравнение (в т.ч. кириллица) для подстрочного поиска."""
    if not s or not str(s).strip():
        return ''
    return unicodedata.normalize('NFC', str(s).strip()).casefold()


def schedule(request):
    
    games_setup = GamesSetup.objects.all().first()
    games = Games.objects.select_related('city', 'category').all().order_by(
        F('date_date').asc(nulls_last=True),
        F('display_priority').desc(),
        'id',
    )

    city = get_subdomain(request)
    if city:
        games = games.filter(city=city)

    search_date = request.GET.get('date', '').strip()
    search_game = request.GET.get('game', '').strip()
    search_place = request.GET.get('place', '').strip()

    if search_date:
        try:
            parsed = datetime.strptime(search_date, '%Y-%m-%d').date()
            games = games.filter(date_date=parsed)
        except (ValueError, TypeError):
            pass

    if search_game:
        needle = _text_needle(search_game)
        if needle:
            matching_ids = []
            for gid, name, cat_name in games.values_list('id', 'name', 'category__name'):
                hay_name = _text_needle(name or '')
                hay_cat = _text_needle(cat_name or '')
                if needle in hay_name or needle in hay_cat:
                    matching_ids.append(gid)
            games = games.filter(id__in=matching_ids) if matching_ids else games.none()

    if search_place:
        needle = _text_needle(search_place)
        if needle:
            matching_ids = []
            for gid, loc, caddr, cname in games.values_list(
                'id', 'location', 'city__address', 'city__name'
            ):
                parts = (
                    _text_needle(loc or ''),
                    _text_needle(caddr or ''),
                    _text_needle(cname or ''),
                )
                if any(needle in p for p in parts):
                    matching_ids.append(gid)
            games = games.filter(id__in=matching_ids) if matching_ids else games.none()

    schedule_search_active = bool(search_date or search_game or search_place)
    games_empty = not games.exists()

    context = {
        'games_setup': games_setup,
        'games': games,
        'search_date': search_date,
        'search_game': search_game,
        'search_place': search_place,
        'schedule_search_active': schedule_search_active,
        'games_empty': games_empty,
    }



    return render(request, 'home/schedule.html', context)


from django.http import JsonResponse
import requests
from django.conf import settings
from .telegram import send_message
from .max_client import resolve_max_chat_id, send_max_if_configured
from django.db import transaction
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect
from django.core.exceptions import ObjectDoesNotExist
import json

from main.local_settings import SMARTCAPTCHA_SERVER_KEY


def _notify_telegram_and_max(message, telegram_group=None, city=None):
    """Те же уведомления, что в Telegram, дублируются в MAX при настройке."""
    try:
        send_message(message, telegram_group)
    except Exception:
        pass
    try:
        send_max_if_configured(resolve_max_chat_id(city), message)
    except Exception:
        pass


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
        return redirect('/?error=true')

    form = GameOrderForm(request.POST)
    form_data = request.POST.dict()

    city = get_subdomain(request)
    try:
        default_tg = (BaseSettings.objects.get().telegram_default_group or '').strip()
    except BaseSettings.DoesNotExist:
        default_tg = ''
    if city:
        telegram_group = (city.telegram_group or '').strip() or default_tg
    else:
        telegram_group = default_tg

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
            first_time = form.cleaned_data.get('first_time')
            agree_personal_data = form.cleaned_data.get('agree_personal_data')
            agree_ads = form.cleaned_data.get('agree_ads')


            try:
                with transaction.atomic():
                    game = Games.objects.select_for_update().get(id=game_id)

                    if not game.site_can_register():
                        return redirect('/?error=true')

                    main_o = (
                        game.orders.filter(reserve=False).aggregate(s=Sum('command_number'))['s'] or 0
                    )
                    res_o = (
                        game.orders.filter(reserve=True).aggregate(s=Sum('command_number'))['s'] or 0
                    )

                    if main_o + command_number <= game.number_of_seats:
                        order_reserve = False
                    elif game.reserve_enabled and res_o + command_number <= game.numbers_of_reserves:
                        order_reserve = True
                    else:
                        return redirect('/?error=true')

                    GameOrder.objects.create(
                        game=game,
                        name=name,
                        phone=phone,
                        command=command,
                        comment=comment,
                        promo=promo,
                        how=how,
                        command_number=command_number,
                        first_time=bool(first_time),
                        agree_personal_data=bool(agree_personal_data),
                        agree_ads=bool(agree_ads),
                        reserve=order_reserve,
                    )
                    reserve = order_reserve
            except Games.DoesNotExist:
                error_message = (
                    f"Игра с id {game_id} не найдена.\n"
                    f"Полученные данные: {form_data}"
                )
                _notify_telegram_and_max(error_message, city=city)
                return redirect('/?error=true')
            except Exception as create_err:
                error_message = (
                    f"Ошибка при сохранении заявки.\n"
                    f"Полученные данные: {form_data}\n"
                    f"Ошибка: {str(create_err)}"
                )
                _notify_telegram_and_max(error_message, city=city)
                return redirect('/?error=true')

            # Формируем сообщение для Telegram
            message = (
                f"Новая заявка на игру ***{game}***\n"
                f"Очередь: {'резерв' if reserve else 'основной состав'}\n"
                f"Команда: {command}\n"
                f"Имя: {name}\n"
                f"Телефон: {phone}\n"
                f"Количество человек: {command_number}\n"
                f"Играем впервые: {'Да' if first_time else 'Нет'}\n"
                f"Комментарий: {comment}\n"
                f"Промокод: {promo}\n"
                f"Как вы узнали о нас: {how}\n"
                f"Согласие на обработку ПД: {'Да' if agree_personal_data else 'Нет'}\n"
                f"Согласие на рекламу: {'Да' if agree_ads else 'Нет'}"
            )
            _notify_telegram_and_max(message, telegram_group, city=city)

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
            _notify_telegram_and_max(message, city=city)

            return redirect('/?error=true')



    except Exception as e:
        # Ловим любые непредвиденные ошибки, отправляем информацию в Telegram
        error_message = (
            f"Ошибка при обработке заявки.\n"
            f"Полученные данные: {form_data}\n"
            f"Ошибка: {str(e)}"
        )
        _notify_telegram_and_max(error_message, city=city)

        return redirect('/?error=true')






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
            _notify_telegram_and_max(message)

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
            _notify_telegram_and_max(message)

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
    games = Games.objects.all().order_by(
        F('date_date').asc(nulls_last=True),
        F('display_priority').desc(),
        'id',
    )

    if city:
        games = games.filter(city=city)


    games_category_setup = GamesCategorySetup.objects.all().first()
    games_category = GameCategory.objects.filter(show_to_home=True)
    games_photo = GamesPhoto.objects.all()


    # order_by('id') — чтобы .first() всегда возвращал один и тот же объект,
    # даже если в БД случайно оказалось больше одной записи singleton-модели.
    what_setup = WhatSetup.objects.all().order_by('id').first()
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
