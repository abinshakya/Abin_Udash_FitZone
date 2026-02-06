from django.contrib import admin
from .models import MembershipPlan, UserMembership

@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration", "is_active")
    list_filter = ("duration", "is_active")
    search_fields = ("name",)


@admin.register(UserMembership)
class UserMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "membership_plan", "start_date", "end_date", "days_left", "is_active")
    list_filter = ("is_active", "created_at")
    search_fields = ("user__username", "user__email", "membership_plan__name")
    readonly_fields = ("start_date", "created_at", "updated_at", "days_left", "progress_percentage")
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("User Information", {
            "fields": ("user", "membership_plan")
        }),
        ("Membership Period", {
            "fields": ("start_date", "end_date", "days_left", "progress_percentage")
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        })
    )
