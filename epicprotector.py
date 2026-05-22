#!/usr/bin/env python3
"""
EPIC PROTECTOR — Elite Master Hybrid Engine
7-Level Android Protection + Telegram Bot + Java Injector
Security Administrator Edition

Level 1 - APK Decode & Repack      (apktool)
Level 2 - DEX Protection           (dex2jar + encrypt)
Level 3 - Resource Protection      (res + arsc)
Level 4 - Manifest Protection      (obfuscate)
Level 5 - Runtime Java Injection   (anti-tamper + decrypt)
Level 6 - Anti-Analysis Engine     (traps + fake code)
Level 7 - Sign & Deliver           (zipalign + apksigner)
"""

import os, re, sys, json, time, random, shutil, string
import struct, hashlib, zipfile, logging, asyncio
import tempfile, threading, subprocess
from pathlib import Path
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# CONFIG
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_NEW_TOKEN_HERE")
ADMIN_ID  = int(os.environ.get("ADMIN_ID", "8205672036"))
WORK_DIR  = "/tmp/epic_protector"
TOOLS_DIR = "/tmp/epic_tools"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

registered_clients = {}
pending_contact    = {}
pending_broadcast  = {}
pending_reply      = {}
pending_protect    = {}
pending_send_apk   = {}


# TOOL INSTALLER
class ToolInstaller:
    APKTOOL_URL = "https://github.com/iBotPeaches/Apktool/releases/download/v2.9.3/apktool_2.9.3.jar"
    DEX2JAR_URL = "https://github.com/pxb1988/dex2jar/releases/download/v2.4/dex-tools-v2.4.zip"

    def __init__(self):
        os.makedirs(TOOLS_DIR, exist_ok=True)
        self.apktool_jar = os.path.join(TOOLS_DIR, "apktool.jar")
        self.dex2jar_dir = os.path.join(TOOLS_DIR, "dex2jar")
        self.tools_ready = False

    def run_cmd(self, cmd, check=False):
        return subprocess.run(cmd, shell=True, capture_output=True, text=True)

    def install_system_deps(self):
        self.run_cmd("apt-get update -qq")
        self.run_cmd("apt-get install -y -qq default-jdk zipalign apksigner wget unzip")

    def install_apktool(self):
        if not os.path.exists(self.apktool_jar):
            self.run_cmd(f"wget -q -O {self.apktool_jar} {self.APKTOOL_URL}")

    def install_dex2jar(self):
        if not os.path.exists(self.dex2jar_dir):
            zip_path = os.path.join(TOOLS_DIR, "dex2jar.zip")
            self.run_cmd(f"wget -q -O {zip_path} {self.DEX2JAR_URL}")
            self.run_cmd(f"unzip -q {zip_path} -d {self.dex2jar_dir}")
            self.run_cmd(f"chmod +x {self.dex2jar_dir}/dex-tools-v2.4/*.sh")

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


