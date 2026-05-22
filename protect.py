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
        self.name_map = {}  # original -> obfuscated

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

    def _encrypt_string_literals(self, content):
        """Replace plain strings with XOR-decoded calls (stub)."""
        def xor_encode(s, key=0x5A):
            encoded = [str(ord(c) ^ key) for c in s]
            return f"decodeStr(new int[]{{{','.join(encoded)}}}, 0x5A)"

        # Only encode simple short strings in assignments
        def replacer(match):
            s = match.group(1)
            if len(s) < 40 and s.isascii():
                return f'/* enc */ {xor_encode(s)}'
            return match.group(0)

        content = re.sub(r'"([^"\\]{1,39})"', replacer, content)
        return content

    def obfuscate_project(self):
        log("Starting Java source obfuscation...")
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        shutil.copytree(self.project_dir, self.output_dir)

        java_files = list(Path(self.output_dir).rglob("*.java"))
        log(f"Found {len(java_files)} Java files to obfuscate...")

        for java_file in java_files:
            try:
                with open(java_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                obfuscated = self._obfuscate_java_source(content)
                with open(java_file, "w", encoding="utf-8") as f:
                    f.write(obfuscated)
                log(f"  Obfuscated: {java_file.name}")
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
