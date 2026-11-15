# OwnVideo Apps

Aplikasi **Windows x64 portable** untuk menghasilkan video Bahasa Melayu:
import bahan → sunting storyboard → narasi Ludo → sari kata → MP4.

## Muat turun dan buka

1. Buka tab **Actions → Windows portable**, pilih binaan `main` yang lulus.
2. Muat turun artifact **OwnVideoApps-Windows-x64** (memerlukan login GitHub).
3. Ekstrak artifact, kemudian ekstrak `OwnVideoApps-Windows-x64.zip` sepenuhnya.
4. Buka `OwnVideoApps.exe`. Tiada installer atau pemasangan Python/Node/FFmpeg.

Projek dan profil aplikasi disimpan dalam `Data/` di sebelah EXE. Narasi Google
memerlukan internet, login sendiri dan kuota; render menggunakan komponen
setempat yang dibundel. Pakej awal belum mempunyai tandatangan kod Windows.

## Fungsi versi awal

- Import TXT/MD, PDF berteks, DOCX dan PPTX menjadi draf babak.
- Sunting tajuk, isi visual dan narasi setiap babak.
- Buka AI Studio melalui pelayar biasa dan import WAV Ludo terus pada babak.
  Tetingkap automasi aplikasi kekal pilihan jika login Google membenarkannya.
- Dengar WAV dan sunting cap masa sari kata secara manual.
- Render MP4 H.264/AAC 720p dengan muzik instrumental, SRT dan trek sari kata.
- Versi projek setempat mengikut tajuk; tiada Git atau upload dalam aliran app.

Skill Markdown daripada repo sumber tidak dijalankan sebagai agent. Versi ini
menggunakan kod Electron/Python/renderer; orkestrasi agent AI belum disediakan.
PDF imbasan belum di-OCR, tiada penjajaran sari kata automatik, dan draf import
bukan ringkasan AI. Templat visual asal mengandungi jenama UiTM. Semak fakta,
jenama, sebutan dan sari kata sebelum berkongsi hasil.

Panduan penuh: [PORTABLE.md](docs/PORTABLE.md).
Komponen dan lesen: [THIRD-PARTY.md](docs/THIRD-PARTY.md).
Status pengujian: [VALIDATION.md](docs/VALIDATION.md).

## Bina daripada sumber

Pada mesin pembina dengan Python 3.12+ dan pip:

```bash
python tools/build_portable.py
```

Pembina boleh dijalankan pada Linux atau Windows dan menghasilkan
`dist/OwnVideoApps-Windows-x64.zip`. Hash komponen dipinkan dan wheel Python
disahkan terhadap metadata PyPI. CI di Windows menguji runtime dan eksport MP4.
Tiada branch, tag atau GitHub Release dicipta oleh workflow.

Untuk pembangunan UI (Node 24+, FFmpeg dan Python bersama dependency render):

```bash
npm --prefix desktop ci
npm --prefix desktop start
node --test desktop/tests/*.test.cjs
python -m unittest discover -s tests -v
```

`OWNVIDEO_PYTHON` boleh menunjuk kepada Python venv untuk mod pembangunan.
Folder data pembangunan ialah `.cache/portable/Data`.

## Peraturan repo

Semua kemas kini projek ini hanya ke **`main`** dalam
**`shazwannoor95-jpg/ownvideoapps`**. Repo asal **`ownvideo` tidak boleh disentuh**.
Arahan kekal disimpan dalam [AGENTS.md](AGENTS.md). Runtime, ZIP, profil Google
dan bahan pengguna tidak dimasukkan dalam Git.
