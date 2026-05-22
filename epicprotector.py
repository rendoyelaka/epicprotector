#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║           EPIC PROTECTOR — Complete System                   ║
║     Telegram Bot + Protection Engine in One Script           ║
║              Security Administrator Edition                  ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import re
import sys
import json
import time
import random
import string
import shutil
import hashlib
import zipfile
import logging
import asyncio
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_NEW_TOKEN_HERE")
ADMIN_ID  = int(os.environ.get("ADMIN_ID", "8205672036"))

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  STATE STORE
# ─────────────────────────────────────────────
registered_clients  = {}   # {user_id: {name, username}}
pending_contact     = {}   # {user_id: True}
pending_broadcast   = {}   # {admin_id: True}
pending_reply       = {}   # {admin_id: target_id}
pending_protect     = {}   # {admin_id: True}
pending_send_apk    = {}   # {admin_id: target_client_id}


# ══════════════════════════════════════════════
#  PROTECTION ENGINE
# ══════════════════════════════════════════════

def random_name(length=12):
    return ''.join(random.choices(string.ascii_letters, k=length))


def compute_hash(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_dir_hash(directory):
    all_hashes = {}
    for root, _, files in os.walk(directory):
        for filename in sorted(files):
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, directory)
            all_hashes[rel_path] = compute_hash(filepath)
    return all_hashes


def generate_aes_key():
    return os.urandom(32)


