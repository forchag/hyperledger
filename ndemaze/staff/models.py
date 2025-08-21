from django.contrib.auth.models import AbstractUser
from django.db import models


class StaffUser(AbstractUser):
    """User model for hotel staff.

    Guests never create accounts; only staff members exist in the auth
    system. The ``role`` field helps control access to different modules
    of the back office.
    """

    ROLE_CHOICES = [
        ("frontdesk", "Front Desk"),
        ("housekeeping", "Housekeeping"),
        ("maintenance", "Maintenance"),
        ("finance", "Finance"),
        ("manager", "Manager"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=30)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.username} ({self.get_role_display()})"
