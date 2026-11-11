---
applyTo: "install.sh,install.ps1,Install-*.sh,Install-*.bat,Install-*.command,one_click_installer.sh"
---
Preserve private `.env` and `data/`; make installation idempotent and Ctrl-C-safe. Avoid executing unreviewed remote scripts and never turn on cloud tunnel or firewall exposure without owner approval. Verify Linux/macOS/Windows/Termux/iSH variants separately, logging only redacted results. Do not claim a service is deployed until observed running.
