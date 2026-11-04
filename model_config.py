"""Shared provider configuration, independent of any rules system."""
import os

DEFAULT_MODEL='claude-haiku-5-5'


def model_name():
    name=os.environ.get('ANTHROPIC_MODEL',DEFAULT_MODEL)
    if not name.startswith('claude-haiku-'):raise ValueError('ANTHROPIC_MODEL debe ser un modelo Claude Haiku')
    return name
