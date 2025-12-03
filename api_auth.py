"""Helpers para autenticação das rotas da API do painel."""
from functools import wraps
from flask import request, jsonify
from config import PANEL_API_TOKEN

UNAUTHORIZED_RESPONSE = ({'success': False, 'error': 'Não autorizado'}, 401)
MISSING_TOKEN_RESPONSE = ({'success': False, 'error': 'Token de API não configurado'}, 500)


def require_api_token(func):
    """Decorator que valida o token enviado no header Authorization."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not PANEL_API_TOKEN:
            return MISSING_TOKEN_RESPONSE

        token = _extract_token()
        if token != PANEL_API_TOKEN:
            return UNAUTHORIZED_RESPONSE

        return func(*args, **kwargs)

    return wrapper


def _extract_token():
    """Extrai token do header Authorization ou do header personalizado."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.lower().startswith('bearer '):
        return auth_header[7:].strip()

    custom_header = request.headers.get('X-API-Token')
    if custom_header:
        return custom_header.strip()

    return request.args.get('api_token', '').strip()
