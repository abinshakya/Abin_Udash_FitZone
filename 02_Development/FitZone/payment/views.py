from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from membership.models import MembershipPlan, UserMembership
from django.contrib import messages
from login_logout_register.models import UserProfile
from .models import KhaltiPayment
from django.conf import settings
import requests
import uuid
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from trainer.models import TrainerBooking


@login_required
def checkout(request, plan_id):
    try:
        profile = UserProfile.objects.get(user=request.user)
        
        if not profile.email_verified:
            messages.error(request, "Please verify your email address before purchasing a membership.")
            return redirect('verify_otp')
    except UserProfile.DoesNotExist:
        messages.error(request, "Profile not found. Please complete your registration.")
        return redirect('register')
    
    plan = get_object_or_404(MembershipPlan, id=plan_id, is_active=True)
    context = {
        'plan': plan,
        'user': request.user
    }
    return render(request, 'checkout.html', context)


@login_required
def initiate_khalti_payment(request, plan_id):
    try:
        profile = UserProfile.objects.get(user=request.user)
        if not profile.email_verified:
            messages.error(request, "Please verify your email to proceed with payment.")
            return redirect('verify_otp')
    except UserProfile.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect('register')
    
    plan = get_object_or_404(MembershipPlan, id=plan_id, is_active=True)
    
    # Generate unique purchase order ID
    purchase_order_id = f"FZ-{request.user.id}-{uuid.uuid4().hex[:8].upper()}"
    
    # Amount in paisa (NPR * 100)
    amount_in_paisa = int(plan.price * 100)
    
    # Build return URL (absolute URL)
    return_url = request.build_absolute_uri(reverse('payment_callback'))
    website_url = request.build_absolute_uri('/')
    
    # Prepare payload for Khalti
    payload = {
        "return_url": return_url,
        "website_url": website_url,
        "amount": amount_in_paisa,
        "purchase_order_id": purchase_order_id,
        "purchase_order_name": f"{plan.name} Membership",
        "customer_info": {
            "name": request.user.get_full_name() or request.user.username,
            "email": request.user.email,
            "phone": getattr(profile, 'phone', "9800000000")
        }
    }
    
    # Khalti API headers
    headers = {
        "Authorization": f"key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Call Khalti initiate API
        api_url = f"{settings.KHALTI_API_URL}/epayment/initiate/"
        print(f"DEBUG: Calling Khalti API at: {api_url}")
        print(f"DEBUG: Payload: {payload}")
        print(f"DEBUG: Headers: Authorization: key {settings.KHALTI_SECRET_KEY[:10]}...")
        
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"DEBUG: Response Status: {response.status_code}")
        print(f"DEBUG: Response Headers: {dict(response.headers)}")
        print(f"DEBUG: Response Body: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Save payment record
            payment = KhaltiPayment.objects.create(
                user=request.user,
                membership_plan=plan,
                pidx=data['pidx'],
                purchase_order_id=purchase_order_id,
                purchase_order_name=payload['purchase_order_name'],
                amount=amount_in_paisa,
                payment_url=data['payment_url'],
                status='Initiated',
                expires_at=timezone.now() + timedelta(minutes=10)
            )
            
            # Redirect to Khalti payment page
            return redirect(data['payment_url'])
        else:
            # Log detailed error for debugging
            error_msg = f"Khalti API Error ({response.status_code}): {response.text[:200]}"
            print(f"DEBUG: {error_msg}")
            messages.error(request, f"Payment initialization failed. Please try again or contact support.")
            return redirect('checkout', plan_id=plan_id)
            
    except requests.RequestException as e:
        print(f"DEBUG: Payment gateway connection error: {str(e)}")
        messages.error(request, f"Payment gateway connection error. Please try again.")
        return redirect('checkout', plan_id=plan_id)
    except Exception as e:
        print(f"DEBUG: Unexpected error in payment initiation: {str(e)}")
        messages.error(request, f"An unexpected error occurred. Please try again.")
        return redirect('checkout', plan_id=plan_id)


@csrf_exempt
def payment_callback(request):
    # Handle Khalti payment callback
    pidx = request.GET.get('pidx')
    status = request.GET.get('status')
    transaction_id = request.GET.get('transaction_id')
    
    if not pidx:
        messages.error(request, "Invalid payment callback.")
        return redirect('membership')
    
    try:
        payment = KhaltiPayment.objects.get(pidx=pidx)
        
        # Update transaction ID
        if transaction_id:
            payment.transaction_id = transaction_id
        
        # Update status from callback
        if status:
            payment.status = status
            payment.save()
        
        # Verify payment with Khalti lookup API
        if status == 'Completed':
            return redirect('verify_payment', pidx=pidx)
        else:
            messages.warning(request, f"Payment {status}. Please try again.")
            return redirect('payment_failed', pidx=pidx)
            
    except KhaltiPayment.DoesNotExist:
        messages.error(request, "Payment record not found.")
        return redirect('membership')


@login_required
def verify_payment(request, pidx):
    # Verify payment with Khalti lookup API
    payment = get_object_or_404(KhaltiPayment, pidx=pidx, user=request.user)
    
    # Prepare lookup request
    headers = {
        "Authorization": f"key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {"pidx": pidx}
    
    try:
        response = requests.post(
            f"{settings.KHALTI_API_URL}/epayment/lookup/",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Update payment record
            payment.status = data.get('status', payment.status)
            payment.transaction_id = data.get('transaction_id', payment.transaction_id)
            payment.total_amount = data.get('total_amount', payment.amount)
            payment.fee = data.get('fee', 0)
            payment.refunded = data.get('refunded', False)
            payment.mobile = data.get('mobile')
            payment.save()
            
            if payment.status == 'Completed':
                # Check payment type and handle accordingly
                if payment.payment_type == 'booking' and payment.booking:
                    # Handle booking payment completion
                    booking = payment.booking
                    booking.payment_status = 'completed'
                    booking.save()
                    messages.success(request, "Payment successful! Your trainer booking has been confirmed and paid.")
                    return render(request, 'payment_success.html', {'payment': payment})
                else:
                    # Handle membership payment completion
                    try:
                        user_profile = UserProfile.objects.get(user=request.user)
                        
                        # Create UserMembership record
                        if payment.membership_plan:
                            end_date = timezone.now() + timedelta(days=payment.membership_plan.get_duration_days())
                            UserMembership.objects.create(
                                user=request.user,
                                membership_plan=payment.membership_plan,
                                end_date=end_date,
                                is_active=True
                            )
                        
                        # Change role to member
                        if user_profile.role == 'user':
                            user_profile.role = 'member'
                            user_profile.save()
                            messages.success(request, "Payment successful! Your membership has been activated. You are now a member!")
                        else:
                            messages.success(request, "Payment successful! Your membership has been renewed.")
                    except UserProfile.DoesNotExist:
                        messages.success(request, "Payment successful!")
                    
                    return render(request, 'payment_success.html', {'payment': payment})
            else:
                messages.warning(request, f"Payment status: {payment.status}")
                return render(request, 'payment_failed.html', {'payment': payment})
        else:
            messages.error(request, "Payment verification failed.")
            return render(request, 'payment_failed.html', {'payment': payment})
            
    except requests.RequestException as e:
        messages.error(request, f"Verification error: {str(e)}")
        return render(request, 'payment_failed.html', {'payment': payment})


@login_required
def payment_failed(request, pidx):
    payment = get_object_or_404(KhaltiPayment, pidx=pidx, user=request.user)
    return render(request, 'payment_failed.html', {'payment': payment})


# ──────────────────────────────────────────────
#  TRAINER BOOKING PAYMENT
# ──────────────────────────────────────────────

@login_required
# Checkout page for a trainer booking payment
def booking_checkout(request, booking_id):
    booking = get_object_or_404(
        TrainerBooking,
        id=booking_id,
        user=request.user,
        status='confirmed',
        payment_status='pending'
    )
    
    try:
        profile = UserProfile.objects.get(user=request.user)
        if not profile.email_verified:
            messages.error(request, "Please verify your email address before making a payment.")
            return redirect('verify_otp')
    except UserProfile.DoesNotExist:
        messages.error(request, "Profile not found. Please complete your registration.")
        return redirect('register')
    
    context = {
        'booking': booking,
        'user': request.user,
    }
    return render(request, 'booking_checkout.html', context)


@login_required
# Initiate Khalti payment for a trainer booking
def initiate_booking_payment(request, booking_id):
    booking = get_object_or_404(
        TrainerBooking,
        id=booking_id,
        user=request.user,
        status='confirmed',
        payment_status='pending'
    )
    
    try:
        profile = UserProfile.objects.get(user=request.user)
        if not profile.email_verified:
            messages.error(request, "Please verify your email to proceed with payment.")
            return redirect('verify_otp')
    except UserProfile.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect('register')
    
    if not booking.amount or booking.amount <= 0:
        messages.error(request, "Invalid booking amount. Please contact the trainer.")
        return redirect('trainer_client_dashboard')
    
    # Generate unique purchase order ID
    purchase_order_id = f"FZB-{request.user.id}-{booking.id}-{uuid.uuid4().hex[:8].upper()}"
    
    # Amount in paisa (NPR * 100)
    amount_in_paisa = int(booking.amount * 100)
    
    trainer_name = booking.trainer.user.get_full_name() or booking.trainer.user.username
    
    # Build return URL
    return_url = request.build_absolute_uri(reverse('payment_callback'))
    website_url = request.build_absolute_uri('/')
    
    # Prepare payload for Khalti
    payload = {
        "return_url": return_url,
        "website_url": website_url,
        "amount": amount_in_paisa,
        "purchase_order_id": purchase_order_id,
        "purchase_order_name": f"Trainer Booking - {trainer_name}",
        "customer_info": {
            "name": request.user.get_full_name() or request.user.username,
            "email": request.user.email,
            "phone": getattr(profile, 'phone', "9800000000")
        }
    }
    
    # Khalti API headers
    headers = {
        "Authorization": f"key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        api_url = f"{settings.KHALTI_API_URL}/epayment/initiate/"
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Save payment record
            payment = KhaltiPayment.objects.create(
                user=request.user,
                booking=booking,
                payment_type='booking',
                pidx=data['pidx'],
                purchase_order_id=purchase_order_id,
                purchase_order_name=payload['purchase_order_name'],
                amount=amount_in_paisa,
                payment_url=data['payment_url'],
                status='Initiated',
                expires_at=timezone.now() + timedelta(minutes=10)
            )
            
            # Redirect to Khalti payment page
            return redirect(data['payment_url'])
        else:
            messages.error(request, "Payment initialization failed. Please try again or contact support.")
            return redirect('booking_checkout', booking_id=booking_id)
            
    except requests.RequestException as e:
        messages.error(request, "Payment gateway connection error. Please try again.")
        return redirect('booking_checkout', booking_id=booking_id)
    except Exception as e:
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect('booking_checkout', booking_id=booking_id)
