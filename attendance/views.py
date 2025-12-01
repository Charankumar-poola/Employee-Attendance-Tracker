# attendance/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Sum, F, Q, Case, When, IntegerField

import csv
import calendar

from .models import Employee, Attendance, Leave
from .forms import EmployeeRegisterForm, AttendanceMarkForm, LeaveApplyForm


def index(request):
    return render(request, "attendance/index.html")


def register_employee(request):
    """
    Web registration view:
    - On GET: render HTML form
    - On POST: validate -> create User + Employee inside a transaction
    then add a success message and redirect (POST-Redirect-GET)
    Notes:
    - This view assumes the form is the improved bootstrap form in templates.
    """
    if request.method == "POST":
        form = EmployeeRegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=data["username"],
                        password=data["password"],
                        first_name=data.get("first_name", ""),
                        last_name=data.get("last_name", ""),
                    )
                    if data.get("is_admin", False):
                        user.is_staff = True
                        user.is_superuser = True
                        user.save()
                    emp = Employee.objects.create(
                        user=user,
                        employee_id=data["employee_id"],
                        department=data.get("department", ""),
                        designation=data.get("designation", ""),
                    )
                messages.success(request, f"Registration successful for {emp.employee_id} — {user.get_full_name() or user.username}. Please login to continue.")
                # Redirect to login page instead of auto-login
                return redirect(reverse("attendance:login"))
            except Exception as e:
                # If something unexpected happened (unique constraint, etc.)
                messages.error(request, f"Could not register user: {str(e)}")
        else:
            # Show validation errors with a friendly message
            messages.error(request, "Please correct the errors below.")
    else:
        form = EmployeeRegisterForm()

    return render(request, "attendance/register.html", {"form": form})


@require_POST
def mark_attendance(request):
    """
    Mark attendance via POST with fields: employee_id, action (IN or OUT), optional timestamp
    (keeps JSON API style to support AJAX / mobile clients)
    """
    form = AttendanceMarkForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"status": "error", "errors": form.errors}, status=400)

    employee_id = form.cleaned_data["employee_id"]
    action = form.cleaned_data["action"]
    timestamp = form.cleaned_data.get("timestamp") or timezone.now()

    try:
        emp = Employee.objects.select_related("user").get(employee_id=employee_id)
    except Employee.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Employee not found"}, status=404)

    date = timezone.localtime(timestamp).date()

    attendance, created = Attendance.objects.get_or_create(employee=emp, date=date)
    if action == "IN":
        attendance.clock_in = timestamp
    else:  # OUT
        attendance.clock_out = timestamp
    attendance.save()

    return JsonResponse({
        "status": "ok",
        "employee": emp.employee_id,
        "date": str(attendance.date),
        "clock_in": attendance.clock_in.isoformat() if attendance.clock_in else None,
        "clock_out": attendance.clock_out.isoformat() if attendance.clock_out else None,
        "worked_seconds": attendance.worked_seconds
    })


@login_required
def mark_attendance_page(request):
    """
    Dedicated page for marking attendance with Clock In and Clock Out buttons.
    """
    return render(request, "attendance/mark_attendance.html")


@login_required
def apply_leave(request):
    """
    View for employees to apply for leave.
    """
    if request.method == "POST":
        form = LeaveApplyForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = request.user.employee
            leave.save()
            messages.success(request, "Leave application submitted successfully.")
            return redirect("attendance:leave_list")
    else:
        form = LeaveApplyForm()
    return render(request, "attendance/apply_leave.html", {"form": form})


@login_required
def leave_list(request):
    """
    View for employees to see their leave applications.
    Staff can see all.
    """
    if request.user.is_staff:
        leaves = Leave.objects.all().select_related("employee__user")
    else:
        leaves = Leave.objects.filter(employee=request.user.employee).select_related("employee__user")
    return render(request, "attendance/leave_list.html", {"leaves": leaves})


