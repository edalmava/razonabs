import random
import csv
import io
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, FormView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.db import models
from django.urls import reverse_lazy
from django.http import FileResponse, HttpResponseForbidden, Http404, HttpResponse
from .models import Test, TestAttempt, Question, AttemptQuestion, StudentResponse, CustomUser
from .forms import TestForm, CustomLoginForm, QuestionForm, StudentImportForm, StudentForm
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.template.loader import render_to_string

# Librerías para exportación
import openpyxl
from openpyxl.styles import Font, Alignment
from xhtml2pdf import pisa

# --- Utilidades ---

def check_and_expire_attempts(user):
    """Cierra intentos que han superado el tiempo límite teórico."""
    if not user.is_authenticated:
        return
    
    active_attempts = TestAttempt.objects.filter(status=TestAttempt.Status.IN_PROGRESS)
    if user.role == 'student':
        active_attempts = active_attempts.filter(student=user)

    for attempt in active_attempts:
        max_seconds = (attempt.test.num_questions * attempt.test.seconds_per_question) + 1800
        elapsed_seconds = (timezone.now() - attempt.start_date).total_seconds()
        
        if elapsed_seconds > max_seconds:
            attempt.status = TestAttempt.Status.FINISHED
            attempt.end_date = attempt.start_date + timezone.timedelta(seconds=max_seconds)
            attempt.save()

# --- Vistas de Autenticación y Redirección ---

def home_redirect(request):
    if not request.user.is_authenticated:
        return redirect('test_razonamiento:login')
    if request.user.is_teacher or request.user.is_superuser:
        return redirect('test_razonamiento:teacher_dashboard')
    return redirect('test_razonamiento:test_list')

class CustomLoginView(LoginView):
    authentication_form = CustomLoginForm
    template_name = 'test_razonamiento/registration/login.html'

def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('test_razonamiento:login')

# --- Vistas para Estudiantes ---

@login_required
def test_list(request):
    check_and_expire_attempts(request.user)
    tests = Test.objects.filter(is_active=True)
    test_data = []
    for test in tests:
        test_data.append({
            'test': test,
            'user_attempts_count': test.get_user_attempts_count(request.user),
            'has_active_attempt': test.has_active_attempt(request.user),
            'can_start_new': test.can_start_new(request.user)
        })
    return render(request, 'test_razonamiento/test_list.html', {'test_data': test_data, 'user': request.user})

@login_required
def test_start(request, test_id):
    test = get_object_or_404(Test, id=test_id, is_active=True)
    attempt = TestAttempt.objects.filter(student=request.user, test=test, status=TestAttempt.Status.IN_PROGRESS).first()
    
    # Contar intentos finalizados
    finished_attempts_count = TestAttempt.objects.filter(student=request.user, test=test, status=TestAttempt.Status.FINISHED).count()

    if request.method == "POST":
        if not attempt:
            # VALIDACIÓN: Límite de intentos
            if finished_attempts_count >= test.max_attempts:
                messages.error(request, f"Has alcanzado el límite máximo de intentos para este test ({test.max_attempts}).")
                return redirect('test_razonamiento:test_list')

            # FILTRO: Solo preguntas asignadas al test
            test_questions_pool = list(test.questions.filter(is_active=True))
            
            if len(test_questions_pool) < test.num_questions:
                messages.error(request, f"Este test no tiene suficientes preguntas asignadas (Mínimo requerido: {test.num_questions}). Por favor, avise a su docente.")
                return redirect('test_razonamiento:test_list')
            
            attempt = TestAttempt.objects.create(student=request.user, test=test)
            selected_questions = random.sample(test_questions_pool, test.num_questions)
            
            for i, question in enumerate(selected_questions):
                AttemptQuestion.objects.create(attempt=attempt, question=question, order=i + 1)
        
        return redirect('test_razonamiento:render_question', attempt_id=attempt.id)

    return render(request, 'test_razonamiento/test_start.html', {'test': test, 'attempt': attempt})

