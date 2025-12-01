#!/usr/bin/env python
"""
Script to demonstrate different ways to query user data from the Employee Attendance Tracker database
"""

import os
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_project.settings')
django.setup()

from attendance.models import Employee, Attendance, Leave
from django.contrib.auth.models import User
from django.db.models import Count, Sum, F

def query_employees_django_orm():
    """Query employee data using Django ORM"""
    print("=== EMPLOYEE DATA (Django ORM) ===")

    employees = Employee.objects.select_related('user').filter(user__is_active=True)

    for emp in employees:
        print(f"Employee ID: {emp.employee_id}")
        print(f"Name: {emp.user.get_full_name() or emp.user.username}")
        print(f"Username: {emp.user.username}")
        print(f"Email: {emp.user.email}")
        print(f"Department: {emp.department}")
        print(f"Designation: {emp.designation}")
        print(f"Date Joined: {emp.date_joined}")
        print(f"Is Staff: {emp.user.is_staff}")
        print("-" * 50)

def query_attendance_data():
    """Query attendance data"""
    print("\n=== ATTENDANCE DATA ===")

    attendance_records = Attendance.objects.select_related('employee__user').order_by('-date')[:10]

    for att in attendance_records:
        print(f"Employee: {att.employee.employee_id} - {att.employee.user.get_full_name() or att.employee.user.username}")
        print(f"Date: {att.date}")
        print(f"Clock In: {att.clock_in}")
        print(f"Clock Out: {att.clock_out}")
        print(f"Worked Hours: {att.worked_seconds // 3600}h {(att.worked_seconds % 3600) // 60}m")
        print("-" * 50)

def query_leave_data():
    """Query leave data"""
    print("\n=== LEAVE DATA ===")

    leaves = Leave.objects.select_related('employee__user', 'approved_by').order_by('-applied_at')[:5]

    for leave in leaves:
        print(f"Employee: {leave.employee.employee_id} - {leave.employee.user.get_full_name() or leave.employee.user.username}")
        print(f"Leave Period: {leave.start_date} to {leave.end_date}")
        print(f"Reason: {leave.reason}")
        print(f"Status: {leave.status}")
        print(f"Applied At: {leave.applied_at}")
        if leave.approved_by:
            print(f"Approved By: {leave.approved_by.get_full_name() or leave.approved_by.username}")
        print("-" * 50)

def query_with_raw_sql():
    """Query using raw SQL"""
    print("\n=== RAW SQL QUERY RESULTS ===")

    with connection.cursor() as cursor:
        # Query employee data with user information
        cursor.execute("""
            SELECT
                e.employee_id,
                u.username,
                u.first_name,
                u.last_name,
                u.email,
                e.department,
                e.designation,
                e.date_joined,
                u.is_staff,
                u.is_active
            FROM attendance_employee e
            JOIN auth_user u ON e.user_id = u.id
            WHERE u.is_active = 1
            ORDER BY e.date_joined DESC
        """)

        columns = [col[0] for col in cursor.description]
        results = cursor.fetchall()

        print(f"Found {len(results)} active employees:")
        for row in results:
            data = dict(zip(columns, row))
            print(f"ID: {data['employee_id']}, Name: {data['first_name']} {data['last_name']}, Dept: {data['department']}")

def get_attendance_summary():
    """Get attendance summary statistics"""
    print("\n=== ATTENDANCE SUMMARY ===")

    # Monthly attendance summary
    from django.db.models import Case, When, IntegerField, Avg
    from django.utils import timezone
    import calendar

    current_year = timezone.now().year
    current_month = timezone.now().month

    last_day = calendar.monthrange(current_year, current_month)[1]
    start_date = f"{current_year}-{current_month:02d}-01"
    end_date = f"{current_year}-{current_month:02d}-{last_day}"

    summary = Attendance.objects.filter(
        date__range=[start_date, end_date]
    ).values('employee__employee_id', 'employee__user__first_name').annotate(
        total_days=Count('date'),
        present_days=Sum(
            Case(
                When(clock_in__isnull=False, then=1),
                default=0,
                output_field=IntegerField()
            )
        ),
        total_seconds=Sum(F('worked_seconds'))
    ).order_by('employee__employee_id')

    print(f"Attendance Summary for {current_year}-{current_month:02d}:")
    for stat in summary:
        attendance_rate = (stat['present_days'] / stat['total_days'] * 100) if stat['total_days'] > 0 else 0
        total_hours = stat['total_seconds'] // 3600 if stat['total_seconds'] else 0
        print(f"{stat['employee__employee_id']} - {stat['employee__user__first_name']}: {stat['present_days']}/{stat['total_days']} days ({attendance_rate:.1f}%), {total_hours}h worked")

def export_to_csv():
    """Export employee data to CSV"""
    print("\n=== EXPORTING TO CSV ===")

    import csv
    from django.http import HttpResponse

    # Simulate CSV export like in the views
    employees = Employee.objects.select_related('user').filter(user__is_active=True)

    filename = "employee_data_export.csv"
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Employee ID', 'Username', 'Full Name', 'Email', 'Department', 'Designation', 'Date Joined', 'Is Staff'])

        for emp in employees:
            writer.writerow([
                emp.employee_id,
                emp.user.username,
                emp.user.get_full_name(),
                emp.user.email,
                emp.department,
                emp.designation,
                emp.date_joined.isoformat(),
                emp.user.is_staff
            ])

    print(f"Data exported to {filename}")

if __name__ == '__main__':
    print("Employee Attendance Tracker - Database Query Examples")
    print("=" * 60)

    query_employees_django_orm()
    query_attendance_data()
    query_leave_data()
    query_with_raw_sql()
    get_attendance_summary()
    export_to_csv()

    print("\n=== ADDITIONAL QUERY EXAMPLES ===")
    print("1. Get employees by department:")
    print("   Employee.objects.filter(department='IT')")
    print("\n2. Get attendance for specific employee:")
    print("   Attendance.objects.filter(employee__employee_id='EMP001')")
    print("\n3. Get pending leaves:")
    print("   Leave.objects.filter(status='PENDING')")
    print("\n4. Get users with admin access:")
    print("   User.objects.filter(is_staff=True)")
    print("\n5. Complex query with aggregations:")
    print("   Attendance.objects.filter(date__month=12).aggregate(avg_hours=Avg('worked_seconds'))")
