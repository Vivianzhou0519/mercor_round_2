# SWE-bench Verified -- optional stretch

Not scored. Not Part 1 or Part 2. Do not run these. Read-only stretch if you finish the exercise in `tasks/` with time to spare; otherwise ignore this folder.

These six tasks are real instances from [SWE-bench Verified](https://www.swebench.com/), pulled from the Harbor hub in the same format as `tasks/`. They are here so you can see what production Harbor tasks look like: tests live as a diff inside `tests/test.sh`, and `tests/config.json` holds SWE-bench ground truth (`FAIL_TO_PASS`, `PASS_TO_PASS`, the base commit, the gold patch).

The local harness is not meant to run them. Their Dockerfiles pull multi-gigabyte x86 images and take minutes per task.

If you do look, anything your checks have to say about them can go in the report. If you never open this folder, that is the expected outcome.
