# Emotional Atlas: ACM manuscript sources

Uses the official ACM `acmart` class with `manuscript,screen,nonacm` options. This is an independently distributed technical report, not a claim of ACM publication or acceptance.

The content describes software version 0.9.10 (original report dated November 11, 2026). The ACM edition is dated November 13, 2026. Historical results and version-specific limitations are retained.

## Build

```sh
latexmk -pdf main.tex
```

Or, with Tectonic:

```sh
tectonic --keep-logs main.tex
```

Tested with Tectonic 0.17.0 and bundled acmart v1.83. The output is `main.pdf`, distributed as `Emotional-Atlas.pdf`. Equations, tables, and the TikZ workflow diagram are native LaTeX. Implementation references remain linked in the report; the original does not contain a separate scholarly bibliography.

The Markdown edition is included. Its `acm/` download paths correspond to its repository location at `docs/TECHNICAL_REPORT.md`; source implementation links are relative to that location.
