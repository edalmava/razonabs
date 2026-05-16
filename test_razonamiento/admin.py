from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, Question, Test, TestAttempt, AttemptQuestion, StudentResponse

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "role", "is_active"]
    fieldsets = UserAdmin.fieldsets + (
        (_("Información de Rol"), {"fields": ("role", "uid")}),
    )
    readonly_fields = ["uid"]

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["title", "stimulus_preview", "correct_option", "is_active"]
    
    fieldsets = (
        (_("General"), {"fields": ("title", "is_active")}),
        (_("Estímulo"), {"fields": ("stimulus_image", "correct_option")}),
        (_("Opciones de Respuesta"), {
            "fields": (
                "option_1_image", "option_2_image", "option_3_image",
                "option_4_image", "option_5_image", "option_6_image"
            ),
            "description": _("Suba las 6 imágenes correspondientes a las opciones de respuesta.")
        }),
    )

    def stimulus_preview(self, obj):
        if obj.stimulus_image:
            return format_html('<img src="{}" style="height:50px;"/>', obj.stimulus_image.url)
        return "-"
    stimulus_preview.short_description = _("Vista previa")

class AttemptQuestionInline(admin.TabularInline):
    model = AttemptQuestion
    extra = 0
    readonly_fields = ["question", "order"]

class StudentResponseInline(admin.TabularInline):
    model = StudentResponse
    extra = 0
    readonly_fields = ["question", "selected_option", "time_taken", "is_correct"]

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ["name", "seconds_per_question", "num_questions", "is_active"]
    list_filter = ["is_active"]

@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ["student", "test", "status", "start_date"]
    list_filter = ["status", "test"]
    inlines = [AttemptQuestionInline, StudentResponseInline]
    readonly_fields = ["student", "test", "start_date", "end_date"]
