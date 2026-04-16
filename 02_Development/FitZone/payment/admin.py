from django.contrib import admin
from .models import KhaltiPayment, TrainerPaymentRequest
from django.utils.html import format_html


@admin.register(KhaltiPayment)
class KhaltiPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'purchase_order_id',
        'user',
        'payment_type',
        'amount_display',
        'status_badge',
        'created_at'
    ]

    list_per_page = 10
    list_select_related = ('user', 'membership_plan', 'booking')
    
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


@admin.register(TrainerPaymentRequest)
class TrainerPaymentRequestAdmin(admin.ModelAdmin):
    list_display = ['trainer', 'get_client', 'amount', 'status', 'has_receipt', 'created_at']
    list_filter = ['status', 'created_at']
    list_editable = ['status']
    search_fields = ['trainer__user__username', 'booking__user__username', 'bank_name', 'account_holder_name']
    readonly_fields = ['trainer', 'booking', 'amount', 'bank_name', 'account_holder_name', 'account_number', 'bank_qr', 'created_at', 'updated_at']

    fieldsets = (
        ('Request Info', {
            'fields': ('trainer', 'booking', 'amount', 'status')
        }),
        ('Trainer Bank Details', {
            'fields': ('bank_name', 'account_holder_name', 'account_number', 'bank_qr')
        }),
        ('Admin Action', {
            'fields': ('receipt', 'admin_note')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_client(self, obj):
        return obj.booking.user.get_full_name() or obj.booking.user.username
    get_client.short_description = 'Client'

    def has_receipt(self, obj):
        if obj.receipt:
            return format_html('<span style="color:{};font-weight:700;">{}</span>', '#16a34a', '✓ Uploaded')
        return format_html('<span style="color:{};">{}</span>', '#d97706', '—')
    has_receipt.short_description = 'Receipt'
