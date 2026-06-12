#!/usr/bin/env python3
"""
Manual Component Rename Test
Decodes base.apk, renames components, rebuilds, signs, sends to Telegram.
Run on GitHub Actions where apktool/keytool/apksigner are available.
"""

import os, sys, subprocess, shutil, zipfile, struct, random, re, time
import xml.etree.ElementTree as ET
from pathlib import Path

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID  = os.environ.get("ADMIN_ID", "")
WORK_DIR  = "/tmp/manual_rename_test"

def send_msg(text):
    if not BOT_TOKEN or not ADMIN_ID: return
    subprocess.run([
        "curl", "-s", "-X", "POST",
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        "-d", f"chat_id={ADMIN_ID}",
        "-d", "parse_mode=Markdown",
        "-d", f"text={text}"
    ], capture_output=True)

def send_apk(path, caption):
    if not BOT_TOKEN or not ADMIN_ID: return
    with open(path, "rb") as f:
        subprocess.run([
            "curl", "-s", "-X", "POST",
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
            "-F", f"chat_id={ADMIN_ID}",
            "-F", f"document=@{path}",
            "-F", f"caption={caption}"
        ], capture_output=True)

def run(cmd, **kw):
    print(f">> {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.stdout: print(r.stdout[:500])
    if r.stderr: print(r.stderr[:500])
    return r

# ── Setup ─────────────────────────────────────────────────────────────────────
send_msg("🔧 *Manual Component Rename Test* — Starting...")
os.makedirs(WORK_DIR, exist_ok=True)
base_apk = "/home/runner/work/EpicProtector/EpicProtector/base.apk"
if not os.path.exists(base_apk):
    send_msg("❌ base.apk not found")
    sys.exit(1)

# ── Step 1: Decode ────────────────────────────────────────────────────────────
ws = os.path.join(WORK_DIR, "workspace")
shutil.rmtree(ws, ignore_errors=True)
r = run(["apktool", "d", base_apk, "-o", ws, "-f"])
if not os.path.exists(ws):
    send_msg(f"❌ apktool decode failed: {r.stderr[:200]}")
    sys.exit(1)
send_msg("✅ Step 1: Decoded")

# ── Step 2: Rename components ─────────────────────────────────────────────────
manifest_path = os.path.join(ws, "AndroidManifest.xml")
tree = ET.parse(manifest_path)
root = tree.getroot()
pkg  = root.get("package", "")
ns   = "http://schemas.android.com/apk/res/android"

SAFE = ["CoreHandler","BaseModule","DataProcessor","ServiceUnit",
        "NetworkUnit","StorageUnit","SessionUnit","BinderUnit",
        "TaskUnit","WorkerUnit","ProviderUnit","ReceiverUnit"]

# Find launcher
launchers = set()
for act in root.iter("activity"):
    for inf in act.iter("intent-filter"):
        for cat in inf.iter("category"):
            cat_name = cat.get(f"{{{ns}}}name","") or cat.get("android:name","")
            if cat_name == "android.intent.category.LAUNCHER":
                n = act.get(f"{{{ns}}}name","") or act.get("android:name","")
                if n.startswith("."): n = pkg+n
                if n: launchers.add(n)

# Collect components
components = {}
for tag in ["activity","service","receiver","provider"]:
    for elem in root.iter(tag):
        n = elem.get(f"{{{ns}}}name","")
        if not n: continue
        if n.startswith("."): n = pkg+n
        if not n.startswith(pkg): continue
        if n in launchers: continue
        components[n] = tag

# Build rename map
rename_map = {}
for idx, old in enumerate(sorted(components.keys())):
    rename_map[old] = f"{pkg}.{SAFE[idx % len(SAFE)]}{idx:03d}"
    print(f"  {old} → {rename_map[old]}")

send_msg(f"✅ Step 2: Found {len(components)} components to rename\n"
         f"Launcher preserved: {launchers}")

# Update manifest XML
content = open(manifest_path).read()
for old, new in rename_map.items():
    content = content.replace(old, new)
    short = old.replace(pkg,"")
    short_new = new.replace(pkg,"")
    if short != old:
        content = content.replace(f'"{short}"', f'"{short_new}"')
open(manifest_path,"w").write(content)

# Update all smali files
smali_dirs = [Path(ws)/"smali"]
for i in range(2,10):
    d = Path(ws)/f"smali_classes{i}"
    if d.exists(): smali_dirs.append(d)

files_updated = 0
files_renamed = 0
for sd in smali_dirs:
    if not sd.exists(): continue
    for fp in sd.rglob("*.smali"):
        txt = fp.read_text(encoding="utf-8", errors="ignore")
        orig = txt
        for old,new in rename_map.items():
            old_ref = "L"+old.replace(".","/")+";"; new_ref = "L"+new.replace(".","/")+";";
            old_path = old.replace(".","/"       ); new_path = new.replace(".","/"       );
            txt = txt.replace(old_ref,new_ref).replace(old,new).replace(old_path,new_path)
        if txt != orig:
            fp.write_text(txt, encoding="utf-8")
            files_updated += 1

for sd in smali_dirs:
    if not sd.exists(): continue
    for old,new in rename_map.items():
        old_file = sd / (old.replace(".","/")+".smali")
        new_file = sd / (new.replace(".","/")+".smali")
        if old_file.exists():
            new_file.parent.mkdir(parents=True, exist_ok=True)
            old_file.rename(new_file)
            files_renamed += 1

send_msg(f"✅ Step 2 complete: {len(rename_map)} renamed | "
         f"{files_updated} smali updated | {files_renamed} files renamed")

# ── Step 3: Rebuild ───────────────────────────────────────────────────────────
rebuilt = os.path.join(WORK_DIR, "rebuilt.apk")
r = run(["apktool", "b", ws, "-o", rebuilt])
if not os.path.exists(rebuilt):
    send_msg(f"❌ apktool rebuild failed: {r.stderr[:300]}")
    sys.exit(1)
send_msg("✅ Step 3: Rebuilt")

# ── Step 4: Generate keystore ─────────────────────────────────────────────────
ks_path  = os.path.join(WORK_DIR, "test.keystore")
ks_pass  = "TestPass123"
ks_alias = "testkey"
run(["keytool", "-genkeypair",
     "-keystore", ks_path, "-storepass", ks_pass,
     "-keypass",  ks_pass, "-alias", ks_alias,
     "-keyalg",  "RSA", "-keysize", "4096",
     "-validity", "10000",
     "-dname", "CN=Test User, OU=Dev, O=Test Corp, L=Test, ST=Test, C=US"])
send_msg("✅ Step 4: Keystore generated")

# ── Step 5: Zipalign ──────────────────────────────────────────────────────────
aligned = os.path.join(WORK_DIR, "aligned.apk")
run(["zipalign", "-f", "-v", "4", rebuilt, aligned])
send_msg("✅ Step 5: Zipaligned")

# ── Step 6: Sign ──────────────────────────────────────────────────────────────
signed = os.path.join(WORK_DIR, "MANUAL_RENAME_TEST.apk")
shutil.copy2(aligned, signed)
r = run(["apksigner", "sign",
         "--ks", ks_path, "--ks-key-alias", ks_alias,
         "--ks-pass", f"pass:{ks_pass}", "--key-pass", f"pass:{ks_pass}",
         "--v1-signing-enabled", "true",
         "--v2-signing-enabled", "true",
         "--v3-signing-enabled", "true",
         "--out", signed, aligned])
send_msg("✅ Step 6: Signed")

# ── Step 7: Verify rename worked ──────────────────────────────────────────────
with zipfile.ZipFile(signed) as z:
    raw = z.read("AndroidManifest.xml")
    old_names_found = [n for n in rename_map.keys() if n.encode() in raw]
    new_names_found = [n for n in rename_map.values() if n.encode() in raw]

msg = (f"📋 *Rename Verification*\n"
       f"Old names still present: {len(old_names_found)}\n"
       f"New names present: {len(new_names_found)}\n"
       f"{'✅ WORKING' if len(old_names_found)==0 and len(new_names_found)>0 else '❌ NOT WORKING'}")
send_msg(msg)

# ── Step 8: Send APK ──────────────────────────────────────────────────────────
size_mb = os.path.getsize(signed) / (1024*1024)
send_apk(signed, f"🔧 Manual Rename Test APK — {size_mb:.2f} MB\nInstall and test.")
send_msg("✅ Manual test complete — APK delivered.")
print("Done.")