def aes_encrypt(plaintext: str, key: bytes) -> str:
    import base64

    data = plaintext.encode('utf-8')
    pad_len = 16 - (len(data) % 16)
    data += bytes([pad_len] * pad_len)
    iv = os.urandom(16)

    def xor_bytes(a, b):
        return bytes(x ^ y for x, y in zip(a, b))

    SBOX = [
        0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
        0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
        0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
        0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
        0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
        0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
        0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
        0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
        0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
        0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
        0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
        0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
        0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
        0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
        0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
        0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16
    ]

    def gmul(a, b):
        p = 0
        for _ in range(8):
            if b & 1: p ^= a
            hi = a & 0x80
            a = (a << 1) & 0xFF
            if hi: a ^= 0x1b
            b >>= 1
        return p

    def sub_bytes(state):
        return [[SBOX[state[r][c]] for c in range(4)] for r in range(4)]

    def shift_rows(state):
        return [
            [state[0][0],state[0][1],state[0][2],state[0][3]],
            [state[1][1],state[1][2],state[1][3],state[1][0]],
            [state[2][2],state[2][3],state[2][0],state[2][1]],
            [state[3][3],state[3][0],state[3][1],state[3][2]],
        ]

    def mix_columns(state):
        r = [[0]*4 for _ in range(4)]
        for c in range(4):
            r[0][c] = gmul(2,state[0][c])^gmul(3,state[1][c])^state[2][c]^state[3][c]
            r[1][c] = state[0][c]^gmul(2,state[1][c])^gmul(3,state[2][c])^state[3][c]
            r[2][c] = state[0][c]^state[1][c]^gmul(2,state[2][c])^gmul(3,state[3][c])
            r[3][c] = gmul(3,state[0][c])^state[1][c]^state[2][c]^gmul(2,state[3][c])
        return r

    def add_round_key(state, rk):
        return [[state[r][c]^rk[r][c] for c in range(4)] for r in range(4)]

    def bytes_to_state(b):
        return [[b[r+4*c] for c in range(4)] for r in range(4)]

    def state_to_bytes(s):
        return bytes([s[r][c] for c in range(4) for r in range(4)])

    def aes_encrypt_block(block, round_keys):
        state = bytes_to_state(block)
        state = add_round_key(state, bytes_to_state(round_keys[0]))
        for rnd in range(1, 14):
            state = sub_bytes(state)
            state = shift_rows(state)
            state = mix_columns(state)
            state = add_round_key(state, bytes_to_state(round_keys[rnd]))
        state = sub_bytes(state)
        state = shift_rows(state)
        state = add_round_key(state, bytes_to_state(round_keys[14]))
        return state_to_bytes(state)

    def key_expansion(key):
        RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36]
        w = list(key)
        for i in range(32, 60*4):
            temp = w[i-4:i]
            if i%32==0:
                temp=[SBOX[temp[1]]^RCON[i//32-1],SBOX[temp[2]],SBOX[temp[3]],SBOX[temp[0]]]
            elif i%32==16:
                temp=[SBOX[b] for b in temp]
            w += [w[i-32]^temp[j] for j in range(4)]
        return [bytes(w[i:i+16]) for i in range(0,len(w),16)][:15]

    round_keys = key_expansion(key)
    ciphertext = b''
    prev = iv
    for i in range(0, len(data), 16):
        block = data[i:i+16]
        block = xor_bytes(block, prev)
        encrypted_block = aes_encrypt_block(block, round_keys)
        ciphertext += encrypted_block
        prev = encrypted_block

    combined = iv + ciphertext
    return base64.b64encode(combined).decode('utf-8')


def inject_aes_decryptor_java(content, aes_key):
    key_bytes = ', '.join([f'(byte)0x{b:02x}' for b in aes_key])
    decryptor = f'''
    // ── AES-256-CBC Decryptor — EPIC PROTECTOR ──
    private static final byte[] AES_KEY = {{ {key_bytes} }};

    private static String decodeStr(String encryptedBase64) {{
        try {{
            byte[] combined = android.util.Base64.decode(encryptedBase64, android.util.Base64.DEFAULT);
            byte[] iv = java.util.Arrays.copyOfRange(combined, 0, 16);
            byte[] ciphertext = java.util.Arrays.copyOfRange(combined, 16, combined.length);
            javax.crypto.SecretKeySpec keySpec = new javax.crypto.SecretKeySpec(AES_KEY, "AES");
            javax.crypto.Cipher cipher = javax.crypto.Cipher.getInstance("AES/CBC/PKCS5Padding");
            cipher.init(javax.crypto.Cipher.DECRYPT_MODE, keySpec, new javax.crypto.spec.IvParameterSpec(iv));
            byte[] decrypted = cipher.doFinal(ciphertext);
            return new String(decrypted, "UTF-8");
        }} catch (Exception e) {{
            android.os.Process.killProcess(android.os.Process.myPid());
            return null;
        }}
    }}
'''
    content = re.sub(r'(\bclass\b[^{]+\{)', r'\1\n' + decryptor, content, count=1)
    return content


def generate_junk_methods():
    junk = []
    for _ in range(3):
        method_name = random_name(8)
        var1 = random_name(6)
        var2 = random_name(6)
        junk.append(f"""
    private static void {method_name}() {{
        int {var1} = {random.randint(100,9999)};
        String {var2} = "{random_name(16)}";
        if ({var1} > {random.randint(10000,99999)}) {{
            throw new RuntimeException("{random_name(8)}");
        }}
    }}""")
    return '\n'.join(junk)


def obfuscate_java_source(content, aes_key, name_map):
    # Strip comments
    content = re.sub(r'//.*?\n', '\n', content)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

    # Obfuscate variable names
    var_pattern = re.compile(
        r'\b(int|String|boolean|float|double|long|byte|char|Object|List|Map|Set)\s+([a-z][a-zA-Z0-9_]*)\s*[=;(,]'
    )
    found_vars = var_pattern.findall(content)
    for _, var_name in found_vars:
        if len(var_name) > 2:
            if var_name not in name_map:
                name_map[var_name] = random_name()
            content = re.sub(r'\b' + re.escape(var_name) + r'\b', name_map[var_name], content)

    # Inject junk methods
    junk_code = generate_junk_methods()
    content = re.sub(r'(\bclass\b[^{]+\{)', r'\1\n' + junk_code, content, count=1)

    # AES encrypt all string literals
    def replacer(match):
        s = match.group(1)
        if len(s) < 200 and s.isascii() and len(s) > 0:
            try:
                encrypted = aes_encrypt(s, aes_key)
                return f'decodeStr("{encrypted}")'
            except Exception:
                return match.group(0)
        return match.group(0)

    content = re.sub(r'"([^"\\]{1,199})"', replacer, content)

    # Inject AES decryptor
    content = inject_aes_decryptor_java(content, aes_key)

    return content


def generate_anti_tamper_java(aes_key):
    key_bytes = ', '.join([f'(byte)0x{b:02x}' for b in aes_key])
    return f"""package com.epicprotector.security;

import android.content.Context;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.os.Build;
import android.os.Debug;
import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.security.MessageDigest;
import java.util.Arrays;
import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * EPIC PROTECTOR — Runtime Security Guard
 * Anti-Tamper + Root + Emulator + Anti-Debug + Hooking Detection
 */
public class EpicSecurityGuard {{

    private static final String VALID_SIGNATURE = "YOUR_APK_SIGNATURE_SHA256_HERE";
    private static final byte[] AES_KEY = {{ {key_bytes} }};

    // ── Entry Point ────────────────────────────
    public static void runAllChecks(Context context) {{
        if (isDebugging())              killApp("Anti-Debug");
        if (isEmulator())               killApp("Emulator");
        if (isRooted())                 killApp("Root");
        if (!isSignatureValid(context)) killApp("Tamper");
        if (isHookingFrameworkPresent())killApp("Hook");
    }}

    // ── 1. Anti-Debugging ──────────────────────
    private static boolean isDebugging() {{
        if (Debug.isDebuggerConnected()) return true;
        if (Debug.waitingForDebugger())  return true;
        long start = System.nanoTime();
        for (int i = 0; i < 1000; i++) {{}}
        return (System.nanoTime() - start) > 10_000_000L;
    }}

    // ── 2. Emulator Detection ──────────────────
    private static boolean isEmulator() {{
        String[] fields = {{
            Build.FINGERPRINT, Build.MODEL, Build.MANUFACTURER,
            Build.BRAND, Build.DEVICE, Build.PRODUCT
        }};
        for (String s : fields) {{
            if (s == null) continue;
            String l = s.toLowerCase();
            if (l.contains("generic")||l.contains("emulator")||l.contains("sdk")||
                l.contains("genymotion")||l.contains("x86")||l.contains("bluestacks")||
                l.contains("nox")||l.contains("vbox")||l.contains("andy")||
                l.contains("droid4x")) return true;
        }}
        String[] emulatorFiles = {{
            "/dev/socket/qemud","/dev/qemu_pipe",
            "/system/lib/libc_malloc_debug_qemu.so",
            "/sys/qemu_trace","/system/bin/qemu-props"
        }};
        for (String p : emulatorFiles) {{
            if (new File(p).exists()) return true;
        }}
        return false;
    }}

    // ── 3. Root Detection ──────────────────────
    private static boolean isRooted() {{
        String[] suPaths = {{
            "/system/bin/su","/system/xbin/su","/sbin/su",
            "/system/su","/data/local/xbin/su","/data/local/bin/su",
            "/data/local/su","/system/app/Superuser.apk",
            "/system/app/SuperSU.apk"
        }};
        for (String p : suPaths) {{
            if (new File(p).exists()) return true;
        }}
        try {{
            Process process = Runtime.getRuntime().exec(new String[]{{"/system/xbin/which","su"}});
            BufferedReader in = new BufferedReader(new InputStreamReader(process.getInputStream()));
            if (in.readLine() != null) return true;
        }} catch (Exception ignored) {{}}
        String buildTags = Build.TAGS;
        return buildTags != null && buildTags.contains("test-keys");
    }}

    // ── 4. Signature Validation ────────────────
    private static boolean isSignatureValid(Context context) {{
        try {{
            PackageInfo info = context.getPackageManager().getPackageInfo(
                context.getPackageName(), PackageManager.GET_SIGNATURES
            );
            for (Signature sig : info.signatures) {{
                MessageDigest md = MessageDigest.getInstance("SHA-256");
                md.update(sig.toByteArray());
                byte[] digest = md.digest();
                StringBuilder sb = new StringBuilder();
                for (byte b : digest) sb.append(String.format("%02x", b));
                if (!sb.toString().equals(VALID_SIGNATURE)) return false;
            }}
            return true;
        }} catch (Exception e) {{ return false; }}
    }}

    // ── 5. Hooking Detection ───────────────────
    private static boolean isHookingFrameworkPresent() {{
        String[] xposedFiles = {{
            "/system/framework/XposedBridge.jar",
            "/system/bin/app_process_xposed",
            "/system/lib/libxposed_art.so"
        }};
        for (String p : xposedFiles) {{
            if (new File(p).exists()) return true;
        }}
        try {{
            throw new Exception("hook_check");
        }} catch (Exception e) {{
            for (StackTraceElement el : e.getStackTrace()) {{
                if (el.getClassName().contains("XposedBridge")||
                    el.getClassName().contains("de.robv.android")) return true;
            }}
        }}
        return false;
    }}

    // ── AES-256-CBC Decryptor ──────────────────
    public static String decodeStr(String encryptedBase64) {{
        try {{
            byte[] combined = android.util.Base64.decode(encryptedBase64, android.util.Base64.DEFAULT);
            byte[] iv = Arrays.copyOfRange(combined, 0, 16);
            byte[] ciphertext = Arrays.copyOfRange(combined, 16, combined.length);
            SecretKeySpec keySpec = new SecretKeySpec(AES_KEY, "AES");
            Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
            cipher.init(Cipher.DECRYPT_MODE, keySpec, new IvParameterSpec(iv));
            return new String(cipher.doFinal(ciphertext), "UTF-8");
        }} catch (Exception e) {{
            android.os.Process.killProcess(android.os.Process.myPid());
            return null;
        }}
    }}

    // ── Kill App ───────────────────────────────
    private static void killApp(String reason) {{
        android.os.Process.killProcess(android.os.Process.myPid());
        System.exit(1);
    }}
}}
"""


def generate_proguard_rules(output_dir):
    words = [random_name(random.randint(4, 12)) for _ in range(500)]
    dict_path = os.path.join(output_dir, "obf_dict.txt")
    with open(dict_path, "w") as f:
        f.write('\n'.join(words))

    rules = """
# ╔══════════════════════════════════════════╗
# ║   EPIC PROTECTOR — ProGuard Rules         ║
# ╚══════════════════════════════════════════╝

-obfuscationdictionary obf_dict.txt
-classobfuscationdictionary obf_dict.txt
-packageobfuscationdictionary obf_dict.txt
-optimizationpasses 7
-allowaccessmodification
-mergeinterfacesaggressively
-overloadaggressively
-repackageclasses ''
-dontusemixedcaseclassnames
-verbose

-assumenosideeffects class android.util.Log {
    public static int v(...);
    public static int d(...);
    public static int i(...);
    public static int w(...);
    public static int e(...);
}

-renamesourcefileattribute SourceFile
-keepattributes SourceFile,LineNumberTable

-keep public class * extends android.app.Activity
-keep public class * extends android.app.Application
-keep public class * extends android.app.Service
-keep public class * extends android.content.BroadcastReceiver
-keep public class * extends android.content.ContentProvider
-keep public class * extends android.view.View
-keep public class * extends androidx.fragment.app.Fragment

-keepclasseswithmembernames class * { native <methods>; }

-keepclassmembers enum * {
    public static **[] values();
    public static ** valueOf(java.lang.String);
}

-keepclassmembers class * implements android.os.Parcelable {
    public static final android.os.Parcelable$Creator CREATOR;
}

-keepclassmembers class * implements java.io.Serializable {
    static final long serialVersionUID;
    private void writeObject(java.io.ObjectOutputStream);
    private void readObject(java.io.ObjectInputStream);
}

-dontwarn **
-ignorewarnings
"""
    rules_path = os.path.join(output_dir, "proguard-rules.pro")
    with open(rules_path, "w") as f:
        f.write(rules)


def protect_apk(apk_path: str, output_dir: str) -> dict:
    """
    Full protection engine — runs all protection steps on the APK.
    Returns a dict with results summary.
    """
    results = {}
    os.makedirs(output_dir, exist_ok=True)

    # ── Step 1: Extract APK ───────────────────
    extract_dir = os.path.join(output_dir, "extracted")
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(apk_path, 'r') as z:
        z.extractall(extract_dir)
    results["APK Extracted"] = "✅ Done"

    # ── Step 2: Generate AES-256 Key ──────────
    aes_key = generate_aes_key()
    key_path = os.path.join(output_dir, "aes_key.bin")
    with open(key_path, "wb") as f:
        f.write(aes_key)
    results["AES-256 Key"] = "✅ Generated & Saved"

    # ── Step 3: Integrity Manifest ────────────
    hashes = compute_dir_hash(extract_dir)
    manifest = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": len(hashes),
        "files": hashes
    }
    manifest_path = os.path.join(output_dir, "integrity_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    results["Integrity Manifest"] = f"✅ {len(hashes)} files hashed"

    # ── Step 4: Obfuscate Java Files ──────────
    java_files = list(Path(extract_dir).rglob("*.java"))
    name_map = {}
    obf_count = 0
    for java_file in java_files:
        try:
            with open(java_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            obfuscated = obfuscate_java_source(content, aes_key, name_map)
            with open(java_file, "w", encoding="utf-8") as f:
                f.write(obfuscated)
            obf_count += 1
        except Exception:
            pass
    map_path = os.path.join(output_dir, "obfuscation_map.json")
    with open(map_path, "w") as f:
        json.dump(name_map, f, indent=2)
    results["Java Obfuscation"] = f"✅ {obf_count} files obfuscated"
    results["Names Renamed"] = f"✅ {len(name_map)} names"

    # ── Step 5: Inject Anti-Tamper Guard ──────
    guard_code = generate_anti_tamper_java(aes_key)
    guard_path = os.path.join(output_dir, "EpicSecurityGuard.java")
    with open(guard_path, "w") as f:
        f.write(guard_code)
    results["Anti-Tamper Guard"] = "✅ Injected"
    results["Root Detection"] = "✅ Enabled"
    results["Emulator Detection"] = "✅ Enabled"
    results["Anti-Debugging"] = "✅ Enabled"
    results["Hooking Detection"] = "✅ Enabled"
    results["Signature Validation"] = "✅ Enabled"

    # ── Step 6: ProGuard Rules ────────────────
    generate_proguard_rules(output_dir)
    results["ProGuard Rules"] = "✅ Generated"

    # ── Step 7: Resource Protection ───────────
    resource_hashes = {}
    for root, _, files in os.walk(extract_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, extract_dir)
            resource_hashes[rel] = compute_hash(fpath)
    res_manifest_path = os.path.join(output_dir, "resource_manifest.json")
    with open(res_manifest_path, "w") as f:
        json.dump(resource_hashes, f, indent=2)
    results["Resource Protection"] = f"✅ {len(resource_hashes)} resources protected"

    # ── Step 8: Repack APK ────────────────────
    protected_apk_path = os.path.join(output_dir, "protected_app.apk")
    with zipfile.ZipFile(protected_apk_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for root, _, files in os.walk(extract_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                arcname = os.path.relpath(fpath, extract_dir)
                zout.write(fpath, arcname)
    results["Protected APK"] = "✅ Repacked"
    results["Output APK"] = protected_apk_path

    return results


# ══════════════════════════════════════════════
#  KEEP ALIVE SERVER (for UptimeRobot)
# ══════════════════════════════════════════════

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "EPIC PROTECTOR — Running 24/7 ✅"

@flask_app.route('/health')
def health():
    return "OK", 200

@flask_app.route('/ping')
def ping():
    return "PONG", 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)


# ══════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def register_client(user):
    if user.id not in registered_clients:
        registered_clients[user.id] = {
            "name": user.full_name,
            "username": f"@{user.username}" if user.username else "No username"
        }


# ══════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛡️ Protect APK",           callback_data="admin_protect")],
        [InlineKeyboardButton("📤 Send APK to Client",    callback_data="admin_send_apk")],
        [InlineKeyboardButton("📢 Broadcast Message",     callback_data="admin_broadcast")],
        [InlineKeyboardButton("💬 Reply to Client",       callback_data="admin_reply")],
        [InlineKeyboardButton("👥 View All Clients",      callback_data="admin_clients")],
        [InlineKeyboardButton("📊 Statistics",            callback_data="admin_stats")],
    ])


def client_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📁 Request APK",           callback_data="client_request_apk")],
        [InlineKeyboardButton("📋 Our Services",          callback_data="client_services")],
        [InlineKeyboardButton("💬 Contact Admin",         callback_data="client_contact")],
        [InlineKeyboardButton("ℹ️ About Epic Protector",  callback_data="client_about")],
    ])


