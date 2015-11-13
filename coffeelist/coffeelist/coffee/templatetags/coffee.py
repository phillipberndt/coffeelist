from django import template

from django.utils.safestring import mark_safe

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
