import datetime
from django.test import TestCase
from .models import Vehicle, Driver, FuelRecord, MaintenanceRecord


def make_vehicle(**kwargs):
    defaults = dict(
        make='Toyota',
        model='Hilux',
        year=2020,
        license_plate='ZM 001 AB',
        vehicle_type='Hilux',
        current_mileage=50000,
        seating_capacity=5,
        fuel_type='Diesel',
        status='Available',
        maintenance_interval_km=5000,
    )
    defaults.update(kwargs)
    return Vehicle.objects.create(**defaults)


def make_driver(**kwargs):
    defaults = dict(name='Driver 1', phone='', status='Available')
    defaults.update(kwargs)
    return Driver.objects.create(**defaults)


class VehicleModelTest(TestCase):

    def test_str_representation(self):
        v = make_vehicle()
        self.assertEqual(str(v), '2020 Toyota Hilux (ZM 001 AB)')

    def test_license_plate_unique(self):
        make_vehicle(license_plate='ZM 999 XY')
        with self.assertRaises(Exception):
            make_vehicle(license_plate='ZM 999 XY')

    def test_default_status_is_available(self):
        v = make_vehicle()
        self.assertEqual(v.status, 'Available')

    def test_default_maintenance_interval(self):
        v = make_vehicle()
        self.assertEqual(v.maintenance_interval_km, 5000)

    def test_maintenance_status_green(self):
        v = make_vehicle(current_mileage=50000, maintenance_interval_km=5000,
                         last_service_mileage=46000)
        # km_until_service = (46000 + 5000) - 50000 = 1000 → green
        self.assertEqual(v.maintenance_status, 'green')

    def test_maintenance_status_amber(self):
        v = make_vehicle(current_mileage=50300, maintenance_interval_km=5000,
                         last_service_mileage=46000)
        # km_until_service = 51000 - 50300 = 700... wait, 46000+5000=51000, 51000-50300=700 → green
        # Let's make it tighter: last_service=45600, interval=5000 → next=50600, current=50200 → 400 → amber
        v.last_service_mileage = 45600
        v.current_mileage = 50200
        v.save()
        self.assertEqual(v.maintenance_status, 'amber')

    def test_maintenance_status_red(self):
        v = make_vehicle(current_mileage=55000, maintenance_interval_km=5000,
                         last_service_mileage=49000)
        # km_until_service = (49000 + 5000) - 55000 = -1000 → red
        self.assertEqual(v.maintenance_status, 'red')

    def test_maintenance_status_unknown_when_no_service_record(self):
        v = make_vehicle(last_service_mileage=None)
        self.assertEqual(v.maintenance_status, 'unknown')

    def test_km_until_service_none_without_baseline(self):
        v = make_vehicle(last_service_mileage=None)
        self.assertIsNone(v.km_until_service)

    def test_km_until_service_calculated_correctly(self):
        v = make_vehicle(current_mileage=50000, maintenance_interval_km=5000,
                         last_service_mileage=47000)
        self.assertEqual(v.km_until_service, 2000)

    def test_ordering_by_license_plate(self):
        make_vehicle(license_plate='ZM 002 BB')
        make_vehicle(license_plate='ZM 001 AA')
        plates = list(Vehicle.objects.values_list('license_plate', flat=True))
        self.assertEqual(plates, sorted(plates))


class DriverModelTest(TestCase):

    def test_str_representation(self):
        d = make_driver(name='Driver 5')
        self.assertEqual(str(d), 'Driver 5')

    def test_default_status_is_available(self):
        d = make_driver()
        self.assertEqual(d.status, 'Available')

    def test_phone_optional(self):
        d = Driver.objects.create(name='Driver 2')
        self.assertEqual(d.phone, '')

    def test_ordering_by_name(self):
        make_driver(name='Driver 3')
        make_driver(name='Driver 1')
        names = list(Driver.objects.values_list('name', flat=True))
        self.assertEqual(names, sorted(names))