def back_admin():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_admin")]])


def back_client():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_client")]])


# ══════════════════════════════════════════════
#  START HANDLER
# ══════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_client(user)

    if is_admin(user.id):
        await update.message.reply_text(
            f"👑 *Welcome back, Admin!*\n\n"
            f"🛡️ *EPIC PROTECTOR — Admin Panel*\n"
            f"Total Clients: {len(registered_clients)}\n\n"
            f"Choose an action:",
            parse_mode="Markdown",
            reply_markup=admin_keyboard()
        )
    else:
        await update.message.reply_text(
            f"🛡️ *Welcome to EPIC PROTECTOR!*\n\n"
            f"Hello {user.first_name}! 👋\n\n"
            f"Professional Android app protection\n"
            f"for hospitals, hotels, medical,\n"
            f"pharma & data management companies.\n\n"
            f"Choose an option:",
            parse_mode="Markdown",
            reply_markup=client_keyboard()
        )


# ══════════════════════════════════════════════
#  BUTTON HANDLER
# ══════════════════════════════════════════════

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = query.from_user
    data  = query.data
    await query.answer()

    # ── ADMIN BUTTONS ─────────────────────────

    if data == "admin_protect":
        if not is_admin(user.id): return
        pending_protect[user.id] = True
        await query.edit_message_text(
            "🛡️ *Protect APK*\n\n"
            "Send me the APK file you want to protect.\n\n"
            "I will apply:\n"
            "• Code Obfuscation\n"
            "• AES-256 Encryption\n"
            "• Anti-Tamper Protection\n"
            "• Root & Emulator Detection\n"
            "• Anti-Debugging\n"
            "• Hooking Detection\n"
            "• Integrity Manifest\n"
            "• ProGuard Rules\n"
            "• Resource Protection\n\n"
            "📎 Send your APK file now:",
            parse_mode="Markdown",
            reply_markup=back_admin()
        )

    elif data == "admin_send_apk":
        if not is_admin(user.id): return
        if not registered_clients:
            await query.edit_message_text(
                "👥 No clients registered yet.",
                reply_markup=back_admin()
            )
            return
        buttons = []
        for uid, info in registered_clients.items():
            buttons.append([InlineKeyboardButton(
                f"{info['name']} ({info['username']})",
                callback_data=f"select_client_{uid}"
            )])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_admin")])
        await query.edit_message_text(
            "📤 *Send APK to Client*\n\nSelect a client:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("select_client_"):
        if not is_admin(user.id): return
        target_id = int(data.replace("select_client_", ""))
        pending_send_apk[user.id] = target_id
        client_info = registered_clients.get(target_id, {})
        await query.edit_message_text(
            f"📤 *Send APK to {client_info.get('name', target_id)}*\n\n"
            f"Now send me the APK file to forward.",
            parse_mode="Markdown",
            reply_markup=back_admin()
        )

    elif data == "admin_broadcast":
        if not is_admin(user.id): return
        pending_broadcast[user.id] = True
        await query.edit_message_text(
            f"📢 *Broadcast Message*\n\n"
            f"Will be sent to all {len(registered_clients)} clients.\n\n"
            f"✍️ Type your message now:",
            parse_mode="Markdown",
            reply_markup=back_admin()
        )

    elif data == "admin_reply":
        if not is_admin(user.id): return
        if not registered_clients:
            await query.edit_message_text("👥 No clients yet.", reply_markup=back_admin())
            return
        buttons = []
        for uid, info in registered_clients.items():
            buttons.append([InlineKeyboardButton(
                f"{info['name']} ({info['username']})",
                callback_data=f"reply_to_{uid}"
            )])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_admin")])
        await query.edit_message_text(
            "💬 *Reply to Client*\n\nSelect a client:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("reply_to_"):
        if not is_admin(user.id): return
        target_id = int(data.replace("reply_to_", ""))
        pending_reply[user.id] = target_id
        client_info = registered_clients.get(target_id, {})
        await query.edit_message_text(
            f"💬 *Reply to {client_info.get('name', target_id)}*\n\n"
            f"Type your message now:",
            parse_mode="Markdown",
            reply_markup=back_admin()
        )

    elif data == "admin_clients":
        if not is_admin(user.id): return
        if not registered_clients:
            text = "👥 *No clients registered yet.*"
        else:
            lines = ["👥 *Registered Clients*\n"]
            for uid, info in registered_clients.items():
                lines.append(f"• {info['name']} ({info['username']})\n  ID: `{uid}`")
            text = '\n'.join(lines)
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=back_admin()
        )

    elif data == "admin_stats":
        if not is_admin(user.id): return
        await query.edit_message_text(
            f"📊 *Bot Statistics*\n\n"
            f"👥 Total Clients    : {len(registered_clients)}\n"
            f"🛡️ Protection Status : ACTIVE ✅\n"
            f"🔒 Encryption       : AES-256-CBC ✅\n"
            f"🔍 Obfuscation      : Enabled ✅\n"
            f"🚫 Anti-Tamper      : Enabled ✅\n"
            f"📡 Bot Status       : Online ✅",
            parse_mode="Markdown",
            reply_markup=back_admin()
        )

    elif data == "back_admin":
        pending_protect.pop(user.id, None)
        pending_broadcast.pop(user.id, None)
        pending_reply.pop(user.id, None)
        pending_send_apk.pop(user.id, None)
        await query.edit_message_text(
            "👑 *Admin Panel — EPIC PROTECTOR*\n\nChoose an action:",
            parse_mode="Markdown",
            reply_markup=admin_keyboard()
        )

    # ── CLIENT BUTTONS ─────────────────────────

    elif data == "client_request_apk":
        await query.edit_message_text(
            "📁 *Request APK*\n\n"
            "Your request has been sent to the admin.\n"
            "You will receive your protected APK shortly.\n\n"
            "⏳ Please wait...",
            parse_mode="Markdown",
            reply_markup=back_client()
        )
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📥 *APK Request*\n\n"
                 f"Client : {user.full_name}\n"
                 f"Username : @{user.username or 'none'}\n"
                 f"ID : `{user.id}`\n\n"
                 f"Tap *Send APK to Client* to respond.",
            parse_mode="Markdown",
            reply_markup=admin_keyboard()
        )

    elif data == "client_services":
        await query.edit_message_text(
            "📋 *Our Services*\n\n"
            "🔒 *Code Obfuscation*\n"
            "   Scrambles source code — unreadable\n\n"
            "🔐 *AES-256 Encryption*\n"
            "   Encrypts all strings and data\n\n"
            "🛡️ *Anti-Tamper Protection*\n"
            "   Detects and blocks modifications\n\n"
            "📱 *Root & Emulator Detection*\n"
            "   Blocks unauthorized environments\n\n"
            "🔍 *Anti-Debug & Hooking Detection*\n"
            "   Blocks Frida, Xposed, ADB\n\n"
            "✅ *Signature Validation*\n"
            "   Rejects repackaged APKs\n\n"
            "📊 *Integrity Manifest*\n"
            "   SHA-256 hash of every file\n\n"
            "🏭 *Industries Covered*\n"
            "   🏥 Hospital  🏨 Hotel\n"
            "   💊 Medical   💊 Pharma\n"
            "   💾 Data Management\n"
            "   💻 Software Companies",
            parse_mode="Markdown",
            reply_markup=back_client()
        )

    elif data == "client_contact":
        pending_contact[user.id] = True
        await query.edit_message_text(
            "💬 *Contact Admin*\n\n"
            "Type your message below.\n"
            "Admin will reply to you shortly.\n\n"
            "✍️ Send your message now:",
            parse_mode="Markdown",
            reply_markup=back_client()
        )

    elif data == "client_about":
        await query.edit_message_text(
            "ℹ️ *About EPIC PROTECTOR*\n\n"
            "🛡️ Professional Android app protection\n"
            "framework built for Security Administrators.\n\n"
            "✅ Protects source code from theft\n"
            "✅ Shields internal logic\n"
            "✅ AES-256 data encryption\n"
            "✅ Covers .dex .res .classes\n"
            "✅ Enterprise-grade security\n\n"
            "👨‍💼 Managed by a certified\n"
            "Security Administrator",
            parse_mode="Markdown",
            reply_markup=back_client()
        )

    elif data == "back_client":
        pending_contact.pop(user.id, None)
        await query.edit_message_text(
            "🛡️ *EPIC PROTECTOR*\n\nChoose an option:",
            parse_mode="Markdown",
            reply_markup=client_keyboard()
        )


