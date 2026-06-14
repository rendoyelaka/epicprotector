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

## Telegram Bot UI

### Main Admin Panel
```
[ 🧪 Step-by-Step Test   ]
[ 📊 Protection History  ]
[ 📦 Base APK            ]
[ 📁 Workspace Browser   ]
```

### 📁 Workspace Browser
Inspect and download any folder from the decoded workspace at any stage:
```
[ 📁 smali/    ] [ 📁 assets/  ]
[ 📁 res/      ] [ 📁 lib/     ]
[ 📁 META-INF  ] [ 📦 Full Workspace ]
[ 📲 Download Current APK         ]
[ 📸 BEFORE Snapshot ] [ 📸 AFTER Snapshot ]
```

### Post-Phase Buttons
After every phase completes — additional options appear:
```
[ 📲 Get APK                     ]
[ 📲 Download APK at This Stage  ]
[ 📁 Browse Workspace Folders    ]
[ ✅ Continue to Next Phase      ]
```

### Before / After Comparison
Take a snapshot of `smali/` before any phase runs — then take another after — download both ZIPs and compare what changed:
```
[ 📸 BEFORE Snapshot ] → runs before obfuscation
[ 📸 AFTER Snapshot  ] → runs after obfuscation
[ 📥 Download BEFORE ]
[ 📥 Download AFTER  ]
```

---

## 24-Step Pipeline

```
Phase 1 — Setup & Analysis
  Step  1 — preflight_validation       Check tools and input before starting
  Step  2 — strip_signature            Remove existing signature artifacts
  Step  3 — decode_workspace           Decode APK to editable workspace
  Step  4 — compliance_scan            Scan for issues before any changes
  Step  5 — red_flag_renamer           Rename all red flag words to safe words
  Step  6 — manifest_component_renamer Rename component class names in manifest + smali

Phase 2 — Code Protection
  Step  7 — obfuscation                Fragment sensitive strings + rename locals
  Step  8 — safe_rename                Rename files and classes safely
  Step  9 — dex_repackaging            Move smali to classes2 + encode DEX in RAM
  Step 10 — encryption                 Encode asset and library files
  Step 11 — native_methods_obfuscation Handle native signatures before guard
  Step 12 — security_guard             Inject runtime integrity checker
  Step 13 — tamper_detection           Embed build-time verification hashes

Phase 3 — Resource & Cleanup
  Step 14 — dex_sourcefile_strip       Strip .source debug attributes
  Step 15 — resource_normalisation     Fix resources.arsc anomalies
  Step 16 — metadata_stripping         Remove build tool fingerprints
  Step 17 — apk_size_optimizer         Remove unused files
  Step 18 — aes_key_management         Display AES-256 session key

Phase 4 — Build
  Step 19 — rebuild_apk                Compile workspace back to APK  ← CRITICAL BOUNDARY
  Step 20 — manifest_entry_hardening   ZIP header protection — anti-analysis layer
  Step 21 — integrity_manifest         Hash final APK state for audit

Phase 5 — Sign
  Path A — GPP Optimised:  certificate_aging → unique_fingerprint → signing_lineage
  Path B — Standard:       keystore_generation → unique_fingerprint → zipalign → sign_apk

  Step 22 — certificate_aging          Aged certificate — Path A
  Step 23 — keystore_generation        Fresh keystore per job — Path B
  Step 24 — unique_fingerprint         Confirm identity — works with either path
  Step 25 — signing_lineage            V3 lineage — Path A
  Step 26 — zipalign                   Byte-align APK — Path B
  Step 27 — sign_apk                   Sign with v1+v2+v3 schemes — Path B  ← CRITICAL
  Step 28 — protection_score           Calculate and report score
```

---

## SO Library Compiler System (Steps 9 + 10)

Core DEX protection system. Stores encoded DEX inside the APK using multi-layer encoding.

### Build Time Flow

```
Step 19 produces: rebuilt.apk containing real classes.dex

Step 9 — DEX Repackaging:
  1. Read real classes.dex from workspace
  2. Apply primary RC4 encoding
  3. Apply secondary XOR encoding
  4. Move encoded DEX to classes2.dex
  5. Inject bootstrap stub loader as classes.dex

Step 10 — Encryption:
  1. Encode all assets/ and lib/ files with XOR session key
  2. Add security fields to workspace
```

### Runtime Flow (On Device)

```
Android loads bootstrap classes.dex
    ↓
Bootstrap stub decodes classes2.dex in RAM
    ↓
RC4 decode → XOR decode → real DEX in RAM
    ↓
InMemoryDexClassLoader loads real application classes
    ↓
Real Application.onCreate() called — app opens normally
```

### Security Properties

- Real DEX never on disk in readable form at runtime
- Double encoding layer — RC4 + XOR
- Static scanners see only tiny bootstrap — result: CLEAN
- Security guard validates APK signature at runtime

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
| python-telegram-bot | 21.9 | pip |
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
*Version 8 — Workspace Browser Edition — June 2026*
