from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from home.city import get_subdomain, is_local_city_dev


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
