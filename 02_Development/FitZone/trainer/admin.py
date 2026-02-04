from django.contrib import admin
from .models import TrainerRegistration, TrainerRegistrationDocument
from login_logout_register.models import UserProfile


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
			"fields": ("is_verified", "submitted_at")
		}),
	)

	def save_model(self, request, obj, form, change):
		super().save_model(request, obj, form, change)
		if obj.is_verified:
			# Set user role to trainer
			try:
				profile = UserProfile.objects.get(user=obj.user)
				if profile.role != 'trainer':
					profile.role = 'trainer'
					profile.save()
			except UserProfile.DoesNotExist:
				pass
