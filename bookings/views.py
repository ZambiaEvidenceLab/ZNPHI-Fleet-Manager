import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView, View

from accounts.mixins import GroupRequiredMixin
from fleet.models import Driver, Vehicle
from .forms import CoordinationAcknowledgmentForm, RequestApprovalForm, TransportRequestForm
from .models import District, Province, TransportRequest, TripAssignment

# Default nudge window. Made configurable via Settings model in Phase 8.
NUDGE_WINDOW_DAYS = 7

# Default buffer days between consecutive trips for the same vehicle. Made configurable in Phase 8.
BUFFER_DAYS = 1


def get_overlapping_trips(district, period_from, period_to):
    """Return active requests to the same district whose dates fall within the
    nudge time window around the requested period.

    Uses a symmetric window: any trip that overlaps [from - window, to + window]
    qualifies, so requesters are warned about trips departing a few days earlier
    or later — not just exact date overlaps.
    """
    window_start = period_from - datetime.timedelta(days=NUDGE_WINDOW_DAYS)
    window_end = period_to + datetime.timedelta(days=NUDGE_WINDOW_DAYS)
    return (
        TransportRequest.objects
        .filter(
            district=district,
            status__in=['Submitted', 'Approved', 'In Progress'],
            period_from__lte=window_end,
            period_to__gte=window_start,
        )
        .select_related('department')
        .prefetch_related('assignments__vehicle')
    )


def _save_transport_request(cleaned_data, submitted_by=None,
                             coordination_acknowledged=False, coordination_note=''):
    return TransportRequest.objects.create(
        requester_name=cleaned_data['requester_name'],
        department=cleaned_data['department'],
        position=cleaned_data['position'],
        programme_activity=cleaned_data['programme_activity'],
        period_from=cleaned_data['period_from'],
        period_to=cleaned_data['period_to'],
        province=cleaned_data['province'],
        district=cleaned_data['district'],
        destination=cleaned_data['destination'],
        num_vehicles=cleaned_data['num_vehicles'],
        num_drivers=cleaned_data['num_drivers'],
        num_passengers=cleaned_data['num_passengers'],
        is_emergency=cleaned_data.get('is_emergency', False),
        submitted_by=submitted_by,
        coordination_acknowledged=coordination_acknowledged,
        coordination_note=coordination_note,
    )


class DistrictOptionsView(View):
    """HTMX endpoint: returns <option> tags for districts in the selected province."""

    def get(self, request):
        province_id = request.GET.get('province')
        districts = District.objects.none()
        if province_id:
            try:
                districts = District.objects.filter(province_id=int(province_id))
            except (ValueError, TypeError):
                pass
        return render(request, 'bookings/htmx/district_options.html', {'districts': districts})


class TransportRequestCreateView(GroupRequiredMixin, View):
    group_required = ['Requester', 'Fleet Manager', 'Dashboard Viewer', 'Superadmin']
    template_name = 'bookings/request_form.html'

    def get(self, request):
        form = TransportRequestForm()
        provinces = Province.objects.all()
        return render(request, self.template_name, {'form': form, 'provinces': provinces})

    def post(self, request):
        form = TransportRequestForm(request.POST)
        provinces = Province.objects.all()

        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'provinces': provinces})

        cd = form.cleaned_data
        is_late = (cd['period_from'] - datetime.date.today()) < datetime.timedelta(weeks=2)
        overlapping = get_overlapping_trips(cd['district'], cd['period_from'], cd['period_to'])

        if overlapping.exists():
            # Store POST data in session; redirect to nudge page.
            request.session['pending_request_data'] = {
                k: v for k, v in request.POST.items() if k != 'csrfmiddlewaretoken'
            }
            request.session['overlapping_trip_ids'] = list(overlapping.values_list('id', flat=True))
            request.session['pending_request_is_late'] = is_late
            return redirect('bookings:coordination_nudge')

        _save_transport_request(cd, submitted_by=request.user)
        if is_late:
            messages.warning(
                request,
                'Request submitted. Note: this trip starts in less than 2 weeks — '
                'please allow extra time for the Fleet Manager to process it.'
            )
        else:
            messages.success(request, 'Transport request submitted successfully.')
        return redirect(reverse_lazy('bookings:my_requests'))


