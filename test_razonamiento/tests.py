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
