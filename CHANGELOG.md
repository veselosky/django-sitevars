# CHANGELOG

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
