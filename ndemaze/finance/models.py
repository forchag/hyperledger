from django.db import models
from django.conf import settings


class Payment(models.Model):
    METHOD_CHOICES = [
        ("cash", "Cash"),
        ("bank", "Bank Transfer"),
        ("momo", "Mobile Money"),
        ("card", "Card"),
    ]

    reservation = models.ForeignKey(
        "public.Reservation", on_delete=models.CASCADE, related_name="payments"
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="XAF")
    gateway_ref = models.CharField(max_length=100, blank=True, null=True)
    staff_note = models.TextField(blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )


class Receipt(models.Model):
    reservation = models.ForeignKey(
        "public.Reservation", on_delete=models.CASCADE, related_name="receipts"
    )
    receipt_number = models.CharField(max_length=30, unique=True)
    pdf_url = models.URLField()
    issued_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
