from django.contrib import admin
from .models import TrainerNotification, UserNotification


@admin.register(TrainerNotification)
class TrainerNotificationAdmin(admin.ModelAdmin):
    list_display = ('trainer', 'notif_type', 'title', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'trainer__user__username')
    readonly_fields = ('created_at',)
    list_per_page = 50


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notif_type', 'title', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username')
    readonly_fields = ('created_at',)
    list_per_page = 50
