from django.db import connection
from django.http import JsonResponse


def health(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        connection.ensure_connection()
        database = 'connected'
    except Exception:
        database = 'disconnected'

    return JsonResponse({
        'status': 'running',
        'database': database,
        'service': 'astronaut-intelligence',
    })
