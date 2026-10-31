"""Tokenisation shared by training, document embedding and query embedding.

The same function must be used everywhere: a word that is tokenised differently
at query time than at training time is an unknown word.
"""
import re
from typing import List

_WORD = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")

# Short, fixed English stop-word list (no external download). Used only when
# a configuration asks for it; the PDF baseline keeps every word.
STOPWORDS = frozenset("""
a about above after again against all am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have
having he her here hers herself him himself his how i if in into is it its itself just let me more
most my myself no nor not now of off on once only or other our ours ourselves out over own same she
should so some such than that the their theirs them themselves then there these they this those
through to too under until up very was we were what when where which while who whom why will with
would you your yours yourself yourselves s t ll ve re d m
""".split())


def tokenize(text: str, drop_stopwords: bool = False, min_length: int = 1) -> List[str]:
    """Lower-case word tokens; digits kept (visa categories and form numbers matter here)."""
    tokens = _WORD.findall(text.lower())
    if drop_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    if min_length > 1:
        tokens = [t for t in tokens if len(t) >= min_length]
    return tokens
