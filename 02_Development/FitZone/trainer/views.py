from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.utils import timezone
from datetime import timedelta
from formtools.wizard.views import SessionWizardView
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
import os
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import TrainerBooking
from .forms import (
    Step1BasicInfoForm, Step2CertificationForm, Step3DocumentsForm, TrainerProfileEditForm
)
from .models import TrainerRegistrationDocument, TrainerRegistration, TrainerPhoto, TrainerBooking
from notifications.models import TrainerNotification, UserNotification
from chat.models import ChatRoom, Message


def trainer(request):
    # Base queryset: all verified trainers
    verified_trainers = TrainerRegistration.objects.filter(
        is_verified=True
    ).select_related('user').prefetch_related('documents').order_by('-submitted_at')

    # Search + filters
    query = request.GET.get('q', '').strip()
    specialization = request.GET.get('specialization', '').strip()
    min_experience = request.GET.get('min_experience', '').strip()
    sort = request.GET.get('sort', 'newest').strip() or 'newest'

    trainers_qs = verified_trainers

    if query:
        trainers_qs = trainers_qs.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__username__icontains=query)
            | Q(specialization__icontains=query)
            | Q(bio__icontains=query)
        )

    if specialization:
        trainers_qs = trainers_qs.filter(specialization__icontains=specialization)

    if min_experience.isdigit():
        trainers_qs = trainers_qs.filter(experience__gte=int(min_experience))

    if sort == 'experience_desc':
        trainers_qs = trainers_qs.order_by('-experience', '-submitted_at')
    elif sort == 'price_asc':
        trainers_qs = trainers_qs.order_by('monthly_price', '-submitted_at')
    elif sort == 'price_desc':
        trainers_qs = trainers_qs.order_by('-monthly_price', '-submitted_at')
    else:
        sort = 'newest'
        trainers_qs = trainers_qs.order_by('-submitted_at')

    paginator = Paginator(trainers_qs, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Build specialization filter options from verified trainer data
    specialization_options = sorted(
        {
            item.strip()
            for trainer_obj in verified_trainers
            for item in (trainer_obj.specialization or '').split(',')
            if item.strip()
        },
        key=lambda x: x.lower(),
    )

    # Booking context
    user_is_email_verified = False
    pending_booking_trainer_ids = []
    if request.user.is_authenticated:
        from login_logout_register.models import UserProfile
        try:
            profile = UserProfile.objects.get(user=request.user)
            user_is_email_verified = profile.email_verified
        except UserProfile.DoesNotExist:
            pass
        pending_booking_trainer_ids = list(
            TrainerBooking.objects.filter(user=request.user, status='pending').values_list('trainer_id', flat=True)
        )

    params = request.GET.copy()
    params.pop('page', None)
    querystring = params.urlencode()

    context = {
        'trainers': page_obj.object_list,
        'today': timezone.now().date().isoformat(),
        'user_is_email_verified': user_is_email_verified,
        'pending_booking_trainer_ids': pending_booking_trainer_ids,
        'specialization_options': specialization_options,
        'filters': {
            'q': query,
            'specialization': specialization,
            'min_experience': min_experience,
            'sort': sort,
        },
        'result_count': trainers_qs.count(),
        'has_active_filters': bool(query or specialization or min_experience),
        'page_obj': page_obj,
        'querystring': querystring,
    }
    return render(request, 'trainer.html', context)


def trainer_profile_detail(request, trainer_id):
    from django.shortcuts import get_object_or_404
    from django.db.models import Q
    
    trainer = get_object_or_404(
        TrainerRegistration.objects.select_related('user').prefetch_related('documents', 'photos'),
        id=trainer_id,
        is_verified=True
    )
    
    # Get documents by type
    certifications = trainer.documents.filter(doc_type='certification').all()
    profile_pic = trainer.documents.filter(doc_type='profile_pic').first()
    experience_docs = trainer.documents.filter(doc_type='experience_verification').all()
    
    # Get photos
    photos = trainer.photos.all()
    
    # Parse specializations
    specializations = []
    if trainer.specialization:
        specializations = [s.strip() for s in trainer.specialization.split(',')]
    
    # Get count of active clients (confirmed bookings that are still valid)
    active_clients_count = TrainerBooking.objects.filter(
        trainer=trainer,
        status='confirmed',
        valid_until__isnull=False
    ).filter(
        Q(valid_until__gte=timezone.now()) | Q(valid_until__isnull=True)
    ).values('user').distinct().count()
    
    # Check if logged-in user already has a pending booking
    has_pending_booking = False
    user_is_email_verified = False
    if request.user.is_authenticated:
        has_pending_booking = TrainerBooking.objects.filter(
            user=request.user, trainer=trainer, status='pending'
        ).exists()
        try:
            user_is_email_verified = request.user.userprofile.email_verified
        except Exception:
            pass
    
    context = {
        'trainer': trainer,
        'certifications': certifications,
        'profile_pic': profile_pic,
        'experience_docs': experience_docs,
        'specializations': specializations,
        'photos': photos,
        'has_pending_booking': has_pending_booking,
        'user_is_email_verified': user_is_email_verified,
        'today': timezone.now().date().isoformat(),
        'active_clients_count': active_clients_count,
        'reviews': trainer.reviews.all(),
        'avg_rating': round(sum(r.rating for r in trainer.reviews.all()) / max(trainer.reviews.count(), 1), 1) if trainer.reviews.exists() else 0.0,
    }
    
    return render(request, 'trainer_profile_detail.html', context)


def trainer_booking_modal(request, trainer_id):
    from django.shortcuts import get_object_or_404
    from django.http import JsonResponse
    
    trainer = get_object_or_404(
        TrainerRegistration.objects.select_related('user'),
        id=trainer_id,
        is_verified=True
    )
    
    data = {
        'trainer_name': trainer.user.get_full_name() or trainer.user.username,
        'monthly_price': str(trainer.monthly_price) if trainer.monthly_price else 'Contact for pricing',
        'available_time': trainer.available_time or 'Not specified',
        'experience': trainer.experience,
        'specialization': trainer.specialization,
    }
    
    return JsonResponse(data)


@login_required
def trainer_dashboard(request):
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied. Trainers only!")
        return redirect('/')
    
    registration = TrainerRegistration.objects.filter(user=request.user).first()
    
    # Parse specializations
    specializations = []
    if registration and registration.specialization:
        specializations = [s.strip() for s in registration.specialization.split(',')]
    
    # Get photos
    photos = []
    if registration:
        photos = registration.photos.all()
    
    # Get notifications and bookings
    notifications = []
    unread_count = 0
    bookings = []
    active_clients = 0
    booking_status_counts = {"pending": 0, "confirmed": 0, "completed": 0, "rejected": 0, "cancelled": 0}
    earnings_total = 0
    if registration:
        notifications = registration.notifications.all()[:20]
        unread_count = registration.notifications.filter(is_read=False).count()
        all_bookings_qs = registration.bookings.select_related('user').all()
        bookings = all_bookings_qs[:20]
        active_clients = all_bookings_qs.filter(status='confirmed').values('user').distinct().count()

        # Aggregate simple analytics
        for b in all_bookings_qs:
            if b.status in booking_status_counts:
                booking_status_counts[b.status] += 1
            if b.payment_status == 'completed' and b.amount:
                earnings_total += float(b.amount)
    
    context = {
        'registration': registration,
        'specializations': specializations,
        'photos': photos,
        'notifications': notifications,
        'unread_count': unread_count,
        'bookings': bookings,
        'active_clients': active_clients,
        'booking_status_counts': booking_status_counts,
        'earnings_total': earnings_total,
        'all_bookings': registration.bookings.select_related('user').all(),
    }
    
    return render(request, 'trainer_dashboard.html', context)


@login_required
def trainer_client_bookings(request):
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied. Trainers only!")
        return redirect('/')

    registration = TrainerRegistration.objects.filter(user=request.user).first()
    
    pending_requests = []
    active_clients = []
    notifications = []
    unread_count = 0

    if registration:
        now = timezone.now()
        notifications = registration.notifications.all()[:20]
        unread_count = registration.notifications.filter(is_read=False).count()
        all_bookings = registration.bookings.select_related('user')
        
        pending_requests = all_bookings.filter(
            Q(status='pending') | Q(status='confirmed', payment_status='pending')
        ).order_by('-created_at')

        # Flag renewals
        for req in pending_requests:
            req.is_renewal = all_bookings.filter(
                user=req.user,
                status__in=['confirmed', 'completed'],
                payment_status='completed',
                valid_until__gte=now
            ).exclude(id=req.id).exists()
        
        active_clients = all_bookings.filter(
            status='confirmed', 
            payment_status='completed'
        ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now)).order_by('-created_at')
        
        completed_clients = all_bookings.filter(
            Q(status='completed') | 
            Q(status='confirmed', payment_status='completed', valid_until__lt=now)
        ).order_by('-created_at')

    context = {
        'registration': registration,
        'notifications': notifications,
        'unread_count': unread_count,
        'pending_requests': pending_requests,
        'active_clients': active_clients,
        'completed_clients': completed_clients,
        'all_bookings': registration.bookings.select_related('user').all(),
        'active_sidebar': 'client_bookings',
    }

    return render(request, 'trainer_client_bookings.html', context)


