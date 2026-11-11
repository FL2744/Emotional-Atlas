"""Stable analysis identities and distinct, readable save names."""
from datetime import datetime, timezone
import re
import uuid


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def session_identity(title, saved=None):
    saved = saved if isinstance(saved, dict) else {}
    identity = saved.get('session_id')
    try:
        identity = str(uuid.UUID(identity))
    except (ValueError, TypeError, AttributeError):
        identity = str(uuid.uuid4())
    created = saved.get('created_at')
    try:
        date = datetime.fromisoformat(created)
        if date.tzinfo is None: date = date.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        date = datetime.now(timezone.utc)
    created = date.isoformat()
    name = saved.get('session_name')
    if not isinstance(name, str) or not name.strip():
        title = ' '.join(str(title).split())[:70] or 'Untitled text'
        name = f"{title} — {date.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')} — {identity[:8]}"
    return {'session_id': identity, 'session_name': name, 'created_at': created}


def session_filename(identity, saved_at):
    name = re.sub(r'[^\w .-]+', '-', identity['session_name']).strip(' .-').encode('utf-8')[:140].decode('utf-8', errors='ignore')
    date = datetime.fromisoformat(saved_at).astimezone()
    return f"{name} — saved {date.strftime('%Y-%m-%d_%H-%M-%S-%f%z')}.json"
