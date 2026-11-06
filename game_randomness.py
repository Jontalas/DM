"""Per-execution dice source, isolated across threads and reset on exceptions."""
from contextlib import contextmanager
from contextvars import ContextVar
import secrets

_SOURCE=ContextVar('cronicas-game-random-source',default=None)


@contextmanager
def using_random_source(source):
    if not callable(source):raise ValueError('Fuente de dados inválida')
    token=_SOURCE.set(source)
    try:yield
    finally:_SOURCE.reset(token)


def draw(sides):
    if type(sides)!=int or not 2<=sides<=1000000:raise ValueError('Dado fuera del límite operativo')
    source=_SOURCE.get();value=source(sides) if source is not None else secrets.randbelow(sides)+1
    if type(value)!=int or not 1<=value<=sides:raise ValueError('La fuente devolvió un dado inválido')
    return value


def initiative_tie():
    # Preserve the original uniform 16-bit ordering key. It belongs to the same
    # durable stream when running a persisted action, rather than fresh entropy.
    return secrets.randbits(16) if _SOURCE.get() is None else draw(65536)-1
