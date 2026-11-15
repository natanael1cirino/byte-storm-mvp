"""Cabeçalho Content-Security-Policy (RNF02): scripts e estilos só da própria origem."""

POLITICA = (
    "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith("/admin/"):
            response.setdefault("Content-Security-Policy", POLITICA)
        return response
