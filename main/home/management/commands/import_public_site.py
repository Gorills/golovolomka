"""Import the public Krasnodar site into the local database and media folder."""

from datetime import date
from pathlib import Path
import re
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from home.models import (
    AboutFranchSetup,
    BtnBlockItem, BtnBlockSetup, City, FAQ, FAQSetup, GameCategory, Games,
    GamesCategorySetup, GamesPhoto, GamesSetup, HomeGamesSetup, Page, Slider,
    SliderSetup, WaitItem, WaitSetup, WhatItem, WhatSetup,
    CallbackFranchSetup, DirectorWordsSetup, DoverCorpSetup, DoverCorpSlider,
    FiveFranchItem, FiveFranchSetup, FormatFranchItem, FotmatFranchSetup,
    NumbetsTableItem, NumbersFranchItem, NumbersFranchSetup, StartCorpSetup,
    StartFranchSetup, WhatCorpItem, WhatCorpItemSetup, WhatCorpSetup,
    WhatFranchBtn, WhatFranchItem, WhatFranchSetup, WhatOtlItem,
    WhatYouGetItem, WhatYouGetSetup, WhyWeCorpItem, WhyWeCorpSetup,
    YourPayItem, YourPaySetup,
)
from setup.models import BaseSettings, Colors, ThemeSettings


MONTHS = {
    'ЯНВАРЯ': 1, 'ФЕВРАЛЯ': 2, 'МАРТА': 3, 'АПРЕЛЯ': 4,
    'МАЯ': 5, 'ИЮНЯ': 6, 'ИЮЛЯ': 7, 'АВГУСТА': 8,
    'СЕНТЯБРЯ': 9, 'ОКТЯБРЯ': 10, 'НОЯБРЯ': 11, 'ДЕКАБРЯ': 12,
}


def clean(node):
    return ' '.join(node.stripped_strings).strip() if node else ''


def inner_html(node):
    return ''.join(str(child) for child in node.contents).strip() if node else ''


