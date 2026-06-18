import datetime
from django.test import TestCase
from .models import Province, District, Department, TransportRequest, TripAssignment
from fleet.models import Vehicle, Driver


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
