from django.contrib import admin

from apps.studios.models import ClassSession, Studio


@admin.register(Studio)
class StudioAdmin(admin.ModelAdmin[Studio]):
    list_display  = ("name", "timezone", "cancellation_cutoff_hours", "created_at")
    search_fields = ("name",)


@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin[ClassSession]):
    list_display        = ("studio", "starts_at", "duration_minutes", "spots", "credit_cost")
    list_filter         = ("studio",)
    date_hierarchy      = "starts_at"
    list_select_related = ("studio",)
