"""
URL configuration for finance_tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path("", views.home, name="home")
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path("", Home.as_view(), name="home")
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path("blog/", include("blog.urls"))
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView, LoginView
from django.shortcuts import redirect
from django.contrib.auth import logout as django_logout
from django.views.decorators.http import require_POST
from django.contrib import admin
from django.urls import path, include
from expenses.views import register

@require_POST
def logout_view(request):
    django_logout(request)
    return redirect("login")


urlpatterns = [
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
    path("accounts/login/", LoginView.as_view(template_name="expenses/login.html"), name="login"),
    path("accounts/logout/", logout_view, name="logout"),
    path("signup/", register, name="signup"),
    path("", include("expenses.urls")),
]
