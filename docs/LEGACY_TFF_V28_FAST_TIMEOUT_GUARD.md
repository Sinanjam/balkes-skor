# TFF Factory v2.8 - Safe Legacy Fast Timeout Guard

v2.7 fixed repeated HTTP 504 branches, but some old TFF URLs do not return an
HTTP error immediately. They hang until urllib's 75 second timeout, which makes
GitHub Actions appear stuck for minutes.

v2.8 does **not** add a season-wide duration limit. It only changes unreachable
network branches:

- Legacy fetch timeout is reduced to 12 seconds.
- HTTP 502/503/504 and network timeouts are fast-skipped.
- A single dead pageID / grupID / week branch is abandoned after cumulative
  unreachable errors.
- The season scan continues with other branches.
- Published match data still passes the existing Balıkesirspor + season-date
  validation before it is written.

Good log signs:

```text
Run TFF Factory v2.8 safe legacy fast timeout guard
fetch hızlı atla: ... -> timed out
page_week_branch_abandoned
group_week_branch_abandoned
selectedIds=...
detail doğrulama ... hits=...
```
