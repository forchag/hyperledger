from django.http import HttpResponse


def home(request):
    """Public landing page placeholder."""
    return HttpResponse("Ndemaze Guest House")
