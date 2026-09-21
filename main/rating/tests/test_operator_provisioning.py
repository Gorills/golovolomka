from unittest import mock

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from rating.models import CityRatingAccess
from rating.services import create_city_operator

from .factories import city, user


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '.localhost'])
class OperatorProvisioningHttpTests(TestCase):
    def setUp(self):
        self.city_a = city('provision-a')
        self.city_b = city('provision-b')
        self.root = user('provision-root', superuser=True)
        self.ordinary = user('provision-existing')
        self.password = 'B7-CityOperator-Strong-482!'
        self.client.force_login(self.root)

    def _create_payload(self, **overrides):
        payload = {
            'create-username': 'new-city-operator',
            'create-email': 'new-city-operator@example.com',
            'create-password1': self.password,
            'create-password2': self.password,
            'create-city': self.city_a.pk,
        }
        payload.update(overrides)
        return payload

    def test_superuser_creates_ordinary_operator_and_operator_can_login_to_city_portal(self):
        response = self.client.post(reverse('rating_operator_create'), self._create_payload())
        self.assertRedirects(response, reverse('admin_users'))
        account = get_user_model().objects.get(username='new-city-operator')
        self.assertTrue(account.is_active)
        self.assertFalse(account.is_staff)
        self.assertFalse(account.is_superuser)
        self.assertTrue(account.check_password(self.password))
        self.assertTrue(
            CityRatingAccess.objects.filter(
                user=account, city=self.city_a, is_active=True
            ).exists()
        )

        self.client.logout()
        protected = self.client.get(reverse('rating_admin:team_list'))
        self.assertEqual(protected.status_code, 302)
        login_url = protected.url
        self.assertIn('next=/rating-admin/', login_url)
        logged_in = self.client.post(
            login_url,
            {'login': account.username, 'password': self.password},
        )
        self.assertRedirects(
            logged_in,
            reverse('rating_admin:team_list'),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.get(reverse('rating_admin:team_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin_users')).status_code, 302)

    def test_admin_entry_routes_city_operator_to_city_portal_after_login(self):
        CityRatingAccess.objects.create(user=self.ordinary, city=self.city_a)
        self.client.logout()

        protected = self.client.get(reverse('admin'))
        self.assertRedirects(
            protected,
            '{}?next={}'.format(reverse('account_login'), reverse('admin')),
            fetch_redirect_response=False,
        )
        logged_in = self.client.post(
            protected.url,
            {'login': self.ordinary.username, 'password': 'test-password'},
        )
        self.assertRedirects(logged_in, reverse('admin'), fetch_redirect_response=False)
        self.assertRedirects(
            self.client.get(reverse('admin')),
            reverse('rating_admin:team_list'),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.get(reverse('rating_admin:team_list')).status_code, 200)

    def test_admin_entry_denies_user_without_active_city_access(self):
        self.client.force_login(self.ordinary)
        self.assertEqual(self.client.get(reverse('admin')).status_code, 302)

        access = CityRatingAccess.objects.create(user=self.ordinary, city=self.city_a)
        access.is_active = False
        access.save(update_fields=('is_active',))
        self.assertEqual(self.client.get(reverse('admin')).status_code, 302)

    def test_password_and_city_validation_leave_no_partial_account(self):
        weak = self.client.post(
            reverse('rating_operator_create'),
            self._create_payload(
                **{
                    'create-username': 'weak-city-operator',
                    'create-password1': '123',
                    'create-password2': '123',
                }
            ),
        )
        self.assertEqual(weak.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='weak-city-operator').exists())

        foreign = self.client.post(
            reverse('rating_operator_create'),
            self._create_payload(**{'create-username': 'bad-city-operator', 'create-city': 999999}),
        )
        self.assertEqual(foreign.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='bad-city-operator').exists())

    def test_create_rolls_back_user_when_access_creation_fails(self):
        with mock.patch(
            'rating.services.CityRatingAccess.objects.create',
            side_effect=IntegrityError('forced access failure'),
        ):
            with self.assertRaises(IntegrityError):
                create_city_operator(
                    actor=self.root,
                    username='rolled-back-operator',
                    email='',
                    password=self.password,
                    city=self.city_a,
                )
        self.assertFalse(get_user_model().objects.filter(username='rolled-back-operator').exists())

    def test_grant_duplicate_revoke_and_regrant_preserve_one_audit_row(self):
        grant_url = reverse('rating_access_grant')
        payload = {'user': self.ordinary.pk, 'city': self.city_a.pk}
        self.assertRedirects(self.client.post(grant_url, payload), reverse('admin_users'))
        self.assertRedirects(self.client.post(grant_url, payload), reverse('admin_users'))
        access = CityRatingAccess.objects.get(user=self.ordinary, city=self.city_a)
        self.assertTrue(access.is_active)
        self.assertEqual(
            CityRatingAccess.objects.filter(user=self.ordinary, city=self.city_a).count(), 1
        )

        revoke_url = reverse('rating_access_revoke', args=[access.pk])
        self.assertRedirects(self.client.post(revoke_url), reverse('admin_users'))
        access.refresh_from_db()
        self.assertFalse(access.is_active)
        self.assertRedirects(self.client.post(grant_url, payload), reverse('admin_users'))
        access.refresh_from_db()
        self.assertTrue(access.is_active)
        self.assertEqual(
            CityRatingAccess.objects.filter(user=self.ordinary, city=self.city_a).count(), 1
        )

    def test_invalid_or_privileged_target_is_rejected_without_access(self):
        grant_url = reverse('rating_access_grant')
        invalid_city = self.client.post(
            grant_url, {'user': self.ordinary.pk, 'city': 999999}
        )
        self.assertEqual(invalid_city.status_code, 400)
        self.assertFalse(CityRatingAccess.objects.filter(user=self.ordinary).exists())

        privileged = self.client.post(
            grant_url, {'user': self.root.pk, 'city': self.city_b.pk}
        )
        self.assertEqual(privileged.status_code, 400)
        self.assertFalse(
            CityRatingAccess.objects.filter(user=self.root, city=self.city_b).exists()
        )

    def test_operator_cannot_provision_and_post_endpoints_require_csrf(self):
        self.client.force_login(self.ordinary)
        for url, payload in (
            (reverse('rating_operator_create'), self._create_payload()),
            (reverse('rating_access_grant'), {'user': self.ordinary.pk, 'city': self.city_a.pk}),
        ):
            self.assertEqual(self.client.post(url, payload).status_code, 302)
        self.assertFalse(get_user_model().objects.filter(username='new-city-operator').exists())
        self.assertFalse(CityRatingAccess.objects.filter(user=self.ordinary).exists())

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.root)
        self.assertEqual(
            csrf_client.post(reverse('rating_operator_create'), self._create_payload()).status_code,
            403,
        )
        self.assertFalse(get_user_model().objects.filter(username='new-city-operator').exists())

    def test_state_changes_reject_get_and_operator_delete_is_audited_by_revoke(self):
        CityRatingAccess.objects.create(user=self.ordinary, city=self.city_a)
        access = CityRatingAccess.objects.get(user=self.ordinary, city=self.city_a)
        self.assertEqual(self.client.get(reverse('rating_operator_create')).status_code, 405)
        self.assertEqual(self.client.get(reverse('rating_access_grant')).status_code, 405)
        self.assertEqual(
            self.client.get(reverse('rating_access_revoke', args=[access.pk])).status_code, 405
        )
        self.assertEqual(
            self.client.get(reverse('users_delete', args=[self.ordinary.pk])).status_code, 405
        )
        self.assertEqual(
            self.client.post(reverse('users_delete', args=[self.ordinary.pk])).status_code, 400
        )
        self.assertTrue(get_user_model().objects.filter(pk=self.ordinary.pk).exists())

    def test_city_portal_exposes_city_aware_public_rating_url(self):
        CityRatingAccess.objects.create(user=self.ordinary, city=self.city_a)
        self.client.force_login(self.ordinary)
        local = self.client.get(
            reverse('rating_admin:team_list'), HTTP_HOST='localhost'
        )
        self.assertEqual(
            local.context['public_rating_url'],
            '/rating/?city={}'.format(self.city_a.slug),
        )
        hosted = self.client.get(reverse('rating_admin:team_list'), HTTP_HOST='testserver')
        self.assertEqual(
            hosted.context['public_rating_url'],
            'https://{}.golovolomka.fun/rating/'.format(self.city_a.slug),
        )
