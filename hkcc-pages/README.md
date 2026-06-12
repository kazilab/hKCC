# hKCC atlas — hosted bundle

This repository hosts **one self-contained file** — `index.html` — the offline,
read-only standalone build of the hKCC atlas (Key Characteristics of Human
Carcinogens). It is served via GitHub Pages.

- **Live site:** https://<user>.github.io/<repo>/
- All data is embedded in the HTML; no backend or network access is required.
- Licenses: data CC-BY-4.0 · code MIT.

## Updating
This file is a generated artifact. To refresh it, rebuild in the main hKCC
project and copy the result here:

```bash
cd /path/to/hKCC/standalone
npm run build
cp dist/index.html /path/to/this-repo/index.html
git commit -am "Update bundle" && git push
```

`.nojekyll` is present so GitHub Pages serves the file verbatim.
