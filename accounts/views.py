from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, ListView, View

from .forms import UserCreateForm, UserGroupForm
from .mixins import GroupRequiredMixin

User = get_user_model()


class FleetLoginView(DjangoLoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class HomeView(LoginRequiredMixin, View):
    """Route authenticated users to the landing page for their role."""

    def get(self, request):
        user = request.user
        if user.is_superuser or user.groups.filter(name='Superadmin').exists():
            return redirect(reverse_lazy('accounts:user_list'))
        if user.groups.filter(name='Fleet Manager').exists():
            return redirect('/bookings/queue/')
        if user.groups.filter(name='Requester').exists():
            return redirect('/bookings/my-requests/')
        if user.groups.filter(name='Dashboard Viewer').exists():
            return redirect('/dashboard/')
        # Ungrouped users see a neutral home page rather than an error.
        return render(request, 'home.html')


class UserListView(GroupRequiredMixin, ListView):
    group_required = 'Superadmin'
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    ordering = ['username']

    def get_queryset(self):
        return super().get_queryset().prefetch_related('groups')


class UserCreateView(GroupRequiredMixin, CreateView):
    group_required = 'Superadmin'
    model = User
    form_class = UserCreateForm
    template_name = 'accounts/user_create.html'
    success_url = reverse_lazy('accounts:user_list')


class UserGroupUpdateView(GroupRequiredMixin, FormView):
    group_required = 'Superadmin'
    form_class = UserGroupForm
    template_name = 'accounts/user_group_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.target_user = get_object_or_404(User, pk=kwargs['pk'])

    def get_initial(self):
        return {'group': self.target_user.groups.first()}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target_user'] = self.target_user
        return context

    def form_valid(self, form):
        self.target_user.groups.set([form.cleaned_data['group']])
        return super().form_valid(form)
