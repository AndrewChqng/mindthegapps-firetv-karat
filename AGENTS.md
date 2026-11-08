# AGENTS.md

Instructions, operational architecture, and background context for autonomous AI coding agents working on or maintaining this codebase.

---

## 1. System Overview & Hardware Architecture

* **Device**: Amazon Fire TV Stick 4K Max 2nd Gen (`karat` / `AFTKRT`).
* **Platform**: MediaTek MT8696 (Quad-Core ARM Cortex-A55, 32-bit `armeabi-v7a` userland on 64-bit kernel).
* **OS**: Fire OS 8 (based on Android 11 / API 30).
* **Storage Layout**:
  - MMC device: `/dev/block/mmcblk0`
  - Dynamic partition container: `/dev/block/by-name/super` (`1,625,292,800` bytes / ~`1.51 GB`).
  - Logical mapped subpartitions in device-mapper:
    - `/dev/block/mapper/system` (`dm-0`)
    - `/dev/block/mapper/vendor` (`dm-1`)
    - `/dev/block/mapper/product` (`dm-2`)
    - `/dev/block/mapper/userdata` (`dm-3` / `/data`, 12 GB ext4).

---

## 2. Core Failure Modes & Invariants

When creating, updating, or debugging GApps packages for Fire OS 8, agents MUST uphold the following rules:

### A. The Inode and Ext4 Block Group Ceiling
* `/product` on stock Fire OS 8 is created with only `16 MB` (`4,094` 4K-blocks, `368` inodes).
* Ext4 allocates inodes per block group (`32,768` 4K-blocks per group).
* Simply resizing `product` to e.g. `30 MB` does NOT increase inode count because it remains in block group 0.
* **Invariant**: `product` MUST be resized past `128 MB` (e.g. `144 MB` / `150,994,944` bytes) using `lptools resize` + `resize2fs`. This forces ext4 to create block group 1, expanding inode capacity to `736` inodes (`371` free).

### B. The PackageVerificationReceiver Collision
* In AOSP Android 11 `PackageManagerService`:
  ```java
  List<ResolveInfo> receivers = queryIntentReceiversInternal(
      new Intent(Intent.ACTION_PACKAGE_NEEDS_VERIFICATION),
      "application/vnd.android.package-archive",
      MATCH_SYSTEM_ONLY | MATCH_DIRECT_BOOT_AWARE | MATCH_DIRECT_BOOT_UNAWARE,
      ...
  );
  if (receivers.size() != 1) {
      throw new RuntimeException("There must be exactly one verifier; found " + receivers);
  }
  ```
* `com.amazon.adep` (`com.amazon.adep.nimh.receiver.PackageVerificationReceiver`) and `com.android.vending` (`com.google.android.finsky.verifier.impl.PackageVerificationReceiver`) both register for this intent filter.
* **Resolution Rule**:
  - Do NOT delete `/system/system_ext/priv-app/com.amazon.adep` permanently unless requested by user.
  - Use the bundled Magisk module `adep_verifier_disabler`:
    - `post-fs-data.sh` edits `/data/system/users/0/package-restrictions.xml` to mark `com.amazon.adep.nimh.receiver.PackageVerificationReceiver` as disabled before `system_server` boots.
    - If `/data/system/packages.xml` is missing (fresh wipe), temporarily use `.replace` on `com.amazon.adep` for first boot, then switch to component disabling once `packages.xml` is created.

### C. Native Bionic Library Loading (.so extraction)
* Modern Android bionic `dlopen` requires uncompressed, page-aligned `.so` files to `mmap` directly from APKs.
* In MindTheGapps, `PrebuiltGmsCorePano.apk` and `Tubesky.apk` store `.so` files with `compression=DEFLATE` (`method=8`).
* Consequently, `dlopen("libconscrypt_gmscore_jni.so")` fails with `UnsatisfiedLinkError`.
* **Invariant**: Any custom GApps package for this platform MUST extract all `.so` files to:
  - `system/product/priv-app/PrebuiltGmsCorePano/lib/arm/*.so`
  - `system/product/priv-app/Tubesky/lib/arm/*.so`
  - Permissions MUST be `0755` for directories, `0644` for files, and context `u:object_r:system_file:s0`.

### D. Symlink Overwrite Collision in update-binary
* On `karat`, `/mnt/system/system/product` is a symlink pointing to `/product`.
* Stock MindTheGapps `update-binary` issues `cp --preserve=a -r ./* "${SYSTEM_OUT}/"`, which tries to overwrite the symlink with directory `./product`, causing either failed writes or circular mount confusion.
* **Invariant**: `update-binary` MUST copy `./addon.d` to `${SYSTEM_OUT}/addon.d/`, and selectively copy `./product/*` directly to `/product/` and `./system_ext/*` to `/system_ext/` (or `${SYSTEM_OUT}/system_ext/`).

---

## 3. Directory Layout & Key Files

* `patch_mindthegapps.py`: Main automated transformation CLI.
* `README.md`: Human-facing documentation, prerequisites, and build steps.
* `AGENTS.md`: Technical specification, runtime invariants, and architecture guide (this file).

---

## 4. Verification & Testing Commands

To verify a newly patched package on a connected device in TWRP:

```bash
# 1. Check recovery device status
adb devices

# 2. Start TWRP sideload
adb shell twrp sideload
adb sideload MindTheGapps-11.0.0-arm-ATV-PlayStore-minimal.zip

# 3. Verify partitions and filesystem integrity in TWRP
adb shell "e2fsck -fn /dev/block/mapper/system; e2fsck -fn /dev/block/mapper/product"

# 4. Wipe caches and reboot
adb shell twrp wipe cache
adb shell twrp wipe dalvik
adb reboot

# 5. Verify system boot and crash buffer
adb wait-for-device
adb shell "while [ \"\$(getprop sys.boot_completed)\" != '1' ]; do sleep 2; done; echo BOOT_OK"
adb logcat -d -b crash

# 6. Verify Google Play Store launch
adb shell am start -n com.android.vending/com.google.android.finsky.tvmainactivity.TvMainActivity
```
