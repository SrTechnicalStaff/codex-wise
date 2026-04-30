---
name: codex-wise-search-and-export
description: >
  Use when the user asks to search Codex Wise, find indexed codebase docs, search by keyword,
  semantic meaning, symbol name, or export wiki pages. Covers codex-wise search and export.
user-invocable: false
---

# Codex Wise Search And Export

Use this skill when the user wants to query or extract indexed Codex Wise content through the CLI.

## Search

Run searches from the target repository root:

```shell
codex-wise search "query"
```

Choose mode based on intent:

```shell
codex-wise search --mode fulltext "database session"
codex-wise search --mode semantic "how authentication requests are validated"
codex-wise search --mode symbol "UserService"
codex-wise search --limit 20 "routing"
```

If semantic search fails or returns nothing, the repo may be index-only or the vector index may be stale. Suggest:

```shell
codex-wise reindex
```

## Export

Export generated wiki pages when the user wants files, sharing artifacts, or offline review:

```shell
codex-wise export
```

Useful variants:

```shell
codex-wise export --format markdown
codex-wise export --format html --output .codex-wise/export-html
codex-wise export --format json --full
```

## Reporting

Summarize the most relevant search results or exported output path. Do not paste huge result sets unless the user asks.
