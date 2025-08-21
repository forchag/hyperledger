from django.db import models
from django.conf import settings


class BlogPost(models.Model):
    STATUS_CHOICES = [("draft", "Draft"), ("published", "Published")]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    body_html = models.TextField()
    cover_media_url = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    published_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["-published_at", "-id"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.title
