"""Prepara .env local sem sobrescrever configuracoes existentes."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parent
target = root / '.env'
if target.exists():
    print('.env ja existe; nenhuma alteracao realizada.')
else:
    template = (root / '.env.example').read_text(encoding='utf-8')
    target.write_text(template.replace('SERVICE_API_KEY=\n',
                                      f'SERVICE_API_KEY={secrets.token_urlsafe(32)}\n'),
                      encoding='utf-8')
    print('.env criado. Abra-o para copiar SERVICE_API_KEY para o Authorize do Swagger.')