@login_required
def upload_trainer_photo(request):
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied. Trainers only!")
        return redirect('/')
    
    registration = TrainerRegistration.objects.filter(user=request.user).first()
    if not registration:
        messages.error(request, "Please complete trainer registration first.")
        return redirect('trainer_settings')
    
    if request.method == 'POST':
        # Add check for photo limit
        if registration.photos.count() >= 6:
            messages.error(request, "You can only upload up to 6 photos.")
            return redirect('trainer_settings')

        photo_file = request.FILES.get('photo')
        caption = request.POST.get('caption', '')
        
        if photo_file:
            TrainerPhoto.objects.create(
                trainer=registration,
                photo=photo_file,
                caption=caption
            )
            messages.success(request, "Photo uploaded successfully!")
        else:
            messages.error(request, "Please select a photo to upload.")
    
    return redirect('trainer_settings')


@login_required
def update_profile_picture(request):
    """Update trainer's profile picture."""
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied. Trainers only!")
        return redirect('/')

    registration = TrainerRegistration.objects.filter(user=request.user).first()
    if not registration:
        messages.error(request, "Please complete trainer registration first.")
        return redirect('trainer_settings')

    if request.method == 'POST':
        pic_file = request.FILES.get('profile_picture')
        if pic_file:
            # Delete old profile_pic document if exists
            old_pic = registration.documents.filter(doc_type='profile_pic').first()
            if old_pic:
                old_pic.delete()

            # Save new profile_pic document with username prefix
            username = request.user.username
            file_ext = pic_file.name.split('.')[-1] if '.' in pic_file.name else 'jpg'
            new_filename = f"{username}_profilepic.{file_ext}"
            doc = TrainerRegistrationDocument.objects.create(
                registration=registration,
                doc_type="profile_pic",
                original_filename=pic_file.name,
            )
            doc.file.save(new_filename, pic_file, save=True)

            # Sync to UserProfile
            try:
                profile.profile_picture.save(new_filename, pic_file, save=True)
            except:
                pass

            messages.success(request, "Profile picture updated successfully!")
        else:
            messages.error(request, "Please select an image.")

    return redirect('trainer_settings')


