# Swarm for iPhone / iPad

iOS can't run the detection service. The iPhone is a viewer/controller: live cameras, swarm alerts, add cameras. Point it at a Swarm server (PC, Mac, Linux box, Pi or Android phone) or its public https link. Offline it shows the last known cameras and alerts.

## 1. Fastest (no Mac, no Apple ID): web app
1. In Safari open the server address (`http://<server-ip>:8000` on home Wi-Fi, or the https link).
2. Share -> **Add to Home Screen**. Open Swarm from the icon.
3. Push alerts need the **https** link and iOS 16.4+: open from the Home Screen icon, tap **Enable alerts**.

## 2. One tap
Open [the installer](https://cdn.jsdelivr.net/gh/coden607/swarm@main/installer.html) in Safari and tap **Install Swarm**.

- On a server you already run (`http://<server>:8000/install`) that tap downloads a Home Screen icon. Safari opens Settings; tap **Install**.
- On the public installer the same tap opens SideStore and signs Swarm with the Apple ID already saved there. If SideStore is not on the phone, that tap installs SideStore: it asks AltStore first, then downloads [SideStore.ipa](https://github.com/SideStore/SideStore/releases/latest/download/SideStore.ipa) and opens the [official setup](https://docs.sidestore.io/docs/installation/install) (iloader on a computer, once). When you return to the installer, Swarm retries. If SideStore asks you to sign in, use the same Apple ID this phone uses. Swarm does not ask for the password. Then Settings → General → VPN & Device Management → Trust (Apple will not let an app do that tap). Swarm searches the Wi‑Fi for the server on its own.

A free Apple ID expires the app in about 7 days; opening SideStore or AltStore refreshes it with that saved login.

## 3. With a Mac (Xcode)
```sh
brew install xcodegen
cd ios && xcodegen && open Swarm.xcodeproj
```
Select your iPhone, set your Team under Signing, Run.

Unverified on a real device: the unsigned IPA is only built in CI, not tested on hardware.
