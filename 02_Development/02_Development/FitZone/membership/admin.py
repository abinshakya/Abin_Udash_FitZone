from django.contrib import admin
from .models import MembershipPlan

@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration", "is_active")
    list_filter = ("duration", "is_active")
    search_fields = ("name",)
