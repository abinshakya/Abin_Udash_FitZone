from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from membership.models import MembershipPlan, UserMembership
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from login_logout_register.models import UserProfile
from notifications.models import UserNotification


def _send_membership_warning_if_needed(membership):
    if not membership or not membership.is_active or membership.expiry_warning_sent:
        return

    now = timezone.now()
    if not (now < membership.end_date <= now + timedelta(days=2)):
        return

    UserNotification.objects.create(
        user=membership.user,
        notif_type='general',
        title='Membership Expiry Reminder',
        message=(
            f'Your {membership.membership_plan.name} membership will expire on '
            f'{membership.end_date.strftime("%b %d, %Y")}. Please renew to keep access active.'
        ),
    )

    if membership.user.email:
        subject = f'FitZone membership expires in 2 days: {membership.membership_plan.name}'
        message = (
            f'Hi {membership.user.first_name or membership.user.username},\n\n'
            f'Your FitZone membership for {membership.membership_plan.name} will expire on '
            f'{membership.end_date.strftime("%b %d, %Y")}.\n\n'
            'Please renew your membership before it expires to keep your access active.\n\n'
            'Best regards,\nFitZone Team'
        )
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [membership.user.email],
                fail_silently=False,
            )
        except Exception:
            pass

    membership.expiry_warning_sent = True
    membership.save(update_fields=['expiry_warning_sent'])

def membership_page(request):
    plans = MembershipPlan.objects.all()
    
    email_verified = False
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            email_verified = profile.email_verified
        except UserProfile.DoesNotExist:
            pass
    
    return render(request, "membership.html", {
        "plans": plans,
        "email_verified": email_verified
    })


@login_required
def my_plans_page(request):
    try:
        profile = request.user.userprofile
        if profile.role != 'member':
            messages.warning(request, "Membership required to access this page.")
            return redirect('/membership/')
    except UserProfile.DoesNotExist:
        messages.warning(request, "Membership required to access this page.")
        return redirect('/membership/')

    membership = UserMembership.objects.filter(
        user=request.user
    ).select_related('membership_plan').order_by('-created_at').first()

    _send_membership_warning_if_needed(membership)
    if membership:
        membership.refresh_from_db(fields=['expiry_warning_sent'])

    plan = membership.membership_plan if membership else None

    return render(request, "member/my_plans.html", {
        "membership": membership,
        "plan": plan,
    })


