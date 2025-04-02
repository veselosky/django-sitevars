# CHANGELOG

## 2.0.0 BREAKING CHANGES

- BREAKING CHANGE: Overhauled the `get_value` method to deal with several edge cases in
  a smarter way. Now recognizes "false" and "0" as false values when `asa=bool`
  (previously these evaluated as True). Now accepts default values of the target type as
  well as strings. When a default is given, checks the type against the actual return
  value and raises an error if they are incompatible types (to eliminate a footgun).
  Technically this is a breaking change since it will change the return values of some
  queries, but the old values were wrong and would cause bugs.
- BREAKING CHANGE: Removed the internal cache of vars and the `use_cache` method of
  `SitevarsConfig`. The cache was problematic to maintain and did not actually improve
  performance. In fact in some cases it could degrade performance.
- CHANGED: Documented using swappable sites with 3rd party apps.
- CHANGED: Added `get_mulitple_values` to efficiently retrieve values for multiple
  SiteVars at once.

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