@login_required
def monthly_report(request):
    """
    Shows a page where admin/manager can choose month; returns aggregated report.
    Supports department filtering and multiple export formats (CSV, Excel, PDF)

    Non-staff users see only their own data.
    """
    is_staff = request.user.is_staff
    year = int(request.GET.get("year", timezone.now().year))
    month = int(request.GET.get("month", timezone.now().month))
    department = request.GET.get("department", "")

    # compute start/end dates
    last_day = calendar.monthrange(year, month)[1]
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{last_day:02d}"
    working_days = last_day  # Approximate working days

    # query attendance
    att_qs = Attendance.objects.filter(date__range=[start_date, end_date]).select_related("employee", "employee__user")

    if not is_staff:
        # non-staff users only view their own
        try:
            att_qs = att_qs.filter(employee=request.user.employee)
        except Employee.DoesNotExist:
            messages.error(request, "Your account is not linked to an employee record.")
            return redirect("attendance:index")

    # Apply department filter if specified
    if department and is_staff:
        att_qs = att_qs.filter(employee__department=department)

    # aggregate total worked_seconds by employee and compute days_present
    # days_present: count of records where clock_in is not null
    agg = att_qs.values(
        emp_id=F("employee__employee_id"),
        name=F("employee__user__first_name"),
        department=F("employee__department")
    ).annotate(
        total_seconds=Sum("worked_seconds"),
        days_present=Sum(
            Case(
                When(clock_in__isnull=False, then=1),
                default=0,
                output_field=IntegerField()
            )
        )
    ).order_by("emp_id")

    # Prepare rows
    rows = []
    total_present_days = 0
    total_employees = len(agg)

    for r in agg:
        total_seconds = r["total_seconds"] or 0
        hrs = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        days_present = r.get("days_present") or 0
        total_present_days += days_present

        rows.append({
            "employee_id": r["emp_id"],
            "name": r.get("name") or "",
            "department": r.get("department") or "",
            "days_present": days_present,
            "total_time": f"{hrs}h {mins}m",
            "total_seconds": total_seconds
        })

    # Calculate summary statistics
    average_attendance = f"{(total_present_days / (total_employees * working_days) * 100):.1f}%" if total_employees > 0 else "0%"
    total_hours = f"{sum(r['total_seconds'] for r in rows) // 3600}h"

    download = request.GET.get("download")
    if download:
        filename = f"attendance_report_{year}_{month:02d}"

        if download == "csv":
            # CSV response
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
            writer = csv.writer(response)
            writer.writerow(["Employee ID", "Name", "Department", "Days Present", "Total Time", "Attendance %"])
            for r in rows:
                attendance_percent = (r["days_present"] / working_days * 100) if working_days > 0 else 0
                writer.writerow([
                    r["employee_id"],
                    r["name"],
                    r["department"],
                    r["days_present"],
                    r["total_time"],
                    f"{attendance_percent:.1f}%"
                ])
            return response

        elif download == "excel":
            # Excel response (using CSV for simplicity, can be enhanced with openpyxl)
            response = HttpResponse(content_type="application/vnd.ms-excel")
            response["Content-Disposition"] = f'attachment; filename="{filename}.xls"'
            writer = csv.writer(response)
            writer.writerow(["Employee ID", "Name", "Department", "Days Present", "Total Time", "Attendance %"])
            for r in rows:
                attendance_percent = (r["days_present"] / working_days * 100) if working_days > 0 else 0
                writer.writerow([
                    r["employee_id"],
                    r["name"],
                    r["department"],
                    r["days_present"],
                    r["total_time"],
                    f"{attendance_percent:.1f}%"
                ])
            return response

        elif download == "pdf":
            # PDF response (placeholder - would need reportlab or similar)
            response = HttpResponse(content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
            # For now, return CSV as PDF placeholder
            writer = csv.writer(response)
            writer.writerow(["Employee ID", "Name", "Department", "Days Present", "Total Time", "Attendance %"])
            for r in rows:
                attendance_percent = (r["days_present"] / working_days * 100) if working_days > 0 else 0
                writer.writerow([
                    r["employee_id"],
                    r["name"],
                    r["department"],
                    r["days_present"],
                    r["total_time"],
                    f"{attendance_percent:.1f}%"
                ])
            return response

    context = {
        "rows": rows,
        "year": year,
        "month": month,
        "department": department,
        "is_staff": is_staff,
        "total_employees": total_employees,
        "total_present_days": total_present_days,
        "average_attendance": average_attendance,
        "total_hours": total_hours,
        "working_days": working_days
    }

    return render(request, "attendance/report.html", context)


@staff_member_required
def terminate_employee(request, employee_id):
    if request.method == 'POST':
        try:
            emp = Employee.objects.get(employee_id=employee_id)
            emp.user.is_active = False
            emp.user.save()
            messages.success(request, f"Employee {emp.employee_id} has been terminated.")
        except Employee.DoesNotExist:
            messages.error(request, "Employee not found.")
    return redirect('attendance:user_list')


@staff_member_required
def activate_employee(request, employee_id):
    if request.method == 'POST':
        try:
            emp = Employee.objects.get(employee_id=employee_id)
            emp.user.is_active = True
            emp.user.save()
            messages.success(request, f"Employee {emp.employee_id} has been activated.")
        except Employee.DoesNotExist:
            messages.error(request, "Employee not found.")
    return redirect('attendance:user_list')


@staff_member_required
def user_list(request):
    """
    Staff-only view listing registered employees with pagination and search.
    Supports CSV download by adding ?download=csv.
    """
    q = request.GET.get("q", "").strip()
    qs = Employee.objects.select_related("user").filter(user__is_active=True).order_by("-date_joined")

    if q:
        qs = qs.filter(
            Q(employee_id__icontains=q) |
            Q(user__username__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q)
        )

    # CSV export support (exports the entire current filtered queryset)
    if request.GET.get("download") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="employees.csv"'
        writer = csv.writer(response)
        writer.writerow(["employee_id", "username", "full_name", "department", "designation", "date_joined"])
        for emp in qs:
            writer.writerow([
                emp.employee_id,
                emp.user.username,
                emp.user.get_full_name(),
                emp.department,
                emp.designation,
                emp.date_joined.isoformat()
            ])
        return response

    paginator = Paginator(qs, 20)  # 20 rows/page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    total_count = Employee.objects.filter(user__is_active=True).count()

    return render(request, "attendance/user_list.html", {
        "page_obj": page_obj,
        "total_count": total_count,
        "q": q,
    })
