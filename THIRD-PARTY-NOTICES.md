# Third-party notices

The viewer (`docs/graph/explorer.html`) and the dataset artifacts in this
repository are built on the following open-source projects. All are
redistributed inside this repository under their respective licenses.

| Component | Version | License (SPDX) | Project |
| --- | --- | --- | --- |
| AntV G6 | 5.1.1 | MIT | https://github.com/antvis/G6 |
| Vega | 5.30.0 | BSD-3-Clause | https://github.com/vega/vega |
| Vega-Lite | 5.21.0 | BSD-3-Clause | https://github.com/vega/vega-lite |
| vega-embed | 6.26.0 | BSD-3-Clause | https://github.com/vega/vega-embed |

G6 draws the succession network; the Vega-Lite stack renders the
timeline spectrum from the explicit specification in
`docs/graph/law_timeline.vl.json`.

The unminified and minified library files are vendored verbatim under
`docs/graph/` (`g6.min.js`, `vega.min.js`, `vega-lite.min.js`,
`vega-embed.min.js`) and are additionally inlined into
`docs/graph/explorer.html` so that the artifact runs without network
access. The minified bundles carry no licence banner, so this file is the
authoritative licence record for them.

## Web fonts (loaded from Google Fonts, optional)

These are requested at runtime only to improve typography. They are not
required: the stylesheet is loaded non-blocking and the viewer renders
fully with system fonts.

| Family | License (SPDX) | Project |
| --- | --- | --- |
| Be Vietnam Pro | OFL-1.1 | https://fonts.google.com/specimen/Be+Vietnam+Pro |
| IBM Plex Mono | OFL-1.1 | https://fonts.google.com/specimen/IBM+Plex+Mono |

## Formats (no software included)

- **GEXF 1.3** — the graph exchange format used by Gephi and Gephi-Lite;
  `docs/graph/law_graph.gexf` is an instance of that open format.
- **JSON / JSON Lines** — plain data formats.

## This work

Everything else in this repository - the data, the corpus builder, the
indexes, the benchmark files, the provenance records and the viewer's own
code (lane layout, time-travel state, detail drawer, PNG export) - is part
of ViCivil-TKG and is released under the repository's own license.