# Swarm for iPhone / iPad

iOS can't run the detection service. The iPhone is a viewer/controller: live cameras, swarm alerts, add cameras. Point it at a Swarm server (PC, Mac, Linux box, Pi or Android phone) or its public https link. Offline it shows the last known cameras and alerts.

## 1. Fastest (no Mac, no Apple ID): web app
1. In Safari open the server address (`http://<server-ip>:8000` on home Wi-Fi, or the https link).
2. Share -> **Add to Home Screen**. Open Swarm from the icon.
3. Push alerts need the **https** link and iOS 16.4+: open from the Home Screen icon, tap **Enable alerts**.

## 2. Native app, one tap
Install [SideStore](https://sidestore.io) or [AltStore](https://altstore.io) once (free Apple ID). Then tap:

- [Install with SideStore](sidestore://install?url=https%3A%2F%2Fgithub.com%2Fcoden607%2Fswarm%2Freleases%2Fdownload%2Fapk%2FSwarm-unsigned.ipa)
- [Install with AltStore](altstore://install?url=https%3A%2F%2Fgithub.com%2Fcoden607%2Fswarm%2Freleases%2Fdownload%2Fapk%2FSwarm-unsigned.ipa)

Confirm the install. Settings → General → VPN & Device Management → trust your Apple ID. First launch asks for the server address (for example `192.168.1.20:8000`). A free Apple ID expires the app in about 7 days; open SideStore or AltStore to refresh it.

The same package is [Swarm-unsigned.ipa](https://github.com/coden607/swarm/releases/download/apk/Swarm-unsigned.ipa). [Add the Swarm source](sidestore://source?url=https%3A%2F%2Fraw.githubusercontent.com%2Fcoden607%2Fswarm%2Fmain%2Fios%2Faltstore.json) if you want later versions to show up inside SideStore.

## 3. With a Mac (Xcode)
```sh
brew install xcodegen
cd ios && xcodegen && open Swarm.xcodeproj
```
Select your iPhone, set your Team under Signing, Run.

Unverified on a real device: the unsigned IPA is only built in CI, not tested on hardware.
