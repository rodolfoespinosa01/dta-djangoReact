from django.http import JsonResponse

def dashboard_view(request):
    return JsonResponse({"message": "Client dashboard placeholder"})
