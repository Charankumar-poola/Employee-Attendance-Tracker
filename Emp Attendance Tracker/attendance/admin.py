from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from .models import Employee, Attendance, Leave
import csv

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "user", "department", "designation", "date_joined", "is_active")
    search_fields = ("employee_id", "user__username", "user__first_name", "user__last_name", "department", "designation")
    list_filter = ("department", "designation", "date_joined", "user__is_active")
    list_editable = ("department", "designation")
    ordering = ("-date_joined",)

    def is_active(self, obj):
        return obj.user.is_active
    is_active.boolean = True
    is_active.short_description = "Active"

    actions = ["export_csv", "activate_users", "deactivate_users"]

    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="employees.csv"'
        writer = csv.writer(response)
        writer.writerow(['Employee ID', 'Username', 'Full Name', 'Department', 'Designation', 'Date Joined', 'Active'])
        for emp in queryset:
            writer.writerow([
                emp.employee_id,
                emp.user.username,
                emp.user.get_full_name(),
                emp.department,
                emp.designation,
                emp.date_joined,
                emp.user.is_active
            ])
        return response
    export_csv.short_description = "Export selected employees to CSV"

    def activate_users(self, request, queryset):
        for emp in queryset:
            emp.user.is_active = True
            emp.user.save()
        self.message_user(request, f"Activated {queryset.count()} employees.")
    activate_users.short_description = "Activate selected employees"

    def deactivate_users(self, request, queryset):
        for emp in queryset:
            emp.user.is_active = False
            emp.user.save()
        self.message_user(request, f"Deactivated {queryset.count()} employees.")
    deactivate_users.short_description = "Deactivate selected employees"


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "clock_in", "clock_out", "worked_seconds", "worked_hours")
    search_fields = ("employee__employee_id", "employee__user__username", "employee__user__first_name", "employee__user__last_name")
    list_filter = ("date", "employee__department")
    date_hierarchy = "date"
    ordering = ("-date", "-clock_in")

    def worked_hours(self, obj):
        if obj.worked_seconds:
            hours = obj.worked_seconds // 3600
            minutes = (obj.worked_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        return "0h 0m"
    worked_hours.short_description = "Worked Hours"

    actions = ["export_csv"]

    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="attendance.csv"'
        writer = csv.writer(response)
        writer.writerow(['Employee ID', 'Name', 'Department', 'Date', 'Clock In', 'Clock Out', 'Worked Hours'])
        for att in queryset.select_related('employee', 'employee__user'):
            worked_hours = self.worked_hours(att)
            writer.writerow([
                att.employee.employee_id,
                att.employee.user.get_full_name() or att.employee.user.username,
                att.employee.department,
                att.date,
                att.clock_in,
                att.clock_out,
                worked_hours
            ])
        return response
    export_csv.short_description = "Export selected attendance records to CSV"


@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ("employee", "start_date", "end_date", "status", "applied_at", "approved_by")
    search_fields = ("employee__employee_id", "employee__user__username", "employee__user__first_name", "employee__user__last_name")
    list_filter = ("status", "start_date", "end_date", "applied_at")
    date_hierarchy = "applied_at"
    ordering = ("-applied_at",)

    actions = ["approve_leaves", "reject_leaves", "export_csv"]

    def approve_leaves(self, request, queryset):
        queryset.update(status="APPROVED", approved_at=timezone.now(), approved_by=request.user)
        self.message_user(request, f"Approved {queryset.count()} leave applications.")
    approve_leaves.short_description = "Approve selected leave applications"

    def reject_leaves(self, request, queryset):
        queryset.update(status="REJECTED", approved_at=timezone.now(), approved_by=request.user)
        self.message_user(request, f"Rejected {queryset.count()} leave applications.")
    reject_leaves.short_description = "Reject selected leave applications"

    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="leaves.csv"'
        writer = csv.writer(response)
        writer.writerow(['Employee ID', 'Name', 'Start Date', 'End Date', 'Reason', 'Status', 'Applied At', 'Approved By'])
        for leave in queryset.select_related('employee', 'employee__user', 'approved_by'):
            writer.writerow([
                leave.employee.employee_id,
                leave.employee.user.get_full_name() or leave.employee.user.username,
                leave.start_date,
                leave.end_date,
                leave.reason,
                leave.status,
                leave.applied_at,
                leave.approved_by.get_full_name() if leave.approved_by else ""
            ])
        return response
    export_csv.short_description = "Export selected leave records to CSV"
