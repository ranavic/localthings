from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.db.models import Avg, Count, Q, Sum, Max

from courses.models import Course, Module
from .models import (
    Quiz, Question, Answer, QuizAttempt, QuestionResponse,
    QuestionFeedback, PracticeSession, QuizTopic
)

class QuizListView(ListView):
    model = Quiz
    template_name = 'quizzes/quiz_list.html'
    context_object_name = 'quizzes'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Quiz.objects.filter(is_active=True)
        
        # Filter by search query if provided
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | 
                Q(description__icontains=query)
            )
            
        # Filter by topic if provided
        topic = self.request.GET.get('topic')
        if topic:
            queryset = queryset.filter(topics__slug=topic)
            
        # Filter by difficulty if provided
        difficulty = self.request.GET.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
            
        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['topics'] = QuizTopic.objects.all()
        
        # If user is authenticated, get their quiz stats
        if self.request.user.is_authenticated:
            user_attempts = QuizAttempt.objects.filter(user=self.request.user)
            context['total_attempts'] = user_attempts.count()
            context['completed_quizzes'] = user_attempts.values('quiz').distinct().count()
            
            # Calculate average score
            if context['total_attempts'] > 0:
                context['avg_score'] = user_attempts.aggregate(Avg('score'))['score__avg']
            else:
                context['avg_score'] = 0
        
        return context


class QuizDetailView(DetailView):
    model = Quiz
    template_name = 'quizzes/quiz_detail.html'
    context_object_name = 'quiz'
    pk_url_kwarg = 'quiz_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = self.get_object()
        
        # Get related course or module if applicable
        if quiz.course:
            context['course'] = quiz.course
        if quiz.module:
            context['module'] = quiz.module
            context['course'] = quiz.module.course
            
        # Get user's previous attempts if authenticated
        if self.request.user.is_authenticated:
            context['previous_attempts'] = QuizAttempt.objects.filter(
                quiz=quiz,
                user=self.request.user
            ).order_by('-created_at')
            
            # Check if user has passed the quiz
            context['has_passed'] = context['previous_attempts'].filter(
                is_passed=True
            ).exists()
            
            # Get best score
            if context['previous_attempts'].exists():
                context['best_score'] = context['previous_attempts'].aggregate(
                    Max('score')
                )['score__max']
            
        # Get quiz stats
        context['total_attempts'] = QuizAttempt.objects.filter(quiz=quiz).count()
        if context['total_attempts'] > 0:
            context['avg_score'] = QuizAttempt.objects.filter(quiz=quiz).aggregate(
                Avg('score')
            )['score__avg']
            context['pass_rate'] = (QuizAttempt.objects.filter(
                quiz=quiz, 
                is_passed=True
            ).count() / context['total_attempts']) * 100
        else:
            context['avg_score'] = 0
            context['pass_rate'] = 0
            
        return context


class CourseQuizzesView(LoginRequiredMixin, ListView):
    model = Quiz
    template_name = 'quizzes/course_quizzes.html'
    context_object_name = 'quizzes'
    paginate_by = 10
    
    def get_queryset(self):
        self.course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        return Quiz.objects.filter(
            Q(course=self.course) | Q(module__course=self.course),
            is_active=True
        ).distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        
        # Group quizzes by module for display
        modules = Module.objects.filter(course=self.course).order_by('order')
        context['modules'] = modules
        
        module_quizzes = {}
        course_quizzes = []
        
        for quiz in context['quizzes']:
            if quiz.module:
                if quiz.module.id not in module_quizzes:
                    module_quizzes[quiz.module.id] = []
                module_quizzes[quiz.module.id].append(quiz)
            else:
                course_quizzes.append(quiz)
                
        context['module_quizzes'] = module_quizzes
        context['course_quizzes'] = course_quizzes
        
        return context


