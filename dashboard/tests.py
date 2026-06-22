import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from bookings.models import Department, District, Province, TransportRequest, TripAssignment
from dashboard.views import _gantt_block
from fleet.models import Driver, Vehicle

User = get_user_model()

GANTT_URL = reverse('dashboard:gantt')


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def make_user(username, group_name):
    user = User.objects.create_user(username=username, password='pass')
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user


def make_vehicle(plate='ZM TEST 001'):
    return Vehicle.objects.create(
        make='Toyota', model='Hilux', year=2020,
        license_plate=plate,
        vehicle_type='Hilux', current_mileage=10000,
        seating_capacity=5, fuel_type='Diesel',
        status='Available', maintenance_interval_km=5000,
    )


def make_driver(name='Test Driver'):
    return Driver.objects.create(name=name, status='Available')


def make_request(province, district, period_from, period_to, status='Approved', department=None):
    if department is None:
        department, _ = Department.objects.get_or_create(name='Test Dept')
    return TransportRequest.objects.create(
        requester_name='Test User',
        department=department,
        position='Officer',
        programme_activity='Activity',
        destination='Destination',
        province=province,
        district=district,
        period_from=period_from,
        period_to=period_to,
        num_vehicles=1,
        num_drivers=1,
        num_passengers=2,
        status=status,
    )


def make_assignment(transport_request, vehicle, driver):
    return TripAssignment.objects.create(
        transport_request=transport_request,
        vehicle=vehicle,
        driver=driver,
    )


# ---------------------------------------------------------------------------
# _gantt_block unit tests
# ---------------------------------------------------------------------------

class GanttBlockTest(TestCase):
    def setUp(self):
        self.window_start = datetime.date(2026, 6, 22)

    def test_block_spanning_full_window(self):
        block = _gantt_block(
            datetime.date(2026, 6, 22), datetime.date(2026, 7, 5),
            self.window_start, 'Approved', 1, 'Lusaka',
        )
        self.assertEqual(block['left_pct'], 0.0)
        self.assertAlmostEqual(block['width_pct'], 100.0, places=1)

    def test_block_starts_at_day_zero(self):
        # Single-day trip on the first day of the window.
        block = _gantt_block(
            datetime.date(2026, 6, 22), datetime.date(2026, 6, 22),
            self.window_start, 'Approved', 1, 'Lusaka',
        )
        self.assertEqual(block['left_pct'], 0.0)
        self.assertAlmostEqual(block['width_pct'], 100 / 14, places=1)

    def test_block_clamped_when_starts_before_window(self):
        # Trip started 3 days before window
        block = _gantt_block(
            datetime.date(2026, 6, 19), datetime.date(2026, 6, 24),
            self.window_start, 'In Progress', 2, 'Ndola',
        )
        self.assertEqual(block['left_pct'], 0.0)
        # Ends on day 2 of window (6/24 - 6/22 = 2, so end_day = 3)
        self.assertGreater(block['width_pct'], 0)

    def test_block_clamped_when_ends_after_window(self):
        # Trip ends 3 days after window
        block = _gantt_block(
            datetime.date(2026, 6, 30), datetime.date(2026, 7, 10),
            self.window_start, 'Approved', 3, 'Kitwe',
        )
        self.assertLess(block['left_pct'], 100.0)
        total = block['left_pct'] + block['width_pct']
        self.assertAlmostEqual(total, 100.0, places=1)

    def test_block_in_middle_of_window(self):
        # Days 2-4 (0-indexed) in the window
        block = _gantt_block(
            datetime.date(2026, 6, 24), datetime.date(2026, 6, 26),
            self.window_start, 'Approved', 4, 'Kabwe',
        )
        expected_left = 2 / 14 * 100
        expected_width = 3 / 14 * 100  # 3 days inclusive
        self.assertAlmostEqual(block['left_pct'], expected_left, places=1)
        self.assertAlmostEqual(block['width_pct'], expected_width, places=1)


# ---------------------------------------------------------------------------
# Access control tests
# ---------------------------------------------------------------------------

class GanttAccessTest(TestCase):
    def test_fleet_manager_can_access(self):
        user = make_user('fm', 'Fleet Manager')
        self.client.force_login(user)
        response = self.client.get(GANTT_URL)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_viewer_can_access(self):
        user = make_user('dv', 'Dashboard Viewer')
        self.client.force_login(user)
        response = self.client.get(GANTT_URL)
        self.assertEqual(response.status_code, 200)

    def test_superadmin_can_access(self):
        user = make_user('sa', 'Superadmin')
        self.client.force_login(user)
        response = self.client.get(GANTT_URL)
        self.assertEqual(response.status_code, 200)

    def test_requester_cannot_access(self):
        user = make_user('req', 'Requester')
        self.client.force_login(user)
        response = self.client.get(GANTT_URL)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(GANTT_URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])


# ---------------------------------------------------------------------------
# Data query and filtering tests
# ---------------------------------------------------------------------------

