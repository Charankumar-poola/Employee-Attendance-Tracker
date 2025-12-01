from django import template
from django.utils.html import format_html

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Usage:
      {% load form_tags %}
      {{ form.fieldname|add_class:"form-control" }}
    """
    try:
        return field.as_widget(attrs={"class": css_class})
    except Exception:
        return format_html("{}", field)