class ModuleQuizzesView(LoginRequiredMixin, ListView):
    model = Quiz
    template_name = 'quizzes/module_quizzes.html'
    context_object_name = 'quizzes'
    
    def get_queryset(self):
        self.module = get_object_or_404(Module, id=self.kwargs['module_id'])
        return Quiz.objects.filter(module=self.module, is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['module'] = self.module
        context['course'] = self.module.course
        
        # If user is authenticated, get their quiz attempts for this module
        if self.request.user.is_authenticated:
            quiz_ids = context['quizzes'].values_list('id', flat=True)
            context['user_attempts'] = QuizAttempt.objects.filter(
                quiz_id__in=quiz_ids,
                user=self.request.user
            )
            
            # Create a dictionary of quiz_id -> best attempt
            context['best_attempts'] = {}
            
            for quiz_id in quiz_ids:
                best_attempt = QuizAttempt.objects.filter(
                    quiz_id=quiz_id,
                    user=self.request.user
                ).order_by('-score').first()
                
                if best_attempt:
                    context['best_attempts'][quiz_id] = best_attempt
        
        return context


class StartQuizView(LoginRequiredMixin, View):
    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
        
        # Check if there are time constraints or other requirements
        if quiz.requires_enrollment and quiz.course:
            if not quiz.course.enrollment_set.filter(user=request.user, is_active=True).exists():
                messages.error(request, "You must be enrolled in the course to take this quiz.")
                return HttpResponseRedirect(reverse('quizzes:quiz_detail', kwargs={'quiz_id': quiz_id}))
        
        # Create new quiz attempt
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            user=request.user,
            is_completed=False,
            time_spent=0
        )
        
        # Get questions for the quiz
        if quiz.random_order:
            questions = quiz.question_set.all().order_by('?')
        else:
            questions = quiz.question_set.all().order_by('order')
            
        # Limit questions if max_questions is set
        if quiz.max_questions and quiz.max_questions < questions.count():
            questions = questions[:quiz.max_questions]
            
        # Create empty responses for each question
        for question in questions:
            QuestionResponse.objects.create(
                attempt=attempt,
                question=question,
                is_correct=False
            )
        
        # Redirect to the quiz attempt page
        return HttpResponseRedirect(reverse('quizzes:quiz_attempt', kwargs={
            'quiz_id': quiz_id,
            'attempt_id': attempt.id
        }))


class QuizAttemptView(LoginRequiredMixin, DetailView):
    model = QuizAttempt
    template_name = 'quizzes/quiz_attempt.html'
    context_object_name = 'attempt'
    pk_url_kwarg = 'attempt_id'
    
    def get_queryset(self):
        return QuizAttempt.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempt = self.get_object()
        context['quiz'] = attempt.quiz
        
        # Get all questions for this attempt
        context['responses'] = QuestionResponse.objects.filter(
            attempt=attempt
        ).order_by('question__order')
        
        # Check if timer is enabled
        if attempt.quiz.time_limit:
            context['time_limit'] = attempt.quiz.time_limit
            context['time_remaining'] = max(0, attempt.quiz.time_limit - attempt.time_spent)
        
        return context
    
    def post(self, request, quiz_id, attempt_id):
        attempt = self.get_object()
        
        # If quiz is already completed, redirect to results
        if attempt.is_completed:
            return HttpResponseRedirect(reverse('quizzes:quiz_results', kwargs={
                'quiz_id': quiz_id,
                'attempt_id': attempt_id
            }))
        
        # Update time spent
        time_spent = int(request.POST.get('time_spent', 0))
        attempt.time_spent = time_spent
        
        # Process responses
        for key, value in request.POST.items():
            if key.startswith('question_'):
                question_id = int(key.split('_')[1])
                question = get_object_or_404(Question, id=question_id)
                
                # Get or create response for this question
                response, created = QuestionResponse.objects.get_or_create(
                    attempt=attempt,
                    question=question,
                    defaults={'is_correct': False}
                )
                
                # Handle different question types
                if question.question_type == 'MCQ':
                    try:
                        selected_answer = Answer.objects.get(id=int(value), question=question)
                        response.selected_answer = selected_answer
                        response.is_correct = selected_answer.is_correct
                    except (Answer.DoesNotExist, ValueError):
                        pass
                elif question.question_type == 'MULTI':
                    selected_answers = request.POST.getlist(key)
                    if selected_answers:
                        response.selected_answers.set(Answer.objects.filter(id__in=selected_answers, question=question))
                        correct_answers = question.answer_set.filter(is_correct=True).count()
                        selected_correct = response.selected_answers.filter(is_correct=True).count()
                        selected_incorrect = response.selected_answers.filter(is_correct=False).count()
                        
                        # All correct answers must be selected and no incorrect answers
                        response.is_correct = (selected_correct == correct_answers and selected_incorrect == 0)
                elif question.question_type == 'TEXT':
                    response.text_response = value
                    
                    # Check text answers - basic exact match for now
                    correct_answers = [a.text.lower().strip() for a in question.answer_set.filter(is_correct=True)]
                    response.is_correct = value.lower().strip() in correct_answers
                
                # Save response
                response.save()
        
        # Check if this is the final submission
        if 'submit_quiz' in request.POST:
            # Calculate score
            total_questions = QuestionResponse.objects.filter(attempt=attempt).count()
            correct_responses = QuestionResponse.objects.filter(attempt=attempt, is_correct=True).count()
            
            if total_questions > 0:
                score_percentage = (correct_responses / total_questions) * 100
            else:
                score_percentage = 0
                
            # Update attempt
            attempt.is_completed = True
            attempt.score = score_percentage
            attempt.is_passed = score_percentage >= attempt.quiz.passing_score
            attempt.save()
            
            # Redirect to results page
            return HttpResponseRedirect(reverse('quizzes:quiz_results', kwargs={
                'quiz_id': quiz_id,
                'attempt_id': attempt_id
            }))
        
        # If not final submission, save progress and stay on the same page
        attempt.save()
        return HttpResponseRedirect(reverse('quizzes:quiz_attempt', kwargs={
            'quiz_id': quiz_id,
            'attempt_id': attempt_id
        }))