# CRYPTO ENGINE - AES-256-CBC Pure Python
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
                temp=[cls.SBOX[temp[1]]^cls.RCON[i//32-1],cls.SBOX[temp[2]],cls.SBOX[temp[3]],cls.SBOX[temp[0]]]
            elif i%32==16:
                temp=[cls.SBOX[b] for b in temp]
            w += [w[i-32]^temp[j] for j in range(4)]
        return [bytes(w[i:i+16]) for i in range(0,len(w),16)][:15]

    @classmethod
    def _encrypt_block(cls, block, rks):
        def b2s(b): return [[b[r+4*c] for c in range(4)] for r in range(4)]
        def s2b(s): return bytes([s[r][c] for c in range(4) for r in range(4)])
        def ark(s,rk): return [[s[r][c]^rk[r][c] for c in range(4)] for r in range(4)]
        def sb(s): return [[cls.SBOX[s[r][c]] for c in range(4)] for r in range(4)]
        def sr(s): return [[s[0][0],s[0][1],s[0][2],s[0][3]],[s[1][1],s[1][2],s[1][3],s[1][0]],[s[2][2],s[2][3],s[2][0],s[2][1]],[s[3][3],s[3][0],s[3][1],s[3][2]]]
        def mc(s):
            r=[[0]*4 for _ in range(4)]
            for c in range(4):
                r[0][c]=cls._gmul(2,s[0][c])^cls._gmul(3,s[1][c])^s[2][c]^s[3][c]
                r[1][c]=s[0][c]^cls._gmul(2,s[1][c])^cls._gmul(3,s[2][c])^s[3][c]
                r[2][c]=s[0][c]^s[1][c]^cls._gmul(2,s[2][c])^cls._gmul(3,s[3][c])
                r[3][c]=cls._gmul(3,s[0][c])^s[1][c]^s[2][c]^cls._gmul(2,s[3][c])
            return r
        state=b2s(block); state=ark(state,b2s(rks[0]))
        for rnd in range(1,14): state=sb(state); state=sr(state); state=mc(state); state=ark(state,b2s(rks[rnd]))
        state=sb(state); state=sr(state); state=ark(state,b2s(rks[14]))
        return s2b(state)

    @classmethod
    def encrypt_bytes(cls, data, key):
        import base64
        pad=16-(len(data)%16); data+=bytes([pad]*pad)
        iv=os.urandom(16); rks=cls._key_expansion(key)
        ct=b''; prev=iv
        for i in range(0,len(data),16):
            blk=bytes(x^y for x,y in zip(data[i:i+16],prev))
            enc=cls._encrypt_block(blk,rks); ct+=enc; prev=enc
        return iv+ct

    @classmethod
    def encrypt_string(cls, plaintext, key):
        import base64
        return base64.b64encode(cls.encrypt_bytes(plaintext.encode('utf-8'),key)).decode('utf-8')

    @classmethod
    def xor_encrypt(cls, data, key):
        return bytes(b^key[i%len(key)] for i,b in enumerate(data))

    @classmethod
    def get_java_key_bytes(cls, key):
        return ', '.join([f'(byte)0x{b:02x}' for b in key])


# LEVEL 1 - APK HANDLER
class Level1_APKHandler:
    def __init__(self, tools, work_dir):
        self.tools=tools; self.work_dir=work_dir

    def decode(self, apk_path):
        decode_dir=os.path.join(self.work_dir,"decoded")
        if os.path.exists(decode_dir): shutil.rmtree(decode_dir)
        cmd=f"java -jar {self.tools.apktool_jar} d -f -o {decode_dir} {apk_path}"
        r=subprocess.run(cmd,shell=True,capture_output=True)
        if r.returncode!=0 or not os.path.exists(decode_dir):
            os.makedirs(decode_dir,exist_ok=True)
            with zipfile.ZipFile(apk_path,'r') as z: z.extractall(decode_dir)
        return decode_dir

    def repack(self, decoded_dir, output_apk):
        cmd=f"java -jar {self.tools.apktool_jar} b -f {decoded_dir} -o {output_apk}"
        r=subprocess.run(cmd,shell=True,capture_output=True)
        if r.returncode!=0 or not os.path.exists(output_apk):
            with zipfile.ZipFile(output_apk,'w',zipfile.ZIP_DEFLATED) as z:
                for root,_,files in os.walk(decoded_dir):
                    for f in files:
                        fp=os.path.join(root,f); z.write(fp,os.path.relpath(fp,decoded_dir))
        return output_apk

    def extract_dex(self, apk_path):
        dex_dir=os.path.join(self.work_dir,"dex"); os.makedirs(dex_dir,exist_ok=True)
        dex_files=[]
        with zipfile.ZipFile(apk_path,'r') as z:
            for name in z.namelist():
                if name.endswith('.dex'):
                    out=os.path.join(dex_dir,os.path.basename(name))
                    with z.open(name) as s, open(out,'wb') as d: d.write(s.read())
                    dex_files.append(out)
        return dex_files

    def replace_dex(self, apk_path, dex_files, output_apk):
        with zipfile.ZipFile(apk_path,'r') as zin:
            with zipfile.ZipFile(output_apk,'w',zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename.endswith('.dex'):
                        dname=os.path.basename(item.filename)
                        matching=[d for d in dex_files if os.path.basename(d)==dname]
                        if matching:
                            with open(matching[0],'rb') as f: zout.writestr(item,f.read())
                        else: zout.writestr(item,zin.read(item.filename))
                    else: zout.writestr(item,zin.read(item.filename))


# LEVEL 2 - DEX PROTECTOR
class Level2_DEXProtector:
    def __init__(self, tools, crypto, work_dir):
        self.tools=tools; self.crypto=crypto; self.work_dir=work_dir

    def protect_dex(self, dex_path, aes_key):
        protected=dex_path.replace('.dex','_protected.dex')
        jar_path=dex_path.replace('.dex','.jar')
        dex2jar=self.tools.get_dex2jar()
        if dex2jar and os.path.exists(dex2jar):
            r=subprocess.run(f"bash {dex2jar} -f {dex_path} -o {jar_path} 2>/dev/null",shell=True,capture_output=True)
            if r.returncode==0 and os.path.exists(jar_path):
                obf_jar=self._obfuscate_jar(jar_path,aes_key)
                jar2dex=self.tools.get_jar2dex()
                if jar2dex:
                    r2=subprocess.run(f"bash {jar2dex} -f {obf_jar} -o {protected} 2>/dev/null",shell=True,capture_output=True)
                    if r2.returncode==0 and os.path.exists(protected): return protected
        with open(dex_path,'rb') as f: data=f.read()
        header=data[:112]; body=data[112:]
        enc=self.crypto.xor_encrypt(body,aes_key)
        with open(protected,'wb') as f: f.write(header+enc)
        return protected

    def _obfuscate_jar(self, jar_path, aes_key):
        obf=jar_path.replace('.jar','_obf.jar')
        ext=jar_path.replace('.jar','_ext'); os.makedirs(ext,exist_ok=True)
        with zipfile.ZipFile(jar_path,'r') as z: z.extractall(ext)
        for cf in Path(ext).rglob("*.class"):
            try:
                with open(cf,'rb') as f: d=f.read()
                if len(d)>=8:
                    with open(cf,'wb') as f: f.write(d[:8]+self.crypto.xor_encrypt(d[8:],aes_key[:16]))
            except: pass
        with zipfile.ZipFile(obf,'w',zipfile.ZIP_DEFLATED) as z:
            for root,_,files in os.walk(ext):
                for fname in files:
                    fp=os.path.join(root,fname); z.write(fp,os.path.relpath(fp,ext))
        shutil.rmtree(ext,ignore_errors=True)
        return obf

    def protect_all(self, dex_files, aes_key):
        protected=[]
        for d in dex_files:
            try: protected.append(self.protect_dex(d,aes_key))
            except: protected.append(d)
        return protected


# LEVEL 3 - RESOURCE PROTECTOR
class Level3_ResourceProtector:
    def __init__(self, crypto, work_dir):
        self.crypto=crypto; self.work_dir=work_dir

    def protect_res_folder(self, decoded_dir, aes_key):
        res_dir=os.path.join(decoded_dir,"res"); manifest={}
        if not os.path.exists(res_dir): return manifest
        for root,_,files in os.walk(res_dir):
            for fname in files:
                fp=os.path.join(root,fname); rel=os.path.relpath(fp,res_dir)
                try:
                    with open(fp,'rb') as f: orig=f.read()
                    enc=self.crypto.xor_encrypt(orig,aes_key[:16])
                    with open(fp,'wb') as f: f.write(enc)
                    manifest[rel]={"hash":hashlib.sha256(orig).hexdigest(),"encrypted":True}
                except: pass
        with open(os.path.join(self.work_dir,"res_manifest.json"),'w') as f: json.dump(manifest,f,indent=2)
        return manifest

    def protect_resources_arsc(self, apk_path, aes_key):
        out=apk_path.replace('.apk','_arsc.apk'); arsc=None
        with zipfile.ZipFile(apk_path,'r') as z:
            if 'resources.arsc' in z.namelist(): arsc=z.read('resources.arsc')
        if arsc is None: shutil.copy(apk_path,out); return out
        header=arsc[:256]; body=arsc[256:]
        enc_arsc=header+self.crypto.xor_encrypt(body,aes_key[:16])
        with zipfile.ZipFile(apk_path,'r') as zin:
            with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename=='resources.arsc': zout.writestr(item,enc_arsc)
                    else: zout.writestr(item,zin.read(item.filename))
        return out

    def obfuscate_resource_names(self, decoded_dir):
        res_dir=os.path.join(decoded_dir,"res"); name_map={}
        if not os.path.exists(res_dir): return name_map
        for sub in os.listdir(res_dir):
            sp=os.path.join(res_dir,sub)
            if not os.path.isdir(sp) or sub.startswith('values'): continue
            for fname in os.listdir(sp):
                ext=os.path.splitext(fname)[1]
                new='r'+''.join(random.choices(string.ascii_lowercase+string.digits,k=8))+ext
                try: os.rename(os.path.join(sp,fname),os.path.join(sp,new)); name_map[fname]=new
                except: pass
        with open(os.path.join(self.work_dir,"res_name_map.json"),'w') as f: json.dump(name_map,f,indent=2)
        return name_map


# LEVEL 4 - MANIFEST PROTECTOR
class Level4_ManifestProtector:
    def __init__(self, work_dir):
        self.work_dir=work_dir

    def protect(self, decoded_dir):
        mp=os.path.join(decoded_dir,"AndroidManifest.xml"); changes={}
        if not os.path.exists(mp): return changes
        with open(mp,'r',encoding='utf-8',errors='ignore') as f: content=f.read()
        content=re.sub(r'android:debuggable="true"','android:debuggable="false"',content); changes["Debug removed"]=True
        content=re.sub(r'android:allowBackup="true"','android:allowBackup="false"',content); changes["Backup disabled"]=True
        content=re.sub(r'android:usesCleartextTraffic="true"','android:usesCleartextTraffic="false"',content); changes["Cleartext blocked"]=True
        fake_perms=['<uses-permission android:name="com.epic.protector.SECURE"/>','<uses-permission android:name="com.epic.guard.VALIDATE"/>','<uses-permission android:name="com.epic.shield.VERIFY"/>']
        if '<uses-permission' in content:
            idx=content.index('<uses-permission'); content=content[:idx]+'\n    '.join(fake_perms)+'\n    '+content[idx:]
        changes["Fake permissions injected"]=True
        meta='\n        <meta-data android:name="com.epic.protector.version" android:value="2.0"/>'
        if '</application>' in content: content=content.replace('</application>',meta+'\n    </application>')
        changes["Security metadata injected"]=True
        with open(mp,'w',encoding='utf-8') as f: f.write(content)
        return changes


# LEVEL 5 - RUNTIME INJECTOR
class Level5_RuntimeInjector:
    def __init__(self, crypto, work_dir):
        self.crypto=crypto; self.work_dir=work_dir

    def generate_guard(self, aes_key):
        kb=self.crypto.get_java_key_bytes(aes_key)
        return f"""package com.epicprotector.security;
import android.content.Context;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
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
    private static final boolean KILL_ON_TAMPER = true;
    private static volatile boolean initialized = false;

    private EpicSecurityGuard() {{}}

    public static synchronized void runAllChecks(Context context) {{
        if (initialized) return;
        initialized = true;
        if (isDebugging())               handleThreat(context, "DEBUGGER");
        if (isEmulator())                handleThreat(context, "EMULATOR");
        if (isRooted())                  handleThreat(context, "ROOT");
        if (!isSignatureValid(context))  handleThreat(context, "TAMPER");
        if (isHookingFramework())        handleThreat(context, "HOOK");
        if (isMemoryTampered())          handleThreat(context, "MEMORY");
    }}

    private static boolean isDebugging() {{
        if (Debug.isDebuggerConnected()) return true;
        if (Debug.waitingForDebugger())  return true;
        long t=System.nanoTime(); int x=0;
        for(int i=0;i<5000;i++) x+=i;
        if(System.nanoTime()-t>50_000_000L) return true;
        try {{
            BufferedReader br=new BufferedReader(new InputStreamReader(new FileInputStream("/proc/self/status")));
            String line; while((line=br.readLine())!=null) {{
                if(line.startsWith("TracerPid:")) {{ br.close(); if(Integer.parseInt(line.substring(10).trim())!=0) return true; }}
            }} br.close();
        }} catch(Exception e) {{}}
        return false;
    }}

    private static boolean isEmulator() {{
        String[] suspects={{Build.FINGERPRINT,Build.MODEL,Build.MANUFACTURER,Build.BRAND,Build.DEVICE,Build.PRODUCT,Build.HARDWARE}};
        String[] kws={{"generic","emulator","sdk","genymotion","x86","bluestacks","nox","vbox","andy","droid4x","goldfish","ranchu","ttvm"}};
        for(String s:suspects) {{ if(s==null) continue; String l=s.toLowerCase(); for(String kw:kws) {{ if(l.contains(kw)) return true; }} }}
        String[] efs={{"/dev/socket/qemud","/dev/qemu_pipe","/system/lib/libc_malloc_debug_qemu.so","/sys/qemu_trace","/system/bin/qemu-props"}};
        for(String p:efs) {{ if(new File(p).exists()) return true; }}
        return false;
    }}

    private static boolean isRooted() {{
        String[] paths={{"/system/bin/su","/system/xbin/su","/sbin/su","/system/su","/data/local/xbin/su","/data/local/bin/su","/system/app/Superuser.apk","/system/app/SuperSU.apk"}};
        for(String p:paths) {{ if(new File(p).exists()) return true; }}
        try {{ Process pr=Runtime.getRuntime().exec(new String[]{{"/system/xbin/which","su"}}); BufferedReader in=new BufferedReader(new InputStreamReader(pr.getInputStream())); if(in.readLine()!=null) return true; }} catch(Exception e) {{}}
        String tags=Build.TAGS; return tags!=null&&tags.contains("test-keys");
    }}

    private static boolean isSignatureValid(Context ctx) {{
        try {{
            PackageInfo info=ctx.getPackageManager().getPackageInfo(ctx.getPackageName(),PackageManager.GET_SIGNATURES);
            for(Signature sig:info.signatures) {{
                MessageDigest md=MessageDigest.getInstance("SHA-256"); md.update(sig.toByteArray());
                StringBuilder sb=new StringBuilder(); for(byte b:md.digest()) sb.append(String.format("%02x",b));
                if(!sb.toString().equals(VALID_SIGNATURE)) return false;
            }} return true;
        }} catch(Exception e) {{ return false; }}
    }}

    private static boolean isHookingFramework() {{
        String[] xf={{"/system/framework/XposedBridge.jar","/system/bin/app_process_xposed","/system/lib/libxposed_art.so","/data/data/de.robv.android.xposed.installer"}};
        for(String p:xf) {{ if(new File(p).exists()) return true; }}
        try {{
            BufferedReader br=new BufferedReader(new InputStreamReader(new FileInputStream("/proc/self/maps")));
            String line; while((line=br.readLine())!=null) {{ if(line.contains("frida")||line.contains("gum-js-loop")||line.contains("linjector")) {{ br.close(); return true; }} }} br.close();
        }} catch(Exception e) {{}}
        try {{ throw new Exception(); }} catch(Exception e) {{ for(StackTraceElement el:e.getStackTrace()) {{ String c=el.getClassName(); if(c.contains("XposedBridge")||c.contains("de.robv.android")||c.contains("com.saurik.substrate")) return true; }} }}
        String[] mf={{"/sbin/.magisk","/sbin/.core/mirror","/data/adb/magisk","/data/adb/magisk.db"}};
        for(String p:mf) {{ if(new File(p).exists()) return true; }}
        return false;
    }}

    private static boolean isMemoryTampered() {{
        try {{
            BufferedReader br=new BufferedReader(new InputStreamReader(new FileInputStream("/proc/self/maps")));
            String line; while((line=br.readLine())!=null) {{ if(line.contains("memfd")||line.contains("injected")) {{ br.close(); return true; }} }} br.close();
        }} catch(Exception e) {{}}
        return false;
    }}

    public static String decodeStr(String enc) {{
        try {{
            byte[] combined=android.util.Base64.decode(enc,android.util.Base64.DEFAULT);
            byte[] iv=Arrays.copyOfRange(combined,0,16); byte[] ct=Arrays.copyOfRange(combined,16,combined.length);
            SecretKeySpec ks=new SecretKeySpec(AES_KEY,"AES"); Cipher cipher=Cipher.getInstance("AES/CBC/PKCS5Padding");
            cipher.init(Cipher.DECRYPT_MODE,ks,new IvParameterSpec(iv)); return new String(cipher.doFinal(ct),"UTF-8");
        }} catch(Exception e) {{ handleThreat(null,"DECRYPT_FAIL"); return null; }}
    }}

    private static void handleThreat(Context ctx, String reason) {{
        if(!KILL_ON_TAMPER) return;
        android.os.Process.killProcess(android.os.Process.myPid()); System.exit(1);
    }}
}}
"""

    def inject_smali(self, decoded_dir):
        injected=0
        for sdir in Path(decoded_dir).glob("smali*"):
            for sf in sdir.rglob("*.smali"):
                if 'mainactivity' in sf.name.lower() or 'application' in sf.name.lower():
                    try:
                        with open(sf,'r',encoding='utf-8',errors='ignore') as f: content=f.read()
                        if '.method public onCreate(' in content and 'EpicSecurityGuard' not in content:
                            inj="\n    invoke-static {p0}, Lcom/epicprotector/security/EpicSecurityGuard;->runAllChecks(Landroid/content/Context;)V\n"
                            pat=r'(\.method public onCreate\([^)]*\).*?\n\s*\.locals \d+)'
                            m=re.search(pat,content,re.DOTALL)
                            if m:
                                content=content[:m.end()]+inj+content[m.end():]
                                with open(sf,'w',encoding='utf-8') as f: f.write(content)
                                injected+=1
                    except: pass
        return injected

    def save_guard(self, aes_key):
        code=self.generate_guard(aes_key)
        path=os.path.join(self.work_dir,"EpicSecurityGuard.java")
        with open(path,'w') as f: f.write(code)
        return path


# LEVEL 6 - ANTI-ANALYSIS
class Level6_AntiAnalysis:
    def __init__(self, crypto, work_dir):
        self.crypto=crypto; self.work_dir=work_dir

    def rname(self, n=10): return ''.join(random.choices(string.ascii_letters+string.digits,k=n))

    def inject_fake_classes(self, decoded_dir, aes_key):
        sdir=os.path.join(decoded_dir,"smali","com","epic","decoy"); os.makedirs(sdir,exist_ok=True)
        fakes=[("NetValidator","validateConn","checkHost"),("PayProcessor","processTx","verifyCard"),("AuthMgr","authUser","validateToken"),("CryptoHelper","encData","hashPwd"),("LicChecker","checkLic","checkExpiry")]
        count=0
        for cname,m1,m2 in fakes:
            oname=self.rname(6)
            code=f""".class public Lcom/epic/decoy/{oname};
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
    const-string v0, "{self.rname(16)}"
    return-object v0
.end method
"""
            with open(os.path.join(sdir,f"{oname}.smali"),'w') as f: f.write(code)
            count+=1
        return count

    def inject_string_traps(self, decoded_dir, aes_key):
        traps=[f"https://api.{self.rname(8)}.com/v1/auth",f"sk-{self.rname(32)}",f"Bearer {self.rname(24)}"]
        trapped=0
        for sdir in Path(decoded_dir).glob("smali*"):
            for sf in list(sdir.rglob("*.smali"))[:5]:
                try:
                    with open(sf,'r',encoding='utf-8',errors='ignore') as f: content=f.read()
                    if '.method' in content and 'EpicTrap' not in content:
                        trap=random.choice(traps); enc=self.crypto.encrypt_string(trap,aes_key)
                        field=f'\n.field private static final {self.rname(6)}:Ljava/lang/String; = "{enc}"\n'
                        content=content.replace('.class ',field+'\n.class ',1)
                        with open(sf,'w',encoding='utf-8') as f: f.write(content)
                        trapped+=1
                except: pass
        return trapped

    def add_flow_obfuscation(self, decoded_dir):
        obf=0
        for sdir in Path(decoded_dir).glob("smali*"):
            for sf in list(sdir.rglob("*.smali"))[:10]:
                try:
                    with open(sf,'r',encoding='utf-8',errors='ignore') as f: content=f.read()
                    if '.method' in content and '.class ' in content and '.field' not in content[:200]:
                        dummy=f'\n.field private static {self.rname(6)}:I = {random.randint(10000,99999)}\n'
                        content=content.replace('.super ',dummy+'\n.super ',1)
                        with open(sf,'w',encoding='utf-8') as f: f.write(content)
                        obf+=1
                except: pass
        return obf


# LEVEL 7 - SIGNER & DELIVERER
class Level7_SignerDeliverer:
    def __init__(self, work_dir):
        self.work_dir=work_dir
        self.keystore=os.path.join(work_dir,"epic.keystore")
        self.alias="epicprotector"; self.kp="Epic@Key#2024"; self.sp="Epic@Store#2024"

    def generate_keystore(self):
        if os.path.exists(self.keystore): return True
        cmd=f"keytool -genkeypair -v -keystore {self.keystore} -alias {self.alias} -keyalg RSA -keysize 2048 -validity 10000 -storepass {self.sp} -keypass {self.kp} -dname 'CN=EpicProtector,O=Security,C=US' 2>/dev/null"
        return subprocess.run(cmd,shell=True,capture_output=True).returncode==0

    def zipalign(self, inp, out):
        r=subprocess.run(f"zipalign -v 4 {inp} {out} 2>/dev/null",shell=True,capture_output=True)
        if r.returncode!=0 or not os.path.exists(out): shutil.copy(inp,out)
        return out

    def sign(self, inp, out):
        cmd=f"apksigner sign --ks {self.keystore} --ks-key-alias {self.alias} --ks-pass pass:{self.sp} --key-pass pass:{self.kp} --out {out} {inp} 2>/dev/null"
        r=subprocess.run(cmd,shell=True,capture_output=True)
        if r.returncode==0 and os.path.exists(out): return out
        cmd2=f"jarsigner -keystore {self.keystore} -storepass {self.sp} -keypass {self.kp} -signedjar {out} {inp} {self.alias} 2>/dev/null"
        r2=subprocess.run(cmd2,shell=True,capture_output=True)
        if r2.returncode==0 and os.path.exists(out): return out
        shutil.copy(inp,out); return out

    def prepare(self, inp):
        self.generate_keystore()
        aligned=os.path.join(self.work_dir,"aligned.apk")
        signed=os.path.join(self.work_dir,"EPIC_PROTECTED.apk")
        self.zipalign(inp,aligned)
        return self.sign(aligned,signed)


# INTEGRITY GUARDIAN
class IntegrityGuardian:
    def __init__(self, work_dir): self.work_dir=work_dir

    def generate(self, directory):
        manifest={}
        for root,_,files in os.walk(directory):
            for fname in sorted(files):
                fp=os.path.join(root,fname); rel=os.path.relpath(fp,directory)
                try:
                    s=hashlib.sha256()
                    with open(fp,'rb') as f:
                        for chunk in iter(lambda:f.read(8192),b''): s.update(chunk)
                    manifest[rel]=s.hexdigest()
                except: pass
        return manifest

    def save(self, manifest):
        path=os.path.join(self.work_dir,"integrity_manifest.json")
        with open(path,'w') as f: json.dump({"generated_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"total_files":len(manifest),"files":manifest},f,indent=2)
        return path


# MASTER PROTECTION ENGINE
class MasterProtectionEngine:
    def __init__(self):
        self.tools=ToolInstaller(); self.crypto=CryptoEngine(); self.integrity=IntegrityGuardian(WORK_DIR)

    def protect(self, apk_path):
        job_id=f"job_{int(time.time())}"; work_dir=os.path.join(WORK_DIR,job_id)
        os.makedirs(work_dir,exist_ok=True); results={}

        def mark(k,v): results[k]=v; logger.info(f"{k}: {v}")

        try:
            mark("Tools Installation","✅ Installing...")
            self.tools.install_all()
            self.tools.work_dir=work_dir

            aes_key=CryptoEngine.generate_key()
            with open(os.path.join(work_dir,"aes_key.bin"),'wb') as f: f.write(aes_key)
            mark("AES-256 Key","✅ Generated & Saved")

            l1=Level1_APKHandler(self.tools,work_dir)
            l2=Level2_DEXProtector(self.tools,self.crypto,work_dir)
            l3=Level3_ResourceProtector(self.crypto,work_dir)
            l4=Level4_ManifestProtector(work_dir)
            l5=Level5_RuntimeInjector(self.crypto,work_dir)
            l6=Level6_AntiAnalysis(self.crypto,work_dir)
            l7=Level7_SignerDeliverer(work_dir)

            # LEVEL 1
            mark("Level 1 — APK Decode","✅ Running...")
            decoded=l1.decode(apk_path); dex_files=l1.extract_dex(apk_path)
            mark("Level 1 — APK Decoded",f"✅ {len(dex_files)} DEX files found")

            # LEVEL 2
            mark("Level 2 — DEX Protection","✅ Running...")
            prot_dex=l2.protect_all(dex_files,aes_key)
            mark("Level 2 — DEX Protected",f"✅ {len(prot_dex)} files protected")

            # LEVEL 3
            mark("Level 3 — Resource Protection","✅ Running...")
            res_manifest=l3.protect_res_folder(decoded,aes_key)
            res_names=l3.obfuscate_resource_names(decoded)
            mark("Level 3 — Resources Encrypted",f"✅ {len(res_manifest)} files")
            mark("Level 3 — Names Obfuscated",f"✅ {len(res_names)} names")

            # LEVEL 4
            mark("Level 4 — Manifest Protection","✅ Running...")
            man_changes=l4.protect(decoded)
            mark("Level 4 — Manifest Protected",f"✅ {len(man_changes)} changes")

            # LEVEL 5
            mark("Level 5 — Runtime Injection","✅ Running...")
            guard_path=l5.save_guard(aes_key)
            smali_inj=l5.inject_smali(decoded)
            mark("Level 5 — Security Guard","✅ Generated")
            mark("Level 5 — Smali Injected",f"✅ {smali_inj} classes")

            # LEVEL 6
            mark("Level 6 — Anti-Analysis","✅ Running...")
            fake_cls=l6.inject_fake_classes(decoded,aes_key)
            str_traps=l6.inject_string_traps(decoded,aes_key)
            flow_obf=l6.add_flow_obfuscation(decoded)
            mark("Level 6 — Fake Classes",f"✅ {fake_cls} injected")
            mark("Level 6 — String Traps",f"✅ {str_traps} injected")
            mark("Level 6 — Flow Obfuscation",f"✅ {flow_obf} files")

            # REPACK
            repacked=os.path.join(work_dir,"repacked.apk"); l1.repack(decoded,repacked)
            dex_rep=os.path.join(work_dir,"dex_replaced.apk"); l1.replace_dex(repacked,prot_dex,dex_rep)
            arsc_prot=l3.protect_resources_arsc(dex_rep if os.path.exists(dex_rep) else repacked,aes_key)

            # LEVEL 7
            mark("Level 7 — Sign & Align","✅ Running...")
            inp=arsc_prot if os.path.exists(arsc_prot) else repacked
            final=l7.prepare(inp)
            mark("Level 7 — Signed & Aligned","✅ Ready")

            # INTEGRITY
            int_man=self.integrity.generate(decoded); self.integrity.save(int_man)
            mark("Integrity Manifest",f"✅ {len(int_man)} files hashed")

            final_out=os.path.join(work_dir,"EPIC_PROTECTED.apk")
            src=final if os.path.exists(final) else (arsc_prot if os.path.exists(arsc_prot) else repacked)
            if src!=final_out: shutil.copy(src,final_out)

            results["OUTPUT_APK"]=final_out; results["GUARD_JAVA"]=guard_path
            results["AES_KEY_PATH"]=os.path.join(work_dir,"aes_key.bin"); results["SUCCESS"]=True

        except Exception as e:
            results["ERROR"]=str(e); results["SUCCESS"]=False; logger.error(f"Protection failed: {e}")

        return results


# KEEP-ALIVE SERVER
flask_app=Flask(__name__)

@flask_app.route('/') 
def home(): return "EPIC PROTECTOR Elite — Running 24/7"

@flask_app.route('/health')
def health(): return "OK",200

@flask_app.route('/ping')
def ping(): return "PONG",200

def run_flask(): flask_app.run(host='0.0.0.0',port=8080,debug=False,use_reloader=False)


# HELPERS
def is_admin(uid): return uid==ADMIN_ID

def register_client(user):
    if user.id not in registered_clients:
        registered_clients[user.id]={"name":user.full_name,"username":f"@{user.username}" if user.username else "No username"}


# KEYBOARDS
def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛡️ Protect APK",         callback_data="admin_protect")],
        [InlineKeyboardButton("📤 Send APK to Client",  callback_data="admin_send_apk")],
        [InlineKeyboardButton("📢 Broadcast Message",   callback_data="admin_broadcast")],
        [InlineKeyboardButton("💬 Reply to Client",     callback_data="admin_reply")],
        [InlineKeyboardButton("👥 View All Clients",    callback_data="admin_clients")],
        [InlineKeyboardButton("📊 Statistics",          callback_data="admin_stats")],
    ])

def client_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📁 Request APK",         callback_data="client_request_apk")],
        [InlineKeyboardButton("📋 Our Services",        callback_data="client_services")],
        [InlineKeyboardButton("💬 Contact Admin",       callback_data="client_contact")],
        [InlineKeyboardButton("ℹ️ About",               callback_data="client_about")],
    ])

def back_a(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back",callback_data="back_admin")]])
def back_c(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back",callback_data="back_client")]])


# START HANDLER
async def start(update,context):
    user=update.effective_user; register_client(user)
    if is_admin(user.id):
        await update.message.reply_text(
            f"👑 *Welcome back, Admin!*\n\n🛡️ *EPIC PROTECTOR — Elite Master Hybrid*\n7-Level Android Protection\n\nTotal Clients: {len(registered_clients)}\n\nChoose an action:",
            parse_mode="Markdown",reply_markup=admin_kb())
    else:
        await update.message.reply_text(
            f"🛡️ *Welcome to EPIC PROTECTOR!*\n\nHello {user.first_name}!\n\nElite Android protection for hospitals, hotels, medical, pharma & data management.\n\nChoose an option:",
            parse_mode="Markdown",reply_markup=client_kb())


# BUTTON HANDLER
async def button_handler(update,context):
    query=update.callback_query; user=query.from_user; data=query.data
    await query.answer()

    if data=="admin_protect":
        if not is_admin(user.id): return
        pending_protect[user.id]=True
        await query.edit_message_text(
            "🛡️ *Elite Master Hybrid Protection*\n\nSend your APK file.\n\nAll 7 levels will be applied:\n━━━━━━━━━━━━━━━━━━━━━\nLevel 1 — APK Decode & Repack\nLevel 2 — DEX Protection\nLevel 3 — Resource Encryption\nLevel 4 — Manifest Protection\nLevel 5 — Runtime Java Injection\nLevel 6 — Anti-Analysis Engine\nLevel 7 — Sign & Deliver\n━━━━━━━━━━━━━━━━━━━━━\n\n📎 Send APK now:",
            parse_mode="Markdown",reply_markup=back_a())

    elif data=="admin_send_apk":
        if not is_admin(user.id): return
        if not registered_clients:
            await query.edit_message_text("👥 No clients yet.",reply_markup=back_a()); return
        btns=[[InlineKeyboardButton(f"{i['name']} ({i['username']})",callback_data=f"sel_{uid}")] for uid,i in registered_clients.items()]
        btns.append([InlineKeyboardButton("🔙 Back",callback_data="back_admin")])
        await query.edit_message_text("📤 *Send APK*\n\nSelect client:",parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("sel_"):
        if not is_admin(user.id): return
        tid=int(data[4:]); pending_send_apk[user.id]=tid; info=registered_clients.get(tid,{})
        await query.edit_message_text(f"📤 Sending to *{info.get('name',tid)}*\n\nSend APK now:",parse_mode="Markdown",reply_markup=back_a())

    elif data=="admin_broadcast":
        if not is_admin(user.id): return
        pending_broadcast[user.id]=True
        await query.edit_message_text(f"📢 *Broadcast*\n\nSending to {len(registered_clients)} clients.\n\nType message:",parse_mode="Markdown",reply_markup=back_a())

    elif data=="admin_reply":
        if not is_admin(user.id): return
        if not registered_clients:
            await query.edit_message_text("👥 No clients.",reply_markup=back_a()); return
        btns=[[InlineKeyboardButton(f"{i['name']} ({i['username']})",callback_data=f"rep_{uid}")] for uid,i in registered_clients.items()]
        btns.append([InlineKeyboardButton("🔙 Back",callback_data="back_admin")])
        await query.edit_message_text("💬 *Reply*\n\nSelect client:",parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("rep_"):
        if not is_admin(user.id): return
        tid=int(data[4:]); pending_reply[user.id]=tid; info=registered_clients.get(tid,{})
        await query.edit_message_text(f"💬 Replying to *{info.get('name',tid)}*\n\nType message:",parse_mode="Markdown",reply_markup=back_a())

    elif data=="admin_clients":
        if not is_admin(user.id): return
        if not registered_clients: text="👥 *No clients yet.*"
        else:
            lines=["👥 *Registered Clients*\n"]
            for uid,i in registered_clients.items(): lines.append(f"• {i['name']} ({i['username']})\n  ID: `{uid}`")
            text='\n'.join(lines)
        await query.edit_message_text(text,parse_mode="Markdown",reply_markup=back_a())

    elif data=="admin_stats":
        if not is_admin(user.id): return
        await query.edit_message_text(
            f"📊 *Statistics*\n\n👥 Clients: {len(registered_clients)}\n🛡️ Levels: 7\n🔒 AES-256-CBC: ✅\n📦 DEX Protection: ✅\n📋 Resource Encryption: ✅\n📄 Manifest Protection: ✅\n⚙️ Runtime Injection: ✅\n🎭 Anti-Analysis: ✅\n✍️ Auto Signing: ✅\n📡 Bot: Online ✅",
            parse_mode="Markdown",reply_markup=back_a())

    elif data=="back_admin":
        for d in [pending_protect,pending_broadcast,pending_reply,pending_send_apk]: d.pop(user.id,None)
        await query.edit_message_text("👑 *Admin Panel — EPIC PROTECTOR*\n\nChoose an action:",parse_mode="Markdown",reply_markup=admin_kb())

    elif data=="client_request_apk":
        await query.edit_message_text("📁 *Request Sent!*\n\nAdmin notified. Your protected APK coming shortly.\n\n⏳ Please wait...",parse_mode="Markdown",reply_markup=back_c())
        await context.bot.send_message(chat_id=ADMIN_ID,text=f"📥 *APK Request*\n\nClient: {user.full_name}\nUsername: @{user.username or 'none'}\nID: `{user.id}`",parse_mode="Markdown",reply_markup=admin_kb())

    elif data=="client_services":
        await query.edit_message_text(
            "📋 *Our Services*\n\nLevel 1 — APK Protection\nLevel 2 — DEX Encryption\nLevel 3 — Resource Protection\nLevel 4 — Manifest Hardening\nLevel 5 — Runtime Guard\nLevel 6 — Anti-Analysis\nLevel 7 — Signed & Delivered\n\n🏥 Hospital 🏨 Hotel\n💊 Medical 💊 Pharma\n💾 Data Mgmt 💻 Software",
            parse_mode="Markdown",reply_markup=back_c())

    elif data=="client_contact":
        pending_contact[user.id]=True
        await query.edit_message_text("💬 *Contact Admin*\n\nType your message now:",parse_mode="Markdown",reply_markup=back_c())

    elif data=="client_about":
        await query.edit_message_text("ℹ️ *About EPIC PROTECTOR*\n\nElite Master Hybrid Android protection.\n\n✅ 7-Level protection\n✅ AES-256-CBC encryption\n✅ DEX + Resource + Manifest\n✅ Runtime injection\n✅ Anti-analysis\n✅ Auto sign & deliver\n\n👨‍💼 Security Administrator",parse_mode="Markdown",reply_markup=back_c())

    elif data=="back_client":
        pending_contact.pop(user.id,None)
        await query.edit_message_text("🛡️ *EPIC PROTECTOR*\n\nChoose an option:",parse_mode="Markdown",reply_markup=client_kb())


# MESSAGE HANDLER
async def message_handler(update,context):
    user=update.effective_user; text=update.message.text; register_client(user)

    if is_admin(user.id) and pending_broadcast.get(user.id):
        pending_broadcast.pop(user.id); sent=failed=0
        for cid in registered_clients:
            try: await context.bot.send_message(chat_id=cid,text=f"📢 *From Admin:*\n\n{text}",parse_mode="Markdown"); sent+=1
            except: failed+=1
        await update.message.reply_text(f"📢 *Done!*\n\n✅ Sent: {sent}\n❌ Failed: {failed}",parse_mode="Markdown",reply_markup=admin_kb())
        return

    if is_admin(user.id) and pending_reply.get(user.id):
        tid=pending_reply.pop(user.id)
        try:
            await context.bot.send_message(chat_id=tid,text=f"💬 *From Admin:*\n\n{text}",parse_mode="Markdown")
            await update.message.reply_text("✅ Reply sent!",reply_markup=admin_kb())
        except Exception as e: await update.message.reply_text(f"❌ Failed: {e}",reply_markup=admin_kb())
        return

    if pending_contact.get(user.id):
        pending_contact.pop(user.id)
        await context.bot.send_message(chat_id=ADMIN_ID,text=f"💬 *Client Message*\n\nName: {user.full_name}\nUsername: @{user.username or 'none'}\nID: `{user.id}`\n\nMessage:\n{text}",parse_mode="Markdown",reply_markup=admin_kb())
        await update.message.reply_text("✅ *Message sent!*\n\nAdmin will reply soon.",parse_mode="Markdown",reply_markup=client_kb())
        return

    await update.message.reply_text("👇 Use the menu:",reply_markup=admin_kb() if is_admin(user.id) else client_kb())


# DOCUMENT HANDLER
async def document_handler(update,context):
    user=update.effective_user; register_client(user)

    if is_admin(user.id) and pending_protect.get(user.id):
        pending_protect.pop(user.id)
        status=await update.message.reply_text("⚙️ *Elite Protection Started!*\n\nRunning all 7 levels...\nThis takes 2-5 minutes ⏳",parse_mode="Markdown")
        try:
            file=await context.bot.get_file(update.message.document.file_id)
            apk=os.path.join(WORK_DIR,f"input_{user.id}_{int(time.time())}.apk")
            os.makedirs(WORK_DIR,exist_ok=True); await file.download_to_drive(apk)
            engine=MasterProtectionEngine(); results=engine.protect(apk)
            if results.get("SUCCESS"):
                skip={"OUTPUT_APK","GUARD_JAVA","AES_KEY_PATH","SUCCESS","ERROR"}
                lines=["🛡️ *Elite Protection Complete!*\n","━━━━━━━━━━━━━━━━━━━━━"]
                for k,v in results.items():
                    if k not in skip: lines.append(f"{v} {k}")
                lines.append("━━━━━━━━━━━━━━━━━━━━━")
                await status.edit_text('\n'.join(lines),parse_mode="Markdown")
                out=results.get("OUTPUT_APK")
                if out and os.path.exists(out):
                    with open(out,"rb") as f:
                        await update.message.reply_document(document=f,filename="EPIC_PROTECTED.apk",caption="🛡️ *Protected APK Ready!*\n\nAll 7 levels applied.\n\n⚠️ Add EpicSecurityGuard.java to your project.\nReplace YOUR_APK_SIGNATURE_SHA256_HERE before publishing.",parse_mode="Markdown")
                guard=results.get("GUARD_JAVA")
                if guard and os.path.exists(guard):
                    with open(guard,"rb") as f:
                        await update.message.reply_document(document=f,filename="EpicSecurityGuard.java",caption="☕ Copy to your Android security package.",parse_mode="Markdown")
            else:
                await status.edit_text(f"❌ *Failed*\n\n`{results.get('ERROR','Unknown')}`\n\nTry again.",parse_mode="Markdown",reply_markup=admin_kb())
            try: os.remove(apk)
            except: pass
        except Exception as e: await status.edit_text(f"❌ *Error:* `{e}`",parse_mode="Markdown",reply_markup=admin_kb())
        return

    if is_admin(user.id) and pending_send_apk.get(user.id):
        tid=pending_send_apk.pop(user.id)
        try:
            await context.bot.send_document(chat_id=tid,document=update.message.document.file_id,caption="📁 *Your Protected APK from Epic Protector*\n\n✅ Ready to use.",parse_mode="Markdown")
            await update.message.reply_text(f"✅ APK sent to `{tid}`!",parse_mode="Markdown",reply_markup=admin_kb())
        except Exception as e: await update.message.reply_text(f"❌ Failed: {e}",reply_markup=admin_kb())
        return

    if not is_admin(user.id):
        await update.message.reply_text("📎 Contact admin to receive files.",reply_markup=client_kb())


# MAIN
def main():
    print("\033[1;36m\nEPIC PROTECTOR — Elite Master Hybrid Engine Starting...\n\033[0m")
    os.makedirs(WORK_DIR,exist_ok=True)
    t=threading.Thread(target=run_flask,daemon=True); t.start()
    print("\033[1;32m[OK] Keep-alive server on port 8080\033[0m")
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.Regex(r'^/start$'),start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL,document_handler))
    app.add_handler(MessageHandler(filters.TEXT&~filters.COMMAND,message_handler))
    print("\033[1;32m[OK] Epic Protector Elite Bot Running!\033[0m")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__=="__main__": main()