@login_required
def render_question(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, id=attempt_id, student=request.user)
    if attempt.status == TestAttempt.Status.FINISHED:
        return redirect('test_razonamiento:test_results', attempt_id=attempt.id)

    attempt_questions = attempt.test_questions.all().select_related('question')
    responded_question_ids = StudentResponse.objects.filter(attempt=attempt).values_list('question_id', flat=True)
    current_attempt_question = attempt_questions.exclude(question_id__in=responded_question_ids).first()

    if not current_attempt_question:
        attempt.status = TestAttempt.Status.FINISHED
        attempt.end_date = timezone.now()
        attempt.save()
        return redirect('test_razonamiento:test_results', attempt_id=attempt.id)

    question = current_attempt_question.question
    if request.method == "POST":
        selected_option_raw = request.POST.get('option')
        selected_option = int(selected_option_raw) if selected_option_raw else None

        if current_attempt_question.started_at:
            time_taken = int((timezone.now() - current_attempt_question.started_at).total_seconds())
        else:
            time_taken = int(request.POST.get('time_taken', 0))

        limit = attempt.test.seconds_per_question + 2
        if time_taken > limit or time_taken > attempt.test.seconds_per_question:
            selected_option = None
            time_taken = attempt.test.seconds_per_question

        StudentResponse.objects.create(
            attempt=attempt,
            question=question,
            selected_option=selected_option,
            time_taken=min(time_taken, attempt.test.seconds_per_question)
        )
        return redirect('test_razonamiento:render_question', attempt_id=attempt.id)

    current_attempt_question.started_at = timezone.now()
    current_attempt_question.save(update_fields=['started_at'])

    context = {
        'attempt': attempt,
        'question': question,
        'order': current_attempt_question.order,
        'total': attempt.test.num_questions,
        'seconds': attempt.test.seconds_per_question
    }
    return render(request, 'test_razonamiento/question.html', context)

@login_required
def serve_question_image(request, attempt_id, question_id, image_type):
    """Sirve imágenes de preguntas solo si el estudiante tiene un intento activo."""
    attempt = get_object_or_404(
        TestAttempt,
        id=attempt_id,
        student=request.user,
        status=TestAttempt.Status.IN_PROGRESS
    )

    if not attempt.test_questions.filter(question_id=question_id).exists():
        return HttpResponseForbidden("Pregunta no válida para este intento.")

    if image_type == 'stimulus':
        field_name = 'stimulus_image'
    elif image_type.startswith('option_'):
        field_name = f'{image_type}_image'
    else:
        return HttpResponseForbidden("Tipo de imagen no válido.")

    question = get_object_or_404(Question, id=question_id)
    image_file = getattr(question, field_name, None)

    if not image_file or not image_file.name:
        raise Http404("Imagen no encontrada.")

    file_path = image_file.path
    if not os.path.exists(file_path):
        raise Http404("Archivo no encontrado.")

    return FileResponse(open(file_path, 'rb'), content_type='image/jpeg')

@login_required
def test_results(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, id=attempt_id, student=request.user)
    return render(request, 'test_razonamiento/test_results.html', {
        'attempt': attempt,
        'correct_count': attempt.score,
        'total': attempt.test.num_questions,
        'score_pct': attempt.score_percentage,
        'nota': attempt.nota
    })

class StudentHistoryView(LoginRequiredMixin, ListView):
    model = TestAttempt
    template_name = 'test_razonamiento/student/history.html'
    context_object_name = 'attempts'

    def get_queryset(self):
        return TestAttempt.objects.filter(student=self.request.user, status='finished').order_by('-end_date')

# --- Vistas para Docentes ---

class TeacherRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (self.request.user.role == 'teacher' or self.request.user.is_superuser)

