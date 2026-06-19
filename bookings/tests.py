import datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from .models import Province, District, Department, TransportRequest, TripAssignment
from .views import get_overlapping_trips
from fleet.models import Vehicle, Driver

User = get_user_model()


def make_user(username='requester', group_name='Requester'):
    user = User.objects.create_user(username=username, password='testpass123')
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


def make_province(name='Lusaka'):
    return Province.objects.get_or_create(name=name)[0]


def make_district(province=None, name='Lusaka'):
    if province is None:
        province = make_province()
    return District.objects.get_or_create(name=name, province=province)[0]


def make_department(name='Surveillance and Disease Intelligence'):
    return Department.objects.get_or_create(name=name)[0]


def make_request(province=None, district=None, department=None, **kwargs):
    if province is None:
        province = make_province()
    if district is None:
        district = make_district(province=province)
    if department is None:
        department = make_department()
    defaults = dict(
        requester_name='Alice Banda',
        department=department,
        position='Officer',
        programme_activity='Field visit',
        period_from=datetime.date(2026, 7, 1),
        period_to=datetime.date(2026, 7, 5),
        province=province,
        district=district,
        destination='Lusaka Central',
        num_vehicles=1,
        num_drivers=1,
        num_passengers=3,
    )
    defaults.update(kwargs)
    return TransportRequest.objects.create(**defaults)


def make_vehicle(license_plate='ZM 001 AB'):
    return Vehicle.objects.create(
        make='Toyota', model='Hilux', year=2020,
        license_plate=license_plate, vehicle_type='Hilux',
        current_mileage=50000, seating_capacity=5,
        fuel_type='Diesel',
    )


def make_driver(name='Driver 1'):
    return Driver.objects.create(name=name)


class ProvinceModelTest(TestCase):

    def test_str_representation(self):
        p = make_province('Eastern')
        self.assertEqual(str(p), 'Eastern')

    def test_name_unique(self):
        Province.objects.create(name='Central')
        with self.assertRaises(Exception):
            Province.objects.create(name='Central')

    def test_ordering_by_name(self):
        Province.objects.create(name='Western')
        Province.objects.create(name='Central')
        names = list(Province.objects.values_list('name', flat=True))
        self.assertEqual(names, sorted(names))


class DistrictModelTest(TestCase):

    def test_str_representation(self):
        d = make_district(name='Chipata')
        self.assertEqual(str(d), 'Chipata')

    def test_district_belongs_to_province(self):
        province = make_province('Eastern')
        district = make_district(province=province, name='Chipata')
        self.assertEqual(district.province, province)

    def test_same_name_allowed_in_different_provinces(self):
        p1 = Province.objects.create(name='Province A')
        p2 = Province.objects.create(name='Province B')
        District.objects.create(name='Shared Name', province=p1)
        # Should not raise — same name is only unique per province.
        District.objects.create(name='Shared Name', province=p2)

    def test_duplicate_name_in_same_province_raises(self):
        province = make_province()
        District.objects.create(name='Duplicate', province=province)
        with self.assertRaises(Exception):
            District.objects.create(name='Duplicate', province=province)

    def test_districts_accessible_via_province_reverse(self):
        province = make_province('Copperbelt')
        District.objects.create(name='Ndola', province=province)
        District.objects.create(name='Kitwe', province=province)
        self.assertEqual(province.districts.count(), 2)

    def test_ordering_by_name(self):
        province = make_province()
        District.objects.create(name='Ndola', province=province)
        District.objects.create(name='Kitwe', province=province)
        names = list(province.districts.values_list('name', flat=True))
        self.assertEqual(names, sorted(names))


class DepartmentModelTest(TestCase):

    def test_str_representation(self):
        d = Department.objects.create(name='Emergency Preparedness and Response')
        self.assertEqual(str(d), 'Emergency Preparedness and Response')

    def test_name_unique(self):
        Department.objects.create(name='NPHLS')
        with self.assertRaises(Exception):
            Department.objects.create(name='NPHLS')


