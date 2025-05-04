from django.http import JsonResponse

def client_dashboard_view(request):
    return JsonResponse({"message": "Client dashboard placeholder"})
