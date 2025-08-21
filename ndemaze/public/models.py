from django.db import models
from django.conf import settings


class RoomType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_occupancy = models.PositiveIntegerField()
    amenities = models.JSONField(default=list)
    photos = models.JSONField(default=list)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name


class Room(models.Model):
    STATUS_CHOICES = [
        ("vacant", "Vacant"),
        ("clean", "Clean"),
        ("dirty", "Dirty"),
        ("ooo", "Out of Order"),
    ]

    number = models.CharField(max_length=10)
    floor = models.IntegerField()
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="vacant")
    notes = models.TextField(blank=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Room {self.number}"


class Guest(models.Model):
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=50)
    email = models.EmailField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.full_name


class Reservation(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("checked_in", "Checked-in"),
        ("checked_out", "Checked-out"),
        ("cancelled", "Cancelled"),
    ]
    SOURCE_CHOICES = [("online", "Online"), ("walkin", "Walk-in")]

    ref_code = models.CharField(max_length=30, unique=True)
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    checkin_date = models.DateField()
    checkout_date = models.DateField()
    adults = models.PositiveIntegerField()
    children = models.PositiveIntegerField(default=0)
    created_by_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.ref_code


class ReservationRoom(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL)
    rate_plan = models.CharField(max_length=50)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    taxes = models.JSONField(default=list)


class FolioItem(models.Model):
    KIND_CHOICES = [
        ("room", "Room"),
        ("addon", "Add-on"),
        ("tax", "Tax"),
        ("adjustment", "Adjustment"),
    ]

    reservation = models.ForeignKey(
        Reservation, on_delete=models.CASCADE, related_name="folio_items"
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="XAF")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