class TransportRequestModelTest(TestCase):

    def test_str_representation(self):
        req = make_request()
        self.assertIn('Alice Banda', str(req))
        self.assertIn('Submitted', str(req))

    def test_default_status_is_submitted(self):
        req = make_request()
        self.assertEqual(req.status, 'Submitted')

    def test_default_emergency_flag_false(self):
        req = make_request()
        self.assertFalse(req.is_emergency)

    def test_date_of_request_auto_set(self):
        req = make_request()
        self.assertEqual(req.date_of_request, datetime.date.today())

    def test_is_late_booking_true_when_under_two_weeks(self):
        soon = datetime.date.today() + datetime.timedelta(days=7)
        req = make_request(period_from=soon, period_to=soon + datetime.timedelta(days=2))
        self.assertTrue(req.is_late_booking)

    def test_is_late_booking_false_when_over_two_weeks(self):
        far = datetime.date.today() + datetime.timedelta(weeks=3)
        req = make_request(period_from=far, period_to=far + datetime.timedelta(days=5))
        self.assertFalse(req.is_late_booking)

    def test_department_relationship(self):
        dept = make_department('Field Epidemiology Program')
        req = make_request(department=dept)
        self.assertEqual(req.department.name, 'Field Epidemiology Program')

    def test_province_and_district_relationship(self):
        province = Province.objects.create(name='Northern')
        district = District.objects.create(name='Kasama', province=province)
        req = make_request(province=province, district=district)
        self.assertEqual(req.province.name, 'Northern')
        self.assertEqual(req.district.name, 'Kasama')

    def test_coordination_fields_default(self):
        req = make_request()
        self.assertFalse(req.coordination_acknowledged)
        self.assertEqual(req.coordination_note, '')

    def test_ordering_newest_first(self):
        # Two requests created sequentially — second should appear first.
        make_request()
        make_request()
        ids = list(TransportRequest.objects.values_list('id', flat=True))
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_cancel_status_transition(self):
        req = make_request()
        req.status = 'Cancelled'
        req.save()
        req.refresh_from_db()
        self.assertEqual(req.status, 'Cancelled')


class TripAssignmentModelTest(TestCase):

    def setUp(self):
        self.province = make_province()
        self.district = make_district(province=self.province)
        self.request = make_request(province=self.province, district=self.district)
        self.vehicle = make_vehicle()
        self.driver = make_driver()

    def test_str_representation(self):
        ta = TripAssignment.objects.create(
            transport_request=self.request,
            vehicle=self.vehicle,
            driver=self.driver,
        )
        self.assertIn(str(self.vehicle), str(ta))
        self.assertIn(str(self.driver), str(ta))

    def test_multiple_assignments_per_request(self):
        """A single request can have multiple vehicle/driver pairs."""
        vehicle2 = make_vehicle(license_plate='ZM 002 BB')
        driver2 = make_driver(name='Driver 2')

        TripAssignment.objects.create(
            transport_request=self.request, vehicle=self.vehicle, driver=self.driver
        )
        TripAssignment.objects.create(
            transport_request=self.request, vehicle=vehicle2, driver=driver2
        )
        self.assertEqual(self.request.assignments.count(), 2)

    def test_assignment_links_to_vehicle_and_driver(self):
        ta = TripAssignment.objects.create(
            transport_request=self.request, vehicle=self.vehicle, driver=self.driver
        )
        self.assertEqual(ta.vehicle, self.vehicle)
        self.assertEqual(ta.driver, self.driver)

    def test_assignments_accessible_from_vehicle(self):
        TripAssignment.objects.create(
            transport_request=self.request, vehicle=self.vehicle, driver=self.driver
        )
        self.assertEqual(self.vehicle.assignments.count(), 1)

    def test_assignments_accessible_from_driver(self):
        TripAssignment.objects.create(
            transport_request=self.request, vehicle=self.vehicle, driver=self.driver
        )
        self.assertEqual(self.driver.assignments.count(), 1)


# ---------------------------------------------------------------------------
# Phase 3: Form, views, and coordination nudge tests
# ---------------------------------------------------------------------------

