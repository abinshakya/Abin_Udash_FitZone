import json
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
from membership.models import UserMembership, MembershipPlan
from trainer.models import TrainerRegistration, TrainerBooking
from payment.models import KhaltiPayment

def admin_stats(request):
    if request.path.startswith('/admin/'):
        try:
            # Basic Stats
            stats = {
                'user_count': User.objects.count(),
                'active_subs': UserMembership.objects.filter(is_active=True).count(),
                'pending_tasks': TrainerRegistration.objects.filter(is_verified=False).count(),
            }

            # Analytics Data (only for main dashboard index)
            if request.path == '/admin/':
                last_6_months = timezone.now() - timedelta(days=180)
                
                # 1. User Growth
                user_growth = (
                    User.objects.filter(date_joined__gte=last_6_months)
                    .annotate(month=TruncMonth('date_joined'))
                    .values('month')
                    .annotate(count=Count('id'))
                    .order_by('month')
                )
                stats['user_growth_labels'] = json.dumps([x['month'].strftime('%b') for x in user_growth])
                stats['user_growth_data'] = json.dumps([x['count'] for x in user_growth])

                # 2. Membership Mix
                membership_mix = (
                    MembershipPlan.objects.annotate(count=Count('usermembership'))
                    .values('name', 'duration', 'count')
                )
                
                # Mapping duration code to display text
                duration_map = dict(MembershipPlan.DURATION_CHOICES)
                stats['membership_labels'] = json.dumps([
                    f"{x['name']} ({duration_map.get(x['duration'], x['duration'])})" 
                    for x in membership_mix
                ])
                stats['membership_data'] = json.dumps([x['count'] for x in membership_mix])

                # 3. Booking Status
                booking_stats = (
                    TrainerBooking.objects.values('status')
                    .annotate(count=Count('id'))
                )
                stats['booking_labels'] = json.dumps([x['status'].capitalize() for x in booking_stats])
                stats['booking_data'] = json.dumps([x['count'] for x in booking_stats])

                # 4. Revenue Trends
                revenue_trends = (
                    KhaltiPayment.objects.filter(status='Completed', created_at__gte=last_6_months)
                    .annotate(month=TruncMonth('created_at'))
                    .values('month')
                    .annotate(total=Sum('amount'))
                    .order_by('month')
                )
                stats['revenue_labels'] = json.dumps([x['month'].strftime('%b') for x in revenue_trends])
                stats['revenue_data'] = json.dumps([float(x['total'] / 100) for x in revenue_trends]) # paisa to rupees

            return stats
        except Exception as e:
            # Fallback for missing apps/models or migration issues
            return {
                'error': str(e),
                'user_count': 0,
                'active_subs': 0,
                'pending_tasks': 0,
                'user_growth_labels': '[]',
                'user_growth_data': '[]',
                'membership_labels': '[]',
                'membership_data': '[]',
                'booking_labels': '[]',
                'booking_data': '[]',
                'revenue_labels': '[]',
                'revenue_data': '[]',
            }
    return {}