class TeacherDashboardView(TeacherRequiredMixin, ListView):
    model = Test
    template_name = 'test_razonamiento/teacher/dashboard.html'
    context_object_name = 'tests'

    def get_queryset(self):
        check_and_expire_attempts(self.request.user)
        if self.request.user.is_superuser:
            return Test.objects.all().order_by('-created_at')
        return Test.objects.filter(created_by=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = TestForm()
        return context

class TestCreateView(TeacherRequiredMixin, CreateView):
    model = Test
    form_class = TestForm
    template_name = 'test_razonamiento/teacher/test_form.html'
    success_url = reverse_lazy('test_razonamiento:teacher_dashboard')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Test creado exitosamente.")
        return super().form_valid(form)

class TestUpdateView(TeacherRequiredMixin, UpdateView):
    model = Test
    form_class = TestForm
    template_name = 'test_razonamiento/teacher/test_form.html'
    success_url = reverse_lazy('test_razonamiento:teacher_dashboard')

    def form_valid(self, form):
        messages.success(self.request, "Test actualizado correctamente.")
        return super().form_valid(form)

class TestDeleteView(TeacherRequiredMixin, DeleteView):
    model = Test
    template_name = 'test_razonamiento/teacher/test_confirm_delete.html'
    success_url = reverse_lazy('test_razonamiento:teacher_dashboard')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Test eliminado correctamente.")
        return super().delete(request, *args, **kwargs)

class TestAttemptDeleteView(TeacherRequiredMixin, DeleteView):
    model = TestAttempt
    template_name = 'test_razonamiento/teacher/attempt_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('test_razonamiento:test_results_report', kwargs={'pk': self.object.test.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Intento de estudiante eliminado.")
        return super().delete(request, *args, **kwargs)

class TestResultsReportView(TeacherRequiredMixin, DetailView):
    model = Test
    template_name = 'test_razonamiento/teacher/results_report.html'
    context_object_name = 'test'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attempts'] = self.object.attempts.filter(status='finished').select_related('student').order_by('-end_date')
        return context

class AttemptDetailView(TeacherRequiredMixin, DetailView):
    model = TestAttempt
    template_name = 'test_razonamiento/teacher/attempt_details.html'
    context_object_name = 'attempt'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        responses = self.object.responses.all().select_related('question')
        context['responses'] = responses
        context['correct_count'] = self.object.score
        context['total_questions'] = self.object.test.num_questions
        context['score_pct'] = self.object.score_percentage
        context['nota'] = self.object.nota
        return context

# CRUD Preguntas
class QuestionListView(TeacherRequiredMixin, ListView):
    model = Question
    template_name = 'test_razonamiento/teacher/question_list.html'
    context_object_name = 'questions'
    ordering = ['-created_at']

class QuestionCreateView(TeacherRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'test_razonamiento/teacher/question_form.html'
    success_url = reverse_lazy('test_razonamiento:question_list')

    def form_valid(self, form):
        messages.success(self.request, "Pregunta creada exitosamente.")
        return super().form_valid(form)

class QuestionUpdateView(TeacherRequiredMixin, UpdateView):
    model = Question
    form_class = QuestionForm
    template_name = 'test_razonamiento/teacher/question_form.html'
    success_url = reverse_lazy('test_razonamiento:question_list')

    def form_valid(self, form):
        messages.success(self.request, "Pregunta actualizada correctamente.")
        return super().form_valid(form)

class QuestionDeleteView(TeacherRequiredMixin, DeleteView):
    model = Question
    template_name = 'test_razonamiento/teacher/question_confirm_delete.html'
    success_url = reverse_lazy('test_razonamiento:question_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Pregunta eliminada.")
        return super().delete(request, *args, **kwargs)

# Importación Masiva REFACTORIZADA
class StudentImportView(TeacherRequiredMixin, FormView):
    template_name = 'test_razonamiento/teacher/student_import.html'
    form_class = StudentImportForm
    success_url = reverse_lazy('test_razonamiento:teacher_dashboard')

    def form_valid(self, form):
        csv_file = self.request.FILES['csv_file']
        
        try:
            # Usar utf-8-sig para manejar el BOM de Excel
            decoded_file = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            
            # 1. Leer primera línea para detectar delimitador y presencia de cabecera
            first_line = io_string.readline()
            io_string.seek(0)
            
            delimiter = ';' if (';' in first_line and ',' not in first_line) else ','
            
            # 2. Detectar si hay cabecera (buscando palabras clave)
            header_keywords = ['username', 'codigo', 'usuario', 'password', 'contraseña', 'clave', 'nombre']
            has_header = any(key in first_line.lower() for key in header_keywords)
            
            if has_header:
                reader = csv.DictReader(io_string, delimiter=delimiter)
            else:
                # Si no hay cabecera, asumimos el orden: username, password, first_name, last_name
                reader = csv.DictReader(io_string, fieldnames=['username', 'password', 'first_name', 'last_name'], delimiter=delimiter)
            
            count = 0
            errors = []
            
            for i, row in enumerate(reader, start=1):
                # Limpiar y normalizar fila
                # DictReader puede devolver valores None o llaves None si la fila no coincide con headers
                clean_row = {str(k).strip().lower(): str(v).strip() for k, v in row.items() if k and v}
                
                # Intentar obtener datos por nombre de columna (si hubo cabecera) o por el orden asignado
                username = clean_row.get('username') or clean_row.get('codigo') or clean_row.get('usuario')
                password = clean_row.get('password') or clean_row.get('contraseña') or clean_row.get('clave')
                first_name = clean_row.get('first_name') or clean_row.get('nombre') or ''
                last_name = clean_row.get('last_name') or clean_row.get('apellido') or ''
                
                # Si DictReader usó fieldnames porque no hubo cabecera, las llaves coincidirán directamente
                
                if not username or not password:
                    errors.append(f"Fila {i}: Faltan campos obligatorios (Código y Contraseña).")
                    continue
                
                if not CustomUser.objects.filter(username=username).exists():
                    try:
                        CustomUser.objects.create_user(
                            username=username,
                            password=password,
                            first_name=first_name,
                            last_name=last_name,
                            role=CustomUser.Role.STUDENT
                        )
                        count += 1
                    except Exception as e:
                        errors.append(f"Fila {i}: Error al crear usuario ({str(e)}).")
                else:
                    # Omitir silenciosamente si ya existe
                    pass
            
            if count > 0:
                messages.success(self.request, f"Se han importado {count} estudiantes exitosamente.")
            
            if errors:
                for err in errors[:5]:
                    messages.warning(self.request, err)
                if len(errors) > 5:
                    messages.warning(self.request, f"...y {len(errors) - 5} errores más.")
                    
        except Exception as e:
            messages.error(self.request, f"Error crítico al procesar el archivo: {str(e)}")

        return super().form_valid(form)

# Gestión de Estudiantes
class StudentListView(TeacherRequiredMixin, ListView):
    model = CustomUser
    template_name = 'test_razonamiento/teacher/student_list.html'
    context_object_name = 'students'
    paginate_by = 20

    def get_queryset(self):
        queryset = CustomUser.objects.filter(role=CustomUser.Role.STUDENT).order_by('-created_at')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(username__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search)
            )
        return queryset

class StudentCreateView(TeacherRequiredMixin, CreateView):
    model = CustomUser
    form_class = StudentForm
    template_name = 'test_razonamiento/teacher/student_form.html'
    success_url = reverse_lazy('test_razonamiento:student_list')

    def form_valid(self, form):
        messages.success(self.request, "Estudiante creado exitosamente.")
        return super().form_valid(form)

class StudentUpdateView(TeacherRequiredMixin, UpdateView):
    model = CustomUser
    form_class = StudentForm
    template_name = 'test_razonamiento/teacher/student_form.html'
    success_url = reverse_lazy('test_razonamiento:student_list')

    def form_valid(self, form):
        messages.success(self.request, "Estudiante actualizado correctamente.")
        return super().form_valid(form)

class StudentDeleteView(TeacherRequiredMixin, DeleteView):
    model = CustomUser
    template_name = 'test_razonamiento/teacher/student_confirm_delete.html'
    success_url = reverse_lazy('test_razonamiento:student_list')

    def get_queryset(self):
        return CustomUser.objects.filter(role=CustomUser.Role.STUDENT)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Estudiante eliminado correctamente.")
        return super().delete(request, *args, **kwargs)

# --- Funciones de Exportación ---

@login_required
def export_test_results_excel(request, pk):
    """Genera un archivo Excel con los resultados de un test."""
    if not (request.user.role == 'teacher' or request.user.is_superuser):
        return HttpResponseForbidden("No tienes permiso para esta acción.")
    
    test = get_object_or_404(Test, pk=pk)
    attempts = test.attempts.filter(status='finished').select_related('student').order_by('-end_date')
    
    # Crear libro de trabajo
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resultados del Test"
    
    # Encabezados
    headers = ['Código', 'Nombre', 'Apellido', 'Puntaje', 'Porcentaje (%)', 'Nota', 'Fecha Finalización']
    ws.append(headers)
    
    # Estilo para encabezados
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    
    # Datos
    for attempt in attempts:
        ws.append([
            attempt.student.username,
            attempt.student.first_name,
            attempt.student.last_name,
            f"{attempt.score} / {test.num_questions}",
            round(attempt.score_percentage, 1),
            round(attempt.nota, 2),
            attempt.end_date.strftime("%d/%m/%Y %H:%M")
        ])
    
    # Ajustar ancho de columnas
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column_letter].width = max_length + 2

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="resultados_{test.name.replace(" ", "_")}.xlsx"'
    wb.save(response)
    return response

@login_required
def export_test_results_pdf(request, pk):
    """Genera un reporte PDF con los resultados de un test."""
    if not (request.user.role == 'teacher' or request.user.is_superuser):
        return HttpResponseForbidden("No tienes permiso para esta acción.")
    
    test = get_object_or_404(Test, pk=pk)
    attempts = test.attempts.filter(status='finished').select_related('student').order_by('-end_date')
    
    context = {
        'test': test,
        'attempts': attempts,
        'today': timezone.now(),
    }
    
    # Renderizar template
    html = render_to_string('test_razonamiento/teacher/results_pdf.html', context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_{test.name.replace(" ", "_")}.pdf"'
    
    # Crear PDF
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Ocurrió un error al generar el PDF.', status=500)
    
    return response
