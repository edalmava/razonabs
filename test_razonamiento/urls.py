from django.urls import path
from . import views

app_name = 'test_razonamiento'

urlpatterns = [
    # Inicio y Autenticación
    path('', views.home_redirect, name='home'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Rutas Estudiante
    path('tests/', views.test_list, name='test_list'),
    path('tests/<int:test_id>/start/', views.test_start, name='test_start'),
    path('tests/attempt/<int:attempt_id>/question/', views.render_question, name='render_question'),
    path('tests/attempt/<int:attempt_id>/results/', views.test_results, name='test_results'),
    path('my-results/', views.StudentHistoryView.as_view(), name='student_history'),

    # Rutas Docente
    path('teacher/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('teacher/test/create/', views.TestCreateView.as_view(), name='test_create'),
    path('teacher/test/<int:pk>/edit/', views.TestUpdateView.as_view(), name='test_update'),
    path('teacher/test/<int:pk>/delete/', views.TestDeleteView.as_view(), name='test_delete'),
    path('teacher/test/<int:pk>/results/', views.TestResultsReportView.as_view(), name='test_results_report'),
    path('teacher/attempt/<int:pk>/details/', views.AttemptDetailView.as_view(), name='attempt_details'),
    path('teacher/attempt/<int:pk>/delete/', views.TestAttemptDeleteView.as_view(), name='attempt_delete'),
    
    # CRUD Preguntas
    path('teacher/questions/', views.QuestionListView.as_view(), name='question_list'),
    path('teacher/questions/add/', views.QuestionCreateView.as_view(), name='question_create'),
    path('teacher/questions/<int:pk>/edit/', views.QuestionUpdateView.as_view(), name='question_update'),
    path('teacher/questions/<int:pk>/delete/', views.QuestionDeleteView.as_view(), name='question_delete'),
    
    # Gestión Estudiantes
    path('teacher/students/', views.StudentListView.as_view(), name='student_list'),
    path('teacher/students/add/', views.StudentCreateView.as_view(), name='student_create'),
    path('teacher/students/<int:pk>/edit/', views.StudentUpdateView.as_view(), name='student_update'),
    path('teacher/students/<int:pk>/delete/', views.StudentDeleteView.as_view(), name='student_delete'),
    path('teacher/students/import/', views.StudentImportView.as_view(), name='student_import'),
]