class GanttQueryTest(TestCase):
    def setUp(self):
        self.fm = make_user('fm', 'Fleet Manager')
        self.client.force_login(self.fm)

        self.province_lsk = Province.objects.create(name='Lusaka')
        self.province_cp = Province.objects.create(name='Copperbelt')
        self.district_lsk = District.objects.create(name='Lusaka', province=self.province_lsk)
        self.district_kb = District.objects.create(name='Kitwe', province=self.province_cp)

        self.vehicle = make_vehicle('ZM-001')
        self.driver = make_driver()

        # Window: 2026-07-01 to 2026-07-14
        self.window_from = '2026-07-01'
        self.window_start = datetime.date(2026, 7, 1)

    def _get(self, **params):
        params.setdefault('from', self.window_from)
        return self.client.get(GANTT_URL, params)

    def test_approved_assignment_appears_in_vehicle_row(self):
        req = make_request(self.province_lsk, self.district_lsk,
                           datetime.date(2026, 7, 3), datetime.date(2026, 7, 5), status='Approved')
        make_assignment(req, self.vehicle, self.driver)

        response = self._get()
        rows = response.context['vehicle_rows']
        vehicle_row = next(r for r in rows if r['vehicle'].pk == self.vehicle.pk)
        self.assertEqual(len(vehicle_row['bookings']), 1)
        self.assertEqual(vehicle_row['bookings'][0]['status'], 'Approved')

    def test_in_progress_assignment_appears_in_vehicle_row(self):
        req = make_request(self.province_lsk, self.district_lsk,
                           datetime.date(2026, 7, 2), datetime.date(2026, 7, 4), status='In Progress')
        make_assignment(req, self.vehicle, self.driver)

        response = self._get()
        rows = response.context['vehicle_rows']
        vehicle_row = next(r for r in rows if r['vehicle'].pk == self.vehicle.pk)
        self.assertEqual(vehicle_row['bookings'][0]['status'], 'In Progress')

    def test_submitted_request_appears_in_pending_blocks(self):
        make_request(self.province_lsk, self.district_lsk,
                     datetime.date(2026, 7, 6), datetime.date(2026, 7, 8), status='Submitted')

        response = self._get()
        self.assertEqual(len(response.context['pending_blocks']), 1)
        self.assertEqual(response.context['pending_blocks'][0]['status'], 'Submitted')

    def test_assignment_outside_window_not_shown(self):
        req = make_request(self.province_lsk, self.district_lsk,
                           datetime.date(2026, 7, 20), datetime.date(2026, 7, 25), status='Approved')
        make_assignment(req, self.vehicle, self.driver)

        response = self._get()
        rows = response.context['vehicle_rows']
        vehicle_row = next(r for r in rows if r['vehicle'].pk == self.vehicle.pk)
        self.assertEqual(len(vehicle_row['bookings']), 0)

    def test_province_filter_excludes_other_provinces(self):
        # Approved trip to Lusaka
        req_lsk = make_request(self.province_lsk, self.district_lsk,
                                datetime.date(2026, 7, 3), datetime.date(2026, 7, 5), status='Approved')
        v2 = make_vehicle('ZM-002')
        d2 = make_driver('Driver B')
        make_assignment(req_lsk, self.vehicle, self.driver)

        # Approved trip to Copperbelt
        req_cb = make_request(self.province_cp, self.district_kb,
                               datetime.date(2026, 7, 3), datetime.date(2026, 7, 5), status='Approved')
        make_assignment(req_cb, v2, d2)

        response = self._get(province=self.province_lsk.pk)

        all_bookings = [b for r in response.context['vehicle_rows'] for b in r['bookings']]
        pks = [b['pk'] for b in all_bookings]

        self.assertIn(req_lsk.pk, pks)
        self.assertNotIn(req_cb.pk, pks)

    def test_province_filter_applies_to_pending_blocks(self):
        make_request(self.province_lsk, self.district_lsk,
                     datetime.date(2026, 7, 6), datetime.date(2026, 7, 8), status='Submitted')
        make_request(self.province_cp, self.district_kb,
                     datetime.date(2026, 7, 6), datetime.date(2026, 7, 8), status='Submitted')

        response = self._get(province=self.province_lsk.pk)
        self.assertEqual(len(response.context['pending_blocks']), 1)
        self.assertEqual(response.context['pending_blocks'][0]['label'], 'Lusaka')

    def test_rejected_request_does_not_appear(self):
        req = make_request(self.province_lsk, self.district_lsk,
                           datetime.date(2026, 7, 3), datetime.date(2026, 7, 5), status='Rejected')
        # Even if there were an assignment, rejected should not show.
        response = self._get()
        all_bookings = [b for r in response.context['vehicle_rows'] for b in r['bookings']]
        self.assertEqual(len(all_bookings), 0)
        self.assertEqual(len(response.context['pending_blocks']), 0)

    def test_all_vehicles_appear_as_rows_regardless_of_bookings(self):
        # Even vehicles with no bookings should have a row.
        response = self._get()
        rows = response.context['vehicle_rows']
        row_vehicle_pks = {r['vehicle'].pk for r in rows}
        self.assertIn(self.vehicle.pk, row_vehicle_pks)

    def test_dashboard_viewer_cannot_interact(self):
        dv = make_user('dv', 'Dashboard Viewer')
        self.client.force_login(dv)
        response = self._get()
        self.assertFalse(response.context['can_interact'])

    def test_fleet_manager_can_interact(self):
        response = self._get()
        self.assertTrue(response.context['can_interact'])
