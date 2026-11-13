---
applyTo: "ui/**,android/**,ios/**"
---
Keep PWA, Android and iOS client behavior distinct. iOS is a viewer/controller, not a Python detection server. Validate offline shell, reconnect, auth, permissions, push notifications and HTTPS requirements. Never embed credentials/Apple IDs in compiled assets or logs. CI build output is not proof of successful hardware install, signing or real push delivery.