@login_required
def trainer_settings(request):
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied. Trainers only!")
        return redirect('/')

    registration = TrainerRegistration.objects.filter(user=request.user).first()

    specializations = []
    if registration and registration.specialization:
        specializations = [s.strip() for s in registration.specialization.split(',')]

    photos = []
    if registration:
        photos = registration.photos.all()

    context = {
        'registration': registration,
        'specializations': specializations,
        'photos': photos,
    }

    return render(request, 'trainersettings.html', context)


@login_required
def delete_trainer_photo(request, photo_id):
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied. Trainers only!")
        return redirect('/')
    
    photo = get_object_or_404(TrainerPhoto, id=photo_id)
    
    # Verify ownership
    if photo.trainer.user != request.user:
        messages.error(request, "You don't have permission to delete this photo.")
        return redirect('trainer_dashboard')
    
    photo.delete()
    messages.success(request, "Photo deleted successfully!")
    return redirect('trainer_settings')


FORMS = [
    ("basic_info", Step1BasicInfoForm),
    ("certification", Step2CertificationForm),
    ("documents", Step3DocumentsForm),
]

TEMPLATES = {
    "basic_info": "wizard/step1_basic_info.html",
    "certification": "wizard/step2_certification.html",
    "documents": "wizard/step3_documents.html",
}

