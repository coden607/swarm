# Android Installation Guide

This guide walks you through a **single‑click** setup on an Android device that:

1. **Installs Termux** from F‑Droid (the trusted, open‑source terminal emulator).
2. Installs the required Termux packages.
3. Pulls the **Swarm Detection Service** script repository.
4. Executes the same `install.sh` you would run on a Linux host (it will spin up Docker inside a proot‑based Linux distro – see notes).

---
### 1️⃣ One‑click Termux install

Open the following URL on your Android device – it will launch the F‑Droid app (or the browser) to the Termux page:

```
https://f-droid.org/packages/com.termux/
```

Tap **Install** and wait for the installation to finish.

---
### 2️⃣ Run the helper script (single tap)

After Termux is installed, tap **Share → Run this script** (or copy‑paste the line below into Termux). This script will:

- Update Termux package repos.
- Install `git`, `python`, `curl`, `wget`, `proot-distro` (to create a lightweight Linux environment where Docker can run).
- Create a `docker‑lite` distro (based on Alpine) and start it.
- Inside that distro it will clone the Swarm repo, install Docker, and launch the service.

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/your-org/swarm/main/android/setup_swarm.sh)"
```

> **Note:** The script requires an internet connection and about 300 MB of storage.

---
### 3️⃣ Access the UI

When the setup finishes, the script will print a local URL like:

```
http://127.0.0.1:8000
```

Open Chrome (or any browser) on the same device and navigate to that URL. The UI will appear as a PWA – you can add it to the home screen for a native‑like experience.

---
### 4️⃣ What the script does under the hood

| Step | Command | Explanation |
|------|---------|-------------|
| Update packages | `pkg update && pkg upgrade -y` | Refresh Termux repos. |
| Install utilities | `pkg install -y git python curl wget proot-distro` | Needed tools. |
| Create distro | `proot-distro install docker-lite` | Small Alpine rootfs with Docker binaries. |
| Start distro | `proot-distro login docker-lite -- bash -c "./install.sh"` | Runs the same installer you use on a normal Linux host. |

---
### 5️⃣ Troubleshooting

- **Termux‑API not installed** – some optional features (e.g., QR‑code scanning) need `termux-api`; install via `pkg install termux-api`.
- **Out of storage** – free at least 500 MB on the device.
- **Network errors** – ensure cellular/Wi‑Fi is stable.

---
### 6️⃣ Uninstall

To remove everything:

```bash
proot-distro remove docker-lite
rm -rf $HOME/swarm
``` 

That will delete the Linux distro and the cloned repository.