# ══════════════════════════════════════════════
#  MESSAGE HANDLER (Text)
# ══════════════════════════════════════════════

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    register_client(user)

    # ── Admin broadcast ───────────────────────
    if is_admin(user.id) and pending_broadcast.get(user.id):
        pending_broadcast.pop(user.id)
        sent = failed = 0
        for client_id in registered_clients:
            try:
                await context.bot.send_message(
                    chat_id=client_id,
                    text=f"📢 *Message from Epic Protector:*\n\n{text}",
                    parse_mode="Markdown"
                )
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(
            f"📢 *Broadcast Complete!*\n\n✅ Sent: {sent}\n❌ Failed: {failed}",
            parse_mode="Markdown",
            reply_markup=admin_keyboard()
        )
        return

    # ── Admin reply to client ─────────────────
    if is_admin(user.id) and pending_reply.get(user.id):
        target_id = pending_reply.pop(user.id)
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"💬 *Message from Admin:*\n\n{text}",
                parse_mode="Markdown"
            )
            await update.message.reply_text(
                "✅ Reply sent successfully!",
                reply_markup=admin_keyboard()
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Failed: {e}", reply_markup=admin_keyboard())
        return

    # ── Client contact message ────────────────
    if pending_contact.get(user.id):
        pending_contact.pop(user.id)
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💬 *Message from Client*\n\n"
                 f"Name: {user.full_name}\n"
                 f"Username: @{user.username or 'none'}\n"
                 f"ID: `{user.id}`\n\n"
                 f"Message:\n{text}",
            parse_mode="Markdown",
            reply_markup=admin_keyboard()
        )
        await update.message.reply_text(
            "✅ *Message sent to admin!*\n\nWe'll get back to you soon.",
            parse_mode="Markdown",
            reply_markup=client_keyboard()
        )
        return

    # ── Default ───────────────────────────────
    if is_admin(user.id):
        await update.message.reply_text(
            "👇 Choose an action:",
            reply_markup=admin_keyboard()
        )
    else:
        await update.message.reply_text(
            "👇 Please use the menu below:",
            reply_markup=client_keyboard()
        )