class CoordinationNudgeView(LoginRequiredMixin, View):
    """Show coordination overlap details and require the requester to acknowledge
    before the request is saved."""
    template_name = 'bookings/coordination_nudge.html'

    def _recover_session(self, request):
        """Rebuild form and overlapping queryset from session. Returns (raw, form, overlapping)
        or (None, None, None) if session data is missing."""
        raw = request.session.get('pending_request_data')
        if not raw:
            return None, None, None
        form = TransportRequestForm(raw)
        form.is_valid()  # populate cleaned_data without raising on errors
        trip_ids = request.session.get('overlapping_trip_ids', [])
        overlapping = (
            TransportRequest.objects
            .filter(id__in=trip_ids)
            .select_related('department')
            .prefetch_related('assignments__vehicle')
        )
        return raw, form, overlapping

    def get(self, request):
        raw, form, overlapping = self._recover_session(request)
        if raw is None:
            return redirect('bookings:request_create')
        is_late = request.session.get('pending_request_is_late', False)
        return render(request, self.template_name, {
            'form': form,
            'overlapping': overlapping,
            'ack_form': CoordinationAcknowledgmentForm(),
            'is_late': is_late,
        })

    def post(self, request):
        raw, form, overlapping = self._recover_session(request)
        if raw is None:
            return redirect('bookings:request_create')

        ack_form = CoordinationAcknowledgmentForm(request.POST)
        if not ack_form.is_valid():
            is_late = request.session.get('pending_request_is_late', False)
            return render(request, self.template_name, {
                'form': form,
                'overlapping': overlapping,
                'ack_form': ack_form,
                'is_late': is_late,
            })

        _save_transport_request(
            form.cleaned_data,
            submitted_by=request.user,
            coordination_acknowledged=True,
            coordination_note=ack_form.cleaned_data.get('coordination_note', ''),
        )

        # Clear session data after saving.
        request.session.pop('pending_request_data', None)
        request.session.pop('overlapping_trip_ids', None)
        request.session.pop('pending_request_is_late', None)

        is_late = request.session.get('pending_request_is_late', False)
        if is_late:
            messages.warning(
                request,
                'Request submitted. Note: this trip starts in less than 2 weeks.'
            )
        else:
            messages.success(request, 'Transport request submitted successfully.')
        return redirect(reverse_lazy('bookings:my_requests'))


class MyRequestsView(GroupRequiredMixin, ListView):
    group_required = ['Requester', 'Fleet Manager', 'Dashboard Viewer', 'Superadmin']
    template_name = 'bookings/my_requests.html'
    context_object_name = 'requests'

    def get_queryset(self):
        return (
            TransportRequest.objects
            .filter(submitted_by=self.request.user)
            .select_related('district', 'province', 'department')
            .prefetch_related('assignments__vehicle')
        )


class TransportRequestDetailView(LoginRequiredMixin, DetailView):
    model = TransportRequest
    template_name = 'bookings/request_detail.html'
    context_object_name = 'transport_request'

    def get_queryset(self):
        user = self.request.user
        # Fleet managers and superadmins can view any request; requesters see only their own.
        if user.groups.filter(name__in=['Fleet Manager', 'Superadmin']).exists() or user.is_superuser:
            return TransportRequest.objects.all()
        return TransportRequest.objects.filter(submitted_by=user)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj is None:
            raise PermissionDenied
        return obj


class TransportRequestCancelView(LoginRequiredMixin, View):
    """POST-only: cancel a pre-completion transport request."""

    def post(self, request, pk):
        user = request.user
        is_manager = user.groups.filter(name__in=['Fleet Manager', 'Superadmin']).exists() or user.is_superuser
        qs = TransportRequest.objects.all() if is_manager else TransportRequest.objects.filter(submitted_by=user)
        tr = get_object_or_404(qs, pk=pk)

        if tr.status in ('Completed', 'Cancelled'):
            messages.error(request, 'This request cannot be cancelled.')
        else:
            tr.status = 'Cancelled'
            tr.save()
            messages.success(request, 'Request cancelled successfully.')

        return redirect('bookings:my_requests')


# ---------------------------------------------------------------------------
# Phase 4: Fleet Manager approval and assignment workflow
# ---------------------------------------------------------------------------

def get_available_vehicles(period_from, period_to, buffer_days=BUFFER_DAYS):
    """Return vehicles that can be assigned for the given date range.

    Excludes vehicles that:
    - Are already committed to a trip whose dates (plus buffer) overlap the window.
    - Have overdue maintenance (current mileage exceeds last_service_mileage + interval).
    """
    window_start = period_from - datetime.timedelta(days=buffer_days)
    window_end = period_to + datetime.timedelta(days=buffer_days)

    booked_ids = (
        TripAssignment.objects
        .filter(
            transport_request__status__in=['Submitted', 'Approved', 'In Progress'],
            transport_request__period_from__lte=window_end,
            transport_request__period_to__gte=window_start,
        )
        .values_list('vehicle_id', flat=True)
    )

    # Overdue: current mileage exceeds the mileage threshold for next service.
    overdue = Q(
        last_service_mileage__isnull=False,
        current_mileage__gt=F('last_service_mileage') + F('maintenance_interval_km'),
    )

    return (
        Vehicle.objects
        .exclude(pk__in=booked_ids)
        .exclude(overdue)
        .order_by('license_plate')
    )


