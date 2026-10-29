# Save the settings file without ever leaving it half-written

`atomicwrite.py` is how the daemon persists its settings file. Operators have twice
found a truncated settings file after a host was power-cycled mid-write, so the module
needs to stop writing over the live file in place.

```python
TEMP_SUFFIX = ".part"
BACKUP_SUFFIX = ".bak"

def render(settings: dict) -> str
def save(path, settings: dict) -> Path
```

`settings` maps string keys to string values. Fix the module so all of the following
hold. Keep the two module-level constants and the two function names and signatures
exactly as they are above.

1. **`render` produces the on-disk form.** One `key=value` line per item, keys in
   ascending sort order, every line terminated by `"\n"`. An empty mapping renders as
   the empty string.
2. **`render` validates before it produces anything.** Raise `ValueError` if a key is
   empty, if a key contains `"="`, or if a key or a value contains `"\n"`. When it
   raises it returns no text at all, not a partially built string.
3. **`save` validates first.** `save` renders the whole document before it touches the
   filesystem, so a `ValueError` from rule 2 propagates out of `save` with nothing on
   disk created, modified or deleted -- not the target, not the temporary file, not the
   backup.
4. **The write goes through a temporary file in the same directory.** `save` writes the
   rendered text to a sibling path whose name is the target's name with `TEMP_SUFFIX`
   appended (`settings.ini` -> `settings.ini.part`), in the target's own directory, and
   then calls `os.replace(temp, target)` to move it into place. `os.replace` is only
   atomic within one filesystem, which is why the temporary file has to be a sibling
   rather than something under the system temp directory. After a successful `save` the
   temporary file no longer exists.
5. **A failed replace cleans up after itself.** If `os.replace` raises an `OSError`,
   `save` deletes the temporary file and re-raises. The target keeps whatever contents
   it had before the call.
6. **Backups, by default on.** If the target already exists, its previous bytes are
   copied to a sibling whose name is the target's name with `BACKUP_SUFFIX` appended
   (`settings.ini` -> `settings.ini.bak`) before the replace happens. If the target does
   not exist yet, no backup file is created.
7. **`ATOMIC_BACKUP` switches the backup policy off.** When that environment variable is
   set to `"0"`, `save` writes no backup and leaves any backup file already on disk
   exactly as it found it. Unset, or set to anything other than `"0"`, means backups are
   on. Read the variable inside `save` rather than at import time, so an operator can
   flip the policy between calls without reimporting.
8. **Paths and encoding.** `path` may be a `str` or any `os.PathLike`. `save` returns the
   target as a `pathlib.Path`. Files are written and read as UTF-8.

`save` does not create missing parent directories; the target's directory is assumed to
exist.
