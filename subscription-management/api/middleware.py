from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.http import JsonResponse

class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.unprotected_routes = {
            '/api/signup/': ['POST'],
            '/api/signin/': ['POST'],
            '/api/validate-otp/': ['POST'],
            '/api/token/refresh/': ['POST'],
            '/api/subscriptions/activate/': ['POST'],
        }

    def __call__(self, request):
        if request.path in self.unprotected_routes:
            unprotected_methods = self.unprotected_routes[request.path]
            if request.method in unprotected_methods:
                return self.get_response(request)
        
        auth_header = request.headers.get('Authorization')

        if auth_header:
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                try:
                    access_token = AccessToken(token)
                    request.customer_id = access_token.payload['customer_id']

                except (InvalidToken, TokenError) as e:
                    return JsonResponse({'error': 'Invalid or expired token'}, status=401)
            else:
                return JsonResponse({'error': 'Authorization header must start with Bearer'}, status=401)
        else:
            return JsonResponse({'error': 'Authorization header missing'}, status=401)

        response = self.get_response(request)
        return response
