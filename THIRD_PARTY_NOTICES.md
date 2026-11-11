# Third-party notices

The application source and project artwork are distributed under the repository's MIT license. Third-party materials retain their own terms.

- The macOS application bundles Python (Python Software Foundation License), Tcl/Tk (their BSD-style licenses), OpenSSL (Apache License 2.0 in this build), and the PyInstaller bootloader (GPL with a distribution exception). Bundled runtime license files are retained with the distribution. PyInstaller's distribution exception permits distribution of applications under their own licenses.
- `frankenstein.txt` is Project Gutenberg ebook #84 by Mary Shelley. The full original file includes the Project Gutenberg license. This public-domain literary text is an optional sample in the source repository, not a model-generated analysis and not included in the application binary. Check applicable copyright terms in your jurisdiction.
- The constellation icon was created with OpenAI's built-in image-generation tool; its generation prompt is in `assets/icon-generation.txt`.

Sources: https://www.python.org/psf/license/ · https://www.tcl-lang.org/software/tcltk/license.html · https://openssl-library.org/source/license/ · https://pyinstaller.org/en/stable/license.html · https://www.gutenberg.org/ebooks/84

## Chinese idiom dictionary

The bundled `datasets/chinese.json` is adapted from PWXCOO's
[chinese-xinhua](https://github.com/pwxcoo/chinese-xinhua), revision
`fe6d6c2e8baa82187f4c96bbe042e43f96c05666`. Copyright (c) 2018 PWXCOO,
MIT license retained in `licenses/chinese-xinhua.txt`. The conversion retains
idiom forms and definitions, adds identifiers/provenance and ten imagery flags.

## Object geometry dependencies

NumPy 2.5.4 and SciPy 1.17.1 provide numerical arrays and Qhull-based spatial
geometry. Their distribution license notices, including bundled third-party
notices, are retained under `licenses/numpy` and `licenses/scipy`.
See https://numpy.org and https://scipy.org.
