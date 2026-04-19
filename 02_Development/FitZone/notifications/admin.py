from django.contrib import admin
from django import forms
from django.contrib import messages
from django.urls import path, reverse
from django.template.response import TemplateResponse
from django.http import HttpResponseRedirect
from .models import TrainerNotification, UserNotification
from login_logout_register.models import UserProfile
from trainer.models import TrainerRegistration


class BroadcastNotificationForm(forms.Form):
    AUDIENCE_CHOICES = [
        ('members', 'All Members'),
        ('trainers', 'All Trainers'),
        ('both', 'Members and Trainers'),
    ]

    audience = forms.ChoiceField(choices=AUDIENCE_CHOICES, initial='both')
    title = forms.CharField(max_length=200)
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))
    user_notif_type = forms.ChoiceField(choices=UserNotification.NOTIF_TYPES, initial='general')
    trainer_notif_type = forms.ChoiceField(choices=TrainerNotification.NOTIF_TYPES, initial='general')


class BroadcastNotificationAdminMixin:
    change_list_template = 'admin/notifications/change_list_with_broadcast.html'

    def get_urls(self):
        urls = super().get_urls()
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        custom_urls = [
            path(
                'broadcast/',
                self.admin_site.admin_view(self.broadcast_view),
                name=f'{app_label}_{model_name}_broadcast',
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        extra_context['broadcast_url'] = reverse(f'admin:{app_label}_{model_name}_broadcast')
        return super().changelist_view(request, extra_context=extra_context)

    def broadcast_view(self, request):
        form = BroadcastNotificationForm(request.POST or None)

        if request.method == 'POST' and form.is_valid():
            audience = form.cleaned_data['audience']
            title = form.cleaned_data['title']
            message_text = form.cleaned_data['message']
            user_notif_type = form.cleaned_data['user_notif_type']
            trainer_notif_type = form.cleaned_data['trainer_notif_type']

            members_count = 0
            trainers_count = 0

            if audience in ('members', 'both'):
                member_ids = UserProfile.objects.filter(role='member').values_list('user_id', flat=True)
                user_notifications = [
                    UserNotification(
                        user_id=user_id,
                        notif_type=user_notif_type,
                        title=title,
                        message=message_text,
                    )
                    for user_id in member_ids
                ]
                if user_notifications:
                    UserNotification.objects.bulk_create(user_notifications, batch_size=500)
                    members_count = len(user_notifications)

            if audience in ('trainers', 'both'):
                trainer_regs = TrainerRegistration.objects.filter(is_verified=True)
                trainer_notifications = [
                    TrainerNotification(
                        trainer=reg,
                        notif_type=trainer_notif_type,
                        title=title,
                        message=message_text,
                    )
                    for reg in trainer_regs
                ]
                if trainer_notifications:
                    TrainerNotification.objects.bulk_create(trainer_notifications, batch_size=500)
                    trainers_count = len(trainer_notifications)

            messages.success(
                request,
                f'Broadcast sent successfully. Members notified: {members_count}, Trainers notified: {trainers_count}.',
            )
            app_label = self.model._meta.app_label
            model_name = self.model._meta.model_name
            return HttpResponseRedirect(reverse(f'admin:{app_label}_{model_name}_changelist'))

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': 'Send Broadcast Notification',
            'form': form,
        }
        return TemplateResponse(request, 'admin/notifications/broadcast_form.html', context)


@admin.register(TrainerNotification)
class TrainerNotificationAdmin(BroadcastNotificationAdminMixin, admin.ModelAdmin):
    list_display = ('trainer', 'notif_type', 'title', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'trainer__user__username')
    readonly_fields = ('created_at',)
    list_per_page = 50


@admin.register(UserNotification)
class UserNotificationAdmin(BroadcastNotificationAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'notif_type', 'title', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username')
    readonly_fields = ('created_at',)
    list_per_page = 50
