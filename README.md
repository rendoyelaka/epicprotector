# EPIC PROTECTOR — Elite Master Hybrid Edition
## 24-Step Android APK Hardening Pipeline

Professional Android application hardening system operated through a Telegram bot. Upload an APK, select hardening operations, receive a fully protected deliverable.

---

## Repository Structure

```
EpicProtector/
├── epicprotector.py          ← Main bot + all 24-step pipeline engines
├── requirements.txt          ← Python dependencies
├── config.json               ← Base APK configuration storage
├── scores.json               ← Hardening score history
├── README.md                 ← This file
├── .gitignore                ← Repository hygiene
└── .github/
    └── workflows/
        └── bot.yml           ← GitHub Actions 24/7 runner
```

---

## 24-Step Pipeline

```
Step  1 — preflight_validation     Check tools and input before starting
Step  2 — strip_signature          Remove existing signature artifacts
Step  3 — decode_workspace         Decode APK to editable workspace
Step  4 — compliance_scan          Scan for issues before any changes
Step  5 — manifest_hardening       Strengthen AndroidManifest.xml
Step  6 — proguard_hardening       Add ProGuard rules
Step  7 — obfuscation              Fragment sensitive strings
Step  8 — safe_rename              Rename classes and methods safely
Step  9 — encryption               Encode asset and library files
Step 10 — security_guard           Inject runtime integrity checker
Step 11 — tamper_detection         Embed build-time verification hashes
Step 12 — dex_repackaging          Restructure DEX format
Step 13 — metadata_stripping       Remove build tool fingerprints
Step 14 — apk_size_optimizer       Remove unused files
Step 15 — aes_key_management       Generate AES-256 session key
Step 16 — rebuild_apk              Compile workspace back to APK  ← CRITICAL BOUNDARY
Step 17 — asset_compiler           SO Library Compiler — DEX → lib/ chunks
Step 18 — dex_encryption           SO Library Encryption — second encode layer
Step 19 — integrity_manifest       Hash final APK state for audit
Step 20 — keystore_generation      Generate fresh keystore per job
Step 21 — unique_fingerprint       Record unique build identity
Step 22 — zipalign                 Byte-align APK for installation
Step 23 — sign_apk                 Sign with v1+v2+v3 schemes  ← CRITICAL
Step 24 — protection_score         Calculate and report score
```

---

## SO Library Compiler System (Steps 17 + 18)

This is the core DEX protection system. It stores the encoded DEX inside native `.so` library files in the `lib/` ABI folders — not in `assets/`. Zero assets folder involvement.

### Build Time Flow (Steps 17 → 18)

```
Step 16 produces: rebuilt.apk containing real classes.dex

Step 17 — SO Library Compiler:
  1. Read real classes.dex from rebuilt APK
  2. Split into 5 equal chunks
  3. Encode each chunk with its own unique RC4 + XOR key pair
  4. Generate SHA-256 integrity hash per chunk
  5. Save all 5 chunks as one libcore.so into all 5 ABI folders:
       lib/arm64-v8a/libcore.so
       lib/armeabi-v7a/libcore.so
       lib/armeabi/libcore.so
       lib/x86/libcore.so
       lib/x86_64/libcore.so
  6. Compile bootstrap DEX with all keys embedded
  7. Replace classes.dex in APK with bootstrap loader (~4KB)
  8. Update AndroidManifest.xml → com.android.support.ep.NativeLoader

Step 18 — SO Library Encryption:
  1. Reads libcore.so from APK
  2. Applies second RC4 + XOR layer on each chunk payload
  3. Writes double-encoded libcore.so back to all 5 ABI folders
```

### Runtime Flow (On Device)

```
Android loads bootstrap classes.dex (~4KB)
    ↓
com.android.support.ep.NativeLoader.onCreate() runs
    ↓
Reads nativeLibraryDir/libcore.so into RAM
    ↓
Parses 5 chunk containers
    ↓
Per chunk: RC4 decode → XOR decode (in RAM only)
    ↓
Reassembles full DEX in RAM — never written to disk
    ↓
InMemoryDexClassLoader loads real application classes
    ↓
Real Application.onCreate() called — app opens normally
```

### Chunk Container Format (per chunk, 116-byte header)

```
Bytes  0-7:   SOLIBMRK marker
Bytes  8-11:  Chunk index (big-endian uint32)
Bytes 12-15:  Total chunks (big-endian uint32)
Bytes 16-19:  Original chunk size (big-endian uint32)
Bytes 20-51:  RC4 key (32 bytes)
Bytes 52-83:  XOR key (32 bytes)
Bytes 84-115: SHA-256 hash of encoded payload (32 bytes)
Bytes 116+:   Encoded chunk payload
```

### Security Properties

- Real DEX never on disk in readable form at runtime
- `.so` extension looks like a native library — not suspicious
- Each chunk has different RC4 + XOR keys — partial extraction useless
- SHA-256 per chunk — any tampering detected
- 5 ABI folders — works on every Android device architecture
- Static scanners see only the tiny bootstrap — result: CLEAN

---

## Tools Required on Server

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | GitHub Actions setup-python |
| Java JDK | 21 | apt default-jdk |
| apktool | 3.0.2 | wget from GitHub (cached) |
| smali assembler | libsmali-java | apt libsmali-java |
| zipalign | — | apt zipalign |
| apksigner | — | apt apksigner |
| keytool | JDK bundled | included with default-jdk |
| python-telegram-bot | 22.7 | pip |
| flask | 3.1.3 | pip |
| androguard | 4.1.4 | pip |

---

## Required GitHub Secrets

| Secret | Description |
|---|---|
| `BOT_TOKEN` | Telegram Bot API token |
| `ADMIN_ID` | Telegram user ID of the administrator |
| `GH_PAT` | GitHub Personal Access Token (for repo operations) |

---

*EPIC PROTECTOR — Elite Master Hybrid Edition*
*Version 7 — SO Library Compiler Edition — June 2026*
