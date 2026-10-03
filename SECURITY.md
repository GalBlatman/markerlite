# Security policy

## Threat model

- markerlite is a local tool for one user. It runs no server and makes no network connection at runtime.
- Its input is untrusted: a PDF may be malformed or crafted to exhaust time, memory or disk.
- A figure or math manifest filled in by a person or a model is untrusted input too.
- It writes only Markdown, images and manifests into the output folder the user chooses, and runs Tesseract as a local subprocess.
- The Windows build is unsigned and is built and published by this repository's GitHub Actions.

## Scope

In scope:

- a PDF that crashes, stalls or exhausts memory during conversion, instead of degrading with a warning;
- any write outside the chosen output folder, including through a manifest;
- file names or error text that inject control sequences into the console, the GUI or the run log;
- weaknesses in the build and release workflow.

Out of scope: vulnerabilities in PyMuPDF/MuPDF, Tesseract or Python themselves (please report those upstream), and conversion quality, which belongs in an ordinary issue.

## Reporting

Report a vulnerability privately through GitHub: the repository's **Security** tab, then **Report a vulnerability**. If that button is not shown, open an ordinary issue that asks for a private channel and contains no details of the problem.

Please include the markerlite version (the app's window title, the first line of the `markerlite-diag.txt` that `markerlite.exe --diag` writes, or `markerlite --version`) and, if you can share it, a PDF that reproduces the problem.

The hardening already done, and the limits that protect a conversion, are recorded in `tests/REPORT-security.md`.
