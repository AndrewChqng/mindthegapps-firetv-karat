# MindTheGapps for Fire TV Stick 4K Max 2nd Gen (`karat` / `AFTKRT`)

A reproducible solution and automated patcher for installing **Google Play Store** and **Google Play Services** on the Amazon Fire TV Stick 4K Max (2nd Gen, codename `karat`), running **Fire OS 8 (Android 11)** via TWRP recovery.

---

## The Problems on Fire OS 8

Installing standard [MindTheGapps 11.0.0 ARM ATV](https://androidfilehost.com/?w=files&flid=322935) directly onto Fire TV Stick 4K Max 2nd Gen fails with three critical blockers:

### 1. Inadequate System & Product Partition Storage
* Fire OS 8 partitions are dynamic logical partitions inside a `super` partition (`/dev/block/by-name/super`, `1.51 GB`).
* Stock firmware allocates `/system` to ~`1.16 GB` (leaving only `~3.6 MB` free) and `/product` to only `16 MB` (leaving `52 KB` free).
* Full MindTheGapps ATV is `~219 MB` uncompressed, exceeding partition limits and aborting in TWRP with `Not enough space for GApps! Aborting`.

### 2. Boot Loop / System Crash (`PackageVerificationReceiver` Collision)
* On boot, `PackageManagerService.getRequiredButNotReallyRequiredVerifierLPr()` inspects all broadcast receivers handling `android.intent.action.PACKAGE_NEEDS_VERIFICATION`.
* Android requires **exactly one** verifier. Both Amazon's `com.amazon.adep` (`com.amazon.adep.nimh.receiver.PackageVerificationReceiver`) and Google Play Store (`com.android.vending` / `com.google.android.finsky.verifier.impl.PackageVerificationReceiver`) provide this component.
* Having both causes `system_server` to crash into a fatal bootloop:
  ```text
  FATAL EXCEPTION IN SYSTEM PROCESS: main
  java.lang.RuntimeException: There must be exactly one verifier; found [
    ResolveInfo{... com.amazon.adep/.nimh.receiver.PackageVerificationReceiver},
    ResolveInfo{... com.android.vending/com.google.android.finsky.verifier.impl.PackageVerificationReceiver}
  ]
  ```

### 3. Missing Native Libraries (`libconscrypt_gmscore_jni.so` UnsatisfiedLinkError)
* In MindTheGapps APKs, native `.so` files (e.g. `libconscrypt_gmscore_jni.so` in GMS, `libcronet.so` in Play Store) are stored `DEFLATE`-compressed.
* Android's bionic dynamic linker cannot `mmap` compressed libraries directly out of system APKs.
* When launching Play Store, it throws an `UnsatisfiedLinkError` and fails to establish TLS/SSL or retrieve device configuration tokens unless the libraries are pre-extracted to `/product/priv-app/<App>/lib/arm/*.so`.

---

## How This Project Solves It

1. **Lightweight Package Trimming**:
   * Drops non-essential AOSP Android TV bloatware (`~150 MB` saved), including `talkback.apk`, `Katniss.apk` (Google Assistant), `AndroidMediaShell.apk` (Cast receiver), `Backdrop.apk`, and crucially `SetupWraithPrebuilt.apk` (Android TV Setup Wizard, which causes remote pairing and setup loops on Fire OS).
   * Retains strictly what is required for Google Play Store functionality:
     - `Tubesky.apk` (`com.android.vending` — Google Play Store)
     - `PrebuiltGmsCorePano.apk` (`com.google.android.gms` — Google Play Services)
     - `SssAuthbridgePrebuilt.apk` (`com.google.android.sss.authbridge` — TV Second-Screen Sign-In)
     - `GoogleServicesFramework.apk` (`com.google.android.gsf`)
     - `GoogleOneTimeInitializer.apk` (`com.google.android.onetimeinitializer`)
     - Core privileged permission and sysconfig XML definitions.

2. **Automated Partition Resizing in TWRP**:
   * The `super` partition contains `~195.5 MB` of unallocated free blocks.
   * The installer script automatically executes `lptools resize` and `resize2fs` inside TWRP:
     - Expands `system` from `1.20 GB` to `1.24 GB` (`+34 MB`, leaving `~49 MB` free space).
     - Expands `product` from `16 MB` to `144 MB` (`+128 MB`, crossing block group boundaries to add `+368` free inodes).

3. **Pre-Extracted Native Libraries**:
   * Automatically extracts all 17 `lib/armeabi-v7a/*.so` files directly into `/product/priv-app/<App>/lib/arm/` during packaging.
   * Fixes SSL/TLS initialization, FCM push token generation, and account authentication out of the box.

4. **Systemless Verifier Conflict Resolver (Magisk Module)**:
   * Rather than permanently deleting Amazon's `com.amazon.adep` (which breaks stock services or risks reintroduction after OTA), the installer bundles and configures a Magisk module: `adep_verifier_disabler`.
   * Operates via `post-fs-data.sh` and `service.sh`:
     - Disables only `com.amazon.adep.nimh.receiver.PackageVerificationReceiver` in `/data/system/users/0/package-restrictions.xml` before `system_server` initializes.
     - Keeps both Amazon ADEP and Google Play Store installed and operational with zero package manager crashes.

---

## Prerequisites

1. **Fire TV Stick 4K Max (2nd Gen)** (`karat` / `AFTKRT`).
2. Bootloader unlocked with **TWRP** recovery installed (e.g. via `amonet`).
3. Rooted with **Magisk** (e.g. `Magisk-31.1.FTV`).
4. Python 3 on your host PC.
5. Official source zip: [MindTheGapps-11.0.0-arm-ATV-20230922_081030.zip](https://androidfilehost.com/?w=files&flid=322935).

---

## Build Instructions

Run the patch script against the official MindTheGapps ATV zip:

```bash
git clone https://github.com/AndrewChqng/mindthegapps-firetv-karat.git
cd mindthegapps-firetv-karat

# Place your official MindTheGapps zip in the directory, then:
python3 patch_mindthegapps.py \
  --src MindTheGapps-11.0.0-arm-ATV-20230922_081030.zip \
  --dst MindTheGapps-11.0.0-arm-ATV-PlayStore-minimal.zip \
  --module-dst adep_verifier_disabler_mm.zip
```

This generates:
* `MindTheGapps-11.0.0-arm-ATV-PlayStore-minimal.zip` (Ready for TWRP sideload)
* `adep_verifier_disabler_mm.zip` (Standalone Magisk module)

---

## Installation via TWRP

1. Reboot your Fire TV Stick into TWRP recovery:
   ```bash
   adb reboot recovery
   ```
2. Enable sideload in TWRP:
   ```bash
   adb shell twrp sideload
   ```
3. Sideload the minimal package:
   ```bash
   adb sideload MindTheGapps-11.0.0-arm-ATV-PlayStore-minimal.zip
   ```
4. Wipe caches and reboot:
   ```bash
   adb shell twrp wipe cache
   adb shell twrp wipe dalvik
   adb reboot
   ```

---

## Verification

Once booted into Fire OS:

1. Confirm both packages are active and non-colliding:
   ```bash
   adb shell "pm path com.amazon.adep; pm path com.android.vending"
   adb shell "dumpsys package com.amazon.adep | grep -A 3 disabledComponents:"
   ```
2. Confirm crash logcat is empty:
   ```bash
   adb logcat -d -b crash
   ```
3. Launch Google Play Store:
   ```bash
   adb shell am start -n com.android.vending/com.google.android.finsky.tvmainactivity.TvMainActivity
   ```

---

## Acknowledgments & Credits

* Documented and engineered with pair programming assistance from **Antigravity (Google DeepMind)**.
* **Disclaimer**: This is experimental low-level device modification software provided for educational and hobbyist purposes. Modifying device partitions and system services carries risks; use at your own discretion.
* Credit to the **MindTheGapps** project, **TeamWin (TWRP)**, and the **XDA Fire TV community** (`yiy`, `SweenWolf`, `Pro-me3us`).
