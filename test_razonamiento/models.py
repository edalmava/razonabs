import uuid
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# ---------------------------------------------------------------------------
# Utilidades compartidas
# ---------------------------------------------------------------------------

def question_media_path(instance, filename: str) -> str:
    """Ruta de carga para las imágenes de la pregunta."""
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"questions/{instance.pk or 'new'}/{uuid.uuid4().hex}.{ext}"

# ---------------------------------------------------------------------------
# Mixin de timestamps
# ---------------------------------------------------------------------------

class TimeStampedModel(models.Model):
    """Mixin abstracto que agrega created_at y updated_at."""
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("fecha de actualización"), auto_now=True)

    class Meta:
        abstract = True

# ---------------------------------------------------------------------------
# 1. USUARIOS
# ---------------------------------------------------------------------------

class CustomUser(AbstractUser, TimeStampedModel):
    class Role(models.TextChoices):
        STUDENT = "student", _("Estudiante")
        TEACHER = "teacher", _("Docente")

    uid = models.UUIDField(_("identificador único"), default=uuid.uuid4, editable=False, unique=True)
    role = models.CharField(_("rol"), max_length=10, choices=Role.choices, default=Role.STUDENT, db_index=True)
    
    groups = models.ManyToManyField("auth.Group", related_name="custom_user_groups", blank=True)
    user_permissions = models.ManyToManyField("auth.Permission", related_name="custom_user_permissions", blank=True)

    class Meta:
        verbose_name = _("usuario")
        verbose_name_plural = _("usuarios")

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_teacher(self) -> bool:
        return self.role == self.Role.TEACHER

# ---------------------------------------------------------------------------
# 2. BANCO DE PREGUNTAS
# ---------------------------------------------------------------------------

class Question(TimeStampedModel):
    title = models.CharField(_("título interno"), max_length=200)
    stimulus_image = models.ImageField(_("imagen estímulo"), upload_to=question_media_path)
    
    # 6 campos de opciones individuales opcionales
    option_1_image = models.ImageField(_("opción 1"), upload_to=question_media_path, null=True, blank=True)
    option_2_image = models.ImageField(_("opción 2"), upload_to=question_media_path, null=True, blank=True)
    option_3_image = models.ImageField(_("opción 3"), upload_to=question_media_path, null=True, blank=True)
    option_4_image = models.ImageField(_("opción 4"), upload_to=question_media_path, null=True, blank=True)
    option_5_image = models.ImageField(_("opción 5"), upload_to=question_media_path, null=True, blank=True)
    option_6_image = models.ImageField(_("opción 6"), upload_to=question_media_path, null=True, blank=True)

    correct_option = models.PositiveSmallIntegerField(
        _("opción correcta"), 
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        help_text=_("Número de la opción correcta (1 a 6).")
    )
    
    is_active = models.BooleanField(_("activa"), default=True)

    class Meta:
        verbose_name = _("pregunta")
        verbose_name_plural = _("preguntas")

    def __str__(self) -> str:
        return f"[#{self.pk}] {self.title}"

# ---------------------------------------------------------------------------
# 3. TEST
# ---------------------------------------------------------------------------

class Test(TimeStampedModel):
    name = models.CharField(_("nombre"), max_length=200)
    description = models.TextField(_("instrucciones"), blank=True)
    
    seconds_per_question = models.PositiveIntegerField(
        _("segundos por pregunta"),
        default=60,
        help_text=_("Tiempo límite individual para cada pregunta.")
    )
    
    num_questions = models.PositiveSmallIntegerField(
        _("número de preguntas (N)"),
        default=10,
        help_text=_("Cantidad de preguntas que se seleccionarán para el test.")
    )

    max_attempts = models.PositiveSmallIntegerField(
        _("máximo de intentos"), 
        default=1,
        help_text=_("Número de veces que un estudiante puede realizar este test.")
    )

    is_active = models.BooleanField(_("activo"), default=False)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, limit_choices_to={"role": CustomUser.Role.TEACHER})
    questions = models.ManyToManyField(Question, related_name='tests', blank=True, verbose_name=_("preguntas asignadas"))

    class Meta:
        verbose_name = _("test")
        verbose_name_plural = _("tests")

    def __str__(self) -> str:
        return self.name

# ---------------------------------------------------------------------------
# 4. INTENTO (SESIÓN)
# ---------------------------------------------------------------------------

class TestAttempt(TimeStampedModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", _("En curso")
        FINISHED = "finished", _("Finalizado")

    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="attempts")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="attempts")
    status = models.CharField(_("estado"), max_length=15, choices=Status.choices, default=Status.IN_PROGRESS)
    
    start_date = models.DateTimeField(_("fecha inicio"), auto_now_add=True)
    end_date = models.DateTimeField(_("fecha fin"), null=True, blank=True)

    class Meta:
        verbose_name = _("intento de test")
        verbose_name_plural = _("intentos de test")

    def __str__(self) -> str:
        return f"{self.student.username} - {self.test.name} ({self.status})"

    @property
    def score(self):
        return self.responses.filter(is_correct=True).count()

    @property
    def score_percentage(self):
        total = self.test.num_questions
        if total == 0: return 0
        return (self.score / total) * 100

class AttemptQuestion(models.Model):
    """Tabla intermedia para fijar la secuencia aleatoria."""
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name="test_questions")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField(_("orden"))

    class Meta:
        ordering = ["order"]
        unique_together = ["attempt", "question"]

# ---------------------------------------------------------------------------
# 5. RESPUESTAS
# ---------------------------------------------------------------------------

class StudentResponse(TimeStampedModel):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.PositiveSmallIntegerField(_("opción seleccionada"), null=True, blank=True)
    time_taken = models.PositiveIntegerField(_("tiempo tomado (segundos)"), default=0)
    is_correct = models.BooleanField(_("¿es correcta?"), default=False)

    class Meta:
        unique_together = ["attempt", "question"]

    def save(self, *args, **kwargs):
        if self.selected_option is not None:
            self.is_correct = (int(self.selected_option) == self.question.correct_option)
        else:
            self.is_correct = False
        super().save(*args, **kwargs)
