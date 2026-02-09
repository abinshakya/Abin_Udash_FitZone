from django.contrib import admin
from .models import TrainerRegistration, TrainerRegistrationDocument, TrainerBooking, TrainerNotification, UserNotification
from login_logout_register.models import UserProfile
from django.contrib import messages


# Inline admin to display documents within the TrainerRegistration admin page
class TrainerRegistrationDocumentInline(admin.TabularInline):
	model = TrainerRegistrationDocument
	extra = 0
	readonly_fields = ("doc_type", "file", "uploaded_at")
	can_delete = False
	
	def has_add_permission(self, request, obj=None):
		return False


@admin.register(TrainerRegistration)
class TrainerRegistrationAdmin(admin.ModelAdmin):
	list_display = ("user", "experience", "specialization", "is_verified", "submitted_at")
	list_filter = ("is_verified", "submitted_at")
	search_fields = ("user__username", "specialization")
	readonly_fields = ("submitted_at",)
	inlines = [TrainerRegistrationDocumentInline]
	
	fieldsets = (
		("Trainer Information", {
			"fields": ("user", "experience", "specialization", "bio")
		}),
		("Verification", {
			"fields": ("is_verified", "remarks", "submitted_at")
		}),
	)

	def save_model(self, request, obj, form, change):
		# Check if verification status changed
		if change:
			old_obj = TrainerRegistration.objects.get(pk=obj.pk)
			verification_changed = old_obj.is_verified != obj.is_verified
			
			super().save_model(request, obj, form, change)
			
			# Send notification if verification status changed
			if verification_changed:
				if obj.is_verified:
					# Trainer approved
					TrainerNotification.objects.create(
						trainer=obj,
						notif_type='approved',
						title='Registration Approved! 🎉',
						message=f'Congratulations! Your trainer registration has been approved. You can now start accepting bookings from members.'
					)
					messages.success(request, f'Approval notification sent to {obj.user.username}')
					
					# Set user role to trainer
					try:
						profile = UserProfile.objects.get(user=obj.user)
						if profile.role != 'trainer':
							profile.role = 'trainer'
							profile.save()
					except UserProfile.DoesNotExist:
						pass
				else:
					# Trainer rejected or verification revoked
					remarks_text = obj.remarks if obj.remarks else 'Please review your application and contact support if needed.'
					TrainerNotification.objects.create(
						trainer=obj,
						notif_type='rejected',
						title='Registration Update',
						message=f'Your trainer registration status has been updated. Admin remarks: {remarks_text}'
					)
					messages.info(request, f'Status update notification sent to {obj.user.username}')
		else:
			# New registration - no notification needed yet
			super().save_model(request, obj, form, change)


@admin.register(TrainerBooking)
class TrainerBookingAdmin(admin.ModelAdmin):
	list_display = ("user", "trainer", "booking_date", "status", "created_at")
	list_filter = ("status", "created_at")
	search_fields = ("user__username", "trainer__user__username")
	readonly_fields = ("created_at", "updated_at")


@admin.register(TrainerNotification)
class TrainerNotificationAdmin(admin.ModelAdmin):
	list_display = ("trainer", "notif_type", "title", "is_read", "created_at")
	list_filter = ("notif_type", "is_read", "created_at")
	search_fields = ("title", "message", "trainer__user__username")
	readonly_fields = ("created_at",)


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
	list_display = ("user", "notif_type", "title", "is_read", "created_at")
	list_filter = ("notif_type", "is_read", "created_at")
	search_fields = ("title", "message", "user__username")
	readonly_fields = ("created_at",)
