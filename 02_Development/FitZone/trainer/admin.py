from django.contrib import admin
from django.contrib import messages
from django import forms
from django.utils import timezone
from django.utils.html import format_html
import datetime
import os

from .models import TrainerRegistration, TrainerRegistrationDocument, TrainerBooking
from notifications.models import TrainerNotification
from login_logout_register.models import UserProfile


# Inline admin to display documents within the TrainerRegistration admin page
class TrainerRegistrationDocumentInline(admin.StackedInline):
	model = TrainerRegistrationDocument
	extra = 0
	readonly_fields = ("doc_type", "preview", "file_link", "original_filename", "uploaded_at")
	fields = ("doc_type", "preview", "file_link", "original_filename", "uploaded_at")
	can_delete = False
	verbose_name = "Document"
	verbose_name_plural = "Trainer documents"

	def preview(self, obj):
		if not obj.file:
			return "-"
		name = obj.original_filename or os.path.basename(obj.file.name)
		url = obj.file.url
		ext = os.path.splitext(obj.file.name)[1].lower()
		if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
			return format_html(
				'<div class="admin-doc-preview">'
				'	<a href="{}" target="_blank" rel="noopener">'
				'		<img src="{}" alt="{}" class="preview-img">'
				'		<div class="preview-overlay"><i class="fas fa-search-plus"></i> View Full Size</div>'
				'	</a>'
				'</div>',
				url,
				url,
				name,
			)
		return format_html(
			'<div class="admin-doc-icon">'
			'	<i class="fas fa-file-pdf"></i>'
			'	<span>{}</span>'
			'</div>',
			"Non-image document (PDF/Other)"
		)
	preview.short_description = "Preview"

	def file_link(self, obj):
		if not obj.file:
			return "-"
		return format_html(
			'<a href="{}" target="_blank" rel="noopener" class="admin-doc-btn">'
			'	<i class="fas fa-external-link-alt"></i> View Full Document'
			'</a>',
			obj.file.url
		)
	file_link.short_description = "File"
	
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


class TrainerBookingAdminForm(forms.ModelForm):
	class Meta:
		model = TrainerBooking
		fields = "__all__"

	def __init__(self, *args, **kwargs):
		instance = kwargs.get("instance")
		# Normalize legacy Date values for valid_until to timezone-aware datetimes
		if instance is not None:
			value = getattr(instance, "valid_until", None)
			if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
				instance.valid_until = timezone.make_aware(
					datetime.datetime.combine(value, datetime.time.min)
				)
		super().__init__(*args, **kwargs)


@admin.register(TrainerBooking)
class TrainerBookingAdmin(admin.ModelAdmin):
	list_display = ("user", "trainer", "booking_date", "status", "created_at")
	list_filter = ("status", "created_at")
	search_fields = ("user__username", "trainer__user__username")
	readonly_fields = ("created_at", "updated_at")
	form = TrainerBookingAdminForm
