#!/usr/bin/env python3
"""
patch_mindthegapps.py

Automates the patching of MindTheGapps 11.0.0 ARM ATV for Fire TV Stick 4K Max 2nd Gen (karat) running Fire OS 8 (Android 11).

Key transformations:
1. Strips non-essential GApps (~150 MB saved: Setup Wizard, TalkBack, Assistant, MediaShell, etc.),
   leaving only core Play Store (Tubesky), Play Services (GMS Pano), SssAuthbridge, GSF, OneTimeInitializer,
   and required privapp-permissions / sysconfig XMLs.
2. Extracts compressed native .so libraries into lib/arm/ for PrebuiltGmsCorePano and Tubesky so that
   bionic dlopen can find and load libconscrypt_gmscore_jni.so / libconscrypt_jni.so.
3. Patches META-INF/com/google/android/update-binary:
   - Auto-resizes dynamic partitions (system & product) inside the super partition using lptools + resize2fs if needed.
   - Prevents collision with symlink /mnt/system/system/product -> /product.
   - Bundles and installs the adep_verifier_disabler Magisk module to systemlessly resolve the
     PackageManagerService collision between com.amazon.adep and com.android.vending (PackageVerificationReceiver).
"""

import sys
import os
import io
import zipfile
import argparse

KEEP_FILES = {
    "META-INF/com/google/android/update-binary",
    "META-INF/com/google/android/updater-script",
    "build.prop",
    "toybox",
    "system/addon.d/addond_head",
    "system/addon.d/addond_tail",
    "system/product/etc/permissions/privapp-permissions-atv-product.xml",
    "system/product/etc/permissions/privapp-permissions-google-p.xml",
    "system/product/etc/sysconfig/google-hiddenapi-package-whitelist.xml",
    "system/product/etc/sysconfig/google.xml",
    "system/product/etc/sysconfig/google_atv.xml",
    "system/product/priv-app/PrebuiltGmsCorePano/PrebuiltGmsCorePano.apk",
    "system/product/priv-app/SssAuthbridgePrebuilt/SssAuthbridgePrebuilt.apk",
    "system/product/priv-app/Tubesky/Tubesky.apk",
    "system/system_ext/etc/permissions/privapp-permissions-google-se.xml",
    "system/system_ext/priv-app/GoogleOneTimeInitializer/GoogleOneTimeInitializer.apk",
    "system/system_ext/priv-app/GoogleServicesFramework/GoogleServicesFramework.apk",
}

POST_FS_DATA_SH = """#!/system/bin/sh
MODDIR=${0%/*}
PKG_XML="/data/system/packages.xml"
PR_XML="/data/system/users/0/package-restrictions.xml"
ADEP_PKG="com.amazon.adep"
ADEP_RCVR="com.amazon.adep.nimh.receiver.PackageVerificationReceiver"
VEND_PKG="com.android.vending"
VEND_RCVR="com.google.android.finsky.verifier.impl.PackageVerificationReceiver"

disable_rcvr_in_xml() {
  local pkg="$1"
  local rcvr="$2"
  [ -f "$PR_XML" ] || return 1
  if grep -q "$rcvr" "$PR_XML"; then
    return 0
  fi
  if ! grep -q "<pkg name=\\"$pkg\\"" "$PR_XML"; then
    sed -i "s|</package-restrictions>|    <pkg name=\\"$pkg\\">\\n        <disabled-components>\\n            <item name=\\"$rcvr\\" />\\n        </disabled-components>\\n    </pkg>\\n</package-restrictions>|" "$PR_XML"
  elif grep -q "<pkg name=\\"$pkg\\"[^>]*/>" "$PR_XML"; then
    sed -i "s|<pkg name=\\"$pkg\\"\\([^>]*\\)/>|<pkg name=\\"$pkg\\"\\1>\\n        <disabled-components>\\n            <item name=\\"$rcvr\\" />\\n        </disabled-components>\\n    </pkg>|" "$PR_XML"
  else
    sed -i "/<pkg name=\\"$pkg\\"[^>]*>/a \\        <disabled-components>\\n            <item name=\\"$rcvr\\" />\\n        </disabled-components>" "$PR_XML"
  fi
  chown 1000:1000 "$PR_XML" 2>/dev/null || true
  chmod 0600 "$PR_XML" 2>/dev/null || true
  restorecon "$PR_XML" 2>/dev/null || true
}

if [ -f "$PKG_XML" ] && [ -f "$PR_XML" ]; then
  if grep -q "<package name=\\"$ADEP_PKG\\"" "$PKG_XML"; then
    rm -rf "$MODDIR/system"
    disable_rcvr_in_xml "$ADEP_PKG" "$ADEP_RCVR"
    exit 0
  elif grep -q "<package name=\\"$VEND_PKG\\"" "$PKG_XML"; then
    rm -rf "$MODDIR/system"
    disable_rcvr_in_xml "$VEND_PKG" "$VEND_RCVR"
    exit 0
  fi
fi

mkdir -p "$MODDIR/system/system_ext/priv-app/com.amazon.adep"
touch "$MODDIR/system/system_ext/priv-app/com.amazon.adep/.replace"
"""

