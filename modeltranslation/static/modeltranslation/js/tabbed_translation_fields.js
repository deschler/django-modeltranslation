/*jslint white: true, onevar: true, undef: true, nomen: true, eqeqeq: true,
  plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true */
var google, django, gettext;

(function () {
    var jQuery = jQuery || $ || django.jQuery;
    jQuery(function ($) {
        function getGroupedTranslationFields() {
            /** Returns a grouped set of all text based model translation fields.
             * The returned datastructure will look something like this:
             * {
             *   'title': {
             *     'en': HTMLInputElement,
             *     'de': HTMLInputElement,
             *     'fr': HTMLInputElement
             *   },
             *   'body': {
             *     'en': HTMLTextAreaElement,
             *     'de': HTMLTextAreaElement,
             *     'fr': HTMLTextAreaElement
             *   }
             * }
             */
            var translation_fields = $('.modeltranslation').filter('input[type=text]:visible, textarea:visible'),
              grouped_translations = {};

            translation_fields.each(function (i, el) {
                /*
                // FIXME: Fails if there's an inline which has the same field name as
                //        the edited object.

                // Extract fieldname and original language code from class attribute
                var css_lang_suffix = 'modeltranslation-field-';
                var name = '';
                var lang = '';
                $.each($(el).attr('class').split(' '), function(j, cls) {
                    if (cls.substring(0, css_lang_suffix.length) === css_lang_suffix) {
                        var v = cls.substring(css_lang_suffix.length,
                                              cls.length).split('__');
                        name = v[0];
                        lang = v[1];
                    }
                });
                */
                var name = $(el).attr('name').split('_'),
                  lang = name.pop();
                name = name.join('_');
                if (!grouped_translations[name]) {
                    grouped_translations[name] = {};
                }
                grouped_translations[name][lang] = el;
            });
            return grouped_translations;
        }

        function createTabs() {
            var grouped_translations = getGroupedTranslationFields();
            var tabs = [];
            $.each(grouped_translations, function (name, languages) {
                var tabs_container = $('<div></div>'),
                  tabs_list = $('<ul></ul>'),
                  insertion_point;
                tabs_container.append(tabs_list);
                $.each(languages, function (lang, el) {
                    var container = $(el).closest('.form-row'),
                      label = $('label', container),
                      field_label = container.find('label'),
                      id = 'tab_' + [name, lang].join('_'),
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
                    tab = $('<li' + (label.hasClass('required') ? ' class="required"' : '') + '><a href="#' + id + '">' + lang + '</a></li>');
                    tabs_list.append(tab);
                    tabs_container.append(panel);
                });
                insertion_point.el[insertion_point.insert](tabs_container);
                tabs_container.tabs();
                tabs.push(tabs_container);
            });
            return tabs;
        }

        function createMainSwitch(tabs) {
            var grouped_translations = getGroupedTranslationFields(),
              unique_languages = [],
              select = $('<select>');
            $.each(grouped_translations, function (name, languages) {
                $.each(languages, function (lang, el) {
                    if ($.inArray(lang, unique_languages) < 0) {
                        unique_languages.push(lang);
                    }
                });
            });
            $.each(unique_languages, function (i, language) {
                select.append($('<option value="' + i + '">' + language + '</option>'));
            });
            select.change(function (e) {
                $.each(tabs, function (i, tab) {
                    tab.tabs('select', parseInt(select.val()));
                });
            });
            $('#content h1').append('&nbsp;').append(select);
        }

        if ($('body').hasClass('change-form')) {
            createMainSwitch(createTabs());
        }
    });
}());
