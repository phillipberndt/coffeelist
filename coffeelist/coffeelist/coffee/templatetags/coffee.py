import re

from django import template
from django.utils.safestring import mark_safe
from django.utils.encoding import force_text

register = template.Library()

@register.filter
def amount(value, smiley=False):
    classes = []
    if value < 0:
        classes.append("debit")
    else:
        classes.append("assets")
    if smiley:
        if value < -10:
            classes.append("bad")
        elif value >= 20:
            classes.append("great")
    return mark_safe('<span class="%s">%+02.2f &euro;</span>' % (" ".join(classes), value))

NAME_PATTERNS = map(re.compile, (
    "(?P<given>[^\s,]+)\s+(?P<family>.+)",
    "(?P<family>[^\s,]+),\s+(?P<given>.+)",
))

def parse_name(name):
    for pattern in NAME_PATTERNS:
        match = pattern.match(name)
        if match:
            return match.groupdict()
    return False

@register.filter
def first_name(value):
    parsed_name = parse_name(force_text(value))
    if parsed_name:
        return parsed_name["given"]
    else:
        return parsed_name
