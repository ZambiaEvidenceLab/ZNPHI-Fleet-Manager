import datetime

from django.shortcuts import render
from django.views.generic import View

from accounts.mixins import GroupRequiredMixin
from bookings.models import Province, TransportRequest, TripAssignment
from fleet.models import Vehicle

GANTT_GROUPS = ['Fleet Manager', 'Dashboard Viewer', 'Superadmin']
_TOTAL_DAYS = 14


def _gantt_block(period_from, period_to, window_start, status, pk, label):
    """Compute percentage-based CSS position of a booking block within the Gantt window."""
    start_day = max((period_from - window_start).days, 0)
    end_day = min((period_to - window_start).days + 1, _TOTAL_DAYS)
    return {
        'left_pct': round(start_day / _TOTAL_DAYS * 100, 4),
        'width_pct': round((end_day - start_day) / _TOTAL_DAYS * 100, 4),
        'status': status,
        'pk': pk,
        'label': label,
    }


class GanttView(GroupRequiredMixin, View):
    group_required = GANTT_GROUPS
    template_name = 'dashboard/gantt.html'

    def get(self, request):
        from_str = request.GET.get('from')
        try:
            window_start = datetime.date.fromisoformat(from_str)
        except (TypeError, ValueError):
            window_start = datetime.date.today()

        window_end = window_start + datetime.timedelta(days=_TOTAL_DAYS - 1)

        today = datetime.date.today()
        today_col_num = (today - window_start).days
        today_in_window = 0 <= today_col_num < _TOTAL_DAYS

        days = []
        for i in range(_TOTAL_DAYS):
            d = window_start + datetime.timedelta(days=i)
            days.append({
                'date': d,
                'is_today': d == today,
                'is_weekend': d.weekday() >= 5,
            })

        province_id = request.GET.get('province') or None
        if province_id:
            try:
                province_id = int(province_id)
            except ValueError:
                province_id = None

        provinces = Province.objects.order_by('name')
        vehicles = Vehicle.objects.order_by('make', 'model', 'license_plate')

        # Approved / In Progress assignments overlapping the window
        assignment_qs = (
            TripAssignment.objects
            .filter(
                transport_request__status__in=['Approved', 'In Progress'],
                transport_request__period_from__lte=window_end,
                transport_request__period_to__gte=window_start,
            )
            .select_related(
                'vehicle',
                'transport_request',
                'transport_request__province',
                'transport_request__district',
            )
        )
        if province_id:
            assignment_qs = assignment_qs.filter(transport_request__province_id=province_id)

        assignment_map = {}
        for a in assignment_qs:
            assignment_map.setdefault(a.vehicle_id, []).append(a)

        # Submitted requests overlapping the window (no vehicle assigned yet)
        pending_qs = (
            TransportRequest.objects
            .filter(
                status='Submitted',
                period_from__lte=window_end,
                period_to__gte=window_start,
            )
            .select_related('province', 'district')
        )
        if province_id:
            pending_qs = pending_qs.filter(province_id=province_id)

        vehicle_rows = []
        for vehicle in vehicles:
            bookings = []
            for a in assignment_map.get(vehicle.id, []):
                req = a.transport_request
                label = req.district.name if req.district else req.province.name
                bookings.append(
                    _gantt_block(req.period_from, req.period_to, window_start, req.status, req.pk, label)
                )
            vehicle_rows.append({'vehicle': vehicle, 'bookings': bookings})

        pending_blocks = []
        for req in pending_qs:
            label = req.district.name if req.district else req.province.name
            pending_blocks.append(
                _gantt_block(req.period_from, req.period_to, window_start, 'Submitted', req.pk, label)
            )

        can_interact = (
            request.user.groups.filter(name__in=['Fleet Manager', 'Superadmin']).exists()
            or request.user.is_superuser
        )

        context = {
            'window_start': window_start,
            'window_end': window_end,
            'prev_start': window_start - datetime.timedelta(days=_TOTAL_DAYS),
            'next_start': window_start + datetime.timedelta(days=_TOTAL_DAYS),
            'today_in_window': today_in_window,
            'today_col_num': today_col_num,
            'days': days,
            'provinces': provinces,
            'selected_province_id': province_id,
            'vehicle_rows': vehicle_rows,
            'pending_blocks': pending_blocks,
            'can_interact': can_interact,
        }
        return render(request, self.template_name, context)
