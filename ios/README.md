# Swarm for iPhone / iPad

iOS can't run the detection service. The iPhone is a viewer/controller: live cameras, swarm alerts, add cameras. Point it at a Swarm server (PC, Mac, Linux box, Pi or Android phone) or its public https link. Offline it shows the last known cameras and alerts.

## 1. Fastest (no Mac, no Apple ID): web app
1. In Safari open the server address (`http://<server-ip>:8000` on home Wi-Fi, or the https link).
2. Share -> **Add to Home Screen**. Open Swarm from the icon.
3. Push alerts need the **https** link and iOS 16.4+: open from the Home Screen icon, tap **Enable alerts**.

## 2. Native app without a Mac (sideload)
1. GitHub -> Actions -> latest `ci` run -> artifact **Swarm-unsigned-ipa** -> download and unzip.
2. Install with [Sideloadly](https://sideloadly.io) or [AltStore](https://altstore.io) using a free Apple ID (re-sign every 7 days).
3. Settings -> General -> VPN & Device Management -> trust your Apple ID.
4. First launch asks for the server address (e.g. `192.168.1.20:8000`).

## 3. With a Mac (Xcode)
```sh
brew install xcodegen
cd ios && xcodegen && open Swarm.xcodeproj
```
Select your iPhone, set your Team under Signing, Run.

Unverified on a real device: the unsigned IPA is only built in CI, not tested on hardware.