SERVICE_SH = """#!/system/bin/sh
MODDIR=${0%/*}
while [ "$(getprop sys.boot_completed)" != "1" ]; do
  sleep 2
done

if [ -d "$MODDIR/system" ]; then
  rm -rf "$MODDIR/system"
  pm disable com.android.vending/com.google.android.finsky.verifier.impl.PackageVerificationReceiver >/dev/null 2>&1 || true
else
  pm disable com.amazon.adep/com.amazon.adep.nimh.receiver.PackageVerificationReceiver >/dev/null 2>&1 || true
  pm enable com.android.vending/com.google.android.finsky.verifier.impl.PackageVerificationReceiver >/dev/null 2>&1 || true
fi
"""

MODULE_PROP = """id=adep_verifier_disabler
name=ADEP PackageVerifier Conflict Resolver
version=v1.1
versionCode=2
author=MindTheGapps-ATV
description=Disables only com.amazon.adep/.nimh.receiver.PackageVerificationReceiver so both Amazon ADEP and Google Play Store coexist without PackageManagerService verifier collision.
"""

OLD_MOUNT_BLOCK = """# Disable rw protection on dynamic partitions
if [ "$DYNAMIC_PARTITIONS" = "true" ]; then
  blockdev --setrw "$SYSTEM_BLOCK"
  if [ -n "$PRODUCT_BLOCK" ]; then
    blockdev --setrw "$PRODUCT_BLOCK"
  fi
  if [ -n "$SYSTEM_EXT_BLOCK" ]; then
    blockdev --setrw "$SYSTEM_EXT_BLOCK"
  fi
fi"""

NEW_MOUNT_BLOCK = """# Disable rw protection and auto-resize dynamic partitions if needed
if [ "$DYNAMIC_PARTITIONS" = "true" ]; then
  if command -v lptools >/dev/null 2>&1; then
    SYS_SIZE=$(blockdev --getsize64 "$SYSTEM_BLOCK" 2>/dev/null || echo 0)
    if [ "$SYS_SIZE" -lt 1300234240 ]; then
      ui_print "Resizing system partition in super..."
      lptools resize system 1300234240
      lptools unmap system
      lptools map system
      SYSTEM_BLOCK=$(find_block "system")
      blockdev --setrw "$SYSTEM_BLOCK"
      e2fsck -fy "$SYSTEM_BLOCK" || true
      resize2fs "$SYSTEM_BLOCK"
    fi
    if [ -n "$PRODUCT_BLOCK" ]; then
      PROD_SIZE=$(blockdev --getsize64 "$PRODUCT_BLOCK" 2>/dev/null || echo 0)
      if [ "$PROD_SIZE" -lt 150994944 ]; then
        ui_print "Resizing product partition in super..."
        lptools resize product 150994944
        lptools unmap product
        lptools map product
        PRODUCT_BLOCK=$(find_block "product")
        blockdev --setrw "$PRODUCT_BLOCK"
        e2fsck -fy "$PRODUCT_BLOCK" || true
        resize2fs "$PRODUCT_BLOCK"
      fi
    fi
  fi
  blockdev --setrw "$SYSTEM_BLOCK"
  if [ -n "$PRODUCT_BLOCK" ]; then
    blockdev --setrw "$PRODUCT_BLOCK"
  fi
  if [ -n "$SYSTEM_EXT_BLOCK" ]; then
    blockdev --setrw "$SYSTEM_EXT_BLOCK"
  fi
fi"""

OLD_COPY_BLOCK = """ui_print "Copying files"
cp --preserve=a -r ./* "${SYSTEM_OUT}/"
if [ -n "$PRODUCT_BLOCK" ]; then
  cp --preserve=a -r ./product/* /product
else
  cp --preserve=a -r ./product/* "${SYSTEM_OUT}/product/"
fi
if [ -n "$SYSTEM_EXT_BLOCK" ]; then
  cp --preserve=a -r ./system_ext/* /system_ext
else
  cp --preserve=a -r ./system_ext/* "${SYSTEM_OUT}/system_ext/"
fi"""