@method_decorator(login_required, name='dispatch')
class TrainerRegistrationWizard(SessionWizardView):
    file_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp_wizard'))
    
    def process_step_files(self, form):
        step = self.steps.current
        files = {}

        for field_name in form.fields:
            field_key = f'{step}-{field_name}'
            field_files = self.request.FILES.getlist(field_key)

            if not field_files:
                continue

            # First (or only) file uses the base key
            files[field_key] = field_files[0]

            # Additional files get numbered keys
            for i in range(1, len(field_files)):
                files[f'{field_key}-{i}'] = field_files[i]

        return files

    def _sanitize_wizard_storage(self):
        step_files = None
        try:
            step_files = self.storage.data.get(self.storage.step_files_key)
        except Exception:
            return

        if not isinstance(step_files, dict):
            self.storage.init_data()
            return

        for step, step_files_dict in step_files.items():
            if not isinstance(step_files_dict, dict):
                self.storage.init_data()
                return
            for _, field_dict in step_files_dict.items():
                if not isinstance(field_dict, dict) or 'tmp_name' not in field_dict:
                    self.storage.init_data()
                    return
    
    def dispatch(self, request, *args, **kwargs):
        self._sanitize_wizard_storage()
        try:
            profile = request.user.userprofile
            if not profile.email_verified:
                messages.warning(request, "Please verify your email before registering as a trainer.")
                return redirect('verify_otp')
        except:
            messages.error(request, "Please complete your profile first.")
            return redirect('/')
        
        existing_registration = TrainerRegistration.objects.filter(user=request.user).first()
        if existing_registration:
            messages.info(request, "You have already submitted a trainer registration. View your status below.")
            return redirect('trainer_registration_status')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]
    
    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context['step_titles'] = {
            'basic_info': 'Basic Information',
            'certification': 'Certifications & Photo',
            'documents': 'Verification Documents',
        }
        context['step_icons'] = {
            'basic_info': 'fa-user',
            'certification': 'fa-certificate',
            'documents': 'fa-file-shield',
        }
        return context
    
    def done(self, form_list, **kwargs):
        form_data = [form.cleaned_data for form in form_list]
        
        basic_info = form_data[0]
        cert_data = form_data[1]
        docs_data = form_data[2]
        
        # Convert specialization list to comma-separated string
        specialization_list = basic_info['specialization']
        specialization_str = ', '.join(specialization_list) if isinstance(specialization_list, list) else specialization_list
        
        # Build available_time string from day range and time slots
        day_from = basic_info.get('available_days_from', '')
        day_to = basic_info.get('available_days_to', '')
        time_slots = basic_info.get('available_time_slots', [])
        
        available_time_str = ''
        if day_from and day_to:
            days_part = f"{day_from.capitalize()} to {day_to.capitalize()}"
            if time_slots:
                time_part = ', '.join(time_slots)
                available_time_str = f"{days_part} | Times: {time_part}"
            else:
                available_time_str = days_part
        elif time_slots:
            available_time_str = f"Times: {', '.join(time_slots)}"
        
        registration = TrainerRegistration.objects.create(
            user=self.request.user,
            experience=basic_info['experience'],
            specialization=specialization_str,
            bio=basic_info.get('bio', ''),
            monthly_price=basic_info.get('monthly_price'),
            available_time=available_time_str if available_time_str else None,
        )
        
        # Helper function to get all files from wizard storage
        def get_files_from_storage(step, field_name):
            files = []
            step_files = self.storage.get_step_files(step) or {}
            
            if not step_files:
                return files
            
            # Look for base key and numbered keys
            base_key = f'{step}-{field_name}'
            
            # Check base key first (for single file or first file)
            if base_key in step_files:
                files.append(step_files[base_key])
            
            # Check numbered keys for additional files
            index = 1
            while True:
                numbered_key = f'{base_key}-{index}'
                if numbered_key in step_files:
                    files.append(step_files[numbered_key])
                    index += 1
                else:
                    break
            
            return files
        
        # Get certification files
        cert_files = get_files_from_storage('certification', 'certification')
        
        # Get profile pic
        profile_files = get_files_from_storage('certification', 'profile_pic')
        profile_file = profile_files[0] if profile_files else None
        
        # Get identity proof files
        id_files = get_files_from_storage('documents', 'identity_proof')
        
        # Get experience verification files
        exp_files = get_files_from_storage('documents', 'experience_verification')
        
        # Map doc_type to a short label for filenames
        doc_type_labels = {
            'certification': 'certificate',
            'identity_proof': 'identityproof',
            'experience_verification': 'experience',
        }

        def save_docs(files, doc_type):
            username = self.request.user.username
            label = doc_type_labels.get(doc_type, doc_type)
            for index, f in enumerate(files, start=1):
                if f:  # Only save if file exists
                    # Get file extension
                    original_name = f.name if hasattr(f, 'name') else 'file'
                    file_ext = original_name.split('.')[-1] if '.' in original_name else 'jpg'
                    
                    # Generate username-prefixed sequential filename
                    new_filename = f"{username}_{label}{index}.{file_ext}"
                    
                    # Save with new filename
                    doc = TrainerRegistrationDocument.objects.create(
                        registration=registration,
                        doc_type=doc_type,
                        original_filename=original_name,
                    )
                    # Save file with custom name
                    doc.file.save(new_filename, f, save=True)
        
        save_docs(cert_files, "certification")
        if profile_file:
            username = self.request.user.username
            # Get file extension for profile pic
            original_name = profile_file.name if hasattr(profile_file, 'name') else 'profile.jpg'
            file_ext = original_name.split('.')[-1] if '.' in original_name else 'jpg'
            new_filename = f"{username}_profilepic.{file_ext}"
            
            doc = TrainerRegistrationDocument.objects.create(
                registration=registration,
                doc_type="profile_pic",
                original_filename=original_name,
            )
            doc.file.save(new_filename, profile_file, save=True)
            # Sync profile picture to UserProfile
            try:
                user_profile = self.request.user.userprofile
                user_profile.profile_picture.save(new_filename, profile_file, save=True)
            except:
                pass
        save_docs(id_files, "identity_proof")
        save_docs(exp_files, "experience_verification")
        
        messages.success(self.request, "✅ Trainer registration successfully submitted! We will verify your application soon.")
        return redirect('trainer_registration_status')


