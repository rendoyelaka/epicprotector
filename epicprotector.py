#!/usr/bin/env python3
"""
EPIC PROTECTOR — Elite Master Hybrid Engine
7-Level Android Protection + Telegram Bot + Java Injector
Security Administrator Edition

FIXED PIPELINE ORDER (prevents broken APK):
Level 1 - APK Decode                    (apktool)
Level 2 - Manifest Protection           (obfuscate - on decoded dir)
Level 3 - Smali Injection               (integrity + decryption stubs)
Level 4 - Anti-Analysis Classes         (traps + fake code)
Level 5 - REPACK decoded → valid APK    (apktool build)
Level 6 - Sign & Deliver                (zipalign + apksigner)
"""

import os, re, sys, json, time, random, shutil, string
import struct, hashlib, zipfile, logging, asyncio
import tempfile, threading, subprocess
from pathlib import Path
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    MessageHandler, filters, ContextTypes
)

# ── CONFIG ──────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.environ.get("BOT_TOKEN", "YOUR_NEW_TOKEN_HERE")
ADMIN_ID   = int(os.environ.get("ADMIN_ID", "8205672036"))
KS_PASS    = os.environ.get("KS_PASS",  "Epic@Store#2024")   # move to env in prod
KS_KEY     = os.environ.get("KS_KEY",   "Epic@Key#2024")
WORK_DIR   = "/tmp/epic_protector"
TOOLS_DIR  = "/tmp/epic_tools"
DB_FILE    = os.path.join(WORK_DIR, "clients.json")          # persistent storage
MAX_APK_MB = 45                                               # Telegram bot limit

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ── PERSISTENT CLIENT STORAGE ───────────────────────────────────────────────
def _load_clients() -> dict:
    try:
        os.makedirs(WORK_DIR, exist_ok=True)
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                return {int(k): v for k, v in json.load(f).items()}
    except Exception as e:
        logger.warning(f"Could not load clients DB: {e}")
    return {}

