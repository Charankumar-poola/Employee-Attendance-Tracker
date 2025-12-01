from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from . import views

app_name = "attendance"

urlpatterns = [
    path("", views.index, name="index"),
    path("register/", views.register_employee, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="attendance/login.html"), name="login"),
    path("mark/", views.mark_attendance, name="mark"),
    path("mark-attendance/", views.mark_attendance_page, name="mark_attendance_page"),
    path("report/", views.monthly_report, name="monthly_report"),
    path("apply-leave/", views.apply_leave, name="apply_leave"),
    path("leave-list/", views.leave_list, name="leave_list"),
    # attendance/urls.py (append)
    path("users/", views.user_list, name="user_list"),
    path("users/terminate/<str:employee_id>/", views.terminate_employee, name="terminate_employee"),
    path("users/activate/<str:employee_id>/", views.activate_employee, name="activate_employee"),
    path("logout/", LogoutView.as_view(next_page="attendance:index"), name="logout"),
]
