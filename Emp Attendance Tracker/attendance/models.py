from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

DEPARTMENT_CHOICES = [
    ('IT', 'Information Technology'),
    ('HR', 'Human Resources'),
    ('FIN', 'Finance'),
    ('MKT', 'Marketing'),
    ('OPS', 'Operations'),
    ('ENG', 'Engineering'),
    ('SALES', 'Sales'),
    ('ADMIN', 'Administration'),
]

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee")
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    date_joined = models.DateField(default=timezone.localdate)

    class Meta:
        indexes = [
            models.Index(fields=["employee_id"]),
            models.Index(fields=["department"]),
        ]

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name() or self.user.username}"


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendances")
    date = models.DateField()  # date for which attendance is recorded
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    # computed worked hours in seconds stored as integer for quick aggregation
    worked_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("employee", "date")
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["employee", "date"]),
        ]

    def __str__(self):
        return f"{self.employee.employee_id} - {self.date}"

    def save(self, *args, **kwargs):
        # compute worked_seconds if both in/out present
        if self.clock_in and self.clock_out:
            delta = self.clock_out - self.clock_in
            self.worked_seconds = max(0, int(delta.total_seconds()))
        super().save(*args, **kwargs)


class Leave(models.Model):
    LEAVE_STATUS = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leaves")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=LEAVE_STATUS, default="PENDING")
    applied_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_leaves")
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Leave {self.employee.employee_id} {self.start_date} → {self.end_date} ({self.status})"
