# Swarm for iPhone / iPad (test build)

Native wrapper around the Swarm web app. iOS can't run the detection service, so point it at a Swarm server (your PC/Mac/Linux box/Android phone, or the remote link). If the server is unreachable it shows the last known cameras and alerts.

```sh
brew install xcodegen
cd ios && xcodegen && open Swarm.xcodeproj
```
In Xcode: select your iPhone, set your Team under Signing, press Run. First launch asks for the server address (e.g. `192.168.1.20:8000`).

No Xcode? Open the server URL in Safari -> Share -> Add to Home Screen (PWA, same features).