@login_required
def trainer_registration_status(request):
    try:
        profile = request.user.userprofile
        if not profile.email_verified:
            messages.warning(request, "Please verify your email first.")
            return redirect('verify_otp')
    except:
        messages.error(request, "Please complete your profile first.")
        return redirect('/')
    
    registration = TrainerRegistration.objects.filter(user=request.user).first()
    
    if not registration:
        messages.info(request, "You haven't submitted a trainer registration yet.")
        return redirect('trainerregestration')
    
    return render(request, 'trainer_registration_status.html', {'registration': registration})


@login_required
def edit_trainer_profile(request):
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied. Trainers only!")
        return redirect('/')
    
    registration = TrainerRegistration.objects.filter(user=request.user).first()
    
    if not registration:
        messages.info(request, "You haven't submitted a trainer registration yet.")
        return redirect('trainerregestration')
    
    if request.method == 'POST':
        form = TrainerProfileEditForm(request.POST)
        if form.is_valid():
            # Update registration
            registration.experience = form.cleaned_data['experience']
            registration.specialization = ','.join(form.cleaned_data['specialization'])
            registration.bio = form.cleaned_data.get('bio', '')
            registration.monthly_price = form.cleaned_data.get('monthly_price')
            
            # Build availability string
            day_from = form.cleaned_data.get('available_days_from')
            day_to = form.cleaned_data.get('available_days_to')
            time_slots = form.cleaned_data.get('available_time_slots', [])
            
            if day_from and day_to and time_slots:
                availability = f"{day_from.capitalize()} to {day_to.capitalize()} | Times: {', '.join(time_slots)}"
                registration.available_time = availability
            elif time_slots:
                registration.available_time = f"Times: {', '.join(time_slots)}"
            else:
                registration.available_time = ''
            
            registration.save()
            messages.success(request, "✅ Profile updated successfully!")
            return redirect('trainer_dashboard')
    else:
        # Pre-populate form with existing data
        initial_data = {
            'experience': registration.experience,
            'specialization': registration.specialization.split(',') if registration.specialization else [],
            'bio': registration.bio or '',
            'monthly_price': registration.monthly_price,
        }
        
        # Parse availability
        if registration.available_time:
            # Try to parse "Monday to Friday | Times: ..."
            if '|' in registration.available_time:
                days_part = registration.available_time.split('|')[0].strip()
                times_part = registration.available_time.split('|')[1].strip()
                
                if ' to ' in days_part:
                    day_from, day_to = days_part.split(' to ')
                    initial_data['available_days_from'] = day_from.strip().lower()
                    initial_data['available_days_to'] = day_to.strip().lower()
                
                if 'Times:' in times_part:
                    time_slots = times_part.replace('Times:', '').strip()
                    initial_data['available_time_slots'] = [t.strip() for t in time_slots.split(',')]
        
        form = TrainerProfileEditForm(initial=initial_data)
    
    return render(request, 'edit_trainer_profile.html', {'form': form, 'registration': registration})