def get_available_drivers(period_from, period_to, buffer_days=BUFFER_DAYS):
    """Return drivers with Available status and no overlapping assignment (with buffer)."""
    window_start = period_from - datetime.timedelta(days=buffer_days)
    window_end = period_to + datetime.timedelta(days=buffer_days)

    busy_ids = (
        TripAssignment.objects
        .filter(
            transport_request__status__in=['Submitted', 'Approved', 'In Progress'],
            transport_request__period_from__lte=window_end,
            transport_request__period_to__gte=window_start,
        )
        .values_list('driver_id', flat=True)
    )

    return Driver.objects.filter(status='Available').exclude(pk__in=busy_ids)


def _vehicles_with_info(available_vehicles_qs):
    """Attach upcoming-trip context to each available vehicle for display on the review screen."""
    result = []
    for v in available_vehicles_qs:
        # Most recent upcoming/active assignment — tells the fleet manager when this vehicle
        # last returns and from where, so they can judge scheduling feasibility.
        upcoming = (
            TripAssignment.objects
            .filter(vehicle=v, transport_request__status__in=['Approved', 'In Progress'])
            .select_related('transport_request__district')
            .order_by('transport_request__period_to')
            .last()
        )
        result.append({
            'vehicle': v,
            'return_trip': upcoming.transport_request if upcoming else None,
        })
    return result


class RequestQueueView(GroupRequiredMixin, ListView):
    """Landing page for Fleet Managers: all pending (Submitted) requests sorted by urgency."""
    group_required = ['Fleet Manager', 'Superadmin']
    template_name = 'bookings/request_queue.html'
    context_object_name = 'requests'

    def get_queryset(self):
        # Emergencies first, then soonest start date.
        return (
            TransportRequest.objects
            .filter(status='Submitted')
            .select_related('department', 'district', 'province')
            .order_by('-is_emergency', 'period_from')
        )


class RequestReviewView(GroupRequiredMixin, View):
    """Review a single Submitted request: display details, show available vehicles,
    and let the Fleet Manager approve (with assignment) or reject."""
    group_required = ['Fleet Manager', 'Superadmin']
    template_name = 'bookings/request_review.html'

    def _get_tr(self, pk):
        return get_object_or_404(
            TransportRequest.objects
            .select_related('department', 'district', 'province')
            .prefetch_related('assignments'),
            pk=pk,
            status='Submitted',
        )

    def _context(self, tr, form, available_vehicles_qs, overlapping):
        return {
            'tr': tr,
            'form': form,
            'vehicles_with_info': _vehicles_with_info(available_vehicles_qs),
            'overlapping': overlapping,
            'is_late': tr.is_late_booking,
        }

    def get(self, request, pk):
        tr = self._get_tr(pk)
        avail_v = get_available_vehicles(tr.period_from, tr.period_to)
        avail_d = get_available_drivers(tr.period_from, tr.period_to)
        overlapping = get_overlapping_trips(tr.district, tr.period_from, tr.period_to).exclude(pk=tr.pk)
        form = RequestApprovalForm(num_vehicles=tr.num_vehicles, available_vehicles=avail_v, available_drivers=avail_d)
        return render(request, self.template_name, self._context(tr, form, avail_v, overlapping))

    def post(self, request, pk):
        tr = self._get_tr(pk)
        action = request.POST.get('action')
        avail_v = get_available_vehicles(tr.period_from, tr.period_to)
        avail_d = get_available_drivers(tr.period_from, tr.period_to)
        overlapping = get_overlapping_trips(tr.district, tr.period_from, tr.period_to).exclude(pk=tr.pk)

        if action == 'reject':
            tr.status = 'Rejected'
            tr.admin_comment = request.POST.get('admin_comment', '')
            tr.save()
            messages.success(request, f'Request #{tr.pk} rejected.')
            return redirect('bookings:request_queue')

        if action == 'approve':
            form = RequestApprovalForm(
                request.POST,
                num_vehicles=tr.num_vehicles,
                available_vehicles=avail_v,
                available_drivers=avail_d,
            )
            if not form.is_valid():
                return render(request, self.template_name, self._context(tr, form, avail_v, overlapping))

            for vehicle, driver in form.assignment_pairs():
                TripAssignment.objects.create(transport_request=tr, vehicle=vehicle, driver=driver)
            tr.status = 'Approved'
            tr.admin_comment = form.cleaned_data.get('admin_comment', '')
            tr.approved_date = datetime.date.today()
            tr.save()
            messages.success(request, f'Request #{tr.pk} approved.')
            return redirect('bookings:request_queue')

        return redirect('bookings:request_review', pk=pk)
