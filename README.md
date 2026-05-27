# 🛡️ EPIC PROTECTOR — Elite Android Protection System

> 22-Step Selective Android APK Protection Pipeline  
> Telegram Bot Administration — Security Administrator Edition

---

## 🎯 What It Does

EPIC PROTECTOR is a professional Android APK protection system operated entirely through a Telegram bot. The Security Administrator uploads an APK, selects protection operations, and receives a fully protected APK — all through Telegram.

| Feature | Description |
|---------|-------------|
| 🧪 Pre-flight Validation | Verifies APK integrity before any operation runs |
| 🧹 Signature Stripping | Removes existing signature artifacts cleanly |
| 📂 Workspace Decode | Decodes APK into editable workspace via apktool |
| 🔍 Compliance Scan | Scans for risk words before protection begins |
| 🔒 Manifest Hardening | Strengthens AndroidManifest security flags |
| 📋 ProGuard Hardening | Adds aggressive ProGuard rules and shrinking config |
| ✏️ Safe Rename | Renames classes, methods and fields — safe targets only |
| 🔀 Obfuscation | Fragments sensitive strings into runtime-only pieces |
| 🛡️ Security Guard | Integrates runtime integrity and verification checks |
| 🛑 Tamper Detection | Embeds build-time hashes — detects post-delivery modification |
| 🔐 Encryption | AES-256-CBC encryption of assets and lib files |
| 🔁 DEX Repackaging | Restructures DEX to resist standard decompilation tools |
| 🧹 Metadata Stripping | Removes build tool fingerprints and compiler traces |
| 📦 APK Size Optimizer | Removes unused resources and dead files |
| 🔨 Rebuild APK | Rebuilds workspace into valid installable APK via apktool |
| 🔗 Integrity Manifest | SHA-256 hash of every file — full audit record |
| 🔑 AES Key Management | Generates and displays AES-256 key per job |
| 🗝️ Keystore Generation | Fresh unique keystore generated per job — destroyed after signing |
| 🔏 Unique Fingerprint | Randomised identity — CN, organisation, location, validity |
| ⚙️ zipalign | Byte-aligns APK for optimal installation performance |
| ✍️ Sign APK | Signs final APK with apksigner — production ready |
| 📊 Protection Score | Calculates protection strength score out of 100 |

---

## 🏗️ System Architecture

```
Security Administrator
        ↓
Telegram Bot (Admin Panel)
        ↓
┌─────────────────────────┐
│  🛡️ Protect APK         │  ← Full automatic pipeline with compliance review
│  🎛️ Manual Control Panel │  ← 22-step selective operation system
└─────────────────────────┘
        ↓
Protected APK delivered via Telegram
```

---

## 🚀 How To Use

### Step 1 — Set Up GitHub Secrets

In your GitHub repository go to:
`Settings → Secrets and variables → Actions → New repository secret`

Add these two secrets:

| Secret | Value |
|--------|-------|
| `BOT_TOKEN` | Your Telegram Bot token from @BotFather |
| `ADMIN_ID` | Your Telegram user ID |

### Step 2 — Push to GitHub

Push all files to the `main` branch. GitHub Actions will start the bot automatically.

### Step 3 — Open Telegram Bot

Send `/start` to your bot. You will see the admin panel:

```
🛡️ Protect APK
🎛️ Manual Control Panel
```

### Step 4 — Protect APK

**Option A — Protect APK (automatic pipeline):**
1. Tap 🛡️ Protect APK
2. Send your APK file
3. Review compliance scan findings
4. Approve — full protection runs automatically
5. Receive protected APK

**Option B — Manual Control Panel (selective):**
1. Tap 🎛️ Manual Control Panel
2. Send your APK file
3. Choose a preset or custom selection:
   - ⚡ Quick Sign Only
   - 🔒 Full Protection
   - 🎯 Custom — tick exactly what you want
4. Tap ✅ Apply Selected
5. Receive protected APK with full summary report

---

## 🎛️ Manual Control Panel — 22-Step Box