@login_required
def book_trainer(request, trainer_id):
    """Handle trainer booking from users with verified email."""
    trainer_reg = get_object_or_404(TrainerRegistration, id=trainer_id, is_verified=True)

    # Can't book yourself
    if request.user == trainer_reg.user:
        messages.error(request, "You cannot book yourself!")
        return redirect('trainer_profile_detail', trainer_id=trainer_id)

    # Check email verification
    try:
        profile = request.user.userprofile
        if not profile.email_verified:
            messages.warning(request, "Please verify your email before booking a trainer.")
            return redirect('trainer_profile_detail', trainer_id=trainer_id)
    except Exception:
        messages.error(request, "Please complete your profile first.")
        return redirect('trainer_profile_detail', trainer_id=trainer_id)

    if request.method == 'POST':
        # Always use today's date as the booking date, regardless of client input
        booking_date = timezone.now().date()
        user_message = request.POST.get('message', '')

        # Check for existing pending booking
        if TrainerBooking.objects.filter(user=request.user, trainer=trainer_reg, status='pending').exists():
            messages.warning(request, "You already have a pending booking with this trainer.")
            return redirect('trainer_profile_detail', trainer_id=trainer_id)

        # Create booking with today's date
        booking = TrainerBooking.objects.create(
            user=request.user,
            trainer=trainer_reg,
            booking_date=booking_date,
            message=user_message,
        )

        # Create notification for the trainer
        user_full_name = request.user.get_full_name() or request.user.username
        trainer_name = trainer_reg.user.get_full_name() or trainer_reg.user.username
        booking_date_str = booking_date.strftime("%b %d, %Y")

        TrainerNotification.objects.create(
            trainer=trainer_reg,
            booking=booking,
            notif_type='booking',
            title=f'New Booking from {user_full_name}',
            message=f'{user_full_name} wants to start training on {booking_date_str}.'
                    + (f' Message: "{user_message}"' if user_message else ''),
        )

        # Create confirmation notification for the user
        UserNotification.objects.create(
            user=request.user,
            booking=booking,
            notif_type='general',
            title='Booking Request Sent',
            message=f'Your booking request to {trainer_name} for {booking_date_str} has been sent. You\'ll be notified once the trainer responds.',
        )

        # Send email to the trainer
        try:
            send_mail(
                subject=f'FitZone: New Booking Request from {user_full_name}',
                message=(
                    f'Hi {trainer_name},\n\n'
                    f'{user_full_name} has requested to book a training session with you.\n\n'
                    f'Preferred Start Date: {booking_date_str}\n'
                    + (f'Message: "{user_message}"\n' if user_message else '')
                    + f'\nPlease log in to your FitZone dashboard to accept or decline this booking.\n\n'
                    f'Best regards,\nFitZone Team'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[trainer_reg.user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        messages.success(request, "Your booking request has been sent to the trainer!")
        return redirect('trainer_client_dashboard')

    return redirect('trainer_profile_detail', trainer_id=trainer_id)


@login_required
def update_booking_status(request, booking_id):
    booking = get_object_or_404(TrainerBooking, id=booking_id)

    if booking.trainer.user != request.user:
        messages.error(request, "Access denied.")
        return redirect('trainer_client_bookings')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        cancellation_reason = request.POST.get('cancellation_reason', '').strip()
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        if new_status in ('confirmed', 'rejected', 'cancelled'):
            old_status = booking.status
            booking.status = new_status
            
            # If confirmed, set payment details
            if new_status == 'confirmed':
                booking.payment_status = 'pending'
                booking.payment_due_date = timezone.now() + timedelta(days=2)
                booking.amount = booking.trainer.monthly_price
            
            # If rejected, store the reason
            if new_status == 'rejected':
                booking.cancellation_reason = rejection_reason or 'No reason provided'
                booking.cancelled_by = 'trainer'
            
            # If cancelled, store the reason
            if new_status == 'cancelled':
                booking.cancellation_reason = cancellation_reason or 'No reason provided'
                booking.cancelled_by = 'trainer'
            
            booking.save()
            messages.success(request, f"Booking {new_status} successfully!")

            # Notify the user
            trainer_name = booking.trainer.user.get_full_name() or booking.trainer.user.username
            user_name = booking.user.get_full_name() or booking.user.username
            if new_status == 'confirmed':
                payment_due_str = booking.payment_due_date.strftime("%b %d, %Y at %I:%M %p")
                UserNotification.objects.create(
                    user=booking.user,
                    booking=booking,
                    notif_type='payment_required',
                    title='Booking Confirmed - Payment Required!',
                    message=f'Great news! {trainer_name} has accepted your booking for {booking.booking_date.strftime("%b %d, %Y")}. Please complete your payment of ₹{booking.amount} by {payment_due_str}. Check your dashboard for payment details.'
                )
                # Send email to the client
                try:
                    send_mail(
                        subject=f'FitZone: Booking Confirmed by {trainer_name}!',
                        message=(
                            f'Hi {user_name},\n\n'
                            f'Great news! {trainer_name} has accepted your booking request.\n\n'
                            f'Booking Date: {booking.booking_date.strftime("%b %d, %Y")}\n'
                            f'Amount: ₹{booking.amount}\n'
                            f'Payment Due By: {payment_due_str}\n\n'
                            f'Please log in to your FitZone dashboard to complete the payment.\n\n'
                            f'Best regards,\nFitZone Team'
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[booking.user.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
            elif new_status == 'rejected':
                reason_text = rejection_reason or 'No reason provided'
                UserNotification.objects.create(
                    user=booking.user,
                    booking=booking,
                    notif_type='booking_rejected',
                    title='Booking Declined',
                    message=f'{trainer_name} was unable to accept your booking for {booking.booking_date.strftime("%b %d, %Y")}. Reason: {reason_text}'
                )
            elif new_status == 'cancelled':
                reason_text = cancellation_reason or 'No reason provided'
                UserNotification.objects.create(
                    user=booking.user,
                    booking=booking,
                    notif_type='general',
                    title='Booking Cancelled',
                    message=f'{trainer_name} has cancelled your booking for {booking.booking_date.strftime("%b %d, %Y")}. Reason: {reason_text}'
                )
                # Post a system message to the chat room
                chat_room = ChatRoom.objects.filter(
                    trainer=booking.trainer,
                    client=booking.user
                ).first()
                if chat_room:
                    Message.objects.create(
                        room=chat_room,
                        sender=request.user,
                        content=f'⚠️ Booking Cancelled by Trainer\nReason: {reason_text}',
                        message_type='cancellation'
                    )
                    chat_room.updated_at = timezone.now()
                    chat_room.save(update_fields=['updated_at'])
        else:
            messages.error(request, "Invalid action.")

    return redirect('trainer_client_bookings')


@login_required
def trainer_reject_booking(request, booking_id):
    booking = get_object_or_404(TrainerBooking, id=booking_id)

    if booking.trainer.user != request.user:
        messages.error(request, "Access denied.")
        return redirect('trainer_client_bookings')

    if booking.status != 'pending':
        messages.warning(request, "Only pending bookings can be rejected.")
        return redirect('trainer_client_bookings')

    context = {
        'booking': booking,
        'action_title': 'Reject Booking',
        'action_description': 'Please provide a reason for rejecting this booking. The client will be notified.',
        'reason_field': 'rejection_reason',
        'reason_placeholder': 'e.g. Fully booked, schedule conflict, not a good fit...',
        'status_value': 'rejected',
        'submit_label': 'Reject Booking',
        'is_danger': True,
    }
    return render(request, 'trainer_booking_action.html', context)


@login_required
def trainer_cancel_booking(request, booking_id):
    booking = get_object_or_404(TrainerBooking, id=booking_id)

    if booking.trainer.user != request.user:
        messages.error(request, "Access denied.")
        return redirect('trainer_client_bookings')

    if booking.status != 'confirmed':
        messages.warning(request, "Only confirmed bookings can be cancelled.")
        return redirect('trainer_client_bookings')

    context = {
        'booking': booking,
        'action_title': 'Cancel Booking',
        'action_description': 'Please provide a reason for cancelling this booking. The client will see this message in chat.',
        'reason_field': 'cancellation_reason',
        'reason_placeholder': 'e.g. Schedule conflict, payment issue, personal reasons...',
        'status_value': 'cancelled',
        'submit_label': 'Cancel Booking',
        'is_danger': True,
    }
    return render(request, 'trainer_booking_action.html', context)


@login_required
def user_cancel_booking(request, booking_id):
    booking = get_object_or_404(TrainerBooking, id=booking_id, user=request.user)
    # Allow canceling pending bookings or confirmed bookings that haven't been paid
    if booking.status == 'pending' or (booking.status == 'confirmed' and booking.payment_status == 'pending'):
        cancellation_reason = request.POST.get('cancellation_reason', '').strip() if request.method == 'POST' else ''
        booking.status = 'cancelled'
        booking.cancellation_reason = cancellation_reason or 'Cancelled by user'
        booking.cancelled_by = 'user'
        booking.save()
        # Notify trainer
        user_name = request.user.get_full_name() or request.user.username
        reason_text = cancellation_reason or 'No reason provided'
        TrainerNotification.objects.create(
            trainer=booking.trainer,
            booking=booking,
            notif_type='cancellation',
            title='Booking Cancelled',
            message=f'{user_name} has cancelled their booking for {booking.booking_date.strftime("%b %d, %Y")}. Reason: {reason_text}'
        )
        # Post a system message to the chat room
        chat_room = ChatRoom.objects.filter(
            trainer=booking.trainer,
            client=request.user
        ).first()
        if chat_room:
            Message.objects.create(
                room=chat_room,
                sender=request.user,
                content=f'⚠️ Booking Cancelled by User\nReason: {reason_text}',
                message_type='cancellation'
            )
            chat_room.updated_at = timezone.now()
            chat_room.save(update_fields=['updated_at'])
        messages.success(request, "Booking cancelled successfully.")
    else:
        messages.error(request, "Only pending or unpaid confirmed bookings can be cancelled.")
    return redirect('trainer_client_dashboard')

@login_required
def user_complete_booking(request, booking_id):
    booking = get_object_or_404(TrainerBooking, id=booking_id, user=request.user)
    messages.info(request, 'Bookings now complete automatically based on validity. No manual action is required.')
    return redirect('trainer_client_dashboard')

@login_required
def user_review_trainer(request, booking_id):
    from django.shortcuts import render, get_object_or_404, redirect
    from django.contrib import messages
    from .models import TrainerBooking, TrainerReview
    from .forms import TrainerReviewForm

    booking = get_object_or_404(TrainerBooking, id=booking_id, user=request.user)

    # Allow rating only after the paid booking's validity has ended (DateTime based).
    import datetime
    now = timezone.now()
    valid_until_dt = booking.valid_until
    if isinstance(valid_until_dt, datetime.date) and not isinstance(valid_until_dt, datetime.datetime):
        valid_until_dt = timezone.make_aware(datetime.datetime.combine(valid_until_dt, datetime.time.min))

    if not (
        booking.payment_status == 'completed'
        and valid_until_dt is not None
        and valid_until_dt < now
    ):
        messages.error(request, 'You can rate this trainer after your booking validity has ended.')
        return redirect('trainer_client_dashboard')

    review = TrainerReview.objects.filter(user=request.user, trainer=booking.trainer).first()

    if request.method == 'POST':
        form = TrainerReviewForm(request.POST, instance=review)
        if form.is_valid():
            new_review = form.save(commit=False)
            new_review.user = request.user
            new_review.trainer = booking.trainer
            new_review.booking = booking
            new_review.save()
            messages.success(request, 'Thank you for reviewing the trainer!')
            return redirect('trainer_client_dashboard')
    else:
        form = TrainerReviewForm(instance=review)

    return render(request, 'user_review_trainer.html', {'form': form, 'booking': booking})
