from django.contrib import admin
from .models import KhaltiPayment
from django.utils.html import format_html


@admin.register(KhaltiPayment)
class KhaltiPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'purchase_order_id',
        'user',
        'payment_type',
        'membership_plan',
        'booking',
        'amount_display',
        'status_badge',
        'transaction_id',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'payment_type',
        'refunded',
        'created_at',
        'membership_plan'
    ]
    
    search_fields = [
        'purchase_order_id',
        'transaction_id',
        'pidx',
        'user__username',
        'user__email'
    ]
    
    readonly_fields = [
        'pidx',
        'transaction_id',
        'purchase_order_id',
        'created_at',
        'updated_at',
        'payment_url',
        'amount_in_rupees'
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'payment_type', 'membership_plan', 'booking')
        }),
        ('Payment Details', {
            'fields': (
                'purchase_order_id',
                'purchase_order_name',
                'amount',
                'amount_in_rupees',
                'total_amount',
                'fee'
            )
        }),
        ('Transaction Information', {
            'fields': (
                'pidx',
                'transaction_id',
                'status',
                'refunded',
                'mobile',
                'payment_url'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'expires_at')
        })
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def amount_display(self, obj):
        return f"NPR {obj.amount_in_rupees}"
    amount_display.short_description = 'Amount'
    
    def status_badge(self, obj):
        colors = {
            'Completed': '#22c55e',
            'Pending': '#f59e0b',
            'Initiated': '#3b82f6',
            'Failed': '#ef4444',
            'Expired': '#6b7280',
            'User canceled': '#ef4444',
            'Refunded': '#8b5cf6',
            'Partially refunded': '#a855f7',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{}; color:white; padding:4px 12px; border-radius:12px; font-size:11px; font-weight:600;">{}</span>',
            color,
            obj.status
        )
    status_badge.short_description = 'Status'
