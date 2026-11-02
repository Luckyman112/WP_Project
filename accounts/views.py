from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import SignUpForm


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("tastings:home")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to the masthead, {user.username}.")
        return redirect("tastings:create")
    return render(request, "registration/signup.html", {"form": form})


def profile(request, username):
    author = get_object_or_404(get_user_model(), username=username)
    return render(request, "accounts/profile.html", {
        "author": author,
        "is_me": request.user == author,
    })
