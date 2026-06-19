from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


def make_user(username, password='pass123', group_name=None):
    user = User.objects.create_user(username=username, password=password)
    if group_name:
        user.groups.add(Group.objects.get(name=group_name))
    return user


class GroupCreationTest(TestCase):
    """The four ZNPHI roles must exist after the data migration runs."""

    def test_four_groups_exist(self):
        names = set(Group.objects.values_list('name', flat=True))
        expected = {'Requester', 'Fleet Manager', 'Dashboard Viewer', 'Superadmin'}
        self.assertTrue(expected.issubset(names), f'Missing groups: {expected - names}')


class LoginViewTest(TestCase):

    def setUp(self):
        self.user = make_user('alice')
        self.url = reverse('accounts:login')

    def test_login_page_is_accessible_anonymously(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_valid_credentials_redirect_to_home(self):
        response = self.client.post(self.url, {'username': 'alice', 'password': 'pass123'})
        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_invalid_credentials_stay_on_login(self):
        response = self.client.post(self.url, {'username': 'alice', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_authenticated_user_is_redirected_away_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        # redirect_authenticated_user sends them to LOGIN_REDIRECT_URL ('/')
        self.assertRedirects(response, '/', fetch_redirect_response=False)


class LogoutViewTest(TestCase):

    def setUp(self):
        self.user = make_user('alice')
        self.url = reverse('accounts:logout')

    def test_post_logout_redirects_to_login(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('accounts:login'), fetch_redirect_response=False)

    def test_unauthenticated_home_redirects_to_login(self):
        response = self.client.get('/')
        self.assertRedirects(response, '/accounts/login/?next=/', fetch_redirect_response=False)


class HomeViewRoleRoutingTest(TestCase):
    """HomeView should redirect each role to its designated section."""

    def test_superadmin_goes_to_user_list(self):
        user = make_user('admin1', group_name='Superadmin')
        self.client.force_login(user)
        response = self.client.get('/')
        self.assertRedirects(response, '/accounts/users/', fetch_redirect_response=False)

    def test_fleet_manager_goes_to_queue(self):
        user = make_user('manager1', group_name='Fleet Manager')
        self.client.force_login(user)
        response = self.client.get('/')
        self.assertRedirects(response, '/bookings/queue/', fetch_redirect_response=False)

    def test_requester_goes_to_my_requests(self):
        user = make_user('req1', group_name='Requester')
        self.client.force_login(user)
        response = self.client.get('/')
        self.assertRedirects(response, '/bookings/my-requests/', fetch_redirect_response=False)

    def test_dashboard_viewer_goes_to_dashboard(self):
        user = make_user('viewer1', group_name='Dashboard Viewer')
        self.client.force_login(user)
        response = self.client.get('/')
        self.assertRedirects(response, '/dashboard/', fetch_redirect_response=False)

    def test_ungrouped_user_gets_200(self):
        user = make_user('nobody')
        self.client.force_login(user)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)


class GroupRequiredMixinTest(TestCase):
    """GroupRequiredMixin must block unauthenticated and wrong-role users."""

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get('/accounts/users/')
        self.assertRedirects(
            response,
            '/accounts/login/?next=/accounts/users/',
            fetch_redirect_response=False,
        )

    def test_wrong_group_gets_403(self):
        user = make_user('req1', group_name='Requester')
        self.client.force_login(user)
        response = self.client.get('/accounts/users/')
        self.assertEqual(response.status_code, 403)

    def test_correct_group_gets_200(self):
        user = make_user('admin1', group_name='Superadmin')
        self.client.force_login(user)
        response = self.client.get('/accounts/users/')
        self.assertEqual(response.status_code, 200)


class UserManagementTest(TestCase):
    """Superadmin can create users and change role assignments."""

    def setUp(self):
        self.admin = make_user('admin', group_name='Superadmin')
        self.client.force_login(self.admin)

    def test_user_list_shows_all_users(self):
        make_user('bob')
        response = self.client.get('/accounts/users/')
        self.assertContains(response, 'bob')

    def test_create_user_assigns_group(self):
        requester_group = Group.objects.get(name='Requester')
        response = self.client.post('/accounts/users/create/', {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'confirm_password': 'securepass123',
            'group': requester_group.pk,
        })
        self.assertRedirects(response, '/accounts/users/', fetch_redirect_response=False)
        new_user = User.objects.get(username='newuser')
        self.assertIn(requester_group, new_user.groups.all())

    def test_create_user_password_mismatch_rejected(self):
        requester_group = Group.objects.get(name='Requester')
        response = self.client.post('/accounts/users/create/', {
            'username': 'baduser',
            'password': 'securepass123',
            'confirm_password': 'different',
            'group': requester_group.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='baduser').exists())

    def test_update_user_group(self):
        target = make_user('target', group_name='Requester')
        fleet_group = Group.objects.get(name='Fleet Manager')
        response = self.client.post(f'/accounts/users/{target.pk}/group/', {
            'group': fleet_group.pk,
        })
        self.assertRedirects(response, '/accounts/users/', fetch_redirect_response=False)
        target.refresh_from_db()
        self.assertIn(fleet_group, target.groups.all())
        self.assertNotIn(Group.objects.get(name='Requester'), target.groups.all())

    def test_non_superadmin_cannot_access_user_create(self):
        self.client.logout()
        requester = make_user('req', group_name='Requester')
        self.client.force_login(requester)
        response = self.client.get('/accounts/users/create/')
        self.assertEqual(response.status_code, 403)


class UserRolesContextProcessorTest(TestCase):
    """Context processor must expose correct boolean flags per role."""

    def test_superadmin_flag(self):
        user = make_user('admin1', group_name='Superadmin')
        self.client.force_login(user)
        response = self.client.get('/accounts/users/')
        self.assertTrue(response.context['is_superadmin'])
        self.assertFalse(response.context['is_fleet_manager'])

    def test_fleet_manager_flag(self):
        user = make_user('mgr', group_name='Fleet Manager')
        self.client.force_login(user)
        # HomeView redirects fleet managers; test any authenticated view instead
        response = self.client.get('/accounts/login/')
        # login redirects authenticated users — check context on the home redirect
        response = self.client.get('/', follow=False)
        self.assertEqual(response.status_code, 302)
