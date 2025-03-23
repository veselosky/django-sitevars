# CHANGELOG

## 1.1.1

- CHANGED: Fixed several bugs that caused failures when not using
  `django.contrib.sites`.
- CHANGED: Added CURRENT_SITE_METHOD and CURRENT_SITE_FUNCTION settings to make
  determining the current site configurable when using a custom SITE_MODEL.
- CHANGED: Updated README documentation.

## 1.1.0

- ADDED: Support for a swappable site model so you can use it without
  `django.contrib.sites`.
- CHANGED: Values are now editable in the Admin Change List page.
- CHANGED: Added Django 5.2 (rc1) and Python 3.13 to test matrix.

## 1.0.2

- Fix crashing bug with `transaction.on_commit` calls.
- Do not access or populate the cache when inside a database transaction, which could
  cause cache to get out of sync.
- Test behavior in and outside of transactions.

## 1.0.1

- Clear cache on both save and delete
- Use `transaction.on_commit` so the cache doesn't contain writes that were rolled back.

## 1.0.0 Initial Release

- Basic feature set implemented