class FuelRecordModelTest(TestCase):

    def setUp(self):
        self.vehicle = make_vehicle()

    def test_str_representation(self):
        fr = FuelRecord.objects.create(
            vehicle=self.vehicle,
            date=datetime.date(2026, 3, 1),
            liters=50,
            cost_per_liter='2.50',
            total_cost='125.00',
            location='Lusaka',
            mileage_at_fillup=50000,
        )
        self.assertIn('Fuel:', str(fr))
        self.assertIn('50', str(fr))

    def test_notes_optional(self):
        fr = FuelRecord.objects.create(
            vehicle=self.vehicle,
            date=datetime.date(2026, 3, 1),
            liters=40,
            cost_per_liter='2.50',
            total_cost='100.00',
            location='Kabwe',
            mileage_at_fillup=51000,
        )
        self.assertEqual(fr.notes, '')

    def test_ordering_newest_first(self):
        FuelRecord.objects.create(
            vehicle=self.vehicle, date=datetime.date(2026, 1, 1),
            liters=40, cost_per_liter='2.5', total_cost='100',
            location='X', mileage_at_fillup=48000,
        )
        FuelRecord.objects.create(
            vehicle=self.vehicle, date=datetime.date(2026, 3, 1),
            liters=50, cost_per_liter='2.5', total_cost='125',
            location='Y', mileage_at_fillup=50000,
        )
        dates = list(FuelRecord.objects.values_list('date', flat=True))
        self.assertEqual(dates, sorted(dates, reverse=True))


class MaintenanceRecordModelTest(TestCase):

    def setUp(self):
        self.vehicle = make_vehicle(current_mileage=50000, last_service_mileage=None)

    def test_str_representation(self):
        mr = MaintenanceRecord.objects.create(
            vehicle=self.vehicle,
            date=datetime.date(2026, 3, 10),
            mileage_at_service=48000,
            service_type='Oil change',
            cost='500.00',
            vendor='QuickFix Garage',
        )
        self.assertIn('Maintenance:', str(mr))
        self.assertIn('Oil change', str(mr))

    def test_notes_optional(self):
        mr = MaintenanceRecord.objects.create(
            vehicle=self.vehicle,
            date=datetime.date(2026, 3, 10),
            mileage_at_service=48000,
            service_type='Full service',
            cost='1200.00',
            vendor='Toyota Zambia',
        )
        self.assertEqual(mr.notes, '')

    def test_signal_updates_vehicle_last_service(self):
        """Creating a MaintenanceRecord must automatically update the vehicle's baseline."""
        self.assertIsNone(self.vehicle.last_service_date)
        MaintenanceRecord.objects.create(
            vehicle=self.vehicle,
            date=datetime.date(2026, 3, 10),
            mileage_at_service=48000,
            service_type='Oil change',
            cost='500.00',
            vendor='QuickFix Garage',
        )
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.last_service_date, datetime.date(2026, 3, 10))
        self.assertEqual(self.vehicle.last_service_mileage, 48000)

    def test_signal_uses_latest_record(self):
        """If two MaintenanceRecords exist, the vehicle reflects the most recent one."""
        MaintenanceRecord.objects.create(
            vehicle=self.vehicle,
            date=datetime.date(2026, 1, 1),
            mileage_at_service=45000,
            service_type='Oil change',
            cost='500.00',
            vendor='Garage A',
        )
        MaintenanceRecord.objects.create(
            vehicle=self.vehicle,
            date=datetime.date(2026, 4, 1),
            mileage_at_service=50000,
            service_type='Full service',
            cost='1200.00',
            vendor='Garage B',
        )
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.last_service_mileage, 50000)
        self.assertEqual(self.vehicle.last_service_date, datetime.date(2026, 4, 1))

    def test_vehicle_maintenance_status_after_service(self):
        """After a service record is created, maintenance_status should reflect the new baseline."""
        self.vehicle.current_mileage = 50000
        self.vehicle.maintenance_interval_km = 5000
        self.vehicle.save()

        MaintenanceRecord.objects.create(
            vehicle=self.vehicle,
            date=datetime.date(2026, 4, 1),
            mileage_at_service=50000,
            service_type='Full service',
            cost='1200.00',
            vendor='Toyota Zambia',
        )
        self.vehicle.refresh_from_db()
        # km_until_service = (50000 + 5000) - 50000 = 5000 → green
        self.assertEqual(self.vehicle.maintenance_status, 'green')
