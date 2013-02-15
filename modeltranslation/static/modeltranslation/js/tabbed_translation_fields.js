/*jslint white: true, onevar: true, undef: true, nomen: true, eqeqeq: true,
  plusplus: true, bitwise: true, regexp: true, newcap: true, immed: true */
var google, django, gettext;

(function () {
    var jQuery = jQuery || $ || django.jQuery;
    /* Add a new selector to jQuery that excludes parent items which match a given selector */
    jQuery.expr[':'].parents = function(a, i, m) {
        return jQuery(a).parents(m[3]).length < 1;
    };

    jQuery(function ($) {
        var TranslationField = function (options) {
            this.el = options.el;
            this.cls = options.cls;
            this.id = '';
            this.origFieldname = '';
            this.lang = '';
            this.groupId = '';

            this.init = function () {
                var clsBits = this.cls.substring(TranslationField.cssPrefix.length, this.cls.length).split('-');
                this.origFieldname = clsBits[0];
                this.lang = clsBits[1];
                this.id = $(this.el).attr('id');
                this.groupId = this.buildGroupId();
            };

            this.buildGroupId = function () {
                /**
                 * Returns a unique group identifier with respect to Django's way
                 * of handling inline ids. Essentially that's the translation
                 * field id without the language prefix.
                 *
                 * Examples ('id parameter': 'return value'):
                 *
                 *  'id_name_de': 'id_name'
                 *  'id_name_zh_tw': 'id_name'
                 *  'id_name_set-2-name_de': 'id_name_set-2-name'
                 *  'id_name_set-2-name_zh_tw': 'id_name_set-2-name'
                 *  'id_news-data2-content_type-object_id-0-name_de': 'id_news-data2-content_type-object_id-0-name'
                 *  'id_news-data2-content_type-object_id-0-name_zh_cn': id_news-data2-content_type-object_id-0-name'
                 */
                var idBits = this.id.split('-'),
                    idPrefix = 'id_' + this.origFieldname;
                if (idBits.length === 3) {
                    // Handle standard inlines
                    idPrefix = idBits[0] + '-' + idBits[1] + '-' + idPrefix;
                } else if (idBits.length === 6) {
                    // Handle generic inlines
                    idPrefix = idBits[0] + '-' + idBits[1] + '-' + idBits[2] + '-' +
                        idBits[3] + '-' + idBits[4] + '-' + this.origFieldname;
                }
                return idPrefix;
            };

            this.init();
        };
        TranslationField.cssPrefix = 'mt-field-';

        var TranslationFieldGrouper = function (options) {
            this.$fieldSelector = options.$fieldSelector;
            this.groupedTranslations = {};

            this.init = function () {
                // Handle fields inside collapsed groups as added by zinnia
                this.$fieldSelector = this.$fieldSelector.add('fieldset.collapse-closed .mt');

                this.groupedTranslations = this.getGroupedTranslations();
            };

            this.getGroupedTranslations = function () {
                /**
                 * Returns a grouped set of all model translation fields.
                 * The returned datastructure will look something like this:
                 *
                 * {
                 *     'id_name_de': {
                 *         'en': HTMLInputElement,
                 *         'de': HTMLInputElement,
                 *         'zh_tw': HTMLInputElement
                 *     },
                 *     'id_name_set-2-name': {
                 *         'en': HTMLTextAreaElement,
                 *         'de': HTMLTextAreaElement,
                 *         'zh_tw': HTMLTextAreaElement
                 *     },
                 *     'id_news-data2-content_type-object_id-0-name': {
                 *         'en': HTMLTextAreaElement,
                 *         'de': HTMLTextAreaElement,
                 *         'zh_tw': HTMLTextAreaElement
                 *     }
                 * }
                 *
                 * The keys are unique group identifiers as returned by
                 * TranslationField.buildGroupId() to handle inlines properly.
                 */
                var self = this;
                this.$fieldSelector.each(function (idx, el) {
                    $.each($(el).attr('class').split(' '), function(idx, cls) {
                        if (cls.substring(0, TranslationField.cssPrefix.length) === TranslationField.cssPrefix) {
                            var tfield = new TranslationField({el: el, cls: cls});
                            if (!self.groupedTranslations[tfield.groupId]) {
                                self.groupedTranslations[tfield.groupId] = {};
                            }
                            self.groupedTranslations[tfield.groupId][tfield.lang] = el;
                        }
                    });
                });
                return this.groupedTranslations;
            };

            this.init();
        };

        function handleAddAnotherInline() {
            $('.mt').parents('.inline-group').not('.tabular').find('.add-row a').click(function () {
                var grouper = new TranslationFieldGrouper({
                    $fieldSelector: $(this).parent().prev().prev().find('.mt')
                });
                var tabs = createTabs(grouper.groupedTranslations);

                // Update the main switch as it is not aware of the newly created tabs
                var $select = $('#content').find('h1 select');
                $select.change(function () {
                    $.each(tabs, function (i, tab) {
                        tab.tabs('select', parseInt($select.val()));
                    });
                });
                // Activate the language tab selected in the main switch
                $.each(tabs, function (i, tab) {
                    tab.tabs('select', parseInt($select.val()));
                });
            });
        }

        function createTabs(groupedTranslations) {
            var tabs = [];
            $.each(groupedTranslations, function (groupId, lang) {
                var tabsContainer = $('<div></div>'),
                    tabsList = $('<ul></ul>'),
                    insertionPoint;
                tabsContainer.append(tabsList);
                $.each(lang, function (lang, el) {
                    var container = $(el).closest('.form-row'),
                        label = $('label', container),
                        fieldLabel = container.find('label'),
                        tabId = 'tab_' + $(el).attr('id'),
                        panel,
                        tab;
                    // Remove language and brackets from field label, they are
                    // displayed in the tab already.
                    if (fieldLabel.html()) {
                        fieldLabel.html(fieldLabel.html().replace(/ \[.+\]/, ''));
                    }
                    if (!insertionPoint) {
                        insertionPoint = {
                            'insert': container.prev().length ? 'after' : container.next().length ? 'prepend' : 'append',
                            'el': container.prev().length ? container.prev() : container.parent()
                        };
                    }
                    container.find('script').remove();
                    panel = $('<div id="' + tabId + '"></div>').append(container);
                    tab = $('<li' + (label.hasClass('required') ? ' class="required"' : '') + '><a href="#' + tabId + '">' + lang.replace('_', '-') + '</a></li>');
                    tabsList.append(tab);
                    tabsContainer.append(panel);
                });
                insertionPoint.el[insertionPoint.insert](tabsContainer);
                tabsContainer.tabs();
                tabs.push(tabsContainer);
            });
            return tabs;
        }

        function createMainSwitch(groupedTranslations, tabs) {
            var uniqueLanguages = [],
                select = $('<select>');
            $.each(groupedTranslations, function (id, languages) {
                $.each(languages, function (lang) {
                    if ($.inArray(lang, uniqueLanguages) < 0) {
                        uniqueLanguages.push(lang);
                    }
                });
            });
            $.each(uniqueLanguages, function (idx, language) {
                select.append($('<option value="' + idx + '">' + language.replace('_', '-') + '</option>'));
            });
            select.change(function () {
                $.each(tabs, function (idx, tab) {
                    tab.tabs('select', parseInt(select.val()));
                });
            });
            $('#content').find('h1').append('&nbsp;').append(select);
        }

        if ($('body').hasClass('change-form')) {
            var grouper = new TranslationFieldGrouper({
                $fieldSelector: $('.mt').filter('input[type=text]:visible, textarea:visible').filter(':parents(.tabular)')
            });
            createMainSwitch(grouper.groupedTranslations, createTabs(grouper.groupedTranslations));

            // Note: The add another functionality in admin is injected through inline javascript,
            // here we have to run after that (and after all other ready events just to be sure).
            $(document).ready(function() {
                $(window).load(function() {
                    handleAddAnotherInline();
                });
            });
        }
    });
}());
