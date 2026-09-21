from app.ai.factory import create_provider
from app.core.config import Settings


def get_provider(settings: Settings):
    return create_provider(settings)
