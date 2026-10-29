# Summarise a set of exam scores

Implement `summary(scores)` in `gradebook.py`. `scores` is a non-empty list of
integers in `0..100`. Return a dict with these keys:

- `"mean"` -- arithmetic mean, rounded to 1 decimal place
- `"median"` -- the median; for an even-length list, the mean of the two middle
  values, rounded to 1 decimal place
- `"highest"` -- the largest score
- `"lowest"` -- the smallest score
- `"passing"` -- how many scores are `>= 60`

Do not sort the caller's list in place.
