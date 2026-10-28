"""No implicit external side effects. Caller must opt in to send."""
import requests


def telegram(message, token=None, chat_id=None, dry_run=True):
    if dry_run:
        return {'dry_run': True, 'message': message}
    if not token or not chat_id:
        raise ValueError('Explicit token and chat_id required')
    response = requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
                             json={'chat_id': chat_id, 'text': message}, timeout=30)
    response.raise_for_status()
    result = response.json()
    if not result.get('ok'):
        raise RuntimeError('Telegram rejected message')
    return result
