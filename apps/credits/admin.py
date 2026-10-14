from django.contrib import admin

from apps.credits.models import CreditLedger, CreditPack


@admin.register(CreditPack)
class CreditPackAdmin(admin.ModelAdmin):

    list_display        = ("member", "credits", "granted_on", "expires_on", "granted_by", "created_at")
    list_filter         = ("expires_on",)
    search_fields       = ("member__email",)
    list_select_related = ("member", "granted_by")


@admin.register(CreditLedger)
class CreditLedgerAdmin(admin.ModelAdmin):
    
    list_display        = ("member", "pack", "cause", "amount", "created_at")
    list_filter         = ("cause",)
    search_fields       = ("member__email",)
    list_select_related = ("member", "pack")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False