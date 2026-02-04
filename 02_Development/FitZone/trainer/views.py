# views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect

from .forms import TrainerRegistrationForm, validate_file_size, validate_content_type, ALLOWED_IMAGE_TYPES, ALLOWED_DOC_TYPES
from .models import TrainerRegistrationDocument  # you need this model (see below)


def trainer(request):
    return render(request,'trainer.html')

@login_required
def trainer_dashboard(request):
    # Check if user is a trainer
    try:
        profile = request.user.userprofile
        if profile.role != 'trainer':
            messages.warning(request, "Access denied. Trainers only!")
            return redirect('/')
    except:
        messages.warning(request, "Access denied. Trainers only!")
        return redirect('/')
    
    return render(request, 'trainer_dashboard.html')


@login_required
def trainerregestration(request):
    if request.method == "POST":
        form = TrainerRegistrationForm(request.POST)

        # Get multiple files
        cert_files = request.FILES.getlist("certification")
        profile_files = request.FILES.getlist("profile_pic")
        id_files = request.FILES.getlist("identity_proof")
        exp_files = request.FILES.getlist("experience_verification")

        # Collect file validation errors
        file_errors = []

        def validate_files(files, allowed_types, label):
            for f in files:
                try:
                    validate_file_size(f)
                    validate_content_type(f, allowed_types)
                except ValidationError as e:
                    file_errors.append(f"{label}: {f.name} → {e.messages[0]}")

        # Validate
        validate_files(cert_files, ALLOWED_DOC_TYPES, "Certification")
        validate_files(profile_files, ALLOWED_IMAGE_TYPES, "Profile Picture")
        validate_files(id_files, ALLOWED_DOC_TYPES, "Identity Proof")
        validate_files(exp_files, ALLOWED_DOC_TYPES, "Experience Verification")

        # Require exactly 1 profile photo
        if len(profile_files) == 0:
            file_errors.append("Profile Picture: Please upload a profile photo.")
        elif len(profile_files) > 1:
            file_errors.append("Profile Picture: Only one profile picture is allowed.")

        # Require at least one file for each document type
        if len(cert_files) == 0:
            file_errors.append("Certification: Please upload at least one certification document.")
        if len(id_files) == 0:
            file_errors.append("Identity Proof: Please upload at least one identity proof document.")
        if len(exp_files) == 0:
            file_errors.append("Experience Verification: Please upload at least one experience verification document.")

        if form.is_valid() and not file_errors:
            reg = form.save(commit=False)
            reg.user = request.user
            reg.save()

            # Save files in separate model
            def save_docs(files, doc_type):
                for f in files:
                    TrainerRegistrationDocument.objects.create(
                        registration=reg,
                        doc_type=doc_type,
                        file=f
                    )

            save_docs(cert_files, "certification")
            save_docs(profile_files, "profile_pic")
            save_docs(id_files, "identity_proof")
            save_docs(exp_files, "experience_verification")

            messages.success(request, "✅ Your trainer registration has been submitted successfully!")
            return redirect("trainerregestration")

        # Show form errors nicely
        if not form.is_valid():
            messages.error(request, "❌ Please fix the highlighted errors in the form.")

        # Show file errors nicely
        for err in file_errors:
            messages.error(request, f"❌ {err}")

    else:
        form = TrainerRegistrationForm()

    return render(request, "trainerregestration.html", {"form": form})