def _valid_post_data(province, district, department):
    """Return a minimal valid POST dict for the transport request form."""
    future = datetime.date.today() + datetime.timedelta(weeks=4)
    return {
        'requester_name': 'Alice Banda',
        'department': str(department.pk),
        'position': 'Officer',
        'programme_activity': 'Field Visit',
        'period_from': future.strftime('%Y-%m-%d'),
        'period_to': (future + datetime.timedelta(days=3)).strftime('%Y-%m-%d'),
        'province': str(province.pk),
        'district': str(district.pk),
        'destination': 'Lusaka Central',
        'num_vehicles': '1',
        'num_drivers': '1',
        'num_passengers': '3',
    }


class TransportRequestFormTest(TestCase):

    def setUp(self):
        self.province = make_province()
        self.district = make_district(province=self.province)
        self.department = make_department()

    def test_valid_form_saves(self):
        from .forms import TransportRequestForm
        data = _valid_post_data(self.province, self.district, self.department)
        form = TransportRequestForm(data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_end_before_start_invalid(self):
        from .forms import TransportRequestForm
        data = _valid_post_data(self.province, self.district, self.department)
        data['period_to'] = (datetime.date.today() + datetime.timedelta(weeks=2)).strftime('%Y-%m-%d')
        data['period_from'] = (datetime.date.today() + datetime.timedelta(weeks=3)).strftime('%Y-%m-%d')
        form = TransportRequestForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('End date must be on or after the start date', str(form.errors))

    def test_district_wrong_province_invalid(self):
        from .forms import TransportRequestForm
        other_province = Province.objects.create(name='Southern')
        other_district = District.objects.create(name='Choma', province=other_province)
        data = _valid_post_data(self.province, self.district, self.department)
        # Province is Lusaka but district belongs to Southern
        data['province'] = str(self.province.pk)
        data['district'] = str(other_district.pk)
        form = TransportRequestForm(data)
        self.assertFalse(form.is_valid())

    def test_district_queryset_filtered_by_province_in_data(self):
        from .forms import TransportRequestForm
        data = _valid_post_data(self.province, self.district, self.department)
        form = TransportRequestForm(data)
        self.assertIn(self.district, form.fields['district'].queryset)

    def test_missing_required_field_invalid(self):
        from .forms import TransportRequestForm
        data = _valid_post_data(self.province, self.district, self.department)
        del data['requester_name']
        form = TransportRequestForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('requester_name', form.errors)


class DistrictOptionsViewTest(TestCase):

    def setUp(self):
        self.province = make_province('Lusaka')
        self.district = make_district(province=self.province, name='Lusaka')

    def test_returns_districts_for_province(self):
        url = reverse('bookings:district_options')
        response = self.client.get(url, {'province': str(self.province.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lusaka')

    def test_empty_with_no_province(self):
        url = reverse('bookings:district_options')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Lusaka')

    def test_empty_with_invalid_province_id(self):
        url = reverse('bookings:district_options')
        response = self.client.get(url, {'province': 'abc'})
        self.assertEqual(response.status_code, 200)


class TransportRequestCreateViewTest(TestCase):

    def setUp(self):
        self.province = make_province()
        self.district = make_district(province=self.province)
        self.department = make_department()
        self.user = make_user()
        self.client.login(username='requester', password='testpass123')
        self.url = reverse('bookings:request_create')

    def test_get_renders_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'bookings/request_form.html')

    def test_unauthenticated_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f'/accounts/login/?next={self.url}', fetch_redirect_response=False)

    def test_valid_post_creates_request_no_overlap(self):
        data = _valid_post_data(self.province, self.district, self.department)
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse('bookings:my_requests'), fetch_redirect_response=False)
        self.assertEqual(TransportRequest.objects.count(), 1)
        req = TransportRequest.objects.first()
        self.assertEqual(req.submitted_by, self.user)
        self.assertEqual(req.status, 'Submitted')

    def test_invalid_post_rerenders_form(self):
        data = _valid_post_data(self.province, self.district, self.department)
        data['requester_name'] = ''
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'bookings/request_form.html')
        self.assertEqual(TransportRequest.objects.count(), 0)

    def test_late_booking_shows_warning_message(self):
        data = _valid_post_data(self.province, self.district, self.department)
        soon = datetime.date.today() + datetime.timedelta(days=5)
        data['period_from'] = soon.strftime('%Y-%m-%d')
        data['period_to'] = (soon + datetime.timedelta(days=2)).strftime('%Y-%m-%d')
        response = self.client.post(self.url, data, follow=True)
        messages = list(response.context['messages'])
        self.assertTrue(any('2 weeks' in str(m) or 'late' in str(m).lower() for m in messages))

    def test_overlap_redirects_to_nudge(self):
        # Create an existing request to the same district in the same timeframe.
        future = datetime.date.today() + datetime.timedelta(weeks=4)
        make_request(
            province=self.province, district=self.district, department=self.department,
            period_from=future, period_to=future + datetime.timedelta(days=3),
            status='Approved',
        )
        data = _valid_post_data(self.province, self.district, self.department)
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse('bookings:coordination_nudge'), fetch_redirect_response=False)
        self.assertIn('pending_request_data', self.client.session)


