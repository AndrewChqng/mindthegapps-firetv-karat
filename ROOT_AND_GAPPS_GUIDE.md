# Comprehensive Fire TV Stick 4K Max 2nd Gen (`karat`) Root & GApps Guide

A unified, end-to-end technical reference synthesizing the root, bootloader unlock, recovery, firmware maintenance, and Google Play Store patch methodologies for the **Fire TV Stick 4K Max (2nd Gen, codename `karat` / `AFTKRT`)** running **Fire OS 8**.

---

## Table of Contents

1. [Hardware & Firmware Context](#1-hardware--firmware-context)
2. [Prerequisites & Host Setup](#2-prerequisites--host-setup)
3. [Phase 1: Temporary Root (Ghostlock)](#phase-1-temporary-root-ghostlock)
4. [Phase 2: Permanent Bootloader Unlock & TWRP (Amonet)](#phase-2-permanent-bootloader-unlock--twrp-amonet)
5. [Phase 3: Firmware & Magisk Root Tracks](#phase-3-firmware--magisk-root-tracks)
   - [Track A: SweenWolf Pre-Patched Custom ROM](#track-a-sweenwolf-pre-patched-custom-rom)
   - [Track B: Amazon Stock ROM & Hardening](#track-b-amazon-stock-rom--hardening)
   - [Track C: Updating / Changing Builds](#track-c-updating--changing-builds)
6. [Phase 4: Google Play Store Installation (MindTheGapps Minimal)](#phase-4-google-play-store-installation-mindthegapps-minimal)
7. [Essential Magisk Modules & System Tweaks](#7-essential-magisk-modules--system-tweaks)
8. [Hardware Combos & Remote Shortcuts](#8-hardware-combos--remote-shortcuts)
9. [Primary XDA Threads & Source References](#9-primary-xda-threads--source-references)

---

## 1. Hardware & Firmware Context

* **Model**: Amazon Fire TV Stick 4K Max 2nd Gen (AFTKRT, board `karat`).
* **Processor**: MediaTek MT8696 (Quad-core ARM Cortex-A55, 32-bit `armeabi-v7a` userland on 64-bit kernel).
* **OS**: Fire OS 8 (based on Android 11 / API 30).
* **Exploit Window**: Temp root and bootloader unlock are confirmed functional on Fire OS 8 builds from **`8.1.4.5` (`RS8145.3070N`) through `8.1.8.5` (`RS8185.3885N` / `RS8185.3898N`)**.
* **Display Compositor Note**: Fire OS builds prior to `8.1.8.0` suffer from a MediaTek Hardware Composer (HWC) sync-fence bug locking custom launcher navigation to ~30 FPS; Fire OS `8.1.8.5` includes the patched HWC HAL restoring native 60 FPS pacing.

---

## 2. Prerequisites & Host Setup

### Host Tools
* Linux / macOS / Windows with working `adb` and `fastboot`:
  ```bash
  # Linux (Ubuntu/Debian)
  sudo apt install -y adb fastboot android-sdk-platform-tools-common
  sudo usermod -aG plugdev $USER
  ```
* Micro-USB to USB-A data cable connected to PC, HDMI connected to display.

### Device Prep
1. Connect stick to TV and Wi-Fi.
2. Enable Developer Options: **Settings -> My Fire TV -> About -> Click device name 7 times**.
3. Enable USB Debugging: **Settings -> My Fire TV -> Developer Options -> ADB Debugging -> ON**. Authorize the PC prompt (*Always allow from this computer*).

---

## 3. Phase 1: Temporary Root (Ghostlock)

* **XDA Thread**: [Temp Root Fire TV Stick 4K 2nd Gen Series (karat/mantra)](https://xdaforums.com/t/temp-root-fire-tv-stick-4k-2nd-gen-series-karat-mantra.4798627/) by pro-me3us / yiy.

1. Download the `ghostlock-karat` archive and extract it on the host PC.
2. Open terminal in the extracted folder and run:
   ```bash
   # Linux / macOS
   ./root.sh

   # Windows
   root.bat
   ```
3. The script will cycle through exploit attempts and may reboot the stick. Once successful, it drops into a root shell prompt:
   ```bash
   root@karat:/ # whoami
   root
   ```

---

## 4. Phase 2: Permanent Bootloader Unlock & TWRP (Amonet)

* **XDA Thread**: [Unlock, Root, TWRP, Unbrick Fire TV Stick 4K 2nd Gen Series (karat/mantra)](https://xdaforums.com/t/unlock-root-twrp-unbrick-fire-tv-stick-4k-2nd-gen-series-karat-mantra.4798951/) by k4y0z / pro-me3us / yiy.

1. Download the `amonet-karat` archive and extract it.
2. While the temporary root shell is active, open a separate terminal on host in the `amonet` directory and run:
   ```bash
   # Linux / macOS
   ./unlock.sh

   # Windows
   unlock.bat
   ```
3. The script flashes the patched bootloader (`lk`), patches `vbmeta` flags (`ro.boot.veritymode=disabled`), and installs TWRP recovery.
4. The device reboots into TWRP recovery (`G072JM... recovery` in `adb devices`). Bootloader unlock is permanent.

---

## 5. Phase 3: Firmware & Magisk Root Tracks

### Track A: SweenWolf Pre-Patched Custom ROM
* **XDA Thread**: [ROM karat Fire OS RS8180_3739 / RS8149_3133 with Light Debloat and Custom Launcher](https://xdaforums.com/t/rom-karat-fire-os-rs8180-3739-rs1849-3133-with-light-debloat-and-custom-launcher.4800114/) by SweenWolf.
* Bundles TrustZone (DRM), pre-disables OTA updates, and embeds KFTV Lite for foremost custom launcher control.

1. In TWRP:
   ```bash
   adb shell twrp sideload
   adb sideload RS8180_3739_V4.zip
   adb shell twrp format data
   adb shell twrp wipe cache
   adb shell twrp wipe dalvik
   adb reboot
   ```
2. Complete initial Amazon OOBE setup, re-enable ADB, install Magisk (`Magisk-31.1.FTV.apk`), reboot into TWRP, and flash Magisk (`adb shell twrp install /sdcard/magisk.zip`).

---

### Track B: Amazon Stock ROM & Hardening
* **XDA References**: Stock 8.1.8.5 bin + TrustZone zip matching thread: [Post #90706957](https://xdaforums.com/t/unlock-root-twrp-unbrick-fire-tv-stick-4k-2nd-gen-series-karat-mantra.4798951/page-5#post-90706957).

1. In TWRP:
   ```bash
   adb push stock.bin /tmp/stock.bin
   adb shell twrp format data
   adb shell twrp install /tmp/stock.bin
   adb shell twrp sideload
   adb sideload RS8185-3885-tz.zip
   adb shell twrp install /sdcard/magisk.zip
   adb shell twrp wipe cache
   adb shell twrp wipe dalvik
   adb reboot
   ```
2. **Network Bypass on Setup (if required)**:
   - When checking for updates, disconnect hotspot/Wi-Fi immediately.
   - When network error appears, press and hold **Back + Menu** on the remote for 2s to activate VoiceView screen reader.
   - Press **Back** once to dismiss VoiceView and bypass the forced update screen directly to account login.
3. **Suppress Background OTA & Blacklisting in Root Shell**:
   ```bash
   adb shell su -c '
   pm disable com.amazon.device.software.ota
   pm clear com.amazon.device.software.ota
   pm disable com.amazon.device.software.ota.override
   pm clear com.amazon.device.software.ota.override
   pm disable com.amazon.tv.forcedotaupdater.v2
   pm clear com.amazon.tv.forcedotaupdater.v2
   pm disable com.fireos.arcus.proxy
   pm clear com.fireos.arcus.proxy
   echo "<?xml version=\"1.0\" encoding=\"utf-8\" standalone=\"yes\" ?><map><set name=\"DenyListKeyPackages\"></set></map>" > /data/system/PackageManagerDenyList
   chmod 444 /data/system/PackageManagerDenyList
   chattr +i /data/system/PackageManagerDenyList
   '
   ```

---

### Track C: Updating / Changing Builds
If TWRP and permanent unlock are already established, you never need temporary root (`ghostlock`) or `amonet` again. Simply boot into TWRP (`adb reboot recovery`), flash your stock `.bin` or custom ROM `.zip`, re-flash Magisk zip (`magisk.zip`), wipe cache/Dalvik, and reboot.

---

## 6. Phase 4: Google Play Store Installation (MindTheGapps Minimal)

Installing unmodified MindTheGapps fails on Fire OS 8 due to partition size exhaustion and `PackageManagerService` crashes.

### The Automated Solution: `patch_mindthegapps.py`
Run the patch script against official [MindTheGapps 11.0.0 ARM ATV](https://androidfilehost.com/?w=files&flid=322935):
```bash
python3 patch_mindthegapps.py \
  --src MindTheGapps-11.0.0-arm-ATV-20230922_081030.zip \
  --dst MindTheGapps-11.0.0-arm-ATV-PlayStore-minimal.zip
```

### What It Does Internally:
1. **Trims ~150 MB of Bloat**: Keeps only Play Store (`Tubesky`), Play Services (`PrebuiltGmsCorePano`), `SssAuthbridge`, `GoogleServicesFramework`, `GoogleOneTimeInitializer`, and permission/sysconfig XMLs.
2. **Auto-Resizes Dynamic Partitions in TWRP**: Patches `update-binary` to resize `system` to `1.24 GB` and `product` to `144 MB` via `lptools` and `resize2fs`, creating additional ext4 block groups with 370+ free inodes.
3. **Pre-Extracts Native Libraries**: Extracts all 17 compressed `.so` files to `lib/arm/` to fix `libconscrypt_gmscore_jni.so` UnsatisfiedLinkError.
4. **Installs Systemless Verifier Resolver**: Bundles `adep_verifier_disabler` Magisk module to resolve the `PackageVerificationReceiver` crash between `com.amazon.adep` and `com.android.vending`.

### Installation:
```bash
adb shell twrp sideload
adb sideload MindTheGapps-11.0.0-arm-ATV-PlayStore-minimal.zip
adb shell twrp wipe cache
adb shell twrp wipe dalvik
adb reboot
```

---

## 7. Essential Magisk Modules & System Tweaks

* **XDA Magisk Module Hub**: [Magisk Modules for FireOS Fixing Local ADB and Launcher Manager](https://xdaforums.com/t/mod-magisk-root-fireos-7-8-magisk-modules-for-fireos-fixing-local-adb-and-launcher-manager.4799301/) by SweenWolf.
* **XDA Passthrough Audio Module**: [Dolby DD+, DTS-HD MA, DTS:X Passthrough](https://xdaforums.com/t/mod-magisk-root-fireos-7-8-dolby-dd-dd-and-dts-hd-ma-dts-x-passthrough-module.4804107/) by signde.
* **XDA Launcher Manager**: [Launcher Manager 2.0.0 (System User)](https://xdaforums.com/t/system-user-fire-cube-stick-tv-tablet-ps7704-fireos7-rs8149-fireos8.4759215/) by SweenWolf.

Install essential modules via root ADB:
```bash
adb push local_adb_patch_fos8.zip /sdcard/Download/
adb push adb_shell_helper_fos.zip /sdcard/Download/
adb push lm_su_helper_fos.zip /sdcard/Download/
adb push kftv_lite_mm.zip /sdcard/Download/

adb shell "su -c '
magisk --install-module /sdcard/Download/local_adb_patch_fos8.zip
magisk --install-module /sdcard/Download/adb_shell_helper_fos.zip
magisk --install-module /sdcard/Download/lm_su_helper_fos.zip
magisk --install-module /sdcard/Download/kftv_lite_mm.zip
'"
adb reboot
```

---

## 8. Hardware Combos & Remote Shortcuts

| Action | Physical Remote Buttons | Duration | Notes |
| :--- | :--- | :--- | :--- |
| **Remote BLE Controller Wipe** | `LEFT` + `MENU (3 lines)` + `BACK` | 12 sec | Clears BLE pairing cache; power cycle stick before reinserting batteries |
| **Hardware Force Restart** | `SELECT (Center)` + `PLAY/PAUSE` | ~5 sec | Hardware reset signal bypassing unresponsive UI |
| **Recovery / Factory Reset Screen**| `BACK` + `RIGHT` | 10 sec | Drops directly into system reset dialog |
| **HDMI Resolution Cycling** | `UP` + `REWIND` | ~5 sec | Cycles 480p, 720p, 1080p, 4K every 10s to recover from black screens |
| **System Developer Tools / X-Ray** | `SELECT` (1s) -> Hold `DOWN` (3-4s) -> Release -> `MENU` | Sequence | Toggles real-time CPU/GPU/thermal monitor overlay |
| **Quick Settings Flyout** | `HOME` | 3-5 sec | Opens quick menu (Profiles, Sleep, Mirroring) |
| **Remote Discovery Pairing** | `HOME` | 10 sec | Forces BLE pairing mode within 3 feet of the stick |
| **VoiceView Screen Reader** | `BACK` + `MENU` | 2 sec | Toggles accessibility voice; used to bypass forced OOBE update screen |

---

## 9. Primary XDA Threads & Source References

1. **Temporary Root (`ghostlock`)**:
   [https://xdaforums.com/t/temp-root-fire-tv-stick-4k-2nd-gen-series-karat-mantra.4798627/](https://xdaforums.com/t/temp-root-fire-tv-stick-4k-2nd-gen-series-karat-mantra.4798627/)
2. **Permanent Unlock, Recovery & Unbrick (`amonet`)**:
   [https://xdaforums.com/t/unlock-root-twrp-unbrick-fire-tv-stick-4k-2nd-gen-series-karat-mantra.4798951/](https://xdaforums.com/t/unlock-root-twrp-unbrick-fire-tv-stick-4k-2nd-gen-series-karat-mantra.4798951/)
3. **Custom ROM (`SweenWolf`)**:
   [https://xdaforums.com/t/rom-karat-fire-os-rs8180-3739-rs1849-3133-with-light-debloat-and-custom-launcher.4800114/](https://xdaforums.com/t/rom-karat-fire-os-rs8180-3739-rs1849-3133-with-light-debloat-and-custom-launcher.4800114/)
4. **Fire OS 7/8 Magisk Modules**:
   [https://xdaforums.com/t/mod-magisk-root-fireos-7-8-magisk-modules-for-fireos-fixing-local-adb-and-launcher-manager.4799301/](https://xdaforums.com/t/mod-magisk-root-fireos-7-8-magisk-modules-for-fireos-fixing-local-adb-and-launcher-manager.4799301/)
5. **Launcher Manager 2.0.0**:
   [https://xdaforums.com/t/system-user-fire-cube-stick-tv-tablet-ps7704-fireos7-rs8149-fireos8.4759215/](https://xdaforums.com/t/system-user-fire-cube-stick-tv-tablet-ps7704-fireos7-rs8149-fireos8.4759215/)
6. **Lossless Audio Passthrough**:
   [https://xdaforums.com/t/mod-magisk-root-fireos-7-8-dolby-dd-dd-and-dts-hd-ma-dts-x-passthrough-module.4804107/](https://xdaforums.com/t/mod-magisk-root-fireos-7-8-dolby-dd-dd-and-dts-hd-ma-dts-x-passthrough-module.4804107/)
7. **Fire TV Firmware Database**:
   [https://ftvdb.com/firetv/firmware/com.amazon.karat.android.os/](https://ftvdb.com/firetv/firmware/com.amazon.karat.android.os/)
8. **MindTheGapps Repository (The LineageOS Project)**:
   [https://gitlab.com/MindTheGapps/vendor_gapps](https://gitlab.com/MindTheGapps/vendor_gapps)
