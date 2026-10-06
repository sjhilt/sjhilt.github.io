# sjhilt.github.io

Static personal website and publication archive for Stephen J. Hilt.

## Validation

Run the dependency-free site checks before committing changes:

```shell
python scripts/validate_site.py
```

The validator checks publication fields, dates, descending chronological order, URLs,
duplicate records and links, photo manifest entries and files, favicon coverage,
`_blank` link protection, and local references from HTML and CSS. Legacy HTTP
publication links are reported as warnings so they can be upgraded only after a
working HTTPS destination is verified.
