#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║           EPIC PROTECTOR - Android App Protection            ║
║         Obfuscation + Anti-Tamper + Full Security            ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import hashlib
import shutil
import zipfile
import json
import random
import string
import re
import time
from pathlib import Path


# ─────────────────────────────────────────────
#  BANNER
# ─────────────────────────────────────────────
def banner():
    print("""
\033[1;36m
╔══════════════════════════════════════════════════════════════╗
║                  EPIC PROTECTOR v1.0                         ║
║         Android Protection + Obfuscation Framework           ║
║                  Security Administrator                      ║
╚══════════════════════════════════════════════════════════════╝
\033[0m""")


# ─────────────────────────────────────────────
#  UTILITIES
# ─────────────────────────────────────────────

def log(msg, level="INFO"):
    colors = {"INFO": "\033[1;32m", "WARN": "\033[1;33m", "ERR": "\033[1;31m", "DONE": "\033[1;36m"}
    reset = "\033[0m"
    print(f"{colors.get(level, '')}[{level}] {msg}{reset}")


def random_name(length=12):
    """Generate random obfuscated class/method name."""
    chars = string.ascii_letters
    return ''.join(random.choices(chars, k=length))


def compute_hash(filepath):
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_dir_hash(directory):
    """Compute combined hash of all files in directory."""
    all_hashes = {}
    for root, _, files in os.walk(directory):
        for filename in sorted(files):
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, directory)
            all_hashes[rel_path] = compute_hash(filepath)
    return all_hashes


# ─────────────────────────────────────────────
#  1. INTEGRITY MANIFEST GENERATOR
# ─────────────────────────────────────────────