NEW_COPY_BLOCK = f"""ui_print "Installing ADEP PackageVerifier Conflict Resolver Magisk module"
mount /data 2>/dev/null || true
MODPATH="/data/adb/modules/adep_verifier_disabler"
rm -rf "/data/adb/modules/adep_verifier_remover" "$MODPATH"
mkdir -p "$MODPATH"

cat > "$MODPATH/module.prop" << 'EOF'
{MODULE_PROP.strip()}
EOF

cat > "$MODPATH/post-fs-data.sh" << 'EOF'
{POST_FS_DATA_SH.strip()}
EOF

cat > "$MODPATH/service.sh" << 'EOF'
{SERVICE_SH.strip()}
EOF

chown -R 0:0 "$MODPATH"
chmod 0755 "$MODPATH" "$MODPATH/post-fs-data.sh" "$MODPATH/service.sh"
chmod 0644 "$MODPATH/module.prop"
chcon -R u:object_r:system_file:s0 "$MODPATH"
sh "$MODPATH/post-fs-data.sh" 2>/dev/null || true

ui_print "Copying files"
cp --preserve=a -r ./addon.d "${{SYSTEM_OUT}}/"
if [ -n "$PRODUCT_BLOCK" ]; then
  cp --preserve=a -r ./product/* /product/
else
  cp --preserve=a -r ./product/* "${{SYSTEM_OUT}}/product/"
fi
if [ -n "$SYSTEM_EXT_BLOCK" ]; then
  cp --preserve=a -r ./system_ext/* /system_ext/
else
  cp --preserve=a -r ./system_ext/* "${{SYSTEM_OUT}}/system_ext/"
fi"""


def patch_zip(src_zip: str, dst_zip: str):
    if not os.path.exists(src_zip):
        print(f"Error: Source zip not found at {src_zip}", file=sys.stderr)
        sys.exit(1)

    print(f"Opening source zip: {src_zip}")
    with zipfile.ZipFile(src_zip, "r") as zin, zipfile.ZipFile(
        dst_zip, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for info in zin.infolist():
            if info.filename in KEEP_FILES:
                data = zin.read(info.filename)

                # Patch update-binary
                if info.filename == "META-INF/com/google/android/update-binary":
                    text = data.decode("utf-8")
                    if OLD_MOUNT_BLOCK not in text:
                        raise RuntimeError("OLD_MOUNT_BLOCK target missing from update-binary")
                    if OLD_COPY_BLOCK not in text:
                        raise RuntimeError("OLD_COPY_BLOCK target missing from update-binary")

                    text = text.replace(OLD_MOUNT_BLOCK, NEW_MOUNT_BLOCK, 1)
                    text = text.replace(OLD_COPY_BLOCK, NEW_COPY_BLOCK, 1)
                    data = text.encode("utf-8")

                zout.writestr(info, data)

                # Extract and write uncompressed .so libraries for system APKs
                if info.filename in (
                    "system/product/priv-app/PrebuiltGmsCorePano/PrebuiltGmsCorePano.apk",
                    "system/product/priv-app/Tubesky/Tubesky.apk",
                ):
                    base_dir = info.filename.rsplit("/", 1)[0]
                    with zipfile.ZipFile(io.BytesIO(data)) as apk:
                        for apk_info in apk.infolist():
                            if apk_info.filename.startswith("lib/armeabi-v7a/") and apk_info.filename.endswith(".so"):
                                so_name = apk_info.filename.split("/")[-1]
                                out_path = f"{base_dir}/lib/arm/{so_name}"
                                print(f"  Extracted native lib: {out_path}")
                                zout.writestr(out_path, apk.read(apk_info.filename))

    print(f"Successfully generated patched zip: {dst_zip}")


def build_magisk_module_zip(dst_zip: str):
    update_binary_mm = """#!/sbin/sh
umask 022
OUTFD=$2
ZIPFILE=$3
mount /data 2>/dev/null
[ -f /data/adb/magisk/util_functions.sh ] || exit 1
. /data/adb/magisk/util_functions.sh
install_module
exit 0
"""
    customize_sh = """#!/system/bin/sh
set_perm $MODPATH/post-fs-data.sh 0 0 0755
set_perm $MODPATH/service.sh 0 0 0755
sh $MODPATH/post-fs-data.sh 2>/dev/null || true
"""
    print(f"Building standalone Magisk module: {dst_zip}")
    with zipfile.ZipFile(dst_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("META-INF/com/google/android/update-binary", update_binary_mm)
        z.writestr("META-INF/com/google/android/updater-script", "#MAGISK\n")
        z.writestr("module.prop", MODULE_PROP)
        z.writestr("customize.sh", customize_sh)
        z.writestr("post-fs-data.sh", POST_FS_DATA_SH)
        z.writestr("service.sh", SERVICE_SH)
    print(f"Created {dst_zip}")


def main():
    parser = argparse.ArgumentParser(
        description="Patch MindTheGapps 11.0.0 ARM ATV for Fire TV Stick 4K Max 2nd Gen (karat)"
    )
    parser.add_argument(
        "--src",
        default="MindTheGapps-11.0.0-arm-ATV-20230922_081030.zip",
        help="Input official MindTheGapps ATV zip",
    )
    parser.add_argument(
        "--dst",
        default="MindTheGapps-11.0.0-arm-ATV-PlayStore-minimal.zip",
        help="Output patched TWRP sideload zip",
    )
    parser.add_argument(
        "--module-dst",
        default="adep_verifier_disabler_mm.zip",
        help="Output standalone Magisk module zip",
    )
    args = parser.parse_args()

    patch_zip(args.src, args.dst)
    build_magisk_module_zip(args.module_dst)


if __name__ == "__main__":
    main()