class SubmitQuizView(LoginRequiredMixin, View):
    def post(self, request, quiz_id):
        # This view handles quiz submissions from the ajax interface
        quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
        attempt_id = request.POST.get('attempt_id')
        
        if not attempt_id:
            return JsonResponse({'error': 'No attempt specified'}, status=400)
            
        try:
            attempt = QuizAttempt.objects.get(id=attempt_id, user=request.user, quiz=quiz)
        except QuizAttempt.DoesNotExist:
            return JsonResponse({'error': 'Invalid attempt'}, status=400)
            
        # If already completed, just return the results URL
        if attempt.is_completed:
            return JsonResponse({
                'success': True,
                'redirect': reverse('quizzes:quiz_results', kwargs={
                    'quiz_id': quiz_id,
                    'attempt_id': attempt_id
                })
            })
            
        # Process responses (similar to QuizAttemptView.post)
        responses_data = request.POST.get('responses')
        if not responses_data:
            return JsonResponse({'error': 'No responses provided'}, status=400)
            
        try:
            responses = json.loads(responses_data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid response data'}, status=400)
            
        # Process each response
        for response_data in responses:
            question_id = response_data.get('question_id')
            answer_data = response_data.get('answer')
            
            if not question_id or not answer_data:
                continue
                
            question = get_object_or_404(Question, id=question_id)
            
            response, created = QuestionResponse.objects.get_or_create(
                attempt=attempt,
                question=question,
                defaults={'is_correct': False}
            )
            
            # Process based on question type (similar to QuizAttemptView.post)
            # ...
        
        # Calculate score
        total_questions = QuestionResponse.objects.filter(attempt=attempt).count()
        correct_responses = QuestionResponse.objects.filter(attempt=attempt, is_correct=True).count()
        
        if total_questions > 0:
            score_percentage = (correct_responses / total_questions) * 100
        else:
            score_percentage = 0
            
        # Update attempt
        attempt.is_completed = True
        attempt.score = score_percentage
        attempt.is_passed = score_percentage >= quiz.passing_score
        attempt.time_spent = request.POST.get('time_spent', 0)
        attempt.save()
        
        # Return results URL
        return JsonResponse({
            'success': True,
            'redirect': reverse('quizzes:quiz_results', kwargs={
                'quiz_id': quiz_id,
                'attempt_id': attempt_id
            })
        })


class QuizResultsView(LoginRequiredMixin, DetailView):
    model = QuizAttempt
    template_name = 'quizzes/quiz_results.html'
    context_object_name = 'attempt'
    pk_url_kwarg = 'attempt_id'
    
    def get_queryset(self):
        return QuizAttempt.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempt = self.get_object()
        context['quiz'] = attempt.quiz
        
        # Ensure the attempt is for the specified quiz
        if str(attempt.quiz.id) != self.kwargs['quiz_id']:
            raise Http404("Quiz attempt does not match the specified quiz")
            
        # Get all responses for this attempt
        context['responses'] = QuestionResponse.objects.filter(
            attempt=attempt
        ).order_by('question__order')
        
        # Calculate statistics
        context['total_questions'] = context['responses'].count()
        context['correct_answers'] = context['responses'].filter(is_correct=True).count()
        context['incorrect_answers'] = context['responses'].filter(is_correct=False).count()
        
        # Get user's previous attempts
        context['previous_attempts'] = QuizAttempt.objects.filter(
            quiz=attempt.quiz,
            user=self.request.user
        ).exclude(id=attempt.id).order_by('-created_at')
        
        # Determine if this is the best score
        if context['previous_attempts'].exists():
            best_previous = context['previous_attempts'].order_by('-score').first()
            context['is_best_score'] = attempt.score >= best_previous.score
        else:
            context['is_best_score'] = True
            
        return context


class UserQuizHistoryView(LoginRequiredMixin, ListView):
    model = QuizAttempt
    template_name = 'quizzes/user_quiz_history.html'
    context_object_name = 'attempts'
    paginate_by = 10
    
    def get_queryset(self):
        return QuizAttempt.objects.filter(
            user=self.request.user,
            is_completed=True
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate overall statistics
        context['total_attempts'] = context['attempts'].count()
        context['passed_quizzes'] = context['attempts'].filter(is_passed=True).count()
        
        if context['total_attempts'] > 0:
            context['pass_rate'] = (context['passed_quizzes'] / context['total_attempts']) * 100
            context['avg_score'] = context['attempts'].aggregate(Avg('score'))['score__avg']
        else:
            context['pass_rate'] = 0
            context['avg_score'] = 0
            
        # Group by quiz for unique quiz counts
        unique_quizzes = context['attempts'].values('quiz').distinct().count()
        context['unique_quizzes'] = unique_quizzes
        
        return context


class UserQuizStatsView(LoginRequiredMixin, TemplateView):
    template_name = 'quizzes/user_quiz_stats.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all completed attempts
        attempts = QuizAttempt.objects.filter(
            user=self.request.user,
            is_completed=True
        )
        
        # Basic statistics
        context['total_attempts'] = attempts.count()
        context['unique_quizzes'] = attempts.values('quiz').distinct().count()
        context['passed_quizzes'] = attempts.filter(is_passed=True).values('quiz').distinct().count()
        
        if context['total_attempts'] > 0:
            context['avg_score'] = attempts.aggregate(Avg('score'))['score__avg']
            context['avg_time'] = attempts.aggregate(Avg('time_spent'))['time_spent__avg']
        else:
            context['avg_score'] = 0
            context['avg_time'] = 0
            
        # Get quiz performance by topic
        quiz_topics = QuizTopic.objects.filter(
            quiz__quizattempt__user=self.request.user,
            quiz__quizattempt__is_completed=True
        ).distinct()
        
        topic_stats = []
        
        for topic in quiz_topics:
            topic_attempts = attempts.filter(quiz__topics=topic)
            topic_data = {
                'topic': topic,
                'attempts': topic_attempts.count(),
                'avg_score': topic_attempts.aggregate(Avg('score'))['score__avg'] or 0,
                'pass_rate': (topic_attempts.filter(is_passed=True).count() / topic_attempts.count()) * 100 if topic_attempts.count() > 0 else 0
            }
            topic_stats.append(topic_data)
            
        context['topic_stats'] = topic_stats
        
        # Get recent improvement data for progress charts
        recent_attempts = attempts.order_by('-created_at')[:10]
        context['recent_attempts'] = recent_attempts
        
        return context


class QuestionFeedbackView(LoginRequiredMixin, CreateView):
    model = QuestionFeedback
    template_name = 'quizzes/question_feedback.html'
    fields = ['feedback_type', 'comment']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['question'] = get_object_or_404(Question, id=self.kwargs['question_id'])
        return context
    
    def form_valid(self, form):
        form.instance.question = get_object_or_404(Question, id=self.kwargs['question_id'])
        form.instance.user = self.request.user
        
        messages.success(self.request, "Thank you for your feedback! It helps us improve our quizzes.")
        return super().form_valid(form)
    
    def get_success_url(self):
        # Redirect back to the quiz results or the quiz itself
        referer = self.request.META.get('HTTP_REFERER')
        if referer:
            return referer
        return reverse('quizzes:quiz_list')


class PracticeQuizView(LoginRequiredMixin, View):
    def get(self, request, topic_slug):
        topic = get_object_or_404(QuizTopic, slug=topic_slug)
        
        # Create a new practice session
        session = PracticeSession.objects.create(
            user=request.user,
            topic=topic,
            is_completed=False
        )
        
        # Get questions for the topic
        questions = Question.objects.filter(
            quiz__topics=topic,
            quiz__is_active=True
        ).order_by('?')
        
        # Limit to 10 questions for practice
        practice_questions = questions[:10]
        
        # Associate questions with this practice session
        for question in practice_questions:
            session.questions.add(question)
        
        # Redirect to the practice session
        return HttpResponseRedirect(reverse('quizzes:practice_session', kwargs={
            'topic_slug': topic_slug,
            'session_id': session.id
        }))


class PracticeSessionView(LoginRequiredMixin, DetailView):
    model = PracticeSession
    template_name = 'quizzes/practice_session.html'
    context_object_name = 'session'
    pk_url_kwarg = 'session_id'
    
    def get_queryset(self):
        return PracticeSession.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.get_object()
        context['topic'] = session.topic
        context['questions'] = session.questions.all()
        
        return context
    
    def post(self, request, topic_slug, session_id):
        session = self.get_object()
        
        # Process responses for each question
        correct_count = 0
        total_questions = session.questions.count()
        
        question_results = []
        
        for question in session.questions.all():
            result = {
                'question': question,
                'is_correct': False,
                'user_answer': None,
                'correct_answers': question.answer_set.filter(is_correct=True)
            }
            
            # Get user's answer based on question type
            if question.question_type == 'MCQ':
                answer_key = f'question_{question.id}'
                if answer_key in request.POST:
                    try:
                        selected_answer = Answer.objects.get(
                            id=int(request.POST[answer_key]),
                            question=question
                        )
                        result['user_answer'] = selected_answer
                        result['is_correct'] = selected_answer.is_correct
                    except (Answer.DoesNotExist, ValueError):
                        pass
            elif question.question_type == 'MULTI':
                answer_key = f'question_{question.id}'
                selected_ids = request.POST.getlist(answer_key)
                if selected_ids:
                    selected_answers = Answer.objects.filter(id__in=selected_ids, question=question)
                    result['user_answer'] = selected_answers
                    
                    correct_answers = question.answer_set.filter(is_correct=True).count()
                    selected_correct = selected_answers.filter(is_correct=True).count()
                    selected_incorrect = selected_answers.filter(is_correct=False).count()
                    
                    result['is_correct'] = (selected_correct == correct_answers and selected_incorrect == 0)
            elif question.question_type == 'TEXT':
                answer_key = f'question_{question.id}'
                if answer_key in request.POST:
                    user_text = request.POST[answer_key].strip()
                    result['user_answer'] = user_text
                    
                    correct_answers = [a.text.lower().strip() for a in question.answer_set.filter(is_correct=True)]
                    result['is_correct'] = user_text.lower() in correct_answers
            
            if result['is_correct']:
                correct_count += 1
                
            question_results.append(result)
        
        # Calculate score
        if total_questions > 0:
            score = (correct_count / total_questions) * 100
        else:
            score = 0
            
        # Update session
        session.is_completed = True
        session.score = score
        session.save()
        
        # Store results for display
        request.session['practice_results'] = {
            'session_id': session.id,
            'score': score,
            'correct_count': correct_count,
            'total_questions': total_questions
        }
        
        # Redirect to results page
        return HttpResponseRedirect(reverse('quizzes:practice_results', kwargs={
            'topic_slug': topic_slug
        }))


class PracticeResultsView(LoginRequiredMixin, TemplateView):
    template_name = 'quizzes/practice_results.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['topic'] = get_object_or_404(QuizTopic, slug=self.kwargs['topic_slug'])
        
        # Get results from session
        results = self.request.session.get('practice_results', {})
        context.update(results)
        
        if 'session_id' in results:
            try:
                practice_session = PracticeSession.objects.get(
                    id=results['session_id'],
                    user=self.request.user
                )
                context['session'] = practice_session
                context['questions'] = practice_session.questions.all()
            except PracticeSession.DoesNotExist:
                pass
        
        # Get user's practice history for this topic
        context['previous_sessions'] = PracticeSession.objects.filter(
            user=self.request.user,
            topic=context['topic'],
            is_completed=True
        ).exclude(
            id=results.get('session_id')
        ).order_by('-created_at')
        
        return context
