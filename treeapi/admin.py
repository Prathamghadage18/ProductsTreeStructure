from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.db import models
from django.forms import Textarea
from django.utils.timezone import localtime

from .models import AllowedUser, ExcelUploadTracker, Node, Note


class NoteInline(admin.StackedInline):
    model = Note
    can_delete = True
    extra = 0
    fields = ("content", "updated_at")
    readonly_fields = ("updated_at",)
    max_num = 1


class HasNoteFilter(admin.SimpleListFilter):
    title = "has note"
    parameter_name = "has_note"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        v = self.value()
        if v == "yes":
            return queryset.filter(note__isnull=False)
        if v == "no":
            return queryset.filter(note__isnull=True)
        return queryset


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ("node_id", "has_note", "note_updated")
    search_fields = ("node_id", "note__content")
    list_filter = (HasNoteFilter, ("note__updated_at", DateFieldListFilter))
    inlines = [NoteInline]
    list_select_related = ("note",)

    def has_note(self, obj):
        try:
            return obj.note is not None
        except Note.DoesNotExist:
            return False
    has_note.boolean = True
    has_note.short_description = "Has note"
    has_note.admin_order_field = "note__id"

    def note_updated(self, obj):
        try:
            return localtime(obj.note.updated_at).strftime("%Y-%m-%d %H:%M")
        except Note.DoesNotExist:
            return "-"
    note_updated.short_description = "Note updated"
    note_updated.admin_order_field = "note__updated_at"
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("node", "updated_human", "short_content")
    search_fields = ("content", "node__node_id")
    list_filter = (("updated_at", DateFieldListFilter),)
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)
    readonly_fields = ("updated_at",)
    autocomplete_fields = ("node",)
    list_select_related = ("node",)
    list_per_page = 50
    fieldsets = (
        (None, {"fields": ("node", "content")}),
        ("Meta", {"fields": ("updated_at",)}),
    )
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 30, "cols": 100})},
    }

    def updated_human(self, obj):
        return localtime(obj.updated_at).strftime("%Y-%m-%d %H:%M")
    updated_human.admin_order_field = "updated_at"
    updated_human.short_description = "Updated"

    def short_content(self, obj):
        base = obj.content_without_timestamp()
        if not base:
            return ""
        lines = base.strip().splitlines()
        preview = "\n".join(lines[:3]).strip()
        return (preview[:100] + "...") if len(preview) > 100 or len(lines) > 3 else preview
    
    def save_model(self, request, obj, form, change):
        obj.content = form.cleaned_data.get('content', obj.content)
        obj.save(modified_by=request.user)


@admin.register(ExcelUploadTracker)
class ExcelUploadTrackerAdmin(admin.ModelAdmin):
    list_display = ("is_uploaded", "uploaded_at", "uploaded_by", "file_name")
    readonly_fields = ("uploaded_at", "uploaded_by", "file_name", "is_uploaded")
    
    def has_add_permission(self, request):
        return not ExcelUploadTracker.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(AllowedUser)
class AllowedUserAdmin(admin.ModelAdmin):
    list_display = ("user", "get_username", "get_email", "created_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user",)
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = "Username"
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email"
    
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def save_model(self, request, obj, form, change):
        if not change and AllowedUser.objects.count() >= 9:
            from django.contrib import messages
            messages.error(request, "Maximum of 9 allowed users reached. Cannot add more.")
            return
        super().save_model(request, obj, form, change)