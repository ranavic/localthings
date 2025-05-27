from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.generic import View
from django.utils.decorators import method_decorator

@login_required
def profile_view(request):
    """View for displaying the user's profile."""
    return render(request, 'users/profile.html')

class ProfileView(View):
    """Class-based view for handling user profiles."""
    @method_decorator(login_required)
    def get(self, request):
        return render(request, 'users/profile.html')