class CoordinationNudgeViewTest(TestCase):

    def setUp(self):
        self.province = make_province()
        self.district = make_district(province=self.province)
        self.department = make_department()
        self.user = make_user()
        self.client.login(username='requester', password='testpass123')
        self.url = reverse('bookings:coordination_nudge')
        # Seed the session with pending request data, as the create view would.
        future = datetime.date.today() + datetime.timedelta(weeks=4)
        self.raw_data = {
            'requester_name': 'Alice Banda',
            'department': str(self.department.pk),
            'position': 'Officer',
            'programme_activity': 'Field Visit',
            'period_from': future.strftime('%Y-%m-%d'),
            'period_to': (future + datetime.timedelta(days=3)).strftime('%Y-%m-%d'),
            'province': str(self.province.pk),
            'district': str(self.district.pk),
            'destination': 'Lusaka Central',
            'num_vehicles': '1',
            'num_drivers': '1',
            'num_passengers': '3',
        }
        self.overlap = make_request(
            province=self.province, district=self.district, department=self.department,
            period_from=future, period_to=future + datetime.timedelta(days=3),
            status='Approved',
        )

    def _seed_session(self):
        session = self.client.session
        session['pending_request_data'] = self.raw_data
        session['overlapping_trip_ids'] = [self.overlap.pk]
        session['pending_request_is_late'] = False
        session.save()

    def test_get_without_session_redirects_to_form(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('bookings:request_create'), fetch_redirect_response=False)

    def test_get_with_session_renders_nudge_page(self):
        self._seed_session()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'bookings/coordination_nudge.html')

    def test_post_without_acknowledgment_shows_error(self):
        self._seed_session()
        response = self.client.post(self.url, {'coordination_note': 'needed'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TransportRequest.objects.exclude(pk=self.overlap.pk).count(), 0)

    def test_post_with_acknowledgment_creates_request(self):
        self._seed_session()
        response = self.client.post(self.url, {
            'acknowledged': 'on',
            'coordination_note': 'Different programme requirement.',
        })
        self.assertRedirects(response, reverse('bookings:my_requests'), fetch_redirect_response=False)
        new_requests = TransportRequest.objects.exclude(pk=self.overlap.pk)
        self.assertEqual(new_requests.count(), 1)
        req = new_requests.first()
        self.assertTrue(req.coordination_acknowledged)
        self.assertEqual(req.coordination_note, 'Different programme requirement.')

    def test_session_cleared_after_save(self):
        self._seed_session()
        self.client.post(self.url, {'acknowledged': 'on', 'coordination_note': ''})
        session = self.client.session
        self.assertNotIn('pending_request_data', session)


class GetOverlappingTripsTest(TestCase):

    def setUp(self):
        self.province = make_province()
        self.district = make_district(province=self.province)
        self.department = make_department()
        self.other_district = make_district(province=self.province, name='Kafue')
        self.future = datetime.date.today() + datetime.timedelta(weeks=4)

    def test_same_district_within_window_triggers_nudge(self):
        make_request(
            province=self.province, district=self.district,
            period_from=self.future, period_to=self.future + datetime.timedelta(days=2),
            status='Approved',
        )
        result = get_overlapping_trips(self.district, self.future, self.future + datetime.timedelta(days=2))
        self.assertEqual(result.count(), 1)

    def test_different_district_does_not_trigger(self):
        make_request(
            province=self.province, district=self.other_district,
            period_from=self.future, period_to=self.future + datetime.timedelta(days=2),
            status='Approved',
        )
        result = get_overlapping_trips(self.district, self.future, self.future + datetime.timedelta(days=2))
        self.assertEqual(result.count(), 0)

    def test_completed_request_does_not_trigger(self):
        make_request(
            province=self.province, district=self.district,
            period_from=self.future, period_to=self.future + datetime.timedelta(days=2),
            status='Completed',
        )
        result = get_overlapping_trips(self.district, self.future, self.future + datetime.timedelta(days=2))
        self.assertEqual(result.count(), 0)

    def test_far_future_trip_does_not_trigger(self):
        # A trip 30 days away should not trigger the 7-day window nudge.
        far = self.future + datetime.timedelta(days=30)
        make_request(
            province=self.province, district=self.district,
            period_from=far, period_to=far + datetime.timedelta(days=2),
            status='Approved',
        )
        result = get_overlapping_trips(self.district, self.future, self.future + datetime.timedelta(days=2))
        self.assertEqual(result.count(), 0)

    def test_trip_just_inside_window_triggers(self):
        # A trip starting exactly 7 days after our end date — just inside the window.
        nearby = self.future + datetime.timedelta(days=3 + 7)  # period_to + 3 days + window
        make_request(
            province=self.province, district=self.district,
            period_from=nearby, period_to=nearby + datetime.timedelta(days=1),
            status='Submitted',
        )
        result = get_overlapping_trips(self.district, self.future, self.future + datetime.timedelta(days=3))
        self.assertEqual(result.count(), 1)


class MyRequestsViewTest(TestCase):

    def setUp(self):
        self.province = make_province()
        self.district = make_district(province=self.province)
        self.department = make_department()
        self.user = make_user()
        self.other_user = make_user(username='other', group_name='Requester')
        self.url = reverse('bookings:my_requests')

    def test_unauthenticated_redirects(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f'/accounts/login/?next={self.url}', fetch_redirect_response=False)

    def test_shows_only_own_requests(self):
        own = make_request(province=self.province, district=self.district, submitted_by=self.user)
        make_request(province=self.province, district=self.district, submitted_by=self.other_user)
        self.client.login(username='requester', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        requests_in_context = list(response.context['requests'])
        self.assertEqual(len(requests_in_context), 1)
        self.assertEqual(requests_in_context[0], own)

    def test_empty_state_rendered(self):
        self.client.login(username='requester', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No requests yet')


class TransportRequestDetailViewTest(TestCase):

    def setUp(self):
        self.province = make_province()
        self.district = make_district(province=self.province)
        self.user = make_user()
        self.other_user = make_user(username='other', group_name='Requester')
        self.req = make_request(
            province=self.province, district=self.district,
            submitted_by=self.user,
        )

    def test_owner_can_view(self):
        self.client.login(username='requester', password='testpass123')
        url = reverse('bookings:request_detail', args=[self.req.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_other_user_gets_404(self):
        self.client.login(username='other', password='testpass123')
        url = reverse('bookings:request_detail', args=[self.req.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_fleet_manager_can_view_any(self):
        manager = make_user(username='manager', group_name='Fleet Manager')
        self.client.login(username='manager', password='testpass123')
        url = reverse('bookings:request_detail', args=[self.req.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class TransportRequestCancelViewTest(TestCase):

    def setUp(self):
        self.province = make_province()
        self.district = make_district(province=self.province)
        self.user = make_user()
        self.req = make_request(
            province=self.province, district=self.district,
            submitted_by=self.user,
        )
        self.client.login(username='requester', password='testpass123')

    def _cancel(self):
        return self.client.post(reverse('bookings:request_cancel', args=[self.req.pk]))

    def test_cancel_submitted_request(self):
        self._cancel()
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, 'Cancelled')

    def test_cancel_completed_request_rejected(self):
        self.req.status = 'Completed'
        self.req.save()
        self._cancel()
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, 'Completed')

    def test_other_user_cannot_cancel(self):
        other = make_user(username='other2', group_name='Requester')
        self.client.login(username='other2', password='testpass123')
        self.client.post(reverse('bookings:request_cancel', args=[self.req.pk]))
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, 'Submitted')
