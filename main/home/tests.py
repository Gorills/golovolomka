from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from home.city import get_subdomain, is_local_city_dev
from home.models import City


class FakeCity:
    def __init__(self, slug):
        self.slug = slug


KRASNODAR = FakeCity('krasnodar')


def _filter_by_slug(**kwargs):
    qs = MagicMock()
    qs.first.return_value = KRASNODAR if kwargs.get('slug') == 'krasnodar' else None
    return qs


@override_settings(ALLOWED_HOSTS=['*', 'golovolomka.fun', 'krasnodar.golovolomka.fun'])
class CityResolveTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def _request(self, path='/', host='127.0.0.1', query=None, session=None):
        url = path
        if query:
            url = '%s?%s' % (path, query)
        request = self.rf.get(url, HTTP_HOST=host)
        request.session = {} if session is None else session
        return request

    def test_localhost_without_city(self):
        request = self._request()
        self.assertTrue(is_local_city_dev(request))
        with patch('home.city.City.objects.filter', side_effect=_filter_by_slug):
            self.assertIsNone(get_subdomain(request))

    def test_query_sets_session_on_localhost(self):
        request = self._request(query='city=krasnodar')
        with patch('home.city.City.objects.filter', side_effect=_filter_by_slug):
            city = get_subdomain(request)
        self.assertEqual(city.slug, 'krasnodar')
        self.assertEqual(request.session['dev_city'], 'krasnodar')

    def test_session_persists_on_localhost(self):
        request = self._request(session={'dev_city': 'krasnodar'})
        with patch('home.city.City.objects.filter', side_effect=_filter_by_slug):
            city = get_subdomain(request)
        self.assertEqual(city.slug, 'krasnodar')

    def test_reset_query_clears_session(self):
        request = self._request(query='city=-', session={'dev_city': 'krasnodar'})
        with patch('home.city.City.objects.filter', side_effect=_filter_by_slug):
            city = get_subdomain(request)
        self.assertIsNone(city)
        self.assertNotIn('dev_city', request.session)

    def test_prod_ignores_query_and_session(self):
        request = self._request(
            host='golovolomka.fun',
            query='city=krasnodar',
            session={'dev_city': 'krasnodar'},
        )
        self.assertFalse(is_local_city_dev(request))
        with patch('home.city.City.objects.filter', side_effect=_filter_by_slug):
            self.assertIsNone(get_subdomain(request))

    def test_prod_subdomain(self):
        request = self._request(host='krasnodar.golovolomka.fun')
        with patch('home.city.City.objects.filter', side_effect=_filter_by_slug):
            city = get_subdomain(request)
        self.assertEqual(city.slug, 'krasnodar')

    def test_localhost_subdomain(self):
        request = self._request(host='krasnodar.localhost')
        self.assertTrue(is_local_city_dev(request))
        with patch('home.city.City.objects.filter', side_effect=_filter_by_slug):
            city = get_subdomain(request)
        self.assertEqual(city.slug, 'krasnodar')

    @override_settings(DEV_CITY='krasnodar')
    def test_dev_city_setting(self):
        request = self._request()
        with patch('home.city.City.objects.filter', side_effect=_filter_by_slug):
            city = get_subdomain(request)
        self.assertEqual(city.slug, 'krasnodar')


@override_settings(
    ALLOWED_HOSTS=['localhost', '.localhost', 'golovolomka.fun', '.golovolomka.fun']
)
class PublicRatingNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.city = City.objects.create(
            name='Краснодар',
            slug='krasnodar',
            phone='+70000000000',
            address='Тестовый адрес',
            email='test@example.invalid',
            vk='',
            instagram='',
            telegram='',
            whatsapp='',
        )

    def test_local_city_rating_link_preserves_city_without_session(self):
        response = self.client.get('/rating/?city=krasnodar', HTTP_HOST='localhost')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/rating/?city=krasnodar"', html=False)
        self.assertContains(response, '>Рейтинг</a>', html=False)

    def test_city_subdomain_rating_link_uses_canonical_path(self):
        response = self.client.get('/rating/', HTTP_HOST='krasnodar.golovolomka.fun')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/rating/"', html=False)
        self.assertNotContains(response, '/rating/?city=krasnodar', html=False)

    def test_existing_navigation_links_remain_visible(self):
        response = self.client.get('/rating/', HTTP_HOST='krasnodar.golovolomka.fun')

        self.assertContains(response, '>Расписание</a>', html=False)
        self.assertContains(response, '>Корпоратив</a>', html=False)
        self.assertContains(response, '>Франшиза</a>', html=False)
        self.assertContains(response, '>ХОУМ-ИГРЫ</a>', html=False)


class AdminOperatorNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.superuser = user_model.objects.create_superuser(
            username='navigation-root',
            email='navigation-root@example.invalid',
            password='test-only-password',
        )
        cls.operator = user_model.objects.create_user(
            username='navigation-operator',
            email='navigation-operator@example.invalid',
            password='test-only-password',
        )

    def test_superuser_can_follow_operator_navigation_from_admin_home(self):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse('admin'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="{}"'.format(reverse('admin_users')))
        self.assertContains(response, '>Городские операторы</span>', html=False)

        target = self.client.get(reverse('admin_users'))
        self.assertEqual(target.status_code, 200)
        self.assertContains(target, 'Городские операторы')

    def test_ordinary_user_cannot_open_global_admin_or_operator_management(self):
        self.client.force_login(self.operator)

        admin_response = self.client.get(reverse('admin'))
        users_response = self.client.get(reverse('admin_users'))

        self.assertEqual(admin_response.status_code, 302)
        self.assertEqual(users_response.status_code, 302)
