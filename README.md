# CS 1.6 EmptyX Customization (Decoupled Studio & Mod Suite)

Selamat datang di **CS 1.6 EmptyX Customization**!

Repositori ini adalah **Dedicated Modding & Customization Workspace** yang terpisah dari folder game utama Counter-Strike 1.6, dirancang secara khusus menggunakan **Decoupled Bridge Architecture** dan kini berlokasi bersama di dalam satu folder utama: `D:\Counter-Strike 1.6\`.

---

## 🚀 Mengapa Workspace Ini Dipisahkan?

1. **Super Ringan (< 25 MB)**:
   - Folder instalasi game CS 1.6 berukuran ~2.4 GB karena dipenuhi file `.wad`, maps (`.bsp`), model binary, file suara (`.wav`/`.mp3`), dan executable (`hl.exe`).
   - Gemini AI memiliki batas pembacaan/indexing codebase (< 100 MB). Dengan pemisahan ini, Gemini dapat memuat dan membaca **100% seluruh codebase tools & mod Anda** dalam hitungan detik tanpa terkena limit ukuran file.
2. **Game Asli Tetap Bersih & Aman**:
   - File instalasi game utama Anda di `D:\Counter-Strike 1.6\Counter-Strike 1.6 Original` tetap utuh dan terisolasi dari eksperimen kode sementara.
   - Semua modul tools, script Python, cache, dan profil kustomisasi tersimpan di workspace ini.
3. **Penyimpanan Mod Mandiri (Mod Sandbox)**:
   - Mod-mod kustom yang sedang Anda kembangkan berada di `my_mods/staging/`.
   - Mod pack yang sudah siap dirilis atau di-backup akan tersimpan rapi di `my_mods/exports/`.

---

## 📂 Struktur Direktori Gabungan (`D:\Counter-Strike 1.6\`)

```
D:\Counter-Strike 1.6\
│
├── 📁 Counter-Strike 1.6 Original/         # [FOLDER GAME UTAMA: ~2.4 GB]
│   ├── hl.exe
│   ├── cstrike/ (models, sound, sprites, maps)
│   ├── valve/
│   └── CS16_Asset_Studio_Forwarder.bat     # Penunjuk 1-klik ke Asset Studio
│
└── 📁 cs16-emptyx-customization/           # [CUSTOMIZATION WORKSPACE: ~15 MB (<100MB)]
    ├── config.json                         # Jembatan path ke instalasi game CS 1.6
    ├── CS16_Asset_Studio.bat               # Launcher 1-klik Web Dashboard & Desktop shortcut
    ├── README.md                           # Dokumentasi arsitektur dan panduan
    ├── .geminiignore / .gitignore          # Proteksi file binary agar tetap < 100MB
    ├── scripts/
    │   ├── cs16_studio.py                  # Entry point CLI studio
    │   └── cs16_studio/
    │       ├── config_manager.py           # Dual-Root path resolver (Game Root vs Studio Root)
    │       ├── mdl_core.py                 # Binary parser GoldSrc StudioModel IDST v10
    │       ├── baker.py                    # Engine komposit stiker WYSIWYG
    │       ├── color_adjuster.py           # Engine HSL, saturasi & grading foto
    │       ├── glove_transfer.py           # Engine transfer sarung tangan & arm sleeves
    │       ├── chrome_injector.py          # Dual-layer metallic chrome & foil shimmer
    │       ├── slot_geometry.py            # 3D slot quad injector & health validator
    │       ├── stattrak_customizer.py      # Modul kustomisasi LED StatTrak & counter
    │       ├── wear_simulator.py           # Engine simulasi float wear (FN -> BS)
    │       ├── amxx_manager.py             # Mod manager AMX Mod X & loadout
    │       ├── pov_manager.py              # CS2 First-Person Viewmodel POV controller
    │       ├── modpack_exporter.py         # Modpack exporter (.zip)
    │       └── web/
    │           ├── server.py               # Web HTTP server & REST API (Dual-root fallback)
    │           └── static/                 # Frontend Dashboard modern Titanium Obsidian
    ├── assets/                             # Aset stiker & skin custom (.png, .jpg, .webp)
    │   ├── stickers/
    │   └── skins/
    ├── my_mods/
    │   ├── staging/                        # Tempat kerja mod yang sedang dibuat/diedit
    │   └── exports/                        # File paket modpack .zip yang siap dipakai
    ├── .studio_profiles/                   # Snapshot profil loadout senjata tersimpan
    ├── .studio_glove_presets/              # Preset sarung tangan & lengan tersimpan
    └── .agents/
        └── skills/                         # Antigravity Skills (Asset Studio, Gloves, P/W, dll.)
```

---

## 🎮 Cara Menjalankan

### 1. Menjalankan Web Dashboard Studio
- **Dari Windows Explorer:** Cukup double-click `CS16_Asset_Studio.bat` di dalam `D:\Counter-Strike 1.6\cs16-emptyx-customization\`.
- **Dari Desktop:** Buka shortcut **"CS 1.6 Asset Studio"** di Desktop Anda.
- **Dari PowerShell / Terminal:**
  ```powershell
  cd "D:\Counter-Strike 1.6\cs16-emptyx-customization"
  python scripts/cs16_studio.py --ui
  ```
Dashboard akan otomatis terbuka di browser pada URL: `http://127.0.0.1:5160/`.

### 2. Forwarder dari Folder Game
Jika Anda sedang berada di dalam folder game `D:\Counter-Strike 1.6\Counter-Strike 1.6 Original`, Anda cukup menjalankan:
```cmd
CS16_Asset_Studio_Forwarder.bat
```
Script tersebut menggunakan path relatif sibling (`%~dp0..\cs16-emptyx-customization\CS16_Asset_Studio.bat`) sehingga selalu menemukan studio tanpa peduli lokasi drive.

---

## ⚙️ Konfigurasi Path Game

Lokasi game diatur melalui file `config.json`:
```json
{
  "game_directory": "D:\\Counter-Strike 1.6\\Counter-Strike 1.6 Original",
  "active_team": "ct",
  "auto_backup": true
}
```
Karena studio dan game kini berdampingan dalam satu folder `D:\Counter-Strike 1.6\`, struktur ini sangat rapi, terorganisir, dan mudah di-backup!
