from django.contrib import admin

from apps.bookings.models import Booking, WaitlistEntry



@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display        = ("member", "class_session", "status", "source", "credits_charged", "booked_at", "cancellation_outcome")
    list_filter         = ("status", "source", "cancellation_outcome")
    search_fields       = ("member__email", "idempotency_key")
    list_select_related = ("member", "class_session__studio")



@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display        = ("member", "class_session", "status", "joined_at", "promoted_at", "left_at")
    list_filter         = ("status",)
    search_fields       = ("member__email",)
    list_select_related = ("member", "class_session__studio")