# views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from formtools.wizard.views import SessionWizardView
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os

from .forms import (
    Step1BasicInfoForm, Step2CertificationForm, Step3DocumentsForm
)
from .models import TrainerRegistrationDocument, TrainerRegistration


def trainer(request):
    return render(request,'trainer.html')

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
    
    return render(request, 'trainer_dashboard.html', {'registration': registration})


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
    
    def dispatch(self, request, *args, **kwargs):
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
        
        registration = TrainerRegistration.objects.create(
            user=self.request.user,
            experience=basic_info['experience'],
            specialization=basic_info['specialization'],
            bio=basic_info.get('bio', ''),
        )
        
        cert_files = cert_data.get('certification', [])
        if not isinstance(cert_files, list):
            cert_files = [cert_files] if cert_files else []
            
        profile_file = cert_data.get('profile_pic')
        
        id_files = docs_data.get('identity_proof', [])
        if not isinstance(id_files, list):
            id_files = [id_files] if id_files else []
            
        exp_files = docs_data.get('experience_verification', [])
        if not isinstance(exp_files, list):
            exp_files = [exp_files] if exp_files else []
        
        def save_docs(files, doc_type):
            for f in files:
                TrainerRegistrationDocument.objects.create(
                    registration=registration,
                    doc_type=doc_type,
                    file=f
                )
        
        save_docs(cert_files, "certification")
        if profile_file:
            TrainerRegistrationDocument.objects.create(
                registration=registration,
                doc_type="profile_pic",
                file=profile_file
            )
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