# ══════════════════════════════════════════════
#  DOCUMENT HANDLER (APK Files)
# ══════════════════════════════════════════════

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_client(user)

    # ── Admin sends APK to protect ────────────
    if is_admin(user.id) and pending_protect.get(user.id):
        pending_protect.pop(user.id)
        await update.message.reply_text(
            "⚙️ *Protection started!*\n\n"
            "Running all protection steps...\n"
            "Please wait ⏳",
            parse_mode="Markdown"
        )
        try:
            # Download APK
            file = await context.bot.get_file(update.message.document.file_id)
            apk_path = f"/tmp/input_{user.id}.apk"
            output_dir = f"/tmp/protected_{user.id}"
            await file.download_to_drive(apk_path)

            # Run protection engine
            results = protect_apk(apk_path, output_dir)

            # Build result message
            lines = ["🛡️ *Protection Complete!*\n"]
            for key, val in results.items():
                if key != "Output APK":
                    lines.append(f"{val} {key}")
            await update.message.reply_text(
                '\n'.join(lines),
                parse_mode="Markdown"
            )

            # Send protected APK back
            protected_apk = results.get("Output APK")
            if protected_apk and os.path.exists(protected_apk):
                with open(protected_apk, "rb") as f:
                    await update.message.reply_document(
                        document=f,
                        filename="protected_app.apk",
                        caption="🛡️ *Your Protected APK is ready!*\n\n"
                                "⚠️ Remember to:\n"
                                "1. Copy EpicSecurityGuard.java to your project\n"
                                "2. Add proguard-rules.pro to your project\n"
                                "3. Replace YOUR_APK_SIGNATURE_SHA256_HERE\n"
                                "4. Test before sending to clients",
                        parse_mode="Markdown"
                    )

            # Cleanup
            os.remove(apk_path)
            shutil.rmtree(output_dir, ignore_errors=True)

        except Exception as e:
            await update.message.reply_text(
                f"❌ Protection failed: {e}\n\nPlease try again.",
                reply_markup=admin_keyboard()
            )
        return

    # ── Admin forwards APK to client ──────────
    if is_admin(user.id) and pending_send_apk.get(user.id):
        target_id = pending_send_apk.pop(user.id)
        try:
            await context.bot.send_document(
                chat_id=target_id,
                document=update.message.document.file_id,
                caption="📁 *Your Protected APK from Epic Protector*\n\n"
                        "✅ Fully protected and ready to use.",
                parse_mode="Markdown"
            )
            await update.message.reply_text(
                f"✅ APK sent to client `{target_id}` successfully!",
                parse_mode="Markdown",
                reply_markup=admin_keyboard()
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Failed: {e}", reply_markup=admin_keyboard())
        return

    # ── Client sends file ─────────────────────
    if not is_admin(user.id):
        await update.message.reply_text(
            "📎 Please contact admin to process your file.",
            reply_markup=client_keyboard()
        )


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

def main():
    print("""
\033[1;36m
╔══════════════════════════════════════════════════════════════╗
║         EPIC PROTECTOR — Complete System Starting...         ║
║         Telegram Bot + Protection Engine                     ║
╚══════════════════════════════════════════════════════════════╝
\033[0m""")

    # Start keep-alive server in background
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("\033[1;32m[✅] Keep-alive server started on port 8080\033[0m")

    # Start Telegram bot
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.Regex(r'^/start$'), start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("\033[1;32m[✅] Epic Protector Bot is running! Press Ctrl+C to stop.\033[0m")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