```
☑️ Select operations to apply:

☐ 🧪 Pre-flight Validation
☐ 🧹 Strip Signature
☐ 📂 Decode → Workspace
☐ 🔍 Compliance Scan
☐ 🔒 Manifest Hardening
☐ 📋 ProGuard Hardening
☐ ✏️ Safe Rename
☐ 🔀 Obfuscation
☐ 🛡️ Security Guard
☐ 🛑 Tamper Detection
☐ 🔐 Encryption
☐ 🔁 DEX Repackaging
☐ 🧹 Metadata Stripping
☐ 📦 APK Size Optimizer
☐ 🔨 Rebuild APK
☐ 🔗 Integrity Manifest
☐ 🔑 AES Key Management
☐ 🗝️ Keystore Generation
☐ 🔏 Unique Fingerprint
☐ ⚙️ zipalign
☐ ✍️ Sign APK
☐ 📊 Protection Score

☑️ Select All  |  ☐ Clear All
✅ Apply Selected
⬅️ Back
```

Operations always execute in correct pipeline order regardless of selection — **Operation Order Lock** enforced.

---

## 📊 Protection Score Grades

| Score | Grade |
|-------|-------|
| 95–100 | 🏆 ELITE |
| 85–94 | 🥇 Advanced |
| 70–84 | 🥈 Professional |
| 55–69 | 🥉 Standard |
| 0–54 | ⚠️ Basic |

---

## ⚙️ Pipeline Order — Why It Matters

Operations must always run in this exact sequence to produce a clean installable APK:

```
1  Pre-flight Validation     → confirm clean input before anything runs
2  Strip Signature           → must happen before decode
3  Decode → Workspace        → all operations work on workspace, not APK
4  Compliance Scan           → scan before any code changes
5  Manifest Hardening        → must edit XML before rebuild
6  ProGuard Hardening        → strengthen rules before rebuild
7  Safe Rename               → rename before obfuscation
8  Obfuscation               → after rename — before encryption
9  Security Guard            → after obfuscation — guard must not be scrambled
10 Tamper Detection          → after all code changes — hashes final state
11 Encryption                → last workspace operation
12 DEX Repackaging           → after all smali changes
13 Metadata Stripping        → last cleanup before rebuild
14 APK Size Optimizer        → clean before rebuild
15 Rebuild APK               → workspace → valid APK
16 Integrity Manifest        → hash final rebuilt state
17 AES Key Management        → key displayed before signing
18 Keystore Generation       → fresh keystore before signing
19 Unique Fingerprint        → identity assigned before signing
20 zipalign                  → must happen before signing
21 Sign APK                  → always last — any change after breaks signature
22 Protection Score          → calculated from applied operations
```

---

## 🔐 Keystore & Signing

Every job generates a **fresh unique keystore** with randomised identity:

```
CN:           Random professional name
Organisation: Random enterprise name
City / State: Random location
Country:      Random country code
Validity:     Random 3650–9125 days
```

The keystore is **generated in memory, used for signing, and immediately destroyed**. No keystore file is ever saved to disk or the repository.

---

## 📋 Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| python-telegram-bot | 21.9 |
| flask | 3.1.3 |
| Java (JDK) | Full JDK — not headless |
| apktool | 2.10.0 |
| zipalign | Android Build Tools |
| apksigner | Android Build Tools |
| keytool | Included with full JDK |

All system tools are installed automatically by GitHub Actions on every run.

---

## 📁 Repository Structure

```
EpicProtector/
├── epicprotector.py          ← Main bot + protection engine
├── requirements.txt          ← Python dependencies
├── README.md                 ← This file
├── .gitignore                ← Protects private output files
└── .github/
    └── workflows/
        └── bot.yml           ← GitHub Actions — 24/7 bot runner
```

---

## ⚠️ Important Notes

- Always test the protected APK on a real device before delivery
- Save the AES key displayed after each job — it is shown once only
- The bot runs 24/7 via GitHub Actions — auto-restarts every 5 hours
- Max APK size: 45MB (Telegram Bot API limit)
- All protection operations run in GitHub Actions — no local setup needed

---

## 🏭 Industries Served

- 🏥 Hospitals & Healthcare
- 🏨 Hotels & Hospitality
- 💊 Medical & Pharmaceutical
- 💾 Data Management Companies
- 💻 Software Companies

---

*EPIC PROTECTOR — Elite Master Hybrid Edition — Security Administrator*
