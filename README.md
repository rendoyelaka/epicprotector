# 🛡️ EPIC PROTECTOR — Android App Protection Framework

> Full obfuscation + anti-tamper + runtime security for Android apps.  
> Built for Security Administrators protecting client applications.

---

## ✅ What It Does

| Feature | Description |
|---|---|
| **Code Obfuscation** | Renames all classes, methods, variables to unreadable names |
| **Junk Code Injection** | Injects fake decoy methods to confuse reverse engineers |
| **String Encryption** | Encrypts string literals using XOR encoding |
| **Anti-Tamper** | Detects if APK is modified and shuts down immediately |
| **Root Detection** | Blocks app from running on rooted devices |
| **Emulator Detection** | Blocks fake/test environments (BlueStacks, Genymotion, etc.) |
| **Anti-Debugging** | Detects and blocks debuggers (ADB, JDWP) |
| **Hooking Detection** | Detects Xposed / Frida hooking frameworks |
| **Signature Validation** | Verifies APK is signed by you — rejects repackaged APKs |
| **Integrity Manifest** | SHA-256 hash of every file — detects any modification |
| **Resource Protection** | Hashes all `.dex`, `.res`, `.classes` files |
| **ProGuard Rules** | Production-grade minification + obfuscation config |
| **Protection Report** | Full report of everything applied |

---

## 🚀 How To Use

### Step 1 — Run the protector on your project

```bash
python protect.py ./YourAndroidProject
```

With APK included:
```bash
python protect.py ./YourAndroidProject ./YourApp.apk
```

### Step 2 — Copy generated files into your Android project

```
YourAndroidProject_PROTECTED/
├── proguard-rules.pro        → Copy to your project root
├── EpicSecurityGuard.java    → Copy to your security package
├── obf_dict.txt              → Keep in project root
├── integrity_manifest.json   → Store securely
├── obfuscation_map.json      → ⚠️ KEEP PRIVATE — never share
└── protection_report.txt     → Your full protection summary
```

### Step 3 — Add to your MainActivity.java

```java
import com.epicprotector.security.EpicSecurityGuard;

public class MainActivity extends AppCompatActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 🛡️ Run all security checks on launch
        EpicSecurityGuard.runAllChecks(this);

        // ... rest of your code
    }
}
```

### Step 4 — Set your APK signature

Open `EpicSecurityGuard.java` and replace:
```java
private static final String VALID_SIGNATURE = "YOUR_APK_SIGNATURE_SHA256_HERE";
```
With your real signature. Get it by running:
```bash
keytool -printcert -jarfile YourApp.apk
```

### Step 5 — Enable ProGuard in build.gradle

```gradle
android {
    buildTypes {
        release {
            minifyEnabled true
            shrinkResources true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}
```

### Step 6 — Build your release APK

```bash
./gradlew assembleRelease
```

---

## ⚠️ Important Security Notes

- **NEVER** share `obfuscation_map.json` with clients
- **NEVER** share `obf_dict.txt` publicly
- Always test the protected APK before delivering to clients
- Generate a fresh obfuscation dictionary for each client build
- Store `integrity_manifest.json` in a secure private location

---

## 📋 Requirements

- Python 3.7+
- Android project with Java source files
- Android Studio (for building the final APK)

---

*EPIC PROTECTOR — Security Administrator Edition*
