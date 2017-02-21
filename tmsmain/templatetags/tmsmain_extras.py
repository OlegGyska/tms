from django import template
from django.core.urlresolvers import reverse

register = template.Library()


@register.simple_tag()
def get_choice(choices, index):
    return choices[index-1][1]


@register.simple_tag()
def span_pend_date(task):
    if task.status == task.PEND_N:
        return ' ' + task.delaytill.strftime('%d %b %Y')
    else:
        return ''


@register.simple_tag
def q_transform(request, **kwargs):
    updated = request.GET.copy()
    for key, value in kwargs.items():
        updated[key] = value
    return '?' + updated.urlencode()