# Changelog

All notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.

### [0.19.8](https://github.com/deschler/django-modeltranslation/compare/v0.19.7...v0.19.8) (2024-09-04)


### Bug Fixes

* Fix django-cms compatibility ([d420b6a](https://github.com/deschler/django-modeltranslation/commit/d420b6a9db87e133a34d0462af4c699b6debed96)), closes [#748](https://github.com/deschler/django-modeltranslation/issues/748)
* Fix type error for Python 3.8 ([#754](https://github.com/deschler/django-modeltranslation/issues/754)) ([5cc37c2](https://github.com/deschler/django-modeltranslation/commit/5cc37c256f377f918e3f4b788b900a700a5f22db)), closes [#753](https://github.com/deschler/django-modeltranslation/issues/753)

### [0.19.7](https://github.com/deschler/django-modeltranslation/compare/v0.19.6...v0.19.7) (2024-08-12)


### Features

* add changelog to project urls in package metadata ([#752](https://github.com/deschler/django-modeltranslation/issues/752)) ([303c947](https://github.com/deschler/django-modeltranslation/commit/303c947930a3348bf4037617677dc89fb157e1e2))

### [0.19.6](https://github.com/deschler/django-modeltranslation/compare/v0.19.5...v0.19.6) (2024-08-07)


### Bug Fixes

* Support multiple translation fields in `get_translation_fields` ([56c5784](https://github.com/deschler/django-modeltranslation/commit/56c578400fd6bd29bd8b088bc3e5ba9f6b4fa9a4))

### [0.19.5](https://github.com/deschler/django-modeltranslation/compare/v0.19.4...v0.19.5) (2024-07-05)


### Bug Fixes

* **types:** Use Union instead of | for some types ([13af637](https://github.com/deschler/django-modeltranslation/commit/13af637d87dc9eca2775b46bf2b04da7e741c805)), closes [#744](https://github.com/deschler/django-modeltranslation/issues/744)

### [0.19.4](https://github.com/deschler/django-modeltranslation/compare/v0.19.3...v0.19.4) (2024-06-20)


### Features

* Add global `MODELTRANSLATION_REQUIRED_LANGUAGES` setting ([0bbdb5f](https://github.com/deschler/django-modeltranslation/commit/0bbdb5fe8fa053de2bc54d31b668b3621a9dda78)), closes [#743](https://github.com/deschler/django-modeltranslation/issues/743)

### [0.19.3](https://github.com/deschler/django-modeltranslation/compare/v0.19.2...v0.19.3) (2024-06-01)


### Bug Fixes

* **types:** Make admin classes generic as their super classes ([#737](https://github.com/deschler/django-modeltranslation/issues/737)) ([d2c16fe](https://github.com/deschler/django-modeltranslation/commit/d2c16feba9d9f00f16f9406e2a466cd0cc832433))

### Breaking changes

* Dropped support for python 3.8 and removed it from CI

### [0.19.2](https://github.com/deschler/django-modeltranslation/compare/v0.19.1...v0.19.2) (2024-05-27)

### [0.19.1](https://github.com/deschler/django-modeltranslation/compare/v0.19.0...v0.19.1) (2024-05-27)


### Bug Fixes

* Removed protocol from admin javascript links. ([ed8f2bc](https://github.com/deschler/django-modeltranslation/commit/ed8f2bcf747435e242ce5e0b01287b5162d59476)), closes [#740](https://github.com/deschler/django-modeltranslation/issues/740)

## [0.19.0](https://github.com/deschler/django-modeltranslation/compare/v0.18.13...v0.19.0) (2024-05-26)


### ⚠ BREAKING CHANGES

* **types:** Rename `fields` (dict with set of TranslationField) to `all_fields`, on the TranslationOptions instance.

### Features

* Support F and Concat expressions in annotate() ([a0aeb58](https://github.com/deschler/django-modeltranslation/commit/a0aeb58b470d7b0607bf7e3a4e9dd49e1862dcc3)), closes [#735](https://github.com/deschler/django-modeltranslation/issues/735)


### Bug Fixes

* **types:** Export public variables ([47f8083](https://github.com/deschler/django-modeltranslation/commit/47f80835764be1607ec7463b55c7de8496bc0152))
* **types:** Fix `fields` type ([#739](https://github.com/deschler/django-modeltranslation/issues/739)) ([b97c22c](https://github.com/deschler/django-modeltranslation/commit/b97c22c197686379be5d6237cfd61a92c10aefb5))

### [0.18.13](https://github.com/deschler/django-modeltranslation/compare/v0.18.13-beta1.1...v0.18.13) (2024-05-17)


### Features

* Add build_lang helper in utils ([bdee9ff](https://github.com/deschler/django-modeltranslation/commit/bdee9ff5b906f682cfc8c4a774074a8b2aacf463))
* Add types ([a9e95e8](https://github.com/deschler/django-modeltranslation/commit/a9e95e8c78550aba70712e524fb289b87bdf1b48)), closes [#716](https://github.com/deschler/django-modeltranslation/issues/716)


### Bug Fixes

* Remove deprecated test config starting from Django 5.0 ([b016af5](https://github.com/deschler/django-modeltranslation/commit/b016af5d4a2bdb9a0dfebf1492d6997f2aa9861d))

### [0.18.13-beta1.1](https://github.com/deschler/django-modeltranslation/compare/v0.18.13-beta.0...v0.18.13-beta1.1) (2023-11-17)


### Bug Fixes

* Fixed bug in tabbed_translation_fields.js ([641fbe8](https://github.com/deschler/django-modeltranslation/commit/641fbe89ab674c03dcb41f584e7bb569e3c141a9)), closes [#597](https://github.com/deschler/django-modeltranslation/issues/597)
* **ci:** Replace flake8 with ruff ([2061f6c](https://github.com/deschler/django-modeltranslation/commit/2061f6c264d7cb889ae14d2d52a7547df6d58663))

### [0.18.13-beta.0](https://github.com/deschler/django-modeltranslation/compare/v0.18.13-beta1.0...v0.18.13-beta.0) (2023-09-13)

### [0.18.13-beta1.0](https://github.com/deschler/django-modeltranslation/compare/v0.18.12...v0.18.13-beta1.0) (2023-09-13)


### Bug Fixes

* Apply force_str only to Promise ([e7640c7](https://github.com/deschler/django-modeltranslation/commit/e7640c71197f3c7b34386847c746663123fad07b)), closes [#701](https://github.com/deschler/django-modeltranslation/issues/701)

### [0.18.12](https://github.com/deschler/django-modeltranslation/compare/v0.18.11...v0.18.12) (2023-09-08)


### Features

* Support language-specific field defaults ([2657de7](https://github.com/deschler/django-modeltranslation/commit/2657de7c2ebd6523a31ab04ba9453c715b0c34f3)), closes [#700](https://github.com/deschler/django-modeltranslation/issues/700) [#698](https://github.com/deschler/django-modeltranslation/issues/698)

### [0.18.11](https://github.com/deschler/django-modeltranslation/compare/v0.18.10...v0.18.11) (2023-07-16)


### Features

* extend update_fields with translation fields in Model.save() ([#687](https://github.com/deschler/django-modeltranslation/issues/687)) ([d86c6de](https://github.com/deschler/django-modeltranslation/commit/d86c6defc864b3493955a41f95a85fc5aa8d5649))

### [0.18.10](https://github.com/deschler/django-modeltranslation/compare/v0.18.10-beta.0...v0.18.10) (2023-06-02)


### Bug Fixes

* Add support for JSONField ([25f7305](https://github.com/deschler/django-modeltranslation/commit/25f73058f5f176a61c5368b7aee563874309687e)), closes [#685](https://github.com/deschler/django-modeltranslation/issues/685)

### [0.18.10-beta.1](https://github.com/deschler/django-modeltranslation/compare/v0.18.10-beta.0...v0.18.10-beta.1) (2023-06-02)


### Bug Fixes

* Add support for JSONField ([25f7305](https://github.com/deschler/django-modeltranslation/commit/25f73058f5f176a61c5368b7aee563874309687e)), closes [#685](https://github.com/deschler/django-modeltranslation/issues/685)

### [0.18.10-beta.1](https://github.com/deschler/django-modeltranslation/compare/v0.18.10-beta.0...v0.18.10-beta.1) (2023-06-02)

### [0.18.10-beta.0](https://github.com/deschler/django-modeltranslation/compare/v0.18.9...v0.18.10-beta.0) (2023-05-30)


### Bug Fixes

* Fix update_or_create for Django 4.2 ([d5eefa8](https://github.com/deschler/django-modeltranslation/commit/d5eefa8bd193cd8aee1cd1f97561d2a7e9dc0801)), closes [#682](https://github.com/deschler/django-modeltranslation/issues/682) [#683](https://github.com/deschler/django-modeltranslation/issues/683)

### [0.18.9](https://github.com/deschler/django-modeltranslation/compare/v0.18.8...v0.18.9) (2023-02-09)


### Bug Fixes

* Fix handling of expressions in `values()`/`values_list()` ([d65ff60](https://github.com/deschler/django-modeltranslation/commit/d65ff60007d4088b1f483edd2df85f407be3b5de)), closes [#670](https://github.com/deschler/django-modeltranslation/issues/670)

### [0.18.8](https://github.com/deschler/django-modeltranslation/compare/v0.18.8-beta.1...v0.18.8) (2023-02-01)

### [0.18.8-beta.1](https://github.com/deschler/django-modeltranslation/compare/v0.18.8-beta.0...v0.18.8-beta.1) (2023-01-27)


### Features

* Add support for ManyToManyFields 🧑‍🤝‍🧑 ([#668](https://github.com/deschler/django-modeltranslation/issues/668)) ([f69e317](https://github.com/deschler/django-modeltranslation/commit/f69e3172bc6254a4ddd8def7500632d0046b30eb))


### Bug Fixes

* **docs:** Update documentation regarding inheritance ([#665](https://github.com/deschler/django-modeltranslation/issues/665)) ([ca31a21](https://github.com/deschler/django-modeltranslation/commit/ca31a21f014b04978188562a0e0e1b58d95923e6)), closes [#663](https://github.com/deschler/django-modeltranslation/issues/663)

### [0.18.8-beta.0](https://github.com/deschler/django-modeltranslation/compare/v0.18.7...v0.18.8-beta.0) (2022-11-22)


### Bug Fixes

* Fix admin widget for fk fields ([#662](https://github.com/deschler/django-modeltranslation/issues/662)) ([fcfbd5c](https://github.com/deschler/django-modeltranslation/commit/fcfbd5ce059e4858a2c8d4803d094285282ad2c9)), closes [#660](https://github.com/deschler/django-modeltranslation/issues/660)

### [0.18.7](https://github.com/deschler/django-modeltranslation/compare/v0.18.6...v0.18.7) (2022-11-08)

### [0.18.6](https://github.com/deschler/django-modeltranslation/compare/v0.18.5...v0.18.6) (2022-11-07)


### Bug Fixes

* Fix unexpected ordering after `values()`/`values_list()` followed by `order_by()`. ([09ce0e0](https://github.com/deschler/django-modeltranslation/commit/09ce0e076ba323432275e28eb16fdb19f37df3e0)), closes [#655](https://github.com/deschler/django-modeltranslation/issues/655) [#656](https://github.com/deschler/django-modeltranslation/issues/656)

### [0.18.5](https://github.com/deschler/django-modeltranslation/compare/v0.18.4...v0.18.5) (2022-10-12)


### Features

* Support UserAdmin add_fieldsets ([d414cd3](https://github.com/deschler/django-modeltranslation/commit/d414cd3e0709622a66260088d2da0ade94a01be1)), closes [#654](https://github.com/deschler/django-modeltranslation/issues/654)


### Bug Fixes

* Fix working in strict mode. ([#649](https://github.com/deschler/django-modeltranslation/issues/649)) ([8ef8afd](https://github.com/deschler/django-modeltranslation/commit/8ef8afd2d7aad71ba185f17c0db95494616f3730))

### [0.18.4](https://github.com/deschler/django-modeltranslation/compare/v0.18.3...v0.18.4) (2022-07-22)


### Bug Fixes

* Update django compatibility ([582b612](https://github.com/deschler/django-modeltranslation/commit/582b612ab5d422bf2cd1f45a28748db60819e85c))

### [0.18.3](https://github.com/deschler/django-modeltranslation/compare/v0.18.3-beta.1...v0.18.3) (2022-07-19)


### Bug Fixes

* Remove six (old compat layer for python2) ([86b67c2](https://github.com/deschler/django-modeltranslation/commit/86b67c271e5fcba94e396acc9efd5e52ced2d1e2))

### [0.18.3-beta.1](https://github.com/deschler/django-modeltranslation/compare/v0.18.3-beta.0...v0.18.3-beta.1) (2022-07-13)


### Features

* **dev:** Migrate to pytest ([d3e2396](https://github.com/deschler/django-modeltranslation/commit/d3e2396be6757f0d0b3ee4e06777c37f17d3834b))

### [0.18.3-beta.0](https://github.com/deschler/django-modeltranslation/compare/v0.18.2...v0.18.3-beta.0) (2022-07-10)


### Features

* Support `named` argument for `values_list`  ([#644](https://github.com/deschler/django-modeltranslation/issues/644)) ([39bbe82](https://github.com/deschler/django-modeltranslation/commit/39bbe821b31278b21e0bf3528d036343338bb0f7))

### [0.18.2](https://github.com/deschler/django-modeltranslation/compare/v0.18.1...v0.18.2) (2022-05-15)


### Features

* Update test matrix; Drop python 3.6, add Python 3.10 ([#638](https://github.com/deschler/django-modeltranslation/issues/638)) ([29deb95](https://github.com/deschler/django-modeltranslation/commit/29deb95bf30c0e31c6a031f754677182cdd461a2))

### [0.18.1](https://github.com/deschler/django-modeltranslation/compare/v0.18.0...v0.18.1) (2022-05-15)


### Bug Fixes

* Fix install (included missing VERSION) ([ab66e8d](https://github.com/deschler/django-modeltranslation/commit/ab66e8d2f79c5e7e6f517e53a1698f5113d711bf)), closes [#637](https://github.com/deschler/django-modeltranslation/issues/637)

## [0.18.0](https://github.com/deschler/django-modeltranslation/compare/v0.17.7...v0.18.0) (2022-05-14)


### ⚠ BREAKING CHANGES

* Replaced `VERSION` in tuple format by `__version__` as a string

### Bug Fixes

* Add django version check for default_app_config ([79d2e08](https://github.com/deschler/django-modeltranslation/commit/79d2e089eff2f6bcfd150d3ac6e165bfefa475cb))
* Fix django version detect during install ([876f2e7](https://github.com/deschler/django-modeltranslation/commit/876f2e715804e5cba9f8dde0b8a75ff3179e908c))
* Store version as plain text file to simplify bumping ([#636](https://github.com/deschler/django-modeltranslation/issues/636)) ([6b4bb73](https://github.com/deschler/django-modeltranslation/commit/6b4bb733d971363c223d9d4ff307a0f9be131315))

### [0.17.7](https://github.com/deschler/django-modeltranslation/compare/v0.17.6...v0.17.7) (2022-05-04)


### Bug Fixes

* Do not include annotation fields when selecting specific fields ([#634](https://github.com/deschler/django-modeltranslation/issues/634)) ([defc37c](https://github.com/deschler/django-modeltranslation/commit/defc37c7a539dff1e4af96e7d13856519befe585))

### [0.17.6](https://github.com/deschler/django-modeltranslation/compare/v0.17.5...v0.17.6) (2022-04-29)


### Bug Fixes

* Preserve annotate() fields in queryset ([#633](https://github.com/deschler/django-modeltranslation/issues/633)) ([6f2688f](https://github.com/deschler/django-modeltranslation/commit/6f2688f52c56107da361c7c6197bcf38d8b99f42))

### [0.17.5](https://github.com/deschler/django-modeltranslation/compare/v0.17.4...v0.17.5) (2022-01-30)

### [0.17.4](https://github.com/deschler/django-modeltranslation/compare/v0.17.3...v0.17.4) (2022-01-28)


### Features

* semi-configurable selection of elements to generate tabs in admin ([#607](https://github.com/deschler/django-modeltranslation/issues/607)) ([eb05201](https://github.com/deschler/django-modeltranslation/commit/eb052018bf930146d667be3e47f26d69afb3c2c3))

### [0.17.3](https://github.com/deschler/django-modeltranslation/compare/v0.17.2...v0.17.3) (2021-06-28)

### [0.17.2](https://github.com/deschler/django-modeltranslation/compare/v0.17.1...v0.17.2) (2021-05-31)


### Bug Fixes

* **docs:** Fixed legacy python 2 print statements ([10ec4ed](https://github.com/deschler/django-modeltranslation/commit/10ec4ed8694d949815ccf4ada679a1cb72f24675))
* **MultilingualQuerySet:** Make _clone signature match default django _clone ([c65adb0](https://github.com/deschler/django-modeltranslation/commit/c65adb058d6c60c077138e5099342f31aac1690b)), closes [#483](https://github.com/deschler/django-modeltranslation/issues/483)

### [0.17.1](https://github.com/deschler/django-modeltranslation/compare/v0.16.2...v0.17.1) (2021-04-15)


### Bug Fixes

* Fixed .latest() ORM method with django 3.2 ([eaf613b](https://github.com/deschler/django-modeltranslation/commit/eaf613be1733314ad3b639e1702b0f7423af7899)), closes [#591](https://github.com/deschler/django-modeltranslation/issues/591)

## [0.17.0](https://github.com/deschler/django-modeltranslation/compare/v0.16.2...v0.17.0) (2021-04-15)

### Features

* Add Django 3.2 support

### [0.16.2](https://github.com/deschler/django-modeltranslation/compare/v0.16.1...v0.16.2) (2021-02-18)


### Bug Fixes

* Fix loading for Inline Admin ([c8ea228](https://github.com/deschler/django-modeltranslation/commit/c8ea22877b3f4070ffb4d3d4e602d7ef09ab0860))

### [0.16.1](https://github.com/deschler/django-modeltranslation/compare/v0.16.0...v0.16.1) (2020-11-23)


### Bug Fixes

* missing jquery operator ([7c750de](https://github.com/deschler/django-modeltranslation/commit/7c750def728e163d5bde88fedd1124bd7e9a8122))

## [0.16.0](https://github.com/deschler/django-modeltranslation/compare/v0.15.2...v0.16.0) (2020-10-12)


### ⚠ BREAKING CHANGES

* **js:** It's 2020 already, drop backward compatibility with jquery-ui 1.10.

### Features

* **tabbed-translation-fields:** Make tab with errors visible by default. ([4c2e284](https://github.com/deschler/django-modeltranslation/commit/4c2e284d871044a443817aabfbe3c956799ffe06))


### Bug Fixes

* Fix error detection; add red dot for tab with errors. ([9a93cf6](https://github.com/deschler/django-modeltranslation/commit/9a93cf6b4d4ec24e754159f71cf9d9eda811673e))
* **dev:** Fix install in editable mode. ([aaa2dcf](https://github.com/deschler/django-modeltranslation/commit/aaa2dcf5987e19c2da8460bc73a0681a291f0dc5))


* **js:** It's 2020 already, drop backward compatibility with jquery-ui 1.10. ([d8f432a](https://github.com/deschler/django-modeltranslation/commit/d8f432a5cadd60871101081c87569e3d390474e6))

### [0.15.2](https://github.com/deschler/django-modeltranslation/compare/v0.15.1...v0.15.2) (2020-09-08)


### Features

* Adds a language option to the update_translation_fields commands ([ac91740](https://github.com/deschler/django-modeltranslation/commit/ac91740a5c3d718b8695514da8a0dd7b90aa1ee6)), closes [#563](https://github.com/deschler/django-modeltranslation/issues/563)

### [0.15.1](https://github.com/deschler/django-modeltranslation/compare/v0.15.0...v0.15.1) (2020-07-10)


### Bug Fixes

* **admin:** Fix custom widget initialization problem ([48e7f59](https://github.com/deschler/django-modeltranslation/commit/48e7f598955a09dc4130a0074cb953ecd05d1a01))

## [0.15.0](https://github.com/deschler/django-modeltranslation/compare/0.14.4...0.15.0) (2020-04-22)


### Features

* Use poetry as venv manager ([a5b402c](https://github.com/deschler/django-modeltranslation/commit/a5b402c51673a78a1aa160247746695070e08a2f))
* Drop old python versions (<3.6)
* Drop old django versions (<2.2)

### Bug Fixes

* add NewMultilingualManager __eq__() ([205a8f6](https://github.com/deschler/django-modeltranslation/commit/205a8f6c2f411b8b20235bbf89b88d3781919cbd))

## 0.14.0 (2019-11-14)


### Bug Fixes

* Django 3.0 support (#521)
* Tests when django files not writable (#527)


## 0.13-3 (2019-07-22)


### Bug Fixes

* Broken "Add another inline" (#475)

## 0.13-2 (2019-07-01)


### Bug Fixes

* Outdated formfield_for_dbfield signature (#510)


## 0.13-1 (2019-04-18)


* REMOVED: Python 3.5 from test matrix
* REMOVED: Django 2.0 from test matrix
* FIXED: TabbedTranslationAdmin in django 2.2 (#506)
* ADDED: Django 2.2 to test matrix


## 0.13-0 (2019-02-21)

* ADDED: Django 2.0 and 2.1 support
* ADDED: Python 3.7 support
* REMOVED: Python 3.4 from test matrix


## 0.13-beta3 (2019-02-17)

* FIXED: Patching parent model managers on multi-table inheritance (#467)


## 0.13-beta2 (2019-02-13)


* ADDED: Django 2.1 support
* ADDED: Python 3.7 support
* FIXED: JS errors in admin with new jQuery


## 0.13-beta1 (2018-04-16)


* FIXED: Reverse relations and select_related for Django 2.0.
         (resolves issues #436 and #457, thanks to GreyZmeem and dmarcelino)
* FIXED: Multiple fixes for Django 2.0.
         (resolves issues #436 and #451, thanks PetrDlouhy)
* ADDED: Add primary support to DISTINCT statement
         (resolves issue #368, thanks Virgílio N Santos)
* CHANGED: Check if 'descendants' list has values
         (resolves issue #445, thanks Emilie Zawadzki)


## 0.12.2 (2018-01-26)


* FIXED: order_by with expression
         (resolves issue #398, thanks Benjamin Toueg)


## 0.12.1 (2017-04-05)


* FIXED: Issue in loaddata management command in combination with Django 1.11.
         (resolves issue #401)


## 0.12 (2016-09-20)


* ADDED: Support for Django 1.10.
         (resolves issue #360, thanks Jacek Tomaszewski and Primož Kerin)

* CHANGED: Original field value became more unreliable and undetermined;
         please make sure you're not using it anywhere. See
         http://django-modeltranslation.readthedocs.io/en/latest/usage.html#the-state-of-the-original-field
* CHANGED: Let register decorator return decorated class
         (resolves issue #360, thanks spacediver)

* FIXED: Deferred classes signal connection.
         (resolves issue #379, thanks Jacek Tomaszewski)
* FIXED: values_list + annotate combo bug.
         (resolves issue #374, thanks Jacek Tomaszewski)
* FIXED: Several flake8 and travis related issues.
         (resolves issues #363, thanks Matthias K)


## 0.11 (2016-01-31)


Released without changes.


## 0.11rc2 (2015-12-15)


* FIXED: Custom manager in migrations.
         (resolves issues #330, #339 and #350, thanks Jacek Tomaszewski)


## 0.11rc1 (2015-12-07)


* ADDED: Support for Django 1.9
         (resolves issue #349, thanks Jacek Tomaszewski)


## 0.10.2 (2015-10-27)


* FIXED: Proxy model inheritance for Django >=1.8
         (resolves issues #304, thanks Stratos Moros)


## 0.10.1 (2015-09-04)


* FIXED: FallbackValuesListQuerySet.iterator which broke ORM datetimes
         (resolves issue #324, thanks Venelin Stoykov)


## 0.10.0 (2015-07-03)


* ADDED: CSS support for bi-directional languages to TranslationAdmin
         using mt-bidi class.
         (resolves issue #317, thanks oliphunt)
* ADDED: A decorator to handle registration of models.
         (resolves issue #318, thanks zenoamaro)

* FIXED: Handled annotation fields when using values_list.
         (resolves issue #321, thanks Lukas Lundgren)


## 0.9.1 (2015-05-14)


* FIXED: Handled deprecation of _meta._fill_fields_cache() for Django 1.8
         in add_translation_fields.
         (resolves issue #304, thanks Mathias Ettinger and Daniel Loeb)
* FIXED: Handled deprecation of transaction.commit_unless_managed for
         Django 1.8 in sync_translation_fields management command.
         (resolves issue #310)
* FIXED: Fixed translatable fields discovery with the new _meta API and
         generic relations for Django 1.8.
         (resolves issue #309, thanks Morgan Aubert)


## 0.9 (2015-04-16)


* ADDED: Support for Django 1.8 and the new meta API.
         (resolves issue #299, thanks Luca Corti and Jacek Tomaszewski)


## 0.8.1 (2015-04-02)


* FIXED: Using a queryset with select related.
         (resolves issue #298, thanks Vladimir Sinitsin)
* FIXED: Added missing jquery browser plugin.
         (resolves issue #270, thanks Fabio Caccamo)
* FIXED: Deprecated imports with Django >= 1.7
         (resolves issue #283, thanks Alex Marandon)


## 0.8 (2014-10-06)


* FIXED: JavaScript scoping issue with two jQuery versions in tabbed
         translation fields.
         (resolves issue #267,
          thanks Wojtek Ruszczewski)

* ADDED: Patch db_column of translation fields in migration files.
         (resolves issue #264,
          thanks Thom Wiggers and Jacek Tomaszewski)
* ADDED: Fallback to values and values_list.
         (resolves issue #258,
          thanks Jacek Tomaszewski)


## 0.8b2 (2014-07-18)


* ADDED: Explicit support for Python 3.4 (should have already worked for
         older versions that supported Python 3).
         (resolves issue #254)
* ADDED: Support for Django 1.7 migrations.

* FIXED: Dict iteration Exception under Python 3.
         (resolves issue #256,
          thanks Jacek Tomaszewski)
* FIXED: Reduce usage under Python 3.
         (thanks Jacek Tomaszewski)
* FIXED: Support for AppConfigs in INSTALLED_APPS
         (resolves issue #252,
          thanks Warnar Boekkooi, Jacek Tomaszewski)
* FIXED: Rewrite field names in select_related. Fix deffered models registry.
         Rewrite spanned queries on all levels for defer/only.
         (resolves issue #248,
          thanks Jacek Tomaszewski)


## 0.8b1 (2014-06-22)


* ADDED: Detect custom get_queryset on managers.
         (resolves issue #242,
          thanks Jacek Tomaszewski)
* ADDED: Support for Django 1.7 and the new app-loading refactor.
         (resolves issue #237)
* ADDED: Added required_languages TranslationOptions
         (resolves issue #143)

* FIXED: Fixed sync_translation_fields to be compatible with PostgreSQL.
         (resolves issue #247,
          thanks Jacek Tomaszewski)
* FIXED: Manager .values() with no fields specified behaves as expected.
         (resolves issue #247)
* FIXED: Fieldset headers are not capitalized when group_fieldsets is enabled.
         (resolves issue #234,
          thanks Jacek Tomaszewski)
* FIXED: Exclude for nullable field manager rewriting.
         (resolves issue #231,
          thanks Jacek Tomaszewski)
* FIXED: Use AVAILABLE_LANGUAGES in sync_translation_fields management
         command to detect missing fields.
         (resolves issue #227,
          thanks Mathieu Leplatre)
* FIXED: Take db_column into account while syncing fields
         (resolves issue #225,
          thanks Mathieu Leplatre)

* CHANGED: Moved to get_queryset, which resolves a deprecation warning.
         (resolves issue #244,
          thanks Thom Wiggers)
* CHANGED: Considered iframes in tabbed_translation_fields.js to support
         third party apps like django-summernote.
         (resolves issue #229,
          thanks Francesc Arpí Roca)
* CHANGED: Removed the http protocol from jquery-ui url in admin Media class.
         (resolves issue #224,
          thanks Francesc Arpí Roca)


## 0.7.3 (2014-01-05)


* ADDED: Documentation for TranslationOptions fields reference and
         south/sync_translation_fields.

* FIXED: Some python3 compatibility issues.
         (thanks Jacek Tomaszewski,
          resolves issue #220)
* FIXED: Clearing translated FileFields does not work with easy_thumbnails.
         (thanks Jacek Tomaszewski,
          resolves issue #219)
* FIXED: Compatibility with nested inlines.
         (thanks abstraktor,
          resolves issue #218)
* FIXED: Admin inlines recursion problem in Django 1.6.
         (thanks Oleg Prans,
          resolves issue #214)
* FIXED: Empty FileField handling.
         (thanks Jacek Tomaszewski,
          resolves issue #215)


## 0.7.2 (2013-11-11)


* ADDED: Documentation about empty_values.
         (thanks Jacek Tomaszewski,
          resolves issue #211)

* FIXED: Proxy model handling.
         (thanks Jacek Tomaszewsk)
* FIXED: Abstract managers patching.
         (thanks Jacek Tomaszewski,
          resolves issue #212)


## 0.7.1 (2013-11-07)

Packaged from revision f7c7ea174344f3dc0cf56ac3bf6e92878ed6baea

* ADDED: Configurable formfields. The ultimate approach to nullable CharFields.
         (thanks Jacek Tomaszewski,
          resolves issue #211, ref #163, #187)

* FIXED: Recursion problem with fieldset handling in Django 1.6.
         (thanks to Bas Peschier,
          resolves issue #214)


## 0.7 (2013-10-19)

Packaged from revision 89f5e6712aaf5d5ec7e2d61940dc1a71fb08ca94

* ADDED: A setting to control which language are slug fields based on
         (thanks to Konrad Wojas,
          resolves issue #194)
* ADDED: A noinput option to the sync_translation_fields management command.
         (thanks to cuchac,
          resolves issues #179 and #184)
* ADDED: Support for Python 3.2 and 3.3.
         (thanks to Karol Fuksiewicz,
          resolves issue #174)
* ADDED: Convenient admin classes which already contain proper Media
         definitions.
         (resolves issue #171)
* ADDED: Only, defer, values, values_list, dates, raw_values methods to
         MultilingualManager.
         (resolves issue #166 adn #173)
* ADDED: Support for ForeignKey and OneToOneField.
         (thanks to Braden MacDonald and Jacek Tomaszewski,
          resolves issue #161)
* ADDED: An auto-population option to the loaddata command.
         (resolves issue #160)
* ADDED: A MODELTRANSLATION_LOADDATA_RETAIN_LOCALE setting for loaddata
         command to leave locale alone.
         (resolves issue #151)

* FIXED: Compatibility with Django 1.6 development version.
         (resolves issue #169)
* FIXED: Handling of 3rd party apps' ModelForms.
         (resolves issue #167)
* FIXED: Triggering field fallback on its default value rather than empty
         string only. Also enhance nullable fields in forms with proper
         widgets to preserve ``None``.
         (thanks to Wojtek Ruszczewski,
          resolves issue #163)
* FIXED: Admin prepopulated_fields is now handled properly.
         (thanks to Rafleze,
          resolves issue #181 and #190)
* FIXED: Form saving when translated field is excluded (e.g. in admin)
         (resolves issue #183)
* FIXED: Multilingual clones are Multilingual too.
         (resolved issue #189)

* CHANGED: Every model's manager is patched as MultiLingual, not only objects.
         (resolved issue #198)
* CHANGED: Display "make null" checkboxes in model forms.
* CHANGED: MODELTRANSLATION_DEBUG setting defaults to False instead of
         settings.DEBUG.
* CHANGED: Drop support for Python 2.5 and Django 1.3.


## 0.6.1 (2013-03-17)

Packaged from revision fc8a3034897b8b818c74f41c43a92001e536d970

* FIXED: Joined query does not use translated fields.
         (resolves issue #162)


## 0.6 (2013-03-01)

Packaged from revision ea0e2db68900371146d39dcdf88b29091ee5222f

* ADDED: A new ENABLE_FALLBACKS setting and a context manager for switching
         fallbacks temporarily.
         (thanks to Wojtek Ruszczewski,
          resolves issue #152)
* ADDED: Major refactoring of the tabbed translation fields javascript. Adds
         support for tabular inlines and includes proper handling of stacked
         inlines, which have never been officially supported, but were not
         actively prevented from being tabbified.
         (resolves issue #66)
* ADDED: New group_fieldsets option for TranslationAdmin. When activated
         translation fields and untranslated fields are automatically
         grouped into fieldsets.
         (based on original implementation by Chris Adams,
          resolves issues #38)

* FIXED: Tests to run properly in the scope of a Django project.
         (thanks to Wojtek Ruszczewski,
          resolves issue #153)
* FIXED: Broken tab activation when using jquery-ui 1.10, keeping support for
         older jquery-ui versions and the jquery version shipped by Django.
         (thanks to Dominique Lederer,
          resolves issue #146)
* FIXED: Wrong admin field css class for en-us language.
         (resolves issue #141)
* FIXED: Added missing hook for admin readonly_fields.
         (resolves issue #140)
* FIXED: Keys used in tabbed translation fields to group translations are not
         unique for inlines.
         (resolves issue #121)
* FIXED: The prepopulated_fields TranslationAdmin option only works on the
         first defined field to prepopulate from and made the option aware
         of the current language.
         (resolves issue #57)

* CHANGED: Removed deprecated MODELTRANSLATION_TRANSLATION_REGISTRY setting.
* CHANGED: Refactored auto population manager functionality. Switched to a
         populate method in favour of the old _populate keyword and added a new
         contextmanager to switch the population mode on demand.
         (thanks to Wojtek Ruszczewski,
          resolves issue #145)
* CHANGED: Major refactoring of translation field inheritance and
         TranslationOptions.
         (thanks to Wojtek Ruszczewski,
          resolves issues #50 and #136)


## 0.5 (2013-02-10)

Packaged from revision bedd18ea9e338b133d06f2ed5e7ebfc2e21fd276

* ADDED: Merged autodiscover tests from django-modeltranslation-wrapper.
* ADDED: Rewrite method to MultilingualManager and optimized create.

* FIXED: grouped_translations are computed twice in tabbed translations.
         (thanks to Wojtek Ruszczewski,
          resolves issue #135)
* FIXED: CSS classes in tabbed translation fields when fieldname has a leading
         underscore.
         (thanks to Wojtek Ruszczewski,
          resolves issue #134)
* FIXED: Rewriting of descending ('-' prefixed) ordering fields in
         MultilingualManager.
         (thanks to Wojtek Ruszczewski,
          resolves issue #133)
* FIXED: Download url in setup.py.
         (thanks to Benoît Bryon,
          resolves issue #130)
* FIXED: The update_translation_fields management command does nothing.
         (resolves issue #123)
* FIXED: MultilingualQuerySet custom inheritance.

* CHANGED: Don't raise an exception if TranslationField is accessed via class
         to allow descriptor introspection.
         (resolves issue #131)


## 0.5b1 (2013-01-07)

Packaged from revision da928dd431fcf112e2e9c4c154c5b69e7dadc3b3.

* ADDED: Possibility to turn off query rewriting in MultilingualManager.
         (thanks to Jacek Tomaszewski)

* FIXED: Fixed update_translation_fields management command.
         (thanks to Jacek Tomaszewski,
          resolves issues #123 and #124)

* CHANGED: Major test refactoring.
         (thanks to Jacek Tomaszewski,
          resolves issues #100 and #119)


## 0.5a1 (2012-12-05)

Packaged from revision da4aeba0ea20ddbee67aa49bc90af507997ac386.

* ADDED: Increased the number of supported fields. Essentially all Django
         model fields and subclasses of them should work, except related
         fields (ForeignKey, ManyToManyField, OneToOneField) and AutoField
         which are not supported.
* ADDED: A subclass of TranslationOptions inherits fields from its bases.
         (thanks to Bruno Tavares and Jacek Tomaszewski,
          resolves issue #110)
* ADDED: Support for fallback languages. Allows fine grained configuration
         through project settings and TranslationOptions on model basis.
         (thanks to Jacek Tomaszewski,
          resolves issue #104)
* ADDED: Multilingual manager which is aware of the current language.
         (thanks to Jacek Tomaszewski,
          resolves issues #45, #78 and #84)

* CHANGED: Version code to use a PEP386 compliant version number.
* CHANGED: Constructor rewrites fields to be language aware.
         (thanks to Jacek Tomaszewski,
          resolves issues #33 and #58)

* FIXED: Lacking support for readonly_fields in TranslationAdmin.
         (thanks to sbrandtb,
          resolves issue #111)
* FIXED: Model's db_column option is not applied to the translation field.
         (resolves issue #83)
* FIXED: Admin prevents saving a cleared field. The fix deactivates rule3 and
         implies the new language aware manager and constructor rewrite.
         (resolves issue #85)


## 0.4.1 (2012-11-13)

Packaged from revision d9bf9709e9647fb2af51fc559bbe356010bd51ca.

* FIXED: Pypi wants to install beta version. Happened because pypi treats
         0.4.0-beta2 as latest release. This also effectively resulted in a
         downgrade when using 'pip --upgrade' and 0.4.0 was already installed.
         (thanks to jmagnusson for the report,
          resolves issue #103)

## 0.4.0 (2012-11-11)

Packaged from revision c44f9cfee59f1b440f022422f917f247e16bbc6b.

* CHANGED: Refactored tests to allow test runs with other apps. Includes a
         "backport" of override_settings to ensure Django 1.3 support.
         (thanks to Jacek Tomaszewski)
* CHANGED: Modeltranslation related css class prefix to 'mt'.

* FIXED: Race condition during initialization.
         (resolves issue #91)
* FIXED: Tabs don't properly support two-part language codes.
         (resolves issue #63)


## 0.4.0-beta2 (2012-10-17)

Packaged from revision 7b8cafbde7b14afc8e85235e9b087889a6bfa86e.

* FIXED: Release doesn't include rst files.


## 0.4.0-beta1 (2012-10-17)

Packaged from revision 09a0c4434a676c6fd753e6dcde95056c424db62e.

* CHANGED: Refactored documentation using sphinx.
         (resolves issue #81)

* FIXED: Setting MODELTRANSLATION_TRANSLATION_FILES should be optional.
         (resolves issue #86)


## 0.4.0-alpha1 (2012-10-12)

Packaged from revision 170.

* ADDED: Support for FileField and ImageField.
         (thanks to Bruno Tavares,
          resolves issue #30)
* ADDED: New management command sync_database_fields to sync the database after
         a new model has been registered or a new language has been added.
         (thanks to Sébastien Fievet and the authors of django-transmeta,
          resolves issue #62)

* CHANGED: Excluded tabular inlines from jQuery tabs, as they are currently
         not supported.
* CHANGED: Use app-level translation files in favour of a single project-level
         one. Adds an autoregister feature similiar to the one provided by
         Django's admin. A new setting MODELTRANSLATION_TRANSLATION_FILES keeps
         backwards compatibility with older versions. See documentation for
         details. This is basically a merge from both
         django-modeltranslation-wrapper and hyperweek's branch at github.
         (thanks to Jacek Tomaszewski, Sébastien Fievet and Maxime Haineault,
          resolves issues #19, #58 and #71)
* CHANGED: Moved tests to separate folder and added tests for TranslationAdmin.
         To run the tests the settings provided in model.tests.modeltranslation
         have to be used (settings.LANGUAGES override doesn't work for
         TranslationAdmin).
* CHANGED: Major refactoring of the admin integration. Subclassed BaseModelAdmin
         and InlineModelAdmin. Patching options in init doesn't seem to be
         thread safe. Instead used provided hooks like get_form, get_formset
         and get_fieldsets. This should resolve several problems with the
         exclude and fieldsets options and properly support options in inlines.
         (resolves issue #72)

* FIXED: Non-unicode verbose field names showing up empty in forms.
         (resolves issue #35)
* FIXED: Dynamic TranslationOptions model name.
* FIXED: Widgets for translated fields are not properly copied from original
         fields.
         (thanks to boris-chervenkov, resolves issue #74)
* FIXED: Removed XMLField test which is deprecated since Django 1.3 and
         broke tests in Django 1.4.
         (resolves issue #75)


## 0.3.3 (2012-02-23)

Packaged from revision 129.

* CHANGED: jQuery search path in tabbed_translation_fields.js. This allows use of
         a version of jQuery other than the one provided by Django. Users who
         want to force the use of Django's jQuery can include force_jquery.js.

* FIXED: Another attempt to include static files during installation.
         (resolves reopened issue #61)


## 0.3.2 (2011-06-16)

Packaged from revision 122.

* FIXED: Static files not included during installation.
         (resolves issue #61)


## 0.3.1 (2011-06-07)

Packaged from revision 121.

* CHANGED: Renamed media folder to static.


## 0.3 (2011-06-03)

Packaged from revision 113.

* ADDED: Support for multi-table inheritance.
         (thanks to Sébastien Fievet, resolves issues #50 and #51)
* ADDED: Jquery-ui based admin support for tabbed translation fields.
         (thanks to jaap and adamsc, resolves issue #39)
* ADDED: CSS class to identify a translation field and the default translation
         field in admin.
         (thanks to jaap)
* ADDED: Configurable default value per field instance.
         (thanks to bmihelac, resolves issue #28)
* ADDED: Setting to override the default language.
         (thanks to jaap, resolves issue #2)

* CHANGED: Improved performance of update_translation_fields command.
         (thanks to adamsc, resolves issue #43)
* CHANGED: Factored out settings into a separate settings.py and consistently
         used an app specific settings prefix.
* CHANGED: Refactored creation of translation fields and added handling of
         supported fields.
         (resolves issue #37)

* FIXED: Clearing the default translation field in admin does not clear the
         original field.
         (resolves issue #47)
* FIXED: In some setups appears "This field is required" error for the
         original field.
         (resolves issue #5)
* FIXED: Translations are not saved for tinymce HTMLField when using jquery
         tabs.
         (thanks to kottenator, resolves issue #41)
* FIXED: Fieldname isn't ensured to be string.
         (resolves issue #41)
* FIXED: Kept backwards compatibility with Django-1.0.
         (thanks to jaap, resolves issue #34)
* FIXED: Regression in south_field_triple caused by r55.
         (thanks to jaap, resolves issue #29)
* FIXED: TranslationField pre_save does not get the default language
         correctly.
         (thanks to jaap, resolves issue #31)


## 0.2 (2010-06-15)

Packaged from revision 57.

* ADDED: Support for admin prepopulated_fields.
         (resolves issue #21)
* ADDED: Support for admin list_editable.
         (thanks carl.j.meyer, resolves issue #20)
* ADDED: Preserve the formfield widget of the translated field.
         (thanks piquadrat)
* ADDED: Initial support for django-south.
         (thanks andrewgodwin, resolves issue #11)
* ADDED: Support for admin inlines, common and generic.
         (resolves issue #12 and issue #18)

* FIXED: Admin form validation errors with empty translated values and
         unique=True.
         (thanks to adamsc, resolves issue #26)
* FIXED: Mangling of untranslated prepopulated fields.
         (thanks to carl.j.meyer, resolves issue #25)
* FIXED: Verbose names of translated fields are not translated.
         (thanks to carl.j.meyer, resolves issue #24)
* FIXED: Race condition between model import and translation registration in
         production by ensuring that models are registered for translation
         before TranslationAdmin runs.
         (thanks to carl.j.meyer, resolves issue #19)
* FIXED: Added workaround for swallowed ImportErrors by printing a traceback
         explicitly.
         (resolves issue #17)
* FIXED: Only print debug statements to stdout if the runserver or
         runserver_plus management commands are used.
         (resolves issue #16)
* FIXED: Removed print statements so that modeltranslation is usable with
         mod_wsgi.
         (resolves issue #7)
* FIXED: Broken admin fields and fieldsets.
         (thanks simoncelen, resolves issue #9)
* FIXED: Creation of db fields with invalid python language code.
         (resolves issue #4)
* FIXED: Tests to run from any project.
         (thanks carl.j.meyer, resolves issue #6)
* FIXED: Removed unused dependency to content type which can break syncdb.
         (thanks carl.j.meyer, resolves issue #1)


## 0.1 (2009-02-22)

Initial release packaged from revision 19.
