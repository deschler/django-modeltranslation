import copy

from django.forms.widgets import Widget, CheckboxInput
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext


class ClearableWidgetWrapper(Widget):
    clear_checkbox_label = ugettext("None")
    template = u'<span class="clearable-input">{0} <span>{2}</span> {3}</span>'
    # TODO: Label would be proper, but admin applies some hardly undoable
    #       styling to labels.
    # template = '<span class="clearable-input">{} <label for="{}">{}</label> {}</span>'

    def __init__(self, widget, empty_value=None):
        """
        Remebers the widget we are wrapping and precreates a checkbox input.
        Allows overriding the empty value.
        """
        self.widget = widget
        self.checkbox = CheckboxInput()
        self.empty_value = empty_value

    def __getattr__(self, name):
        """
        If we don't have a property or a method, chances are the wrapped
        widget does.
        """
        return getattr(self.widget, name)

    def render(self, name, value, attrs=None):
        """
        Appends a checkbox for clearing the value (that is setting the field
        with the ``empty_value``).
        """
        wrapped = self.widget.render(name, value, attrs)
        checkbox_name = self.clear_checkbox_name(name)
        checkbox_id = self.clear_checkbox_id(checkbox_name)
        checkbox_label = self.clear_checkbox_label
        checkbox = self.checkbox.render(
            checkbox_name, value == self.empty_value, attrs={'id': checkbox_id})
        return mark_safe(self.template.format(
            conditional_escape(wrapped),
            conditional_escape(checkbox_id),
            conditional_escape(checkbox_label),
            conditional_escape(checkbox)))

    def value_from_datadict(self, data, files, name):
        """
        If the clear checkbox is checked returns the empty value, completely
        ignoring the original input.
        """
        clear = self.checkbox.value_from_datadict(data, files, self.clear_checkbox_name(name))
        if clear:
            return self.empty_value
        return self.widget.value_from_datadict(data, files, name)

    def _has_changed(self, initial, data):
        """
        Widget implementation equates ``None``s with empty strings.
        """
        if (initial is None and data is not None) or (initial is not None and data is None):
            return True
        return self.widget._has_changed(initial, data)

    def clear_checkbox_name(self, name):
        """
        Given the name of the input, returns the name of the clear checkbox.
        """
        return name + '-clear'

    def clear_checkbox_id(self, name):
        """
        Given the name of the clear checkbox input, returns the HTML id for it.
        """
        return name + '_id'
