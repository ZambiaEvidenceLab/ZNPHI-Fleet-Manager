from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

User = get_user_model()

admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_groups', 'is_active')
    list_filter = ('groups', 'is_active', 'is_staff')

    @admin.display(description='Groups')
    def get_groups(self, obj):
        return ', '.join(g.name for g in obj.groups.all()) or '—'