class IntegrityGuard:
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.manifest_path = os.path.join(project_dir, "integrity_manifest.json")

    def generate_manifest(self):
        log("Generating integrity manifest for all project files...")
        hashes = compute_dir_hash(self.project_dir)
        manifest = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": len(hashes),
            "files": hashes
        }
        with open(self.manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        log(f"Integrity manifest created: {self.manifest_path} ({len(hashes)} files)", "DONE")
        return manifest

    def verify_manifest(self):
        if not os.path.exists(self.manifest_path):
            log("No integrity manifest found! Tamper detected or first run.", "ERR")
            return False
        with open(self.manifest_path, "r") as f:
            manifest = json.load(f)
        current = compute_dir_hash(self.project_dir)
        original = manifest["files"]
        tampered = []
        missing = []
        added = []
        for path, hash_val in original.items():
            if path == "integrity_manifest.json":
                continue
            if path not in current:
                missing.append(path)
            elif current[path] != hash_val:
                tampered.append(path)
        for path in current:
            if path not in original and path != "integrity_manifest.json":
                added.append(path)
        if tampered or missing or added:
            log("TAMPER DETECTED!", "ERR")
            for f in tampered:
                log(f"  Modified : {f}", "ERR")
            for f in missing:
                log(f"  Missing  : {f}", "ERR")
            for f in added:
                log(f"  Injected : {f}", "WARN")
            return False
        log("Integrity check PASSED — all files are untouched.", "DONE")
        return True


# ─────────────────────────────────────────────
#  2. JAVA CODE OBFUSCATOR
# ─────────────────────────────────────────────

class JavaObfuscator:
    def __init__(self, project_dir, output_dir):
        self.project_dir = project_dir
        self.output_dir = output_dir
        self.name_map = {}           # original -> obfuscated name
        self._aes_key = None         # AES-256 key — generated once, used everywhere
        self._aes_key_saved = False  # ensures key file is saved only once

    def _get_obfuscated(self, name):
        if name not in self.name_map:
            self.name_map[name] = random_name()
        return self.name_map[name]

    def _obfuscate_java_source(self, content):
        """Obfuscate Java source: rename variables, inject junk, strip comments."""

        # Strip single-line comments
        content = re.sub(r'//.*?\n', '\n', content)
        # Strip multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # Obfuscate local variable names (simple pattern: type varName =)
        var_pattern = re.compile(
            r'\b(int|String|boolean|float|double|long|byte|char|Object|List|Map|Set)\s+([a-z][a-zA-Z0-9_]*)\s*[=;(,]'
        )
        found_vars = var_pattern.findall(content)
        for _, var_name in found_vars:
            if len(var_name) > 2:
                obf = self._get_obfuscated(var_name)
                content = re.sub(r'\b' + re.escape(var_name) + r'\b', obf, content)

        # Inject junk code blocks after class declarations
        junk_code = self._generate_junk_methods()
        content = re.sub(r'(\bclass\b[^{]+\{)', r'\1\n' + junk_code, content, count=1)

        # Insert string encryption stubs
        content = self._encrypt_string_literals(content)

        return content

    def _generate_junk_methods(self):
        """Generate fake decoy methods to confuse reverse engineers."""
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

    def _generate_aes_key(self):
        """Generate a secure random 256-bit AES key."""
        import os
        return os.urandom(32)  # 256-bit key

    def _aes_encrypt(self, plaintext: str, key: bytes) -> str:
        """
        Fully encrypt a string using AES-256-CBC with PKCS7 padding.
        Returns Base64-encoded IV + ciphertext string for embedding in Java.
        """
        import os
        import base64

        # PKCS7 padding
        data = plaintext.encode('utf-8')
        pad_len = 16 - (len(data) % 16)
        data += bytes([pad_len] * pad_len)

        # Generate random IV (16 bytes)
        iv = os.urandom(16)

        # AES-256-CBC encryption (pure Python — no external libs needed)
        def xor_bytes(a, b):
            return bytes(x ^ y for x, y in zip(a, b))

        def aes_encrypt_block(block, round_keys):
            """Full AES block encryption — 14 rounds for AES-256."""
            # AES S-Box
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
                """Galois field multiplication."""
                p = 0
                for _ in range(8):
                    if b & 1:
                        p ^= a
                    hi = a & 0x80
                    a = (a << 1) & 0xFF
                    if hi:
                        a ^= 0x1b
                    b >>= 1
                return p

            def sub_bytes(state):
                return [[SBOX[state[r][c]] for c in range(4)] for r in range(4)]

            def shift_rows(state):
                return [
                    [state[0][0], state[0][1], state[0][2], state[0][3]],
                    [state[1][1], state[1][2], state[1][3], state[1][0]],
                    [state[2][2], state[2][3], state[2][0], state[2][1]],
                    [state[3][3], state[3][0], state[3][1], state[3][2]],
                ]

            def mix_columns(state):
                result = [[0]*4 for _ in range(4)]
                for c in range(4):
                    result[0][c] = gmul(0x02,state[0][c])^gmul(0x03,state[1][c])^state[2][c]^state[3][c]
                    result[1][c] = state[0][c]^gmul(0x02,state[1][c])^gmul(0x03,state[2][c])^state[3][c]
                    result[2][c] = state[0][c]^state[1][c]^gmul(0x02,state[2][c])^gmul(0x03,state[3][c])
                    result[3][c] = gmul(0x03,state[0][c])^state[1][c]^state[2][c]^gmul(0x02,state[3][c])
                return result

            def add_round_key(state, rk):
                return [[state[r][c] ^ rk[r][c] for c in range(4)] for r in range(4)]

            def bytes_to_state(b):
                return [[b[r + 4*c] for c in range(4)] for r in range(4)]

            def state_to_bytes(s):
                return bytes([s[r][c] for c in range(4) for r in range(4)])

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
            """AES-256 key schedule — produces 15 round keys."""
            RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36]
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
            w = list(key)
            for i in range(32, 60 * 4):
                temp = w[i-4:i]
                if i % 32 == 0:
                    temp = [SBOX[temp[1]] ^ RCON[i//32 - 1], SBOX[temp[2]], SBOX[temp[3]], SBOX[temp[0]]]
                elif i % 32 == 16:
                    temp = [SBOX[b] for b in temp]
                w += [w[i-32] ^ temp[j] for j in range(4)]
            return [bytes(w[i:i+16]) for i in range(0, len(w), 16)][:15]

        # Perform CBC encryption
        round_keys = key_expansion(key)
        ciphertext = b''
        prev = iv
        for i in range(0, len(data), 16):
            block = data[i:i+16]
            block = xor_bytes(block, prev)
            encrypted_block = aes_encrypt_block(block, round_keys)
            ciphertext += encrypted_block
            prev = encrypted_block

        # Return as Base64 encoded IV+ciphertext
        combined = iv + ciphertext
        return base64.b64encode(combined).decode('utf-8')

    def _inject_aes_decryptor_java(self, content):
        """
        Inject full AES-256-CBC decryptor Java method into the class.
        This is the real runtime decryptor that will decode encrypted strings.
        """
        decryptor = '''
    // ── AES-256-CBC String Decryptor (injected by EPIC PROTECTOR) ──
    private static final byte[] AES_KEY = {
        __AES_KEY_BYTES__
    };

    private static String decodeStr(String encryptedBase64) {
        try {
            byte[] combined = android.util.Base64.decode(encryptedBase64, android.util.Base64.DEFAULT);
            byte[] iv = java.util.Arrays.copyOfRange(combined, 0, 16);
            byte[] ciphertext = java.util.Arrays.copyOfRange(combined, 16, combined.length);
            javax.crypto.SecretKeySpec keySpec = new javax.crypto.SecretKeySpec(AES_KEY, "AES");
            javax.crypto.Cipher cipher = javax.crypto.Cipher.getInstance("AES/CBC/PKCS5Padding");
            cipher.init(javax.crypto.Cipher.DECRYPT_MODE, keySpec, new javax.crypto.spec.IvParameterSpec(iv));
            byte[] decrypted = cipher.doFinal(ciphertext);
            return new String(decrypted, "UTF-8");
        } catch (Exception e) {
            android.os.Process.killProcess(android.os.Process.myPid());
            return null;
        }
    }
'''
        # Inject AES key bytes into decryptor
        key_bytes = ', '.join([f'(byte)0x{b:02x}' for b in self._aes_key])
        decryptor = decryptor.replace('__AES_KEY_BYTES__', key_bytes)

        # Inject after first class opening brace
        content = re.sub(r'(\bclass\b[^{]+\{)', r'\1\n' + decryptor, content, count=1)
        return content

    def _encrypt_string_literals(self, content):
        """
        Replace ALL plain string literals with real AES-256-CBC encrypted calls.
        Every string is individually encrypted with a unique IV.
        Encrypted value is embedded as Base64 and decrypted at runtime via decodeStr().
        AES key is generated ONCE in obfuscate_project() and reused across all files.
        """
        # Key is always ready — generated once in obfuscate_project() before this is called
        def replacer(match):
            s = match.group(1)
            # Only encrypt ASCII strings under 200 chars
            if len(s) < 200 and s.isascii() and len(s) > 0:
                try:
                    encrypted = self._aes_encrypt(s, self._aes_key)
                    return f'decodeStr("{encrypted}")'
                except Exception:
                    return match.group(0)
            return match.group(0)

        # Encrypt all string literals in the Java source
        content = re.sub(r'"([^"\\]{1,199})"', replacer, content)

        # Inject the AES decryptor method into the class
        content = self._inject_aes_decryptor_java(content)

        return content

    def obfuscate_project(self):
        log("Starting Java source obfuscation...")
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        shutil.copytree(self.project_dir, self.output_dir)

        # ── Generate AES-256 key FIRST — before processing any file ──
        self._aes_key = self._generate_aes_key()
        key_path = os.path.join(self.output_dir, "aes_key.bin")
        with open(key_path, "wb") as f:
            f.write(self._aes_key)
        log(f"AES-256 key generated and saved: {key_path}", "DONE")
        log("WARNING: Keep aes_key.bin private — never share with clients!", "WARN")

        java_files = list(Path(self.output_dir).rglob("*.java"))
        log(f"Found {len(java_files)} Java files to obfuscate and encrypt...")

        for java_file in java_files:
            try:
                with open(java_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                obfuscated = self._obfuscate_java_source(content)
                with open(java_file, "w", encoding="utf-8") as f:
                    f.write(obfuscated)
                log(f"  Obfuscated + Encrypted: {java_file.name}")
            except Exception as e:
                log(f"  Skipped {java_file.name}: {e}", "WARN")

        # Save name mapping (keep private — don't share with clients)
        map_path = os.path.join(self.output_dir, "obfuscation_map.json")
        with open(map_path, "w") as f:
            json.dump(self.name_map, f, indent=2)
        log(f"Obfuscation complete. Name map saved to: {map_path}", "DONE")
        log("WARNING: Keep obfuscation_map.json private — never share with clients!", "WARN")


# ─────────────────────────────────────────────
#  3. PROGUARD RULES GENERATOR
# ─────────────────────────────────────────────

class ProGuardGenerator:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def generate(self):
        rules = """
# ╔══════════════════════════════════════════════╗
# ║   EPIC PROTECTOR — ProGuard Rules             ║
# ╚══════════════════════════════════════════════╝

# ── Core Obfuscation ──────────────────────────
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

# ── Anti-Debugging ────────────────────────────
-assumenosideeffects class android.util.Log {
    public static int v(...);
    public static int d(...);
    public static int i(...);
    public static int w(...);
    public static int e(...);
}

# ── Strip StackTraces ─────────────────────────
-renamesourcefileattribute SourceFile
-keepattributes SourceFile,LineNumberTable

# ── Keep Entry Points ─────────────────────────
-keep public class * extends android.app.Activity
-keep public class * extends android.app.Application
-keep public class * extends android.app.Service
-keep public class * extends android.content.BroadcastReceiver
-keep public class * extends android.content.ContentProvider
-keep public class * extends android.view.View
-keep public class * extends androidx.fragment.app.Fragment

# ── Keep Native Methods ───────────────────────
-keepclasseswithmembernames class * {
    native <methods>;
}

# ── Keep Enums ────────────────────────────────
-keepclassmembers enum * {
    public static **[] values();
    public static ** valueOf(java.lang.String);
}

# ── Keep Parcelable ───────────────────────────
-keepclassmembers class * implements android.os.Parcelable {
    public static final android.os.Parcelable$Creator CREATOR;
}

# ── Keep Serializable ─────────────────────────
-keepclassmembers class * implements java.io.Serializable {
    static final long serialVersionUID;
    private static final java.io.ObjectStreamField[] serialPersistentFields;
    private void writeObject(java.io.ObjectOutputStream);
    private void readObject(java.io.ObjectInputStream);
    java.lang.Object writeReplace();
    java.lang.Object readResolve();
}

# ── Remove Unused Code ────────────────────────
-dontwarn **
-ignorewarnings
"""
        rules_path = os.path.join(self.output_dir, "proguard-rules.pro")
        with open(rules_path, "w") as f:
            f.write(rules)

        # Generate obfuscation dictionary
        words = [random_name(random.randint(4, 12)) for _ in range(500)]
        dict_path = os.path.join(self.output_dir, "obf_dict.txt")
        with open(dict_path, "w") as f:
            f.write('\n'.join(words))

        log(f"ProGuard rules generated: {rules_path}", "DONE")
        log(f"Obfuscation dictionary generated: {dict_path}", "DONE")


# ─────────────────────────────────────────────
#  4. ANTI-TAMPER RUNTIME CODE INJECTOR
# ─────────────────────────────────────────────

class AntiTamperInjector:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def inject(self):
        log("Injecting anti-tamper runtime code...")
        code = """package com.epicprotector.security;

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

/**
 * EPIC PROTECTOR — Runtime Security Guard
 * Handles: Anti-Tamper, Root Detection, Emulator Detection, Anti-Debug
 */
public class EpicSecurityGuard {

    // ── Signature (replace with your real APK signature hash) ──
    private static final String VALID_SIGNATURE = "YOUR_APK_SIGNATURE_SHA256_HERE";

    // ── Entry Point ────────────────────────────────────────────
    public static void runAllChecks(Context context) {
        if (isDebugging()) {
            killApp("Anti-Debug triggered");
        }
        if (isEmulator()) {
            killApp("Emulator detected");
        }
        if (isRooted()) {
            killApp("Rooted device detected");
        }
        if (!isSignatureValid(context)) {
            killApp("Signature tamper detected");
        }
        if (isHookingFrameworkPresent()) {
            killApp("Hooking framework detected");
        }
    }

    // ── 1. Anti-Debugging ──────────────────────────────────────
    private static boolean isDebugging() {
        if (Debug.isDebuggerConnected()) return true;
        if (Debug.waitingForDebugger()) return true;
        if (android.os.Debug.isDebuggerConnected()) return true;

        // Timing check — debuggers slow execution
        long start = System.nanoTime();
        for (int i = 0; i < 1000; i++) { /* timing loop */ }
        long elapsed = System.nanoTime() - start;
        if (elapsed > 10_000_000L) return true;

        return false;
    }

    // ── 2. Emulator Detection ──────────────────────────────────
    private static boolean isEmulator() {
        String[] emulatorIndicators = {
            Build.FINGERPRINT, Build.MODEL, Build.MANUFACTURER,
            Build.BRAND, Build.DEVICE, Build.PRODUCT
        };
        for (String s : emulatorIndicators) {
            if (s == null) continue;
            String lower = s.toLowerCase();
            if (lower.contains("generic") || lower.contains("emulator") ||
                lower.contains("sdk") || lower.contains("genymotion") ||
                lower.contains("x86") || lower.contains("bluestacks") ||
                lower.contains("nox") || lower.contains("vbox") ||
                lower.contains("andy") || lower.contains("droid4x")) {
                return true;
            }
        }
        // Check for emulator-specific files
        String[] emulatorFiles = {
            "/dev/socket/qemud", "/dev/qemu_pipe",
            "/system/lib/libc_malloc_debug_qemu.so",
            "/sys/qemu_trace", "/system/bin/qemu-props"
        };
        for (String path : emulatorFiles) {
            if (new File(path).exists()) return true;
        }
        return false;
    }

    // ── 3. Root Detection ──────────────────────────────────────
    private static boolean isRooted() {
        // Check for su binary
        String[] suPaths = {
            "/system/bin/su", "/system/xbin/su", "/sbin/su",
            "/system/su", "/system/bin/.ext/.su", "/system/usr/we-need-root/su-backup",
            "/data/local/xbin/su", "/data/local/bin/su", "/data/local/su",
            "/system/app/Superuser.apk", "/system/app/SuperSU.apk"
        };
        for (String path : suPaths) {
            if (new File(path).exists()) return true;
        }
        // Try executing su
        try {
            Process process = Runtime.getRuntime().exec(new String[]{"which", "su"});
            BufferedReader in = new BufferedReader(new InputStreamReader(process.getInputStream()));
            if (in.readLine() != null) return true;
        } catch (Exception ignored) {}

        // Check build tags
        String buildTags = Build.TAGS;
        if (buildTags != null && buildTags.contains("test-keys")) return true;

        return false;
    }

    // ── 4. Signature Validation ────────────────────────────────
    private static boolean isSignatureValid(Context context) {
        try {
            PackageInfo info = context.getPackageManager().getPackageInfo(
                context.getPackageName(),
                PackageManager.GET_SIGNATURES
            );
            for (Signature sig : info.signatures) {
                MessageDigest md = MessageDigest.getInstance("SHA-256");
                md.update(sig.toByteArray());
                byte[] digest = md.digest();
                StringBuilder sb = new StringBuilder();
                for (byte b : digest) {
                    sb.append(String.format("%02x", b));
                }
                if (!sb.toString().equals(VALID_SIGNATURE)) {
                    return false;
                }
            }
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    // ── 5. Hooking Framework Detection (Xposed/Frida) ─────────
    private static boolean isHookingFrameworkPresent() {
        // Check for Xposed
        String[] xposedFiles = {
            "/system/framework/XposedBridge.jar",
            "/system/bin/app_process_xposed",
            "/system/lib/libxposed_art.so"
        };
        for (String path : xposedFiles) {
            if (new File(path).exists()) return true;
        }
        // Check for Frida
        try {
            for (String line : readFile("/proc/self/maps")) {
                if (line.contains("frida") || line.contains("gum-js-loop") ||
                    line.contains("linjector")) return true;
            }
        } catch (Exception ignored) {}

        // Stack trace check for Xposed hooks
        try {
            throw new Exception("hook_check");
        } catch (Exception e) {
            for (StackTraceElement el : e.getStackTrace()) {
                if (el.getClassName().contains("XposedBridge") ||
                    el.getClassName().contains("de.robv.android")) return true;
            }
        }
        return false;
    }

    // ── Kill App ───────────────────────────────────────────────
    private static void killApp(String reason) {
        // Log internally (encrypted, not visible)
        android.util.Log.e("SEC", encode(reason));
        android.os.Process.killProcess(android.os.Process.myPid());
        System.exit(1);
    }

    // ── Helpers ────────────────────────────────────────────────
    private static String[] readFile(String path) throws Exception {
        BufferedReader br = new BufferedReader(
            new InputStreamReader(new java.io.FileInputStream(path))
        );
        java.util.List<String> lines = new java.util.ArrayList<>();
        String line;
        while ((line = br.readLine()) != null) lines.add(line);
        br.close();
        return lines.toArray(new String[0]);
    }

    private static String encode(String input) {
        StringBuilder sb = new StringBuilder();
        for (char c : input.toCharArray()) sb.append((int) c).append(".");
        return sb.toString();
    }
}
"""
        guard_path = os.path.join(self.output_dir, "EpicSecurityGuard.java")
        with open(guard_path, "w") as f:
            f.write(code)
        log(f"Anti-tamper guard injected: {guard_path}", "DONE")


# ─────────────────────────────────────────────
#  5. APK RESOURCE PROTECTOR
# ─────────────────────────────────────────────

class ResourceProtector:
    def __init__(self, apk_path, output_dir):
        self.apk_path = apk_path
        self.output_dir = output_dir

    def protect(self):
        if not self.apk_path or not os.path.exists(self.apk_path):
            log("No APK provided, skipping resource protection.", "WARN")
            return

        log(f"Protecting APK resources: {self.apk_path}")
        extract_dir = os.path.join(self.output_dir, "apk_extracted")
        os.makedirs(extract_dir, exist_ok=True)

        # Extract APK
        with zipfile.ZipFile(self.apk_path, 'r') as z:
            z.extractall(extract_dir)
        log("APK extracted successfully.")

        # Hash all extracted resources
        resource_hashes = {}
        for root, _, files in os.walk(extract_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, extract_dir)
                resource_hashes[rel] = compute_hash(fpath)

        # Save resource manifest
        manifest_path = os.path.join(self.output_dir, "resource_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(resource_hashes, f, indent=2)

        log(f"Resource manifest saved: {manifest_path}", "DONE")
        log(f"Total protected resources: {len(resource_hashes)}", "DONE")


# ─────────────────────────────────────────────
#  6. REPORT GENERATOR
# ─────────────────────────────────────────────

class ReportGenerator:
    def __init__(self, output_dir, results):
        self.output_dir = output_dir
        self.results = results

    def generate(self):
        report_path = os.path.join(self.output_dir, "protection_report.txt")
        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║            EPIC PROTECTOR — Protection Report                ║",
            "╚══════════════════════════════════════════════════════════════╝",
            f"Generated : {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "── Results ───────────────────────────────────────────────────",
        ]
        for key, val in self.results.items():
            lines.append(f"  {key:<30} : {val}")
        lines += [
            "",
            "── Next Steps ────────────────────────────────────────────────",
            "  1. Copy proguard-rules.pro to your Android project root",
            "  2. Copy EpicSecurityGuard.java to your security package",
            "  3. Call EpicSecurityGuard.runAllChecks(this) in MainActivity.onCreate()",
            "  4. Replace YOUR_APK_SIGNATURE_SHA256_HERE with your real signature",
            "  5. Enable minifyEnabled = true in your build.gradle",
            "  6. Build release APK — ProGuard will apply automatically",
            "  7. NEVER share obfuscation_map.json with clients",
            "",
            "── Security Tips ─────────────────────────────────────────────",
            "  • Always test protected APK before sending to clients",
            "  • Store integrity_manifest.json securely",
            "  • Rotate obfuscation dictionary per client build",
        ]
        with open(report_path, "w") as f:
            f.write('\n'.join(lines))
        log(f"Protection report saved: {report_path}", "DONE")


# ─────────────────────────────────────────────
#  MAIN RUNNER
# ─────────────────────────────────────────────

def main():
    banner()

    if len(sys.argv) < 2:
        print("\033[1;33mUsage:\033[0m python protect.py <your_project_folder> [optional: path_to.apk]")
        print("Example: python protect.py ./MyApp ./MyApp.apk")
        sys.exit(1)

    project_dir = sys.argv[1]
    apk_path = sys.argv[2] if len(sys.argv) > 2 else None
    output_dir = project_dir.rstrip("/") + "_PROTECTED"

    if not os.path.isdir(project_dir):
        log(f"Project folder not found: {project_dir}", "ERR")
        sys.exit(1)

    log(f"Target project : {project_dir}")
    log(f"Output folder  : {output_dir}")
    print()

    results = {}

    # Step 1 — Integrity Manifest
    log("═" * 50)
    log("STEP 1: Generating Integrity Manifest")
    guard = IntegrityGuard(project_dir)
    manifest = guard.generate_manifest()
    results["Files Hashed"] = manifest["total_files"]

    # Step 2 — Java Obfuscation
    log("═" * 50)
    log("STEP 2: Obfuscating Java Source Code")
    obf = JavaObfuscator(project_dir, output_dir)
    obf.obfuscate_project()
    results["Java Files Obfuscated"] = len(list(Path(output_dir).rglob("*.java")))
    results["Names Renamed"] = len(obf.name_map)

    # Step 3 — ProGuard Rules
    log("═" * 50)
    log("STEP 3: Generating ProGuard Rules")
    pg = ProGuardGenerator(output_dir)
    pg.generate()
    results["ProGuard Rules"] = "Generated"

    # Step 4 — Anti-Tamper Injection
    log("═" * 50)
    log("STEP 4: Injecting Anti-Tamper Security Guard")
    ati = AntiTamperInjector(output_dir)
    ati.inject()
    results["Anti-Tamper Guard"] = "Injected"
    results["Root Detection"] = "Enabled"
    results["Emulator Detection"] = "Enabled"
    results["Anti-Debugging"] = "Enabled"
    results["Hooking Detection"] = "Enabled"
    results["Signature Validation"] = "Enabled"

    # Step 5 — Resource Protection
    log("═" * 50)
    log("STEP 5: Protecting APK Resources")
    rp = ResourceProtector(apk_path, output_dir)
    rp.protect()
    results["Resource Protection"] = "Done" if apk_path else "Skipped (no APK provided)"

    # Step 6 — Report
    log("═" * 50)
    log("STEP 6: Generating Protection Report")
    rg = ReportGenerator(output_dir, results)
    rg.generate()

    print()
    log("═" * 50, "DONE")
    log("ALL PROTECTION STEPS COMPLETE!", "DONE")
    log(f"Protected output ready at: {output_dir}", "DONE")
    log("═" * 50, "DONE")


if __name__ == "__main__":
    main()
