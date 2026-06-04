# JupyterHub VS Code connection screenshots

This directory holds reference PNGs for the VS Code remote-Jupyter setup
documented in `services/jupyterhub/README.md` §10. The four expected files:

| File | Step in README |
|------|---------------|
| `01-vscode-select-existing-server.png` | §10.2 — `Select Another Kernel` → `Existing Jupyter Server` |
| `02-vscode-enter-server-url.png` | §10.2 — URL-entry dialog (with `?token=` suffix) |
| `03-vscode-server-name-prompt.png` | §10.2 — friendly-name prompt |
| `04-vscode-kernel-picker.png` | §10.2 — final kernel picker showing Python + Scala options |

If you arrived here looking for the images and the directory is empty,
see §10.7 of the JupyterHub README for instructions on capturing them
yourself. The README still works without the PNGs — they're a UX
nicety, not a dependency.

PNGs are committed as binary; keep each under ~200 KB so the repo
stays clone-light. Compress with `pngcrush -brute` or
`tinify`/`squoosh-cli` before adding.
