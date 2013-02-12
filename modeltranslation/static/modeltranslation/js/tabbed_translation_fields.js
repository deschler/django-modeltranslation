/*jslint white: true, onevar: true, undef: true, nomen: true, eqeqeq: true,
  plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true */
var google, django, gettext;

(function () {
    var jQuery = jQuery || $ || django.jQuery;
    /* Add a new selector to jQuery that excludes parent items which match a
       given selector */
    jQuery.expr[':'].parents = function(a, i, m) {
        return jQuery(a).parents(m[3]).length < 1;
    };

    jQuery(function ($) {
        function getGroupId(id, orig_fieldname) {
            /** Returns a unique group identifier with respect to Django's
              * data_set prefixes used for inlines. Essentially that's the
              * field id without the language prefix. Examples:
              *     id_float_de --> id_float
              *     id_data_set-2-name_zh_tw --> id_data_set-2-name
              */
            var data_set_prefix = 'id_data_set',
                id_bits = id.split('-'),
                id_prefix = 'id_' + orig_fieldname;
            if (id_bits.length === 3 && id_bits[0] === data_set_prefix) {
                id_prefix = id_bits[0] + '-' + id_bits[1] + '-' + id_prefix;
            }
            return id_prefix;
        }

        function getGroupedTranslationFields() {
            /** Returns a grouped set of all text based model translation fields.
             * The returned datastructure will look something like this:
             * {
             *     'title': {
             *         'en': HTMLInputElement,
             *         'de': HTMLInputElement,
             *         'zh_tw': HTMLInputElement
             *     },
             *     'body': {
             *         'en': HTMLTextAreaElement,
             *         'de': HTMLTextAreaElement,
             *         'zh_tw': HTMLTextAreaElement
             *     }
             * }
             */
            var translation_fields = $('.mt').filter(
                'input[type=text]:visible, textarea:visible').filter(
                    ':parents(.tabular)'),  // exclude tabular inlines
                grouped_translations = {};

            // Handle fields inside collapsed groups as added by zinnia
            translation_fields = translation_fields.add('fieldset.collapse-closed .mt');

            translation_fields.each(function (i, el) {
                var field_prefix = 'mt-field-',
                    id = '',
                    orig_fieldname = '',
                    lang = '';
                $.each($(el).attr('class').split(' '), function(j, cls) {
                    if (cls.substring(0, field_prefix.length) === field_prefix) {
                        var v = cls.substring(field_prefix.length, cls.length).split('-');
                        orig_fieldname = v[0];
                        id = getGroupId($(el).attr('id'), orig_fieldname);
                        lang = v[1];
                    }
                });
                if (!grouped_translations[id]) {
                    grouped_translations[id] = {};
                }
                grouped_translations[id][lang] = el;
            });
            return grouped_translations;
        }

        function createTabs(grouped_translations) {
            var tabs = [];
            $.each(grouped_translations, function (group_id, lang) {
                var tabs_container = $('<div></div>'),
                    tabs_list = $('<ul></ul>'),
                    insertion_point;
                tabs_container.append(tabs_list);
                $.each(lang, function (lang, el) {
                    var container = $(el).closest('.form-row'),
                      label = $('label', container),
                      field_label = container.find('label'),
                      id = $(el).attr('id'),
                      panel, tab;
                    // Remove language and brackets from field label, they are
                    // displayed in the tab already.
                    if (field_label.html()) {
                        field_label.html(field_label.html().replace(/\ \[.+\]/, ''));
                    }
                    if (!insertion_point) {
                        insertion_point = {
                            'insert': container.prev().length ? 'after' : container.next().length ? 'prepend' : 'append',
                            'el': container.prev().length ? container.prev() : container.parent()
                        };
                    }
                    container.find('script').remove();
                    panel = $('<div id="' + id + '"></div>').append(container);
                    tab = $('<li' + (label.hasClass('required') ? ' class="required"' : '') + '><a href="#' + id + '">' + lang.replace('_', '-') + '</a></li>');
                    tabs_list.append(tab);
                    tabs_container.append(panel);
                });
                insertion_point.el[insertion_point.insert](tabs_container);
                tabs_container.tabs();
                tabs.push(tabs_container);
            });
            return tabs;
        }

        function createMainSwitch(grouped_translations, tabs) {
            var unique_languages = [],
                select = $('<select>');
            $.each(grouped_translations, function (id, languages) {
                $.each(languages, function (lang, el) {
                    if ($.inArray(lang, unique_languages) < 0) {
                        unique_languages.push(lang);
                    }
                });
            });
            console.log(unique_languages);
            $.each(unique_languages, function (i, language) {
                select.append($('<option value="' + unique_languages[i] + '">' + language.replace('_', '-') + '</option>'));
            });
            select.change(function (e) {
                $.each(tabs, function (i, tab) {
                    tab.tabs('select', parseInt(select.val()));
                });
            });
            $('#content h1').append('&nbsp;').append(select);
        }

        if ($('body').hasClass('change-form')) {
            var grouped_translations = getGroupedTranslationFields();
            createMainSwitch(grouped_translations, createTabs(grouped_translations));
        }
    });
}());
