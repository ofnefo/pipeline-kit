---
name: adb-pipeline
description: "Use when working with the user's own Android devices over ADB: device inventory, adb shell, scrcpy, Termux setup, app install, per-device profiles and receipts. Enforces exact-serial selection, a loopback-only ADB server, a read-only doctor script, per-operation receipts with rollback, and explicit authorisation for risky operations. Not for devices the user does not own or control, OSINT work, or flashing, unlocking, rooting or wiping without explicit word."
---

# adb-pipeline

## Purpose
Operate the user's **own** Android devices predictably: know exactly which device a command hits, change nothing that was not
asked for, and leave a receipt that can be undone.

## Scope and authorisation
- Only devices the user owns or administers and has explicitly authorised for this work (USB debugging enabled by them, RSA key
  accepted on the device by them). Never someone else's phone, a found device or a device under another person's control.
- No hidden tracking, background recording or monitoring configuration on any device.

## Inputs
- Absolute path to `adb`, the host that physically holds the USB connection, the device serial from a fresh inventory, the goal.

## Hard rules
1. **Exact serial, always.** Every device command carries `-s <SERIAL>` from a fresh inventory receipt. Never rely on "the only
   device", never pick the first line. Unauthorized, offline or duplicate serials are a stop.
2. **Loopback only.** The ADB server listens on `127.0.0.1` (default port 5037). Never `adb tcpip`, never expose tcp/5555, never
   `adb -a`, never `adb connect` to a LAN or public address. Remote access goes through a tunnel the user set up on the device.
3. **Run where the USB is.** Commands execute on the machine physically connected to the device, not over a network file share.
4. **Owned processes.** Start the ADB server deliberately with an owner and a time limit; stop only what you started.
5. **Preserve, don't strip.** No bulk package removal, no `pm uninstall` / `pm disable-user` lists, no "debloat" scripts. Keep
   banking, NFC/payments, telephony, VPN and remote-access apps and their data untouched.
6. **Secrets stay with the user/device.** No SSH private keys, proxy or VPN credentials, subscription links or tokens in receipts,
   repos or chat. One new SSH key per device.

## Needs the user's explicit word (quote it in the receipt)
Bootloader unlock, flashing, custom ROM or root, factory reset or any wipe; installing/removing anything touching banking, NFC,
telephony or VPN; enabling background location or recording; changing remote-access services; any paid or cloud call. A firmware
or root plan is written only after the device is identified (model, build, API, ABI, boot state) and its data is backed up.

## Doctor (read-only)
```
python -X utf8 scripts/doctor.py inventory --adb <ABS_ADB> [--port 5037] --out <receipts>/inventory.json
python -X utf8 scripts/doctor.py inspect   --adb <ABS_ADB> --serial <SERIAL> --out <receipts>/inspect.json
```
- Requires an ADB server already listening on loopback; it never starts one. `--adb` must be an absolute existing path.
- `inspect` requires a serial that matches exactly one entry in `device` state and records manufacturer, model, Android/API, ABI,
  verified-boot and flash-lock props, nfc/wifi/bluetooth/usb.host features, battery.
- Exit 0 = complete, 2 = error (receipt still written with `status: error`). It is not a root or payment test.

## Device profiles
One folder per device (`profiles/<alias>/`): `profile.json` with model/build/API/ABI from an `inspect` receipt, relevant packages
with versions, what must be preserved, the remote-access route, setup steps with rollback. Use an alias in shared docs; keep the
real serial only in local, untracked state.

## Receipts and rollback (every operation)
`<receipts>/<UTC>-<alias>-<op>.json`: serial, op, exact command (no secrets), package/APK version + sha256, exit code, stdout tail,
`verified` (what was checked and how), `rollback` (exact undo), `owner_quote` when the op needed explicit word. Back up user data
before any change that could lose it; record backup path + hash. Write "not tested" for anything not run.

## Gotchas
- Vendor skins may block `pm` actions or change settings paths; check API level and vendor before scripting.
- `adb install -r` keeps data, `adb uninstall` does not (unless `-k`); say which one you used.
- Reports for people are human-readable summaries; never share raw dumps, bugreports, backups, screenshots with personal data or
  recordings of other people without consent.

## Acceptance checklist
- [ ] Device ownership/authorisation stated; serial from a fresh inventory.
- [ ] ADB server on loopback, owned, stopped afterwards if you started it.
- [ ] Every operation has a receipt with verification and rollback.
- [ ] Risky operations carry the user's quoted word; nothing preserved was touched.

## Boundaries
Own, authorised devices only; no flashing/unlock/root/wipe or payment-related changes without explicit word; no network-exposed
ADB; no surveillance features.
