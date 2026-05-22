from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from test_razonamiento.models import CustomUser, Test, Question, TestAttempt, AttemptQuestion, StudentResponse

class TestUnansweredQuestion(TestCase):
    def setUp(self):
        # Crear usuario estudiante
        self.student = CustomUser.objects.create_user(
            username='student1',
            password='password123',
            role=CustomUser.Role.STUDENT
        )
        # Crear usuario docente
        self.teacher = CustomUser.objects.create_user(
            username='teacher1',
            password='password123',
            role=CustomUser.Role.TEACHER
        )
        
        # Crear preguntas (con imágenes mock/vacías para la prueba, pero como Django las valida, usemos archivos simples o simulemos)
        # Nota: El modelo Question requiere stimulus_image. Crearemos una imagen mock pequeña.
        from django.core.files.uploadedfile import SimpleUploadedFile
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b'
        )
        self.stimulus = SimpleUploadedFile('stimulus.gif', small_gif, content_type='image/gif')
        
        self.question1 = Question.objects.create(
            title='Pregunta 1',
            stimulus_image=self.stimulus,
            correct_option=1,
            is_active=True
        )
        self.question2 = Question.objects.create(
            title='Pregunta 2',
            stimulus_image=self.stimulus,
            correct_option=2,
            is_active=True
        )
        
        # Crear Test
        self.test = Test.objects.create(
            name='Test de Razonamiento Abstracto 1',
            seconds_per_question=60,
            num_questions=2,
            max_attempts=1,
            is_active=True,
            created_by=self.teacher
        )
        self.test.questions.add(self.question1, self.question2)
        
        self.client = Client()
        self.client.login(username='student1', password='password123')

    def test_complete_test_with_unanswered_questions(self):
        # 1. Iniciar el test (POST a test_start)
        response = self.client.post(reverse('test_razonamiento:test_start', args=[self.test.id]))
        # Debe redirigir a render_question para el intento creado
        attempt = TestAttempt.objects.get(student=self.student, test=self.test)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('test_razonamiento:render_question', args=[attempt.id]))
        
        # 2. Obtener la primera pregunta (GET a render_question)
        response = self.client.get(reverse('test_razonamiento:render_question', args=[attempt.id]))
        self.assertEqual(response.status_code, 200)
        
        # 3. Enviar la primera pregunta sin responder (POST a render_question con option="")
        # Esto simula tanto el envío manual sin seleccionar como el temporizador expirando
        response = self.client.post(reverse('test_razonamiento:render_question', args=[attempt.id]), {'option': ''})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('test_razonamiento:render_question', args=[attempt.id]))
        
        # Verificar que se creó la respuesta sin opción
        resp1 = StudentResponse.objects.get(attempt=attempt, question=attempt.test_questions.all()[0].question)
        self.assertIsNone(resp1.selected_option)
        self.assertFalse(resp1.is_correct)

        # 4. Obtener la segunda pregunta (GET a render_question)
        response = self.client.get(reverse('test_razonamiento:render_question', args=[attempt.id]))
        self.assertEqual(response.status_code, 200)

        # 5. Enviar la segunda pregunta sin responder (POST a render_question con option="")
        # Esta es la última pregunta del test
        response = self.client.post(reverse('test_razonamiento:render_question', args=[attempt.id]), {'option': ''})
        self.assertEqual(response.status_code, 302)
        
        # Verificamos que redirige a render_question
        self.assertEqual(response.url, reverse('test_razonamiento:render_question', args=[attempt.id]))
        
        # Realizamos el GET a render_question manualmente para ver a dónde nos lleva
        response = self.client.get(reverse('test_razonamiento:render_question', args=[attempt.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('test_razonamiento:test_results', args=[attempt.id]))
        
        # Finalmente accedemos a la página de resultados
        response = self.client.get(reverse('test_razonamiento:test_results', args=[attempt.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Finalizado")
        
        # Verificar que el intento está finalizado
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, TestAttempt.Status.FINISHED)

    def test_finished_attempt_redirects_to_results(self):
        # Iniciar el test y marcarlo como finalizado
        attempt = TestAttempt.objects.create(
            student=self.student,
            test=self.test,
            status=TestAttempt.Status.FINISHED,
            end_date=timezone.now()
        )
        
        # Un GET a render_question debería redirigir a resultados en lugar de devolver 404
        response = self.client.get(reverse('test_razonamiento:render_question', args=[attempt.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('test_razonamiento:test_results', args=[attempt.id]))

        # Un POST a render_question debería también redirigir a resultados en lugar de devolver 404
        response = self.client.post(reverse('test_razonamiento:render_question', args=[attempt.id]), {'option': '1'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('test_razonamiento:test_results', args=[attempt.id]))


# ---------------------------------------------------------------------------
# Pruebas para BatchDeleteAttemptsView
# ---------------------------------------------------------------------------

class TestBatchDeleteAttempts(TestCase):
    """Verifica el comportamiento del borrado masivo de intentos."""

    def setUp(self):
        # Docente
        self.teacher = CustomUser.objects.create_user(
            username='teacher_batch',
            password='pass123',
            role=CustomUser.Role.TEACHER,
        )
        # Estudiante
        self.student = CustomUser.objects.create_user(
            username='student_batch',
            password='pass123',
            role=CustomUser.Role.STUDENT,
        )

        from django.core.files.uploadedfile import SimpleUploadedFile
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b'
        )
        stimulus = SimpleUploadedFile('s.gif', small_gif, content_type='image/gif')
        question = Question.objects.create(
            title='Q1', stimulus_image=stimulus,
            correct_option=1, is_active=True,
        )

        # Test A (el que usaremos para borrado)
        self.test_a = Test.objects.create(
            name='Test A', seconds_per_question=60,
            num_questions=1, max_attempts=5,
            is_active=True, created_by=self.teacher,
        )
        self.test_a.questions.add(question)

        # Test B (para verificar que no borra intentos de otros tests)
        self.test_b = Test.objects.create(
            name='Test B', seconds_per_question=60,
            num_questions=1, max_attempts=5,
            is_active=True, created_by=self.teacher,
        )
        self.test_b.questions.add(question)

        # Crear 3 intentos finalizados en test_a y 1 en test_b
        self.attempt1 = TestAttempt.objects.create(
            student=self.student, test=self.test_a,
            status='finished', end_date=timezone.now(),
        )
        self.attempt2 = TestAttempt.objects.create(
            student=self.student, test=self.test_a,
            status='finished', end_date=timezone.now(),
        )
        self.attempt3 = TestAttempt.objects.create(
            student=self.student, test=self.test_a,
            status='finished', end_date=timezone.now(),
        )
        self.attempt_b = TestAttempt.objects.create(
            student=self.student, test=self.test_b,
            status='finished', end_date=timezone.now(),
        )

        self.url = reverse(
            'test_razonamiento:batch_delete_attempts',
            kwargs={'pk': self.test_a.pk},
        )
        self.client = Client()

    # ── 1. Borrado exitoso de varios intentos ─────────────────────────────
    def test_batch_delete_selected_attempts(self):
        self.client.login(username='teacher_batch', password='pass123')
        response = self.client.post(self.url, {
            'action': 'delete',
            'attempt_ids': [self.attempt1.pk, self.attempt2.pk],
        })
        self.assertRedirects(
            response,
            reverse('test_razonamiento:test_results_report', kwargs={'pk': self.test_a.pk}),
        )
        # Los dos intentos seleccionados ya no existen
        self.assertFalse(TestAttempt.objects.filter(pk=self.attempt1.pk).exists())
        self.assertFalse(TestAttempt.objects.filter(pk=self.attempt2.pk).exists())
        # El tercero del mismo test sigue intacto
        self.assertTrue(TestAttempt.objects.filter(pk=self.attempt3.pk).exists())

    # ── 2. Sin selección muestra advertencia y redirige ───────────────────
    def test_batch_delete_no_selection_shows_warning(self):
        self.client.login(username='teacher_batch', password='pass123')
        response = self.client.post(self.url, {'action': 'delete'})
        self.assertRedirects(
            response,
            reverse('test_razonamiento:test_results_report', kwargs={'pk': self.test_a.pk}),
        )
        # Ningún intento fue borrado
        self.assertEqual(
            TestAttempt.objects.filter(test=self.test_a).count(), 3
        )

    # ── 3. Estudiante no puede acceder (redirige a login) ─────────────────
    def test_student_cannot_batch_delete(self):
        self.client.login(username='student_batch', password='pass123')
        response = self.client.post(self.url, {
            'action': 'delete',
            'attempt_ids': [self.attempt1.pk],
        })
        # Debe denegar el acceso (redirección o 403)
        self.assertIn(response.status_code, [302, 403])
        # El intento no fue borrado
        self.assertTrue(TestAttempt.objects.filter(pk=self.attempt1.pk).exists())

    # ── 4. Usuario anónimo es redirigido ──────────────────────────────────
    def test_anonymous_cannot_batch_delete(self):
        response = self.client.post(self.url, {
            'action': 'delete',
            'attempt_ids': [self.attempt1.pk],
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    # ── 5. No borra intentos de otro test (seguridad cross-test) ─────────
    def test_cannot_delete_attempt_from_other_test(self):
        self.client.login(username='teacher_batch', password='pass123')
        # Intentamos borrar attempt_b (que pertenece a test_b) desde la URL de test_a
        response = self.client.post(self.url, {
            'action': 'delete',
            'attempt_ids': [self.attempt_b.pk],
        })
        self.assertRedirects(
            response,
            reverse('test_razonamiento:test_results_report', kwargs={'pk': self.test_a.pk}),
        )
        # attempt_b debe seguir existiendo
        self.assertTrue(TestAttempt.objects.filter(pk=self.attempt_b.pk).exists())

