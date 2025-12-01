#!/usr/bin/env python
"""
Script to demonstrate safe ways to delete user data from the Employee Attendance Tracker database
WARNING: Deletion operations are irreversible. Use with caution.
"""

import os
import django
from django.db import transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_project.settings')
django.setup()

from attendance.models import Employee, Attendance, Leave
from django.contrib.auth.models import User

def list_all_users():
    """List all users for reference"""
    print("=== CURRENT USERS IN DATABASE ===")

    employees = Employee.objects.select_related('user').order_by('employee_id')
    for emp in employees:
        status = "ACTIVE" if emp.user.is_active else "INACTIVE"
        role = "ADMIN" if emp.user.is_staff else "EMPLOYEE"
        print(f"ID: {emp.employee_id} | Name: {emp.user.get_full_name() or emp.user.username} | Status: {status} | Role: {role}")
    print()

def delete_user_by_employee_id(employee_id):
    """Delete a user by employee ID (safest method)"""
    print(f"=== DELETING USER WITH EMPLOYEE ID: {employee_id} ===")

    try:
        with transaction.atomic():
            # Get the employee
            employee = Employee.objects.select_related('user').get(employee_id=employee_id)

            # Delete related records first (due to foreign keys)
            Attendance.objects.filter(employee=employee).delete()
            Leave.objects.filter(employee=employee).delete()

            # Store user info for confirmation
            user_info = f"{employee.user.get_full_name() or employee.user.username} ({employee.employee_id})"

            # Delete the employee (this will also delete the user due to CASCADE)
            employee.delete()

            print(f"✓ Successfully deleted user: {user_info}")
            print("  - Deleted attendance records")
            print("  - Deleted leave applications")
            print("  - Deleted employee profile")
            print("  - Deleted user account")

    except Employee.DoesNotExist:
        print(f"✗ Employee with ID '{employee_id}' not found")
    except Exception as e:
        print(f"✗ Error deleting user: {e}")

def deactivate_user_by_employee_id(employee_id):
    """Deactivate a user instead of deleting (safer approach)"""
    print(f"=== DEACTIVATING USER WITH EMPLOYEE ID: {employee_id} ===")

    try:
        employee = Employee.objects.select_related('user').get(employee_id=employee_id)
        employee.user.is_active = False
        employee.user.save()

        user_info = f"{employee.user.get_full_name() or employee.user.username} ({employee.employee_id})"
        print(f"✓ Successfully deactivated user: {user_info}")
        print("  Note: Data is preserved but user cannot login")

    except Employee.DoesNotExist:
        print(f"✗ Employee with ID '{employee_id}' not found")
    except Exception as e:
        print(f"✗ Error deactivating user: {e}")

def delete_all_inactive_users():
    """Delete all inactive users"""
    print("=== DELETING ALL INACTIVE USERS ===")

    inactive_employees = Employee.objects.select_related('user').filter(user__is_active=False)

    if not inactive_employees:
        print("No inactive users found")
        return

    count = 0
    for emp in inactive_employees:
        try:
            with transaction.atomic():
                # Delete related records
                Attendance.objects.filter(employee=emp).delete()
                Leave.objects.filter(employee=emp).delete()

                user_info = f"{emp.user.get_full_name() or emp.user.username} ({emp.employee_id})"
                emp.delete()

                print(f"✓ Deleted: {user_info}")
                count += 1

        except Exception as e:
            print(f"✗ Error deleting {emp.employee_id}: {e}")

    print(f"\nTotal inactive users deleted: {count}")

def delete_user_by_username(username):
    """Delete user by username"""
    print(f"=== DELETING USER WITH USERNAME: {username} ===")

    try:
        with transaction.atomic():
            user = User.objects.get(username=username)

            # Find associated employee
            try:
                employee = Employee.objects.get(user=user)

                # Delete related records
                Attendance.objects.filter(employee=employee).delete()
                Leave.objects.filter(employee=employee).delete()

                user_info = f"{user.get_full_name() or user.username} ({employee.employee_id})"
                employee.delete()

            except Employee.DoesNotExist:
                # User exists but no employee record - delete user directly
                user_info = f"{user.get_full_name() or user.username}"
                user.delete()

            print(f"✓ Successfully deleted user: {user_info}")

    except User.DoesNotExist:
        print(f"✗ User with username '{username}' not found")
    except Exception as e:
        print(f"✗ Error deleting user: {e}")

def bulk_delete_by_department(department):
    """Delete all users from a specific department"""
    print(f"=== DELETING ALL USERS FROM DEPARTMENT: {department} ===")

    employees = Employee.objects.select_related('user').filter(department=department)

    if not employees:
        print(f"No employees found in department '{department}'")
        return

    count = 0
    for emp in employees:
        try:
            with transaction.atomic():
                # Delete related records
                Attendance.objects.filter(employee=emp).delete()
                Leave.objects.filter(employee=emp).delete()

                user_info = f"{emp.user.get_full_name() or emp.user.username} ({emp.employee_id})"
                emp.delete()

                print(f"✓ Deleted: {user_info}")
                count += 1

        except Exception as e:
            print(f"✗ Error deleting {emp.employee_id}: {e}")

    print(f"\nTotal users deleted from {department}: {count}")

def show_deletion_options():
    """Show available deletion options"""
    print("=== USER DELETION OPTIONS ===")
    print("1. Delete by Employee ID (safest)")
    print("2. Deactivate by Employee ID (recommended)")
    print("3. Delete by Username")
    print("4. Delete all inactive users")
    print("5. Delete all users from a department")
    print("\nWARNING: Deletion is irreversible!")
    print("Consider deactivating users instead of deleting them.")
    print()

if __name__ == '__main__':
    print("Employee Attendance Tracker - User Deletion Script")
    print("=" * 60)
    print("WARNING: This script can permanently delete user data!")
    print("Make sure to backup your database before proceeding.\n")

    list_all_users()
    show_deletion_options()

    print("=== EXAMPLES (uncomment to use) ===")
    print("# Delete specific user:")
    print("# delete_user_by_employee_id('01')")
    print()
    print("# Deactivate user (safer):")
    print("# deactivate_user_by_employee_id('01')")
    print()
    print("# Delete by username:")
    print("# delete_user_by_username('testuser')")
    print()
    print("# Delete all inactive users:")
    print("# delete_all_inactive_users()")
    print()
    print("# Delete all from department:")
    print("# bulk_delete_by_department('IT')")
    print()
    print("Edit this script and uncomment the desired operation.")