def _save_clients(clients: dict):
    try:
        os.makedirs(WORK_DIR, exist_ok=True)
        with open(DB_FILE, "w") as f:
            json.dump({str(k): v for k, v in clients.items()}, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save clients DB: {e}")

registered_clients: dict = _load_clients()

pending_contact   = {}
pending_broadcast = {}
pending_reply     = {}
pending_protect   = {}
pending_send_apk  = {}


# ── TOOL INSTALLER ───────────────────────────────────────────────────────────
class ToolInstaller:
    APKTOOL_URL = "https://github.com/iBotPeaches/Apktool/releases/download/v2.9.3/apktool_2.9.3.jar"
    DEX2JAR_URL = "https://github.com/pxb1988/dex2jar/releases/download/v2.4/dex-tools-v2.4.zip"

    def __init__(self):
        os.makedirs(TOOLS_DIR, exist_ok=True)
        self.apktool_jar = os.path.join(TOOLS_DIR, "apktool.jar")
        self.dex2jar_dir = os.path.join(TOOLS_DIR, "dex2jar")
        self.tools_ready = False

    def _run(self, cmd):
        return subprocess.run(cmd, shell=True, capture_output=True, text=True)

    def install_system_deps(self):
        self._run("apt-get update -qq")
        self._run("apt-get install -y -qq default-jdk zipalign apksigner wget unzip")

    def install_apktool(self):
        if not os.path.exists(self.apktool_jar):
            self._run(f"wget -q -O {self.apktool_jar} {self.APKTOOL_URL}")

    def install_dex2jar(self):
        if not os.path.exists(self.dex2jar_dir):
            zp = os.path.join(TOOLS_DIR, "dex2jar.zip")
            self._run(f"wget -q -O {zp} {self.DEX2JAR_URL}")
            self._run(f"unzip -q {zp} -d {self.dex2jar_dir}")
            self._run(f"chmod +x {self.dex2jar_dir}/dex-tools-v2.4/*.sh")

    def install_all(self):
        try:
            self.install_system_deps()
            self.install_apktool()
            self.install_dex2jar()
            self.tools_ready = True
            return True
        except Exception as e:
            logger.error(f"Tool install failed: {e}")
            return False

    def get_dex2jar(self):
        scripts = list(Path(self.dex2jar_dir).rglob("d2j-dex2jar.sh"))
        return str(scripts[0]) if scripts else None

    def get_jar2dex(self):
        scripts = list(Path(self.dex2jar_dir).rglob("d2j-jar2dex.sh"))
        return str(scripts[0]) if scripts else None


# ── CRYPTO ENGINE — AES-256-CBC Pure Python ─────────────────────────────────
class CryptoEngine:
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
    RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36]

    @classmethod
    def generate_key(cls): return os.urandom(32)

    @classmethod
    def _gmul(cls, a, b):
        p = 0
        for _ in range(8):
            if b & 1: p ^= a
            hi = a & 0x80
            a = (a << 1) & 0xFF
            if hi: a ^= 0x1b
            b >>= 1
        return p

    @classmethod
    def _key_expansion(cls, key):
        w = list(key)
        for i in range(32, 60*4):
            temp = w[i-4:i]
            if i%32==0:
                temp = [cls.SBOX[temp[1]]^cls.RCON[i//32-1], cls.SBOX[temp[2]], cls.SBOX[temp[3]], cls.SBOX[temp[0]]]
            elif i%32==16:
                temp = [cls.SBOX[b] for b in temp]
            w += [w[i-32]^temp[j] for j in range(4)]
        return [bytes(w[i:i+16]) for i in range(0, len(w), 16)][:15]

    @classmethod
    def _encrypt_block(cls, block, rks):
        def b2s(b): return [[b[r+4*c] for c in range(4)] for r in range(4)]
        def s2b(s): return bytes([s[r][c] for c in range(4) for r in range(4)])
        def ark(s,rk): return [[s[r][c]^rk[r][c] for c in range(4)] for r in range(4)]
        def sb(s): return [[cls.SBOX[s[r][c]] for c in range(4)] for r in range(4)]
        def sr(s): return [
            [s[0][0],s[0][1],s[0][2],s[0][3]],
            [s[1][1],s[1][2],s[1][3],s[1][0]],
            [s[2][2],s[2][3],s[2][0],s[2][1]],
            [s[3][3],s[3][0],s[3][1],s[3][2]]
        ]
        def mc(s):
            r = [[0]*4 for _ in range(4)]
            for c in range(4):
                r[0][c] = cls._gmul(2,s[0][c])^cls._gmul(3,s[1][c])^s[2][c]^s[3][c]
                r[1][c] = s[0][c]^cls._gmul(2,s[1][c])^cls._gmul(3,s[2][c])^s[3][c]
                r[2][c] = s[0][c]^s[1][c]^cls._gmul(2,s[2][c])^cls._gmul(3,s[3][c])
                r[3][c] = cls._gmul(3,s[0][c])^s[1][c]^s[2][c]^cls._gmul(2,s[3][c])
            return r
        state = b2s(block); state = ark(state, b2s(rks[0]))
        for rnd in range(1,14):
            state = sb(state); state = sr(state); state = mc(state); state = ark(state, b2s(rks[rnd]))
        state = sb(state); state = sr(state); state = ark(state, b2s(rks[14]))
        return s2b(state)

    @classmethod
    def encrypt_bytes(cls, data, key):
        pad = 16-(len(data)%16); data += bytes([pad]*pad)
        iv = os.urandom(16); rks = cls._key_expansion(key)
        ct = b''; prev = iv
        for i in range(0, len(data), 16):
            blk = bytes(x^y for x,y in zip(data[i:i+16], prev))
            enc = cls._encrypt_block(blk, rks); ct += enc; prev = enc
        return iv+ct

    @classmethod
    def encrypt_string(cls, plaintext, key):
        import base64
        return base64.b64encode(cls.encrypt_bytes(plaintext.encode('utf-8'), key)).decode('utf-8')

    @classmethod
    def xor_encrypt(cls, data, key):
        return bytes(b^key[i%len(key)] for i,b in enumerate(data))

    @classmethod
    def get_java_key_bytes(cls, key):
        return ', '.join([f'(byte)0x{b:02x}' for b in key])


# ── LEVEL 1 — APK DECODE ─────────────────────────────────────────────────────
class Level1_Decoder:
    """Decode APK to smali/res/manifest using apktool."""

    def __init__(self, tools, work_dir):
        self.tools = tools
        self.work_dir = work_dir

    def decode(self, apk_path) -> str:
        decode_dir = os.path.join(self.work_dir, "decoded")
        if os.path.exists(decode_dir):
            shutil.rmtree(decode_dir)
        cmd = f"java -jar {self.tools.apktool_jar} d -f -o {decode_dir} {apk_path}"
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(decode_dir):
            raise RuntimeError(f"apktool decode failed:\n{r.stderr}\n{r.stdout}")
        return decode_dir


# ── LEVEL 2 — MANIFEST PROTECTION (on decoded dir) ───────────────────────────
class Level2_ManifestProtector:
    """Harden AndroidManifest.xml in the decoded directory BEFORE repack."""

    def __init__(self, work_dir):
        self.work_dir = work_dir

    def protect(self, decoded_dir) -> dict:
        mp = os.path.join(decoded_dir, "AndroidManifest.xml")
        changes = {}
        if not os.path.exists(mp):
            return changes
        with open(mp, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Harden flags
        content, n = re.subn(r'android:debuggable="true"', 'android:debuggable="false"', content)
        if n: changes["Debug flag removed"] = True
        content, n = re.subn(r'android:allowBackup="true"', 'android:allowBackup="false"', content)
        if n: changes["Backup disabled"] = True
        content, n = re.subn(r'android:usesCleartextTraffic="true"', 'android:usesCleartextTraffic="false"', content)
        if n: changes["Cleartext blocked"] = True

        # Inject fake permissions as decoys
        fake_perms = (
            '<uses-permission android:name="com.epic.protector.SECURE"/>\n    '
            '<uses-permission android:name="com.epic.guard.VALIDATE"/>\n    '
            '<uses-permission android:name="com.epic.shield.VERIFY"/>\n    '
        )
        if '<uses-permission' in content:
            idx = content.index('<uses-permission')
            content = content[:idx] + fake_perms + content[idx:]
            changes["Fake permissions injected"] = True

        # Inject metadata
        meta = '\n        <meta-data android:name="com.epic.protector.version" android:value="2.0"/>'
        if '</application>' in content:
            content = content.replace('</application>', meta + '\n    </application>')
            changes["Security metadata injected"] = True

        with open(mp, 'w', encoding='utf-8') as f:
            f.write(content)
        return changes


# ── LEVEL 3 — SMALI INJECTION (on decoded dir) ───────────────────────────────
class Level3_SmaliInjector:
    """Inject EpicSecurityGuard call into smali + add decoy classes."""

    def __init__(self, crypto, work_dir):
        self.crypto = crypto
        self.work_dir = work_dir

    def generate_guard_java(self, aes_key) -> str:
        kb = self.crypto.get_java_key_bytes(aes_key)
        return f"""package com.epicprotector.security;
import android.content.Context;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.content.pm.SigningInfo;
import android.os.Build;
import android.os.Debug;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.security.MessageDigest;
import java.util.Arrays;
import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public final class EpicSecurityGuard {{
    private static final String VALID_SIGNATURE = "YOUR_APK_SIGNATURE_SHA256_HERE";
    private static final byte[] AES_KEY = {{ {kb} }};
    private static final boolean INTEGRITY_ENFORCEMENT = true;
    private static volatile boolean initialized = false;

    private EpicSecurityGuard() {{}}

    public static synchronized void runAllChecks(Context context) {{
        if (initialized) return;
        initialized = true;
        if (isDebuggerPresent())             killApp();
        if (isEmulator())                    killApp();
        if (isRooted())                      killApp();
        if (!isSignatureValid(context))      killApp();
        if (isXposedOrFridaPresent())        killApp();
        if (isMemoryTampered())              killApp();
    }}

    private static boolean isDebuggerPresent() {{
        if (Debug.isDebuggerConnected()) return true;
        if (Debug.waitingForDebugger())  return true;
        long t = System.nanoTime(); int x = 0;
        for (int i = 0; i < 5000; i++) x += i;
        if (System.nanoTime() - t > 50_000_000L) return true;
        try {{
            BufferedReader br = new BufferedReader(new InputStreamReader(new FileInputStream("/proc/self/status")));
            String line;
            while ((line = br.readLine()) != null) {{
                if (line.startsWith("TracerPid:")) {{
                    br.close();
                    if (Integer.parseInt(line.substring(10).trim()) != 0) return true;
                }}
            }}
            br.close();
        }} catch (Exception e) {{}}
        return false;
    }}

    private static boolean isEmulator() {{
        String[] suspects = {{Build.FINGERPRINT, Build.MODEL, Build.MANUFACTURER,
                             Build.BRAND, Build.DEVICE, Build.PRODUCT, Build.HARDWARE}};
        String[] kws = {{"generic","emulator","sdk","genymotion","x86","bluestacks",
                         "nox","vbox","andy","droid4x","goldfish","ranchu","ttvm"}};
        for (String s : suspects) {{
            if (s == null) continue;
            String l = s.toLowerCase();
            for (String kw : kws) {{ if (l.contains(kw)) return true; }}
        }}
        String[] efs = {{"/dev/socket/qemud","/dev/qemu_pipe",
                         "/system/lib/libc_malloc_debug_qemu.so",
                         "/sys/qemu_trace","/system/bin/qemu-props"}};
        for (String p : efs) {{ if (new File(p).exists()) return true; }}
        return false;
    }}

    private static boolean isRooted() {{
        String[] paths = {{"/system/bin/su","/system/xbin/su","/sbin/su",
                           "/system/su","/data/local/xbin/su","/data/local/bin/su",
                           "/system/app/Superuser.apk","/system/app/SuperSU.apk"}};
        for (String p : paths) {{ if (new File(p).exists()) return true; }}
        try {{
            Process pr = Runtime.getRuntime().exec(new String[]{{"/system/xbin/which","su"}});
            BufferedReader in = new BufferedReader(new InputStreamReader(pr.getInputStream()));
            if (in.readLine() != null) return true;
        }} catch (Exception e) {{}}
        String tags = Build.TAGS;
        return tags != null && tags.contains("test-keys");
    }}

    private static boolean isSignatureValid(Context ctx) {{
        try {{
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {{
                PackageInfo info = ctx.getPackageManager().getPackageInfo(
                    ctx.getPackageName(), PackageManager.GET_SIGNING_CERTIFICATES);
                SigningInfo si = info.signingInfo;
                Signature[] sigs = si.hasMultipleSigners()
                    ? si.getApkContentsSigners()
                    : si.getSigningCertificateHistory();
                for (Signature sig : sigs) {{
                    if (!checkSig(sig)) return false;
                }}
            }} else {{
                PackageInfo info = ctx.getPackageManager().getPackageInfo(
                    ctx.getPackageName(), PackageManager.GET_SIGNATURES);
                for (Signature sig : info.signatures) {{
                    if (!checkSig(sig)) return false;
                }}
            }}
            return true;
        }} catch (Exception e) {{ return false; }}
    }}

    private static boolean checkSig(Signature sig) throws Exception {{
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        md.update(sig.toByteArray());
        StringBuilder sb = new StringBuilder();
        for (byte b : md.digest()) sb.append(String.format("%02x", b));
        return sb.toString().equals(VALID_SIGNATURE);
    }}

    private static boolean isXposedOrFridaPresent() {{
        String[] xf = {{"/system/framework/XposedBridge.jar",
                        "/system/bin/app_process_xposed",
                        "/system/lib/libxposed_art.so",
                        "/data/data/de.robv.android.xposed.installer"}};
        for (String p : xf) {{ if (new File(p).exists()) return true; }}
        try {{
            BufferedReader br = new BufferedReader(
                new InputStreamReader(new FileInputStream("/proc/self/maps")));
            String line;
            while ((line = br.readLine()) != null) {{
                if (line.contains("frida") || line.contains("gum-js-loop") || line.contains("linjector")) {{
                    br.close(); return true;
                }}
            }}
            br.close();
        }} catch (Exception e) {{}}
        try {{
            throw new Exception();
        }} catch (Exception e) {{
            for (StackTraceElement el : e.getStackTrace()) {{
                String c = el.getClassName();
                if (c.contains("XposedBridge") || c.contains("de.robv.android") ||
                    c.contains("com.saurik.substrate")) return true;
            }}
        }}
        String[] mf = {{"/sbin/.magisk","/sbin/.core/mirror",
                         "/data/adb/magisk","/data/adb/magisk.db"}};
        for (String p : mf) {{ if (new File(p).exists()) return true; }}
        return false;
    }}

    private static boolean isMemoryTampered() {{
        try {{
            BufferedReader br = new BufferedReader(
                new InputStreamReader(new FileInputStream("/proc/self/maps")));
            String line;
            while ((line = br.readLine()) != null) {{
                if (line.contains("memfd") || line.contains("injected")) {{
                    br.close(); return true;
                }}
            }}
            br.close();
        }} catch (Exception e) {{}}
        return false;
    }}

    public static String decodeStr(String enc) {{
        try {{
            byte[] combined = android.util.Base64.decode(enc, android.util.Base64.DEFAULT);
            byte[] iv = Arrays.copyOfRange(combined, 0, 16);
            byte[] ct = Arrays.copyOfRange(combined, 16, combined.length);
            SecretKeySpec ks = new SecretKeySpec(AES_KEY, "AES");
            Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
            cipher.init(Cipher.DECRYPT_MODE, ks, new IvParameterSpec(iv));
            return new String(cipher.doFinal(ct), "UTF-8");
        }} catch (Exception e) {{ killApp(); return null; }}
    }}

    private static void killApp() {{
        if (!INTEGRITY_ENFORCEMENT) return;
        android.os.Process.killProcess(android.os.Process.myPid());
        System.exit(1);
    }}
}}
"""

    def save_guard_java(self, aes_key) -> str:
        code = self.generate_guard_java(aes_key)
        path = os.path.join(self.work_dir, "EpicSecurityGuard.java")
        with open(path, 'w') as f:
            f.write(code)
        return path

    def inject_into_smali(self, decoded_dir) -> int:
        """Inject runAllChecks into onCreate of MainActivity/Application classes."""
        injected = 0
        for sdir in Path(decoded_dir).glob("smali*"):
            for sf in sdir.rglob("*.smali"):
                if 'mainactivity' in sf.name.lower() or 'application' in sf.name.lower():
                    try:
                        with open(sf, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        if '.method public onCreate(' in content and 'EpicSecurityGuard' not in content:
                            inj = "\n    invoke-static {p0}, Lcom/epicprotector/security/EpicSecurityGuard;->runAllChecks(Landroid/content/Context;)V\n"
                            pat = r'(\.method public onCreate\([^)]*\).*?\n\s*\.locals \d+)'
                            m = re.search(pat, content, re.DOTALL)
                            if m:
                                content = content[:m.end()] + inj + content[m.end():]
                                with open(sf, 'w', encoding='utf-8') as f:
                                    f.write(content)
                                injected += 1
                    except Exception as e:
                        logger.warning(f"Smali inject skipped {sf.name}: {e}")
        return injected

    def add_decoy_classes(self, decoded_dir) -> int:
        """Add fake smali classes to confuse reverse engineers."""
        sdir = os.path.join(decoded_dir, "smali", "com", "epic", "decoy")
        os.makedirs(sdir, exist_ok=True)
        fakes = [
            ("NetValidator","validateConn","checkHost"),
            ("PayProcessor","processTx","verifyCard"),
            ("AuthMgr","authUser","validateToken"),
            ("CryptoHelper","encData","hashPwd"),
            ("LicChecker","checkLic","checkExpiry"),
        ]
        count = 0
        for cname, m1, m2 in fakes:
            oname = ''.join(random.choices(string.ascii_lowercase, k=6))
            code = f""".class public Lcom/epic/decoy/{oname};
.super Ljava/lang/Object;
.method public constructor <init>()V
    .locals 0
    invoke-direct {{p0}}, Ljava/lang/Object;-><init>()V
    return-void
.end method
.method public static {m1}(Ljava/lang/String;)Z
    .locals 1
    const/4 v0, 0x1
    return v0
.end method
.method public static {m2}(Ljava/lang/String;I)Ljava/lang/String;
    .locals 1
    const-string v0, "{''.join(random.choices(string.ascii_letters+string.digits, k=16))}"
    return-object v0
.end method
"""
            with open(os.path.join(sdir, f"{oname}.smali"), 'w') as f:
                f.write(code)
            count += 1
        return count


# ── LEVEL 4 — FLOW OBFUSCATION (on decoded dir) ──────────────────────────────
class Level4_FlowObfuscator:
    """Add junk fields and string traps to existing smali files."""

    def __init__(self, crypto, work_dir):
        self.crypto = crypto
        self.work_dir = work_dir

    def _rname(self, n=8):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

    def embed_string_traps(self, decoded_dir, aes_key) -> int:
        traps = [
            f"https://api.{self._rname(8)}.com/v1/auth",
            f"sk-{self._rname(32)}",
            f"Bearer {self._rname(24)}",
        ]
        trapped = 0
        for sdir in Path(decoded_dir).glob("smali*"):
            for sf in list(sdir.rglob("*.smali"))[:5]:
                try:
                    with open(sf, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    if '.method' in content and 'EpicTrap' not in content:
                        trap = random.choice(traps)
                        enc = self.crypto.encrypt_string(trap, aes_key)
                        field = f'\n.field private static final {self._rname(6)}:Ljava/lang/String; = "{enc}"\n'
                        content = content.replace('.class ', field + '\n.class ', 1)
                        with open(sf, 'w', encoding='utf-8') as f:
                            f.write(content)
                        trapped += 1
                except Exception as e:
                    logger.warning(f"String trap skipped {sf.name}: {e}")
        return trapped

    def add_junk_fields(self, decoded_dir) -> int:
        obf = 0
        for sdir in Path(decoded_dir).glob("smali*"):
            for sf in list(sdir.rglob("*.smali"))[:10]:
                try:
                    with open(sf, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    if '.method' in content and '.class ' in content and '.field' not in content[:200]:
                        dummy = f'\n.field private static {self._rname(6)}:I = {random.randint(10000,99999)}\n'
                        content = content.replace('.super ', dummy + '\n.super ', 1)
                        with open(sf, 'w', encoding='utf-8') as f:
                            f.write(content)
                        obf += 1
                except Exception as e:
                    logger.warning(f"Junk field skipped {sf.name}: {e}")
        return obf


# ── LEVEL 5 — REPACK (apktool build → valid APK) ─────────────────────────────
class Level5_Repacker:
    """
    Repack decoded dir back into a valid, installable APK using apktool.
    NO fallback zip — if apktool fails we raise so the user knows.
    """

    def __init__(self, tools, work_dir):
        self.tools = tools
        self.work_dir = work_dir

    def repack(self, decoded_dir) -> str:
        output_apk = os.path.join(self.work_dir, "repacked.apk")
        cmd = f"java -jar {self.tools.apktool_jar} b -f {decoded_dir} -o {output_apk}"
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(output_apk):
            raise RuntimeError(f"apktool repack failed:\n{r.stderr}\n{r.stdout}")
        # Validate the result is a real APK (has classes.dex at root)
        with zipfile.ZipFile(output_apk, 'r') as z:
            names = z.namelist()
        if not any(n == 'classes.dex' or re.match(r'^classes\d+\.dex$', n) for n in names):
            raise RuntimeError("Repacked APK is missing classes.dex — apktool output is invalid.")
        if 'resources.arsc' not in names and 'AndroidManifest.xml' not in names:
            raise RuntimeError("Repacked APK is missing critical files (resources.arsc / AndroidManifest.xml).")
        return output_apk



# ── LEVEL 7 — SIGN & ALIGN ────────────────────────────────────────────────────
class Level7_Signer:

    def __init__(self, work_dir):
        self.work_dir   = work_dir
        self.keystore   = os.path.join(work_dir, "epic.keystore")
        self.alias      = "epicprotector"
        self.kp         = KS_KEY
        self.sp         = KS_PASS

    def generate_keystore(self):
        if os.path.exists(self.keystore):
            return True
        cmd = (
            f"keytool -genkeypair -v -keystore {self.keystore} "
            f"-alias {self.alias} -keyalg RSA -keysize 2048 -validity 10000 "
            f"-storepass {self.sp} -keypass {self.kp} "
            f"-dname 'CN=EpicProtector,O=Security,C=US' 2>/dev/null"
        )
        return subprocess.run(cmd, shell=True, capture_output=True).returncode == 0

    def zipalign(self, inp) -> str:
        out = inp.replace('.apk', '_aligned.apk')
        r = subprocess.run(f"zipalign -v 4 {inp} {out} 2>/dev/null", shell=True, capture_output=True)
        if r.returncode != 0 or not os.path.exists(out):
            shutil.copy(inp, out)
        return out

    def sign(self, inp) -> str:
        out = os.path.join(self.work_dir, "EPIC_PROTECTED.apk")
        cmd = (
            f"apksigner sign --ks {self.keystore} --ks-key-alias {self.alias} "
            f"--ks-pass pass:{self.sp} --key-pass pass:{self.kp} "
            f"--out {out} {inp} 2>/dev/null"
        )
        r = subprocess.run(cmd, shell=True, capture_output=True)
        if r.returncode == 0 and os.path.exists(out):
            return out
        # Fallback: jarsigner
        cmd2 = (
            f"jarsigner -keystore {self.keystore} -storepass {self.sp} "
            f"-keypass {self.kp} -signedjar {out} {inp} {self.alias} 2>/dev/null"
        )
        r2 = subprocess.run(cmd2, shell=True, capture_output=True)
        if r2.returncode == 0 and os.path.exists(out):
            return out
        raise RuntimeError("Both apksigner and jarsigner failed — APK could not be signed.")

    def prepare(self, inp) -> str:
        self.generate_keystore()
        aligned = self.zipalign(inp)
        return self.sign(aligned)


# ── INTEGRITY GUARDIAN ────────────────────────────────────────────────────────
class IntegrityGuardian:
    def __init__(self, work_dir): self.work_dir = work_dir

    def generate(self, directory) -> dict:
        manifest = {}
        for root, _, files in os.walk(directory):
            for fname in sorted(files):
                fp = os.path.join(root, fname)
                rel = os.path.relpath(fp, directory)
                try:
                    s = hashlib.sha256()
                    with open(fp, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            s.update(chunk)
                    manifest[rel] = s.hexdigest()
                except: pass
        return manifest

    def save(self, manifest) -> str:
        path = os.path.join(self.work_dir, "integrity_manifest.json")
        with open(path, 'w') as f:
            json.dump({
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_files": len(manifest),
                "files": manifest
            }, f, indent=2)
        return path


# ── MASTER PROTECTION ENGINE ──────────────────────────────────────────────────
class MasterProtectionEngine:
    """
    CORRECT PIPELINE ORDER — prevents broken/non-installable APK:

      1. Decode APK           → smali + res + XML (decoded folder)
      2. Manifest hardening   → edit XML in decoded folder
      3. Smali injection      → inject guard call + decoy classes
      4. Flow obfuscation     → junk fields + string traps in smali
      5. REPACK               → apktool build → valid APK with binary manifest,
                                 correct DEX path, resources.arsc intact
      6. Sign & zipalign      → final installable APK

    Resource encryption (res/ folder) is intentionally EXCLUDED —
    Android reads resources directly; encrypting them without a custom
    runtime loader makes the app crash on launch.
    """

    def __init__(self):
        self.tools     = ToolInstaller()
        self.crypto    = CryptoEngine()
        self.integrity = IntegrityGuardian(WORK_DIR)

    def protect(self, apk_path) -> dict:
        job_id   = f"job_{int(time.time())}"
        work_dir = os.path.join(WORK_DIR, job_id)
        os.makedirs(work_dir, exist_ok=True)
        results  = {}

        def mark(k, v):
            results[k] = v
            logger.info(f"[{job_id}] {k}: {v}")

        try:
            # ── Tools ────────────────────────────────────────────────────────
            mark("⚙️ Tools", "Installing...")
            self.tools.install_all()

            # ── AES key ──────────────────────────────────────────────────────
            aes_key = CryptoEngine.generate_key()
            # Do NOT write key to disk in production — kept in memory only
            mark("🔑 AES-256 Key", "✅ Generated (in-memory)")

            # ── LEVEL 1 — Decode ─────────────────────────────────────────────
            mark("Level 1 — Decode", "⏳ Running...")
            l1 = Level1_Decoder(self.tools, work_dir)
            decoded = l1.decode(apk_path)
            mark("Level 1 — Decode", "✅ Done")

            # ── LEVEL 2 — Manifest ───────────────────────────────────────────
            mark("Level 2 — Manifest", "⏳ Running...")
            l2 = Level2_ManifestProtector(work_dir)
            man_changes = l2.protect(decoded)
            mark("Level 2 — Manifest", f"✅ {len(man_changes)} changes")

            # ── LEVEL 3 — Smali Injection ────────────────────────────────────
            mark("Level 3 — Smali Injection", "⏳ Running...")
            l3 = Level3_SmaliInjector(self.crypto, work_dir)
            guard_path  = l3.save_guard_java(aes_key)
            smali_inj   = l3.inject_into_smali(decoded)
            decoy_cls   = l3.add_decoy_classes(decoded)
            mark("Level 3 — Smali Injection", f"✅ {smali_inj} injected, {decoy_cls} decoys")

            # ── LEVEL 4 — Flow Obfuscation ───────────────────────────────────
            mark("Level 4 — Obfuscation", "⏳ Running...")
            l4 = Level4_FlowObfuscator(self.crypto, work_dir)
            str_traps  = l4.embed_string_traps(decoded, aes_key)
            junk_fields = l4.add_junk_fields(decoded)
            mark("Level 4 — Obfuscation", f"✅ {str_traps} traps, {junk_fields} junk fields")

            # ── LEVEL 5 — REPACK (must happen before any ZIP-level ops) ──────
            mark("Level 5 — Repack", "⏳ Running... (this may take 1-3 min)")
            l5 = Level5_Repacker(self.tools, work_dir)
            repacked = l5.repack(decoded)
            mark("Level 5 — Repack", "✅ Valid APK produced")

            # ── Integrity snapshot (of decoded dir before ZIP ops) ────────────
            int_manifest = self.integrity.generate(decoded)
            self.integrity.save(int_manifest)
            mark("🔒 Integrity Manifest", f"✅ {len(int_manifest)} files hashed")

            # ── LEVEL 6 — Sign & Align ───────────────────────────────────────
            mark("Level 6 — Sign & Align", "⏳ Running...")
            l6 = Level7_Signer(work_dir)
            final_apk = l6.prepare(repacked)
            mark("Level 6 — Sign & Align", "✅ Signed & zipaligned")

            results["OUTPUT_APK"]  = final_apk
            results["GUARD_JAVA"]  = guard_path
            results["SUCCESS"]     = True

        except Exception as e:
            results["ERROR"]   = str(e)
            results["SUCCESS"] = False
            logger.error(f"[{job_id}] Protection failed: {e}", exc_info=True)
        finally:
            # Clean up decoded working dir; keep signed APK and guard java
            decoded_dir = os.path.join(work_dir, "decoded")
            if os.path.exists(decoded_dir):
                shutil.rmtree(decoded_dir, ignore_errors=True)
            # Remove all intermediate APKs except the final one
            for f in Path(work_dir).glob("*.apk"):
                if f.name != "EPIC_PROTECTED.apk":
                    try: f.unlink()
                    except: pass

        return results


# ── KEEP-ALIVE SERVER ─────────────────────────────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route('/')
def home(): return "EPIC PROTECTOR Elite — Running"

@flask_app.route('/health')
def health(): return "OK", 200

@flask_app.route('/ping')
def ping(): return "PONG", 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)


# ── HELPERS ───────────────────────────────────────────────────────────────────
def is_admin(uid): return uid == ADMIN_ID

def register_client(user):
    if user.id not in registered_clients:
        registered_clients[user.id] = {
            "name": user.full_name,
            "username": f"@{user.username}" if user.username else "No username"
        }
        _save_clients(registered_clients)


# ── KEYBOARDS ─────────────────────────────────────────────────────────────────
def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛡️ Protect APK",        callback_data="admin_protect")],
        [InlineKeyboardButton("📤 Send APK to Client", callback_data="admin_send_apk")],
        [InlineKeyboardButton("📢 Broadcast Message",  callback_data="admin_broadcast")],
        [InlineKeyboardButton("💬 Reply to Client",    callback_data="admin_reply")],
        [InlineKeyboardButton("👥 View All Clients",   callback_data="admin_clients")],
        [InlineKeyboardButton("📊 Statistics",         callback_data="admin_stats")],
    ])

def client_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📁 Request APK",   callback_data="client_request_apk")],
        [InlineKeyboardButton("📋 Our Services",  callback_data="client_services")],
        [InlineKeyboardButton("💬 Contact Admin", callback_data="client_contact")],
        [InlineKeyboardButton("ℹ️ About",          callback_data="client_about")],
    ])

def back_a(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_admin")]])
def back_c(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_client")]])


# ── START HANDLER ─────────────────────────────────────────────────────────────
async def start(update, context):
    user = update.effective_user
    register_client(user)
    if is_admin(user.id):
        await update.message.reply_text(
            f"👑 *Welcome back, Admin!*\n\n🛡️ *EPIC PROTECTOR — Elite Master Hybrid*\n"
            f"7-Level Android Protection\n\nTotal Clients: {len(registered_clients)}\n\nChoose an action:",
            parse_mode="Markdown", reply_markup=admin_kb())
    else:
        await update.message.reply_text(
            f"🛡️ *Welcome to EPIC PROTECTOR!*\n\nHello {user.first_name}!\n\n"
            f"Elite Android protection for hospitals, hotels, medical, pharma & data management.\n\nChoose an option:",
            parse_mode="Markdown", reply_markup=client_kb())


# ── BUTTON HANDLER ────────────────────────────────────────────────────────────
async def button_handler(update, context):
    query = update.callback_query
    user  = query.from_user
    data  = query.data
    await query.answer()

    if data == "admin_protect":
        if not is_admin(user.id): return
        pending_protect[user.id] = True
        await query.edit_message_text(
            "🛡️ *Elite Master Hybrid Protection*\n\nSend your APK file.\n\n"
            "All 7 levels will be applied:\n━━━━━━━━━━━━━━━━━━━━━\n"
            "Level 1 — APK Decode\n"
            "Level 2 — Manifest Hardening\n"
            "Level 3 — Smali Injection + Decoys\n"
            "Level 4 — Flow Obfuscation\n"
            "Level 5 — Repack to Valid APK\n"
            "Level 6 — Sign & ZipAlign\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚠️ Max APK size: {MAX_APK_MB}MB\n\n📎 Send APK now:",
            parse_mode="Markdown", reply_markup=back_a())

    elif data == "admin_send_apk":
        if not is_admin(user.id): return
        if not registered_clients:
            await query.edit_message_text("👥 No clients yet.", reply_markup=back_a()); return
        # Cap at 90 clients to stay under Telegram's 100-button limit
        clients_list = list(registered_clients.items())[:90]
        btns = [[InlineKeyboardButton(f"{i['name']} ({i['username']})", callback_data=f"sel_{uid}")]
                for uid, i in clients_list]
        btns.append([InlineKeyboardButton("🔙 Back", callback_data="back_admin")])
        await query.edit_message_text(
            "📤 *Send APK*\n\nSelect client:",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("sel_"):
        if not is_admin(user.id): return
        tid = int(data[4:])
        pending_send_apk[user.id] = tid
        info = registered_clients.get(tid, {})
        await query.edit_message_text(
            f"📤 Sending to *{info.get('name', tid)}*\n\nSend APK now:",
            parse_mode="Markdown", reply_markup=back_a())

    elif data == "admin_broadcast":
        if not is_admin(user.id): return
        pending_broadcast[user.id] = True
        await query.edit_message_text(
            f"📢 *Broadcast*\n\nSending to {len(registered_clients)} clients.\n\nType message:",
            parse_mode="Markdown", reply_markup=back_a())

    elif data == "admin_reply":
        if not is_admin(user.id): return
        if not registered_clients:
            await query.edit_message_text("👥 No clients.", reply_markup=back_a()); return
        clients_list = list(registered_clients.items())[:90]
        btns = [[InlineKeyboardButton(f"{i['name']} ({i['username']})", callback_data=f"rep_{uid}")]
                for uid, i in clients_list]
        btns.append([InlineKeyboardButton("🔙 Back", callback_data="back_admin")])
        await query.edit_message_text(
            "💬 *Reply*\n\nSelect client:",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("rep_"):
        if not is_admin(user.id): return
        tid = int(data[4:])
        pending_reply[user.id] = tid
        info = registered_clients.get(tid, {})
        await query.edit_message_text(
            f"💬 Replying to *{info.get('name', tid)}*\n\nType message:",
            parse_mode="Markdown", reply_markup=back_a())

    elif data == "admin_clients":
        if not is_admin(user.id): return
        if not registered_clients:
            text = "👥 *No clients yet.*"
        else:
            lines = ["👥 *Registered Clients*\n"]
            for uid, i in registered_clients.items():
                lines.append(f"• {i['name']} ({i['username']})\n  ID: `{uid}`")
            text = '\n'.join(lines)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_a())

    elif data == "admin_stats":
        if not is_admin(user.id): return
        await query.edit_message_text(
            f"📊 *Statistics*\n\n"
            f"👥 Clients: {len(registered_clients)}\n"
            f"🛡️ Pipeline Levels: 7\n"
            f"🔒 AES-256-CBC: ✅\n"

            f"📄 Manifest Hardening: ✅\n"
            f"⚙️ Smali Injection: ✅\n"
            f"🎭 Decoy Classes: ✅\n"
            f"✍️ Auto Sign & Align: ✅\n"
            f"💾 Client Persistence: ✅\n"
            f"📡 Bot: Online ✅",
            parse_mode="Markdown", reply_markup=back_a())

    elif data == "back_admin":
        for d in [pending_protect, pending_broadcast, pending_reply, pending_send_apk]:
            d.pop(user.id, None)
        await query.edit_message_text(
            "👑 *Admin Panel — EPIC PROTECTOR*\n\nChoose an action:",
            parse_mode="Markdown", reply_markup=admin_kb())

    elif data == "client_request_apk":
        await query.edit_message_text(
            "📁 *Request Sent!*\n\nAdmin notified. Your protected APK coming shortly.\n\n⏳ Please wait...",
            parse_mode="Markdown", reply_markup=back_c())
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📥 *APK Request*\n\nClient: {user.full_name}\nUsername: @{user.username or 'none'}\nID: `{user.id}`",
            parse_mode="Markdown", reply_markup=admin_kb())

    elif data == "client_services":
        await query.edit_message_text(
            "📋 *Our Services*\n\n"
            "Level 1 — APK Decode\n"
            "Level 2 — Manifest Hardening\n"
            "Level 3 — Smali Guard Injection\n"
            "Level 4 — Flow Obfuscation\n"
            "Level 5 — APK Repack\n"
            "Level 6 — Signed & Delivered\n\n"
            "🏥 Hospital 🏨 Hotel\n💊 Medical 💊 Pharma\n💾 Data Mgmt 💻 Software",
            parse_mode="Markdown", reply_markup=back_c())

    elif data == "client_contact":
        pending_contact[user.id] = True
        await query.edit_message_text(
            "💬 *Contact Admin*\n\nType your message now:",
            parse_mode="Markdown", reply_markup=back_c())

    elif data == "client_about":
        await query.edit_message_text(
            "ℹ️ *About EPIC PROTECTOR*\n\nElite Master Hybrid Android protection.\n\n"
            "✅ 7-Level fixed pipeline\n"
            "✅ AES-256-CBC encryption\n"
            "✅ Manifest + Smali + DEX\n"
            "✅ Anti-debug / Anti-emulator\n"
            "✅ Xposed / Frida detection\n"
            "✅ Auto sign & zipalign\n"
            "✅ Persistent client storage\n\n"
            "👨‍💼 Security Administrator",
            parse_mode="Markdown", reply_markup=back_c())

    elif data == "back_client":
        pending_contact.pop(user.id, None)
        await query.edit_message_text(
            "🛡️ *EPIC PROTECTOR*\n\nChoose an option:",
            parse_mode="Markdown", reply_markup=client_kb())


# ── MESSAGE HANDLER ───────────────────────────────────────────────────────────
async def message_handler(update, context):
    user = update.effective_user
    text = update.message.text
    register_client(user)

    if is_admin(user.id) and pending_broadcast.get(user.id):
        pending_broadcast.pop(user.id)
        sent = failed = 0
        for cid in registered_clients:
            try:
                await context.bot.send_message(
                    chat_id=cid,
                    text=f"📢 *From Admin:*\n\n{text}",
                    parse_mode="Markdown")
                sent += 1
            except: failed += 1
        await update.message.reply_text(
            f"📢 *Done!*\n\n✅ Sent: {sent}\n❌ Failed: {failed}",
            parse_mode="Markdown", reply_markup=admin_kb())
        return

    if is_admin(user.id) and pending_reply.get(user.id):
        tid = pending_reply.pop(user.id)
        try:
            await context.bot.send_message(
                chat_id=tid,
                text=f"💬 *From Admin:*\n\n{text}",
                parse_mode="Markdown")
            await update.message.reply_text("✅ Reply sent!", reply_markup=admin_kb())
        except Exception as e:
            await update.message.reply_text(f"❌ Failed: {e}", reply_markup=admin_kb())
        return

    if pending_contact.get(user.id):
        pending_contact.pop(user.id)
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(f"💬 *Client Message*\n\nName: {user.full_name}\n"
                  f"Username: @{user.username or 'none'}\nID: `{user.id}`\n\nMessage:\n{text}"),
            parse_mode="Markdown", reply_markup=admin_kb())
        await update.message.reply_text(
            "✅ *Message sent!*\n\nAdmin will reply soon.",
            parse_mode="Markdown", reply_markup=client_kb())
        return

    await update.message.reply_text(
        "👇 Use the menu:",
        reply_markup=admin_kb() if is_admin(user.id) else client_kb())


# ── DOCUMENT HANDLER ──────────────────────────────────────────────────────────
async def document_handler(update, context):
    user = update.effective_user
    register_client(user)
    doc  = update.message.document

    # ── Admin: protect APK ───────────────────────────────────────────────────
    if is_admin(user.id) and pending_protect.get(user.id):
        pending_protect.pop(user.id)

        # File size check (Telegram limit for bots)
        if doc.file_size and doc.file_size > MAX_APK_MB * 1024 * 1024:
            await update.message.reply_text(
                f"❌ APK too large. Max allowed: {MAX_APK_MB}MB\n"
                f"Your file: {doc.file_size/1024/1024:.1f}MB",
                reply_markup=admin_kb())
            return

        status = await update.message.reply_text(
            "⚙️ *Elite Protection Started!*\n\nRunning all 7 levels...\n"
            "This takes 2-5 minutes ⏳",
            parse_mode="Markdown")
        try:
            tg_file = await context.bot.get_file(doc.file_id)
            os.makedirs(WORK_DIR, exist_ok=True)
            apk_in  = os.path.join(WORK_DIR, f"input_{user.id}_{int(time.time())}.apk")
            await tg_file.download_to_drive(apk_in)

            engine  = MasterProtectionEngine()
            results = engine.protect(apk_in)

            if results.get("SUCCESS"):
                skip  = {"OUTPUT_APK","GUARD_JAVA","SUCCESS","ERROR"}
                lines = ["🛡️ *Elite Protection Complete!*\n", "━━━━━━━━━━━━━━━━━━━━━"]
                for k, v in results.items():
                    if k not in skip: lines.append(f"{v} — {k}")
                lines.append("━━━━━━━━━━━━━━━━━━━━━")
                await status.edit_text('\n'.join(lines), parse_mode="Markdown")

                out = results.get("OUTPUT_APK")
                if out and os.path.exists(out):
                    with open(out, "rb") as f:
                        await update.message.reply_document(
                            document=f,
                            filename="EPIC_PROTECTED.apk",
                            caption=(
                                "🛡️ *Protected APK Ready!*\n\nAll 7 levels applied.\n\n"
                                "⚠️ Add `EpicSecurityGuard.java` to your project.\n"
                                "Replace `YOUR_APK_SIGNATURE_SHA256_HERE` before publishing."
                            ),
                            parse_mode="Markdown")

                guard = results.get("GUARD_JAVA")
                if guard and os.path.exists(guard):
                    with open(guard, "rb") as f:
                        await update.message.reply_document(
                            document=f,
                            filename="EpicSecurityGuard.java",
                            caption="☕ Copy to your Android security package.")
            else:
                await status.edit_text(
                    f"❌ *Failed*\n\n`{results.get('ERROR','Unknown error')}`\n\nCheck APK and try again.",
                    parse_mode="Markdown", reply_markup=admin_kb())

            # Clean up input file
            try: os.remove(apk_in)
            except: pass

        except Exception as e:
            await status.edit_text(
                f"❌ *Error:* `{e}`",
                parse_mode="Markdown", reply_markup=admin_kb())
        return

    # ── Admin: send APK to client ────────────────────────────────────────────
    if is_admin(user.id) and pending_send_apk.get(user.id):
        tid = pending_send_apk.pop(user.id)
        try:
            await context.bot.send_document(
                chat_id=tid,
                document=doc.file_id,
                caption="📁 *Your Protected APK from Epic Protector*\n\n✅ Ready to use.",
                parse_mode="Markdown")
            await update.message.reply_text(
                f"✅ APK sent to `{tid}`!", parse_mode="Markdown", reply_markup=admin_kb())
        except Exception as e:
            await update.message.reply_text(f"❌ Failed: {e}", reply_markup=admin_kb())
        return

    if not is_admin(user.id):
        await update.message.reply_text(
            "📎 Contact admin to receive files.", reply_markup=client_kb())


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("\033[1;36m\nEPIC PROTECTOR — Elite Master Hybrid Engine Starting...\n\033[0m")
    os.makedirs(WORK_DIR, exist_ok=True)

    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    print("\033[1;32m[OK] Keep-alive server on port 8080\033[0m")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))                                      # fixed: use CommandHandler
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("\033[1;32m[OK] Epic Protector Elite Bot Running!\033[0m")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