class Importer:
    def __init__(self, base_url, source_dir=None):
        self.base_url = base_url.rstrip('/') + '/'
        self.source_dir = Path(source_dir) if source_dir else None
        self.media_root = Path(settings.MEDIA_ROOT)
        self.downloaded = 0

    def get(self, path):
        if self.source_dir:
            filename = 'home.html' if path == '/' else path.strip('/') + '.html'
            return (self.source_dir / filename).read_text(encoding='utf-8')
        url = urljoin(self.base_url, path.lstrip('/'))
        request = Request(url, headers={'User-Agent': 'Golovolomka local importer/1.0'})
        with urlopen(request, timeout=45) as response:
            return response.read().decode('utf-8')

    def soup(self, path):
        return BeautifulSoup(self.get(path), 'html.parser')

    def media(self, url):
        if not url or not url.startswith('/media/'):
            return ''
        rel = unquote(urlparse(url).path[len('/media/'):]).lstrip('/')
        destination = self.media_root / rel
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            request = Request(urljoin(self.base_url, url), headers={'User-Agent': 'Golovolomka local importer/1.0'})
            with urlopen(request, timeout=60) as response:
                destination.write_bytes(response.read())
            self.downloaded += 1
        return rel

    def import_all_media(self, *soups):
        for soup in soups:
            for node in soup.select('[src], [href]'):
                value = node.get('src') or node.get('href')
                if value and value.startswith('/media/'):
                    self.media(value)

    def singleton(self, model, **values):
        obj = model.objects.order_by('pk').first() or model()
        for key, value in values.items():
            setattr(obj, key, value)
        obj.save()
        return obj

    def image(self, root, selector):
        node = root.select_one(selector) if root else None
        return self.media(node.get('src')) if node and node.get('src') else ''

    def import_base(self, home):
        phone_link = home.select_one('a[href^="tel:"]')
        phone = clean(phone_link)
        footer = home.select_one('.footer')
        address_node = footer.select_one('.footer__address') if footer else None
        city = City.objects.create(
            name='Краснодар', slug='krasnodar', phone=phone,
            address=clean(address_node), email='',
            vk=(home.select_one('a[href*="vk.com"]') or {}).get('href', ''),
            instagram=(home.select_one('a[href*="instagram.com"]') or {}).get('href', ''),
            telegram=(home.select_one('a[href*="t.me"]') or {}).get('href', ''),
            whatsapp=(home.select_one('a[href*="whatsapp.com"]') or {}).get('href', ''),
        )
        title = clean(home.title)
        description = (home.select_one('meta[name="description"]') or {}).get('content', '')
        self.singleton(
            BaseSettings, name='Головоломка', phone=phone, address=city.address,
            meta_title=title, meta_description=description, meta_keywords='',
            vk=city.vk, instagram=city.instagram, telegram=city.telegram,
            whatsapp=city.whatsapp, copy_year=str(date.today().year),
            copy='Головоломка', theme_color='#000000', active=True,
        )
        self.singleton(ThemeSettings, name='default')
        self.singleton(Colors, primary='#F4D11E', secondary='#92278F')
        return city

    def import_home(self, home, city):
        slider = home.select_one('.slider')
        Slider.objects.bulk_create([
            Slider(name=f'Слайд {i}', image=self.media(img.get('src')))
            for i, img in enumerate(slider.select('.slider__slide'), 1)
        ])
        self.singleton(
            SliderSetup,
            suptitle=clean(slider.select_one('.slider__subtitle')),
            title=inner_html(slider.select_one('.slider__title')),
            text=inner_html(slider.select_one('.slider__text')),
            button_text=clean(slider.select_one('.slider__btn p')),
            link=(slider.select_one('.slider__btn') or {}).get('href', ''),
            bg=self.image(slider, '.slider__bg'),
        )

        schedule = home.select_one('.schedule')
        self.singleton(GamesSetup, title=clean(schedule.select_one('.schedule__title')), bg=self.image(schedule, '.schedule__bg'))
        generic_category = GameCategory.objects.create(
            name='Игры', show_to_home=False, description_short='', description=''
        )
        for card in schedule.select('.schedule__item'):
            rows = [clean(x) for x in card.select('.schedule__row-text')]
            button = card.select_one('.schedule__btn[data-id]')
            status = clean(card.select_one('.schedule__status')).upper()
            date_text = clean(card.select_one('.schedule__date p'))
            match = re.match(r'(\d{1,2})\s+([А-ЯЁ]+)', date_text.upper())
            parsed_date = None
            if match and match.group(2) in MONTHS:
                parsed_date = date(date.today().year, MONTHS[match.group(2)], int(match.group(1)))
            bg_node = card.select_one('.schedule__item-bg')
            Games.objects.create(
                id=int(button['data-id']) if button else None,
                category=generic_category, city=city,
                name=clean(card.select_one('.schedule__item-title')),
                date=date_text, date_date=parsed_date,
                time=rows[0] if rows else '', duration=rows[1] if len(rows) > 1 else '150 минут',
                price=int(re.sub(r'\D', '', rows[2]) or 0) if len(rows) > 2 else 600,
                comands=rows[3] if len(rows) > 3 else '2-12',
                location=clean(card.select_one('.schedule__loc')),
                description=inner_html(card.select_one('.schedule__desc')),
                bg=self.media(bg_node.get('src')) if bg_node else '',
                mark_few_seats='МАЛО' in status,
                manual_sold_out='МЕСТ НЕТ' in status,
                reserve_enabled='МЕСТ НЕТ' not in status,
                number_of_seats=50, numbers_of_reserves=50,
            )

        about = home.select_one('.about')
        video = about.select_one('video[src]')
        iframe = about.select_one('iframe')
        self.singleton(
            WhatSetup, title=clean(about.select_one('.about__title')),
            text=inner_html(about.select_one('.about__rules-text')),
            link=(about.select_one('.about__rules-btn') or {}).get('href', '/pravila'),
            video=self.media(video.get('src')) if video else '',
            embedded_video=str(iframe) if iframe else '', bg=self.image(about, '.about__bg'),
        )
        WhatItem.objects.bulk_create([
            WhatItem(title=clean(item.select_one('.about__count')), text=inner_html(item.select_one('.about__item-text')))
            for item in about.select('.about__item')
        ])

        waiting = home.select_one('.what')
        self.singleton(
            WaitSetup, title=clean(waiting.select_one('.what__title')),
            bg=self.image(waiting, '.what__bg'), image=self.image(waiting, '.what__img'),
        )
        WaitItem.objects.bulk_create([WaitItem(text=clean(x)) for x in waiting.select('.what__text')])

        formats = home.select_one('.format')
        self.singleton(GamesCategorySetup, title=clean(formats.select_one('.format__title')), bg=self.image(formats, '.format__bg'))
        nav = formats.select('.format__nav-item')
        bodies = formats.select('.format__body-item')
        for index, item in enumerate(nav):
            GameCategory.objects.create(
                name=clean(item.select_one('.format__nav-text')), show_to_home=True,
                description_short='', description=inner_html(bodies[index]) if index < len(bodies) else '',
            )
        for link in formats.select('.format__slider-item[href]'):
            GamesPhoto.objects.create(image=self.media(link.get('href')))

        faq = home.select_one('.faq')
        self.singleton(FAQSetup, title=clean(faq.select_one('.faq__title')), bg=self.image(faq, '.faq__bg'))
        for item in faq.select('.faq__item'):
            FAQ.objects.create(
                question=clean(item.select_one('.faq__top-title')),
                answer=inner_html(item.select_one('.faq__body')),
            )

        buttons = home.select_one('.btn-block')
        self.singleton(BtnBlockSetup, bg=self.image(buttons, '.btn-block__item-bg.bg'))
        for item in buttons.select('a.btn-block__item'):
            BtnBlockItem.objects.create(
                title=clean(item.select_one('.btn-block__text')),
                link=item.get('href', ''), link_text=clean(item.select_one('.btn-block__btn p')),
                bg=self.image(item, 'img.btn-block__item-bg'),
            )

        games = home.select_one('.home-games')
        self.singleton(
            HomeGamesSetup, title=clean(games.select_one('.home-games__title')),
            text=inner_html(games.select_one('.home-games__text')),
            link=(games.select_one('.home-games__btn') or {}).get('href', ''),
            link_text=clean(games.select_one('.home-games__btn p')),
            image=self.image(games, '.home-games__img'), bg=self.image(games, '.home-games__bg'),
        )

    def import_pages(self):
        for order, slug in enumerate(('privacy', 'pravila', 'soglashenie')):
            soup = self.soup('/' + slug + '/')
            body = soup.select_one('.page__inner')
            heading = body.select_one('.page__title') if body else None
            page_name = clean(heading) or clean(soup.select_one('.breadcrumbs__item:last-child'))
            if heading:
                heading.extract()
            Page.objects.create(
                type=slug, name=page_name, meta_h1=page_name,
                text=inner_html(body), meta_title=clean(soup.title),
                meta_description=(soup.select_one('meta[name="description"]') or {}).get('content', ''),
                meta_keywords=(soup.select_one('meta[name="keywords"]') or {}).get('content', ''),
                page_order=order,
            )
            yield soup

    def import_corp(self, soup):
        start = soup.select_one('.start')
        self.singleton(StartCorpSetup, title=clean(start.select_one('.start__title')), text=inner_html(start.select_one('.start__text')), bg=self.image(start, '.start__bg'))
        about = soup.select_one('.about')
        video, iframe = about.select_one('video[src]'), about.select_one('iframe')
        self.singleton(WhatCorpSetup, title=clean(about.select_one('.about__title')), video=self.media(video.get('src')) if video else '', embedded_video=str(iframe) if iframe else '', bg=self.image(about, '.about__bg'))
        why = soup.select_one('.why')
        self.singleton(WhatCorpItemSetup, title=clean(why.select_one('.why__title')), bg=self.image(why, '.why__bg'))
        for item in why.select('.why__item'):
            WhatCorpItem.objects.create(image=self.image(item, 'img'), text=clean(item.select_one('.why__text')))
        why_we = soup.select_one('.why-we')
        self.singleton(WhyWeCorpSetup, title=clean(why_we.select_one('.why-we__title')), bg=self.image(why_we, '.why-we__bg'))
        for item in why_we.select('.why-we__item'):
            WhyWeCorpItem.objects.create(image=self.image(item, '.why-we__img'), text=clean(item.select_one('.why-we__text')))
        trust = soup.select_one('.corp-about')
        text_node = trust.select_one('.corp-about__text')
        self.singleton(DoverCorpSetup, title=clean(trust.select_one('h2.corp-about__title')), subtitle=clean(trust.select_one('p.corp-about__title')), count=clean(trust.select_one('.corp-about__count')), text=inner_html(text_node), bg=self.image(trust, '.corp-about__bg'))
        for img in trust.select('.corp-about__slide'):
            DoverCorpSlider.objects.create(image=self.media(img.get('src')))

    def import_franchise(self, soup):
        start = soup.select_one('.start')
        second = soup.select_one('.second-block .slider__text')
        self.singleton(StartFranchSetup, title=clean(start.select_one('.start__title')), subtitle=inner_html(start.select_one('.start__text')), text=inner_html(second), bg=self.image(start, '.start__bg'))
        about = soup.select_one('.about')
        video, iframe = about.select_one('video[src]'), about.select_one('iframe')
        self.singleton(WhatFranchSetup, title=clean(about.select_one('.about__title')), text=inner_html(about.select_one('.about__text-fr')), video=self.media(video.get('src')) if video else '', embedded_video=str(iframe) if iframe else '', bg=self.image(about, '.about__bg'))
        for item in about.select('a.btn-block__item'):
            href = item.get('href', '')
            WhatFranchBtn.objects.create(image=self.image(item, '.btn-block__item-bg'), text=inner_html(item.select_one('.btn-block__text')), link=href if not href.startswith('/media/') else '', file=self.media(href), btn=clean(item.select_one('.btn-block__btn p')))
        forus = soup.select_one('.forus')
        titles = forus.select('.forus__title')
        self.singleton(AboutFranchSetup, title=clean(titles[0]) if titles else '', title_2=clean(titles[1]) if len(titles) > 1 else '', bg=self.image(forus, '.forus__bg'))
        for item in forus.select('.forus__item'):
            WhatFranchItem.objects.create(title=clean(item.select_one('.forus__item-title')), text=inner_html(item.select_one('.forus__text')))
        for item in forus.select('.forus__linear-item'):
            WhatOtlItem.objects.create(title=clean(item.select_one('.forus__linear-itle')), text=inner_html(item.select_one('.forus__linear-text')))
        game_format = soup.select_one('.game-format')
        self.singleton(FotmatFranchSetup, title=clean(game_format.select_one('.game-format__title')), bg=self.image(game_format, '.game-format__bg'))
        for item in game_format.select('.btn-block__item'):
            FormatFranchItem.objects.create(title=clean(item.select_one('.btn-block__text')), text=inner_html(item.select_one('.btn-block__desc')), img=self.image(item, '.btn-block__item-bg'))
        five = soup.select_one('.why-fr')
        self.singleton(FiveFranchSetup, title=clean(five.select_one('.why-fr__title')), text=inner_html(five.select_one('.why-fr__doyou-title')), bg=self.image(five, '.why-fr__bg'))
        for item in five.select('.what__item'):
            FiveFranchItem.objects.create(title=clean(item.select_one('.what__item-title')), text=inner_html(item.select_one('.what__text')))
        got = soup.select_one('.whatweget')
        self.singleton(WhatYouGetSetup, title=clean(got.select_one('.whatweget__title')), subtitle=clean(got.select_one('.whatweget__subtitle')), bg=self.image(got, '.whatweget__bg'))
        for item in got.select('.whatweget__item'):
            WhatYouGetItem.objects.create(image=self.image(item, 'img'), text=inner_html(item.select_one('.whatweget__text')))
        earn = soup.select_one('.earn')
        self.singleton(YourPaySetup, title=clean(earn.select_one('.earn__title')), bg=self.image(earn, '.earn__bg'))
        for item in earn.select('.earn__item'):
            YourPayItem.objects.create(title=clean(item.select_one('.earn__text')))
        numbers = soup.select_one('.fornumbers')
        self.singleton(NumbersFranchSetup, title=clean(numbers.select_one('.fornumbers__title')), bg=self.image(numbers, '.fornumbers__bg'))
        for row in numbers.select('.fornumbers__row > .fornumbers__item'):
            values = row.select(':scope > .fornumbers__text')
            if len(values) >= 2:
                NumbetsTableItem.objects.create(title=clean(values[0]), value=clean(values[1]))
        for item in numbers.select('.fornumbers__grid-item'):
            NumbersFranchItem.objects.create(title=clean(item.select_one('.fornumbers__grid-top')), text=inner_html(item.select_one('.fornumbers__grid-bottom')))
        director = soup.select_one('.osnwords')
        self.singleton(DirectorWordsSetup, title=clean(director.select_one('.osnwords__title')), text=inner_html(director.select_one('.osnwords__text')), image=self.image(director, '.osnwords__img'), bg=self.image(director, '.osnwords__bg'), file=self.media((director.select_one('.osnwords__btn') or {}).get('href', '')))
        callback = soup.select_one('.control')
        subtitles = callback.select('.control__subtitle')
        texts = callback.select('.control__text')
        self.singleton(CallbackFranchSetup, title=clean(callback.select_one('.control__title')), subtitle_1=clean(subtitles[0]) if subtitles else '', text_1=clean(texts[0]) if texts else '', subtitle_2=clean(subtitles[1]) if len(subtitles) > 1 else '', text_2=clean(texts[1]) if len(texts) > 1 else '', bg=self.image(callback, '.control__bg'))

    def clear(self):
        for model in (
            Games, GameCategory, GamesPhoto, Slider, WhatItem, WaitItem, FAQ,
            BtnBlockItem, Page, City, WhatCorpItem, WhyWeCorpItem,
            DoverCorpSlider, WhatFranchBtn, WhatFranchItem, WhatOtlItem,
            FormatFranchItem, FiveFranchItem, WhatYouGetItem, YourPayItem,
            NumbetsTableItem, NumbersFranchItem,
        ):
            model.objects.all().delete()


class Command(BaseCommand):
    help = 'Import public content and media from krasnodar.golovolomka.fun.'

    def add_arguments(self, parser):
        parser.add_argument('--url', default='https://krasnodar.golovolomka.fun/')
        parser.add_argument('--source-dir', help='Directory with home.html and <slug>.html snapshots')

    @transaction.atomic
    def handle(self, *args, **options):
        importer = Importer(options['url'], options.get('source_dir'))
        try:
            home = importer.soup('/')
            importer.clear()
            city = importer.import_base(home)
            importer.import_home(home, city)
            corp = importer.soup('/corp/')
            franchise = importer.soup('/franchise/')
            importer.import_corp(corp)
            importer.import_franchise(franchise)
            page_soups = list(importer.import_pages())
            importer.import_all_media(home, corp, franchise, *page_soups)
        except Exception as exc:
            raise CommandError(f'Import failed: {exc}') from exc
        self.stdout.write(self.style.SUCCESS(
            f'Imported Krasnodar: {Games.objects.count()} games, '
            f'{GameCategory.objects.count()} categories, {Page.objects.count()} pages, '
            f'{importer.downloaded} media files.'
        ))
