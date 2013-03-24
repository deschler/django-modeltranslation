from django.contrib.admin.widgets import AdminTextInputWidget, AdminTextareaWidget
from django.forms.widgets import Widget, TextInput, Textarea, CheckboxInput
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext


class ClearableInput(Widget):
    clear_checkbox_label = ugettext("None")
    template = '{0} <span>{2}</span> {3}'
    # TODO: Label would be proper, but admin applies some hardly undoable
    # styling to labels.
    # template = '{} <label for="{}">{}</label> {}'

    def __init__(self, *args, **kwargs):
        """
        Allows overriding the empty value.
        """
        self.empty_value = kwargs.get('empty_value', None)
        super(ClearableInput, self).__init__(*args, **kwargs)

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

    def render(self, name, value, attrs=None):
        """
        If the field is not required, appends a checkbox that clears the value.
        """
        original = super(ClearableInput, self).render(name, value, attrs)
        if self.is_required:
            return original
        else:
            checkbox_name = self.clear_checkbox_name(name)
            checkbox_id = self.clear_checkbox_id(checkbox_name)
            checkbox_label = self.clear_checkbox_label
            checkbox = CheckboxInput().render(
                checkbox_name, value == self.empty_value, attrs={'id': checkbox_id})
            return mark_safe(self.template.format(
                conditional_escape(original),
                conditional_escape(checkbox_id),
                conditional_escape(checkbox_label),
                conditional_escape(checkbox)))

    def value_from_datadict(self, data, files, name):
        """
        If the clear checkbox is checked returns the empty value, completely
        ignoring the original input.
        """
        clear = CheckboxInput().value_from_datadict(data, files, self.clear_checkbox_name(name))
        if not self.is_required and clear:
            return self.empty_value
        else:
            return super(ClearableInput, self).value_from_datadict(data, files, name)


class ClearableTextInput(ClearableInput, TextInput):
    pass


class ClearableTextarea(ClearableInput, Textarea):
    pass


class ClearableAdminTextInputWidget(ClearableInput, AdminTextInputWidget):
    pass


class ClearableAdminTextareaWidget(ClearableInput, AdminTextareaWidget):
    pass
