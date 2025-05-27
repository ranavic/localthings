from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy, reverse
from django.db.models import Avg, Count, Q
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages

from .models import (
    Course, Category, Tag, Difficulty, Module, Lesson, CourseReview, Enrollment,
    CourseProgress, LessonProgress, CourseWishlist
)

class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Course.objects.filter(is_published=True)
        
        # Apply filters if provided
        query = self.request.GET.get('q')
        category = self.request.GET.get('category')
        tag = self.request.GET.get('tag')
        difficulty = self.request.GET.get('difficulty')
        
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | 
                Q(overview__icontains=query) | 
                Q(description__icontains=query)
            )
        
        if category:
            queryset = queryset.filter(category__slug=category)
            
        if tag:
            queryset = queryset.filter(tags__slug=tag)
            
        if difficulty:
            queryset = queryset.filter(difficulty__slug=difficulty)
            
        return queryset.distinct().order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['tags'] = Tag.objects.all()
        context['difficulties'] = Difficulty.objects.all()
        return context


class CourseListByCategoryView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 12
    
    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['category_slug'])
        return Course.objects.filter(category=self.category, is_published=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['tags'] = Tag.objects.all()
        context['difficulties'] = Difficulty.objects.all()
        context['current_category'] = self.category
        return context


class CourseListByTagView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 12
    
    def get_queryset(self):
        self.tag = get_object_or_404(Tag, slug=self.kwargs['tag_slug'])
        return Course.objects.filter(tags=self.tag, is_published=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['tags'] = Tag.objects.all()
        context['difficulties'] = Difficulty.objects.all()
        context['current_tag'] = self.tag
        return context


class CourseListByDifficultyView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 12
    
    def get_queryset(self):
        self.difficulty = get_object_or_404(Difficulty, slug=self.kwargs['difficulty_slug'])
        return Course.objects.filter(difficulty=self.difficulty, is_published=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['tags'] = Tag.objects.all()
        context['difficulties'] = Difficulty.objects.all()
        context['current_difficulty'] = self.difficulty
        return context


class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'
    slug_url_kwarg = 'course_slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        
        # Get course modules and lessons
        context['modules'] = Module.objects.filter(course=course).order_by('order')
        
        # Get course reviews
        context['reviews'] = CourseReview.objects.filter(course=course).order_by('-created_at')
        context['avg_rating'] = context['reviews'].aggregate(Avg('rating'))['rating__avg'] or 0
        
        # Check if user is enrolled
        if self.request.user.is_authenticated:
            context['is_enrolled'] = Enrollment.objects.filter(
                course=course, 
                user=self.request.user,
                is_active=True
            ).exists()
            
            # Check if course is in user's wishlist
            context['in_wishlist'] = CourseWishlist.objects.filter(
                course=course,
                user=self.request.user
            ).exists()
            
            # Get user's course progress if enrolled
            if context['is_enrolled']:
                try:
                    context['course_progress'] = CourseProgress.objects.get(
                        enrollment__course=course,
                        enrollment__user=self.request.user
                    )
                except CourseProgress.DoesNotExist:
                    context['course_progress'] = None
        
        # Get related courses
        context['related_courses'] = Course.objects.filter(
            Q(category=course.category) | Q(tags__in=course.tags.all())
        ).exclude(id=course.id).distinct()[:4]
        
        return context


class CourseEnrollView(LoginRequiredMixin, View):
    def post(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug, is_published=True)
        
        # Check if already enrolled
        enrollment, created = Enrollment.objects.get_or_create(
            course=course,
            user=request.user,
            defaults={'is_active': True}
        )
        
        if not created and not enrollment.is_active:
            # Reactivate enrollment if it exists but is inactive
            enrollment.is_active = True
            enrollment.save()
            messages.success(request, f"Welcome back to '{course.title}'! Your enrollment has been reactivated.")
        elif created:
            # Create initial course progress
            CourseProgress.objects.create(enrollment=enrollment)
            messages.success(request, f"You have successfully enrolled in '{course.title}'.")
        else:
            messages.info(request, f"You are already enrolled in '{course.title}'.")
        
        return HttpResponseRedirect(reverse('courses:course_detail', kwargs={'course_slug': course_slug}))


class CourseUnenrollView(LoginRequiredMixin, View):
    def post(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug)
        
        try:
            enrollment = Enrollment.objects.get(course=course, user=request.user, is_active=True)
            enrollment.is_active = False
            enrollment.save()
            messages.success(request, f"You have been unenrolled from '{course.title}'.")
        except Enrollment.DoesNotExist:
            messages.error(request, "You are not enrolled in this course.")
        
        return HttpResponseRedirect(reverse('courses:course_detail', kwargs={'course_slug': course_slug}))


class ModuleListView(LoginRequiredMixin, ListView):
    model = Module
    template_name = 'courses/module_list.html'
    context_object_name = 'modules'
    
    def get_queryset(self):
        self.course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        return Module.objects.filter(course=self.course).order_by('order')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        
        # Check if user is enrolled
        context['is_enrolled'] = Enrollment.objects.filter(
            course=self.course, 
            user=self.request.user,
            is_active=True
        ).exists()
        
        if not context['is_enrolled']:
            messages.warning(self.request, "You must be enrolled in this course to view its modules.")
        
        return context


class ModuleDetailView(LoginRequiredMixin, DetailView):
    model = Module
    template_name = 'courses/module_detail.html'
    context_object_name = 'module'
    pk_url_kwarg = 'module_id'
    
    def get_queryset(self):
        self.course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        return Module.objects.filter(course=self.course)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        context['lessons'] = Lesson.objects.filter(module=self.object).order_by('order')
        
        # Check if user is enrolled
        enrollment = get_object_or_404(
            Enrollment, 
            course=self.course, 
            user=self.request.user,
            is_active=True
        )
        
        # Get lesson progress for this module
        if self.request.user.is_authenticated:
            context['lesson_progress'] = {
                lesson.id: LessonProgress.objects.filter(
                    lesson=lesson,
                    course_progress__enrollment=enrollment
                ).first() for lesson in context['lessons']
            }
        
        return context


class LessonDetailView(LoginRequiredMixin, DetailView):
    model = Lesson
    template_name = 'courses/lesson_detail.html'
    context_object_name = 'lesson'
    pk_url_kwarg = 'lesson_id'
    
    def get_queryset(self):
        self.course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        self.module = get_object_or_404(Module, id=self.kwargs['module_id'], course=self.course)
        return Lesson.objects.filter(module=self.module)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        context['module'] = self.module
        
        # Get next and previous lessons
        lessons = list(Lesson.objects.filter(module=self.module).order_by('order'))
        current_index = lessons.index(self.object)
        
        if current_index > 0:
            context['prev_lesson'] = lessons[current_index - 1]
        else:
            # If this is the first lesson of the module, get the last lesson of the previous module
            prev_modules = Module.objects.filter(
                course=self.course, 
                order__lt=self.module.order
            ).order_by('-order')
            
            if prev_modules.exists():
                prev_module = prev_modules.first()
                prev_lessons = Lesson.objects.filter(module=prev_module).order_by('-order')
                if prev_lessons.exists():
                    context['prev_lesson'] = prev_lessons.first()
                    context['prev_module'] = prev_module
        
        if current_index < len(lessons) - 1:
            context['next_lesson'] = lessons[current_index + 1]
        else:
            # If this is the last lesson of the module, get the first lesson of the next module
            next_modules = Module.objects.filter(
                course=self.course, 
                order__gt=self.module.order
            ).order_by('order')
            
            if next_modules.exists():
                next_module = next_modules.first()
                next_lessons = Lesson.objects.filter(module=next_module).order_by('order')
                if next_lessons.exists():
                    context['next_lesson'] = next_lessons.first()
                    context['next_module'] = next_module
        
        # Mark lesson as completed when viewed
        if self.request.user.is_authenticated:
            enrollment = get_object_or_404(
                Enrollment, 
                course=self.course, 
                user=self.request.user,
                is_active=True
            )
            
            course_progress, created = CourseProgress.objects.get_or_create(enrollment=enrollment)
            
            lesson_progress, created = LessonProgress.objects.get_or_create(
                lesson=self.object,
                course_progress=course_progress,
                defaults={'is_completed': False}
            )
            
            context['lesson_progress'] = lesson_progress
        
        return context
    
    def post(self, request, *args, **kwargs):
        lesson = self.get_object()
        enrollment = get_object_or_404(
            Enrollment, 
            course=self.course, 
            user=request.user,
            is_active=True
        )
        
        course_progress = get_object_or_404(CourseProgress, enrollment=enrollment)
        
        lesson_progress, created = LessonProgress.objects.get_or_create(
            lesson=lesson,
            course_progress=course_progress,
            defaults={'is_completed': True}
        )
        
        if not created:
            lesson_progress.is_completed = True
            lesson_progress.save()
        
        # Check if all lessons in the course are completed
        total_lessons = Lesson.objects.filter(module__course=self.course).count()
        completed_lessons = LessonProgress.objects.filter(
            course_progress=course_progress,
            is_completed=True
        ).count()
        
        if total_lessons == completed_lessons:
            course_progress.is_completed = True
            course_progress.save()
            messages.success(request, f"Congratulations! You have completed the course '{self.course.title}'.")
        
        return JsonResponse({
            'success': True,
            'message': 'Lesson marked as completed.'
        })


class CourseProgressView(LoginRequiredMixin, TemplateView):
    template_name = 'courses/course_progress.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        context['course'] = course
        
        enrollment = get_object_or_404(
            Enrollment, 
            course=course, 
            user=self.request.user,
            is_active=True
        )
        
        course_progress, created = CourseProgress.objects.get_or_create(enrollment=enrollment)
        context['course_progress'] = course_progress
        
        # Get all modules and lessons
        modules = Module.objects.filter(course=course).order_by('order')
        context['modules'] = modules
        
        # Get lesson progress for each lesson
        context['lesson_progress'] = {}
        
        for module in modules:
            lessons = Lesson.objects.filter(module=module).order_by('order')
            for lesson in lessons:
                progress = LessonProgress.objects.filter(
                    lesson=lesson,
                    course_progress=course_progress
                ).first()
                
                if progress:
                    context['lesson_progress'][lesson.id] = progress
        
        # Calculate overall progress percentage
        total_lessons = Lesson.objects.filter(module__course=course).count()
        if total_lessons > 0:
            completed_lessons = LessonProgress.objects.filter(
                course_progress=course_progress,
                is_completed=True
            ).count()
            
            context['progress_percentage'] = int((completed_lessons / total_lessons) * 100)
        else:
            context['progress_percentage'] = 0
        
        return context


class CourseCompleteView(LoginRequiredMixin, View):
    def post(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug)
        
        enrollment = get_object_or_404(
            Enrollment, 
            course=course, 
            user=request.user,
            is_active=True
        )
        
        course_progress = get_object_or_404(CourseProgress, enrollment=enrollment)
        course_progress.is_completed = True
        course_progress.save()
        
        messages.success(request, f"Congratulations! You have completed the course '{course.title}'.")
        
        # Trigger any completion hooks or certificate generation here
        
        return HttpResponseRedirect(reverse('courses:course_detail', kwargs={'course_slug': course_slug}))


class CourseReviewListView(ListView):
    model = CourseReview
    template_name = 'courses/course_reviews.html'
    context_object_name = 'reviews'
    paginate_by = 10
    
    def get_queryset(self):
        self.course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        return CourseReview.objects.filter(course=self.course).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        
        # Check if user has already reviewed the course
        if self.request.user.is_authenticated:
            context['user_review'] = CourseReview.objects.filter(
                course=self.course,
                user=self.request.user
            ).first()
            
            # Check if user is eligible to review (i.e., enrolled and has made progress)
            context['can_review'] = Enrollment.objects.filter(
                course=self.course,
                user=self.request.user,
                is_active=True
            ).exists()
        
        # Calculate rating distribution
        rating_distribution = {i: 0 for i in range(1, 6)}
        reviews = self.get_queryset()
        
        for review in reviews:
            rating_distribution[review.rating] += 1
        
        context['rating_distribution'] = rating_distribution
        context['total_reviews'] = reviews.count()
        context['avg_rating'] = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        
        return context


class CourseReviewCreateView(LoginRequiredMixin, CreateView):
    model = CourseReview
    template_name = 'courses/review_form.html'
    fields = ['rating', 'comment']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        return context
    
    def form_valid(self, form):
        course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        
        # Check if user is enrolled in the course
        enrollment = get_object_or_404(
            Enrollment, 
            course=course, 
            user=self.request.user,
            is_active=True
        )
        
        # Check if user has already reviewed this course
        existing_review = CourseReview.objects.filter(
            course=course,
            user=self.request.user
        ).first()
        
        if existing_review:
            messages.error(self.request, "You have already reviewed this course. You can edit your existing review.")
            return HttpResponseRedirect(reverse('courses:course_reviews', kwargs={'course_slug': course.slug}))
        
        form.instance.course = course
        form.instance.user = self.request.user
        
        return super().form_valid(form)
    
    def get_success_url(self):
        messages.success(self.request, "Your review has been submitted successfully.")
        return reverse('courses:course_reviews', kwargs={'course_slug': self.kwargs['course_slug']})


class CourseReviewUpdateView(LoginRequiredMixin, UpdateView):
    model = CourseReview
    template_name = 'courses/review_form.html'
    fields = ['rating', 'comment']
    pk_url_kwarg = 'review_id'
    
    def get_queryset(self):
        return CourseReview.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        context['is_update'] = True
        return context
    
    def get_success_url(self):
        messages.success(self.request, "Your review has been updated successfully.")
        return reverse('courses:course_reviews', kwargs={'course_slug': self.kwargs['course_slug']})


class CourseReviewDeleteView(LoginRequiredMixin, DeleteView):
    model = CourseReview
    template_name = 'courses/review_confirm_delete.html'
    pk_url_kwarg = 'review_id'
    
    def get_queryset(self):
        return CourseReview.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        return context
    
    def get_success_url(self):
        messages.success(self.request, "Your review has been deleted successfully.")
        return reverse('courses:course_reviews', kwargs={'course_slug': self.kwargs['course_slug']})


class UserCourseListView(LoginRequiredMixin, ListView):
    model = Enrollment
    template_name = 'courses/user_courses.html'
    context_object_name = 'enrollments'
    paginate_by = 10
    
    def get_queryset(self):
        return Enrollment.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('-enrolled_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate progress for each enrollment
        for enrollment in context['enrollments']:
            try:
                progress = CourseProgress.objects.get(enrollment=enrollment)
                total_lessons = Lesson.objects.filter(module__course=enrollment.course).count()
                
                if total_lessons > 0:
                    completed_lessons = LessonProgress.objects.filter(
                        course_progress=progress,
                        is_completed=True
                    ).count()
                    
                    enrollment.progress_percentage = int((completed_lessons / total_lessons) * 100)
                else:
                    enrollment.progress_percentage = 0
                    
                enrollment.is_completed = progress.is_completed
            except CourseProgress.DoesNotExist:
                enrollment.progress_percentage = 0
                enrollment.is_completed = False
        
        # Get inactive enrollments
        context['inactive_enrollments'] = Enrollment.objects.filter(
            user=self.request.user,
            is_active=False
        ).order_by('-enrolled_at')
        
        return context


class UserWishlistView(LoginRequiredMixin, ListView):
    model = CourseWishlist
    template_name = 'courses/user_wishlist.html'
    context_object_name = 'wishlist_items'
    paginate_by = 10
    
    def get_queryset(self):
        return CourseWishlist.objects.filter(user=self.request.user).order_by('-added_at')
    
    def post(self, request):
        action = request.POST.get('action')
        course_id = request.POST.get('course_id')
        
        if action and course_id:
            course = get_object_or_404(Course, id=course_id)
            
            if action == 'remove':
                CourseWishlist.objects.filter(
                    user=request.user,
                    course=course
                ).delete()
                
                messages.success(request, f"'{course.title}' has been removed from your wishlist.")
            elif action == 'enroll':
                # Remove from wishlist
                CourseWishlist.objects.filter(
                    user=request.user,
                    course=course
                ).delete()
                
                # Enroll in course
                enrollment, created = Enrollment.objects.get_or_create(
                    course=course,
                    user=request.user,
                    defaults={'is_active': True}
                )
                
                if not created and not enrollment.is_active:
                    enrollment.is_active = True
                    enrollment.save()
                    messages.success(request, f"Welcome back to '{course.title}'! Your enrollment has been reactivated.")
                elif created:
                    CourseProgress.objects.create(enrollment=enrollment)
                    messages.success(request, f"You have successfully enrolled in '{course.title}'.")
                else:
                    messages.info(request, f"You are already enrolled in '{course.title}'.")
        
        return HttpResponseRedirect(reverse('courses:wishlist'))


class RecommendedCoursesView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'courses/recommended_courses.html'
    context_object_name = 'courses'
    paginate_by = 12
    
    def get_queryset(self):
        user = self.request.user
        
        # Get user's enrolled courses
        enrolled_courses = Course.objects.filter(
            enrollment__user=user,
            enrollment__is_active=True
        )
        
        # Get categories and tags from enrolled courses
        categories = enrolled_courses.values_list('category', flat=True).distinct()
        tags = enrolled_courses.values_list('tags', flat=True).distinct()
        
        # Get recommended courses based on categories and tags
        recommended = Course.objects.filter(
            Q(category__in=categories) | Q(tags__in=tags),
            is_published=True
        ).exclude(
            id__in=enrolled_courses.values_list('id', flat=True)
        ).distinct()
        
        # If user has no enrolled courses or no recommendations based on categories/tags,
        # show popular courses based on enrollment count
        if not recommended.exists():
            recommended = Course.objects.filter(
                is_published=True
            ).exclude(
                id__in=enrolled_courses.values_list('id', flat=True)
            ).annotate(
                enrollment_count=Count('enrollment')
            ).order_by('-enrollment_count')
        
        return recommended
