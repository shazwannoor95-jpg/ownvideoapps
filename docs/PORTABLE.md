# OwnVideo Apps — Windows portable

Sasaran: Windows 10/11 x64. Ini binaan awal; pengujian pada Windows sebenar
dan penjanaan Google yang sebenar dinyatakan berasingan dalam laporan ujian.

1. Ekstrak **seluruh** ZIP ke folder yang boleh ditulis, contohnya Documents
   atau pemacu USB. Jangan jalankan EXE terus dari dalam ZIP.
2. Buka `OwnVideoApps.exe`. Python, Node dan FFmpeg tidak perlu dipasang.
3. Isi tajuk dan import TXT/MD, PDF berteks, DOCX atau PPTX. Fail asal dan teks
   ekstrak disimpan dalam `Data/videos/<tajuk>/v001/source/`.
4. Semak draf babak dan simpan suntingan. Ini penyusunan teks secara automatik,
   bukan model AI yang meringkaskan atau menyemak fakta.
5. Tekan **Buka AI Studio dalam pelayar biasa** untuk login melalui Chrome/Edge.
   Pilih suara Ludo, jana narasi dan muat turun WAV. Pada setiap babak, kembangkan
   **Audio & cap masa sari kata**, tekan **Import WAV** dan pilih rakaman babak itu.
   Memerlukan internet, akses model dan kuota akaun Google. Login pelayar biasa
   tidak berkongsi sesi dengan tetingkap automasi aplikasi. Automasi melalui
   tetingkap aplikasi masih pilihan; Google boleh menolak browser itu. Jika login
   tersangkut selepas password, tutup tetingkap automasi dan guna pelayar biasa.
6. Muat semula babak, dengar WAV dan isi cap masa sebenar sari kata pada setiap
   babak. Masa `start`/`end` dalam saat relatif kepada WAV babak. Jangan teka
   masa jika rakaman belum disemak. Contoh format:

   ```json
   [{"start": 0.2, "end": 2.5, "text": "Ayat yang disebut dalam rakaman."}]
   ```

7. Render MP4 + sari kata. Output H.264/AAC 720p, muzik instrumental yang
   dijana mengikut projek/versi, fail SRT dan MP4 dengan trek sari kata boleh
   dipilih disimpan dalam `outputs/`. Sari kata bukan dibakar pada gambar.
8. Semak fakta, visual, sebutan dan masa sari kata dalam hasil akhir.

## Data portable

Tajuk import kini pilihan: jika kosong, nama fail digunakan. Pemilih fail akan
dibuka tanpa perlu mengisi tajuk. Pembukaan halaman Google tidak lagi mengunci
butang import. Navigasi Google dalam tetingkap automasi mempunyai had masa.

Untuk kemas kini aplikasi, tutup aplikasi lama, ekstrak binaan baharu ke folder
baharu dan salin folder `Data` lama ke sebelah EXE baharu. Simpan salinan sandaran
Data. Jangan buang projek atau WAV lama untuk membaiki login.

Projek dan profil login aplikasi berada dalam `Data/` di sebelah EXE. Pindahkan
seluruh folder aplikasi untuk membawa projek. Profil Google disulitkan oleh
Windows/Chromium dan boleh meminta login semula selepas bertukar komputer.
Logout sebelum berkongsi folder. Folder `Data` binaan yang diedarkan kosong.

Tajuk yang sama mencipta v002, v003 dan seterusnya secara setempat. Audio sedia
ada tidak ditimpa; cipta versi baharu untuk pindaan narasi selepas ada WAV.
Tiada Git atau upload video automatik dalam aplikasi.

Templat visual asal menggunakan warna dan logo UiTM. Semak kesesuaian jenama
sebelum menggunakan hasil di luar konteks UiTM. PDF imbasan perlu OCR luaran;
DOC/PPT format lama perlu ditukar kepada DOCX/PPTX dahulu. Cues sari kata masih
manual; penjajaran suara automatik belum disediakan.

## Semakan setempat

Klik kanan folder aplikasi, buka PowerShell dan jalankan:

```powershell
powershell -NoProfile -File .\Semak-Portable.ps1
```

Skrip menguji runtime Windows yang dibundel dan render satu video ujian
menggunakan nada sintetik. Ia tidak login Google atau menjana suara sebenar.

## Bina semula

Aplikasi ini tidak menjalankan skill Markdown sebagai agent AI. Electron
menyediakan antaramuka dan dialog, Python mengekstrak dokumen serta menyusun
draf babak, renderer dan FFmpeg menghasilkan video. Fail skill dalam repo sumber
ialah panduan untuk agent; menyimpan fail tersebut sahaja tidak melaksanakan
arahan, menjana skrip AI, menyemak fakta atau menjajarkan sari kata. Versi ini
belum mengandungi agent AI yang mengorkestrasi keseluruhan workflow skill.

Dari kod sumber, Python 3.12+ dan pip pada mesin pembina diperlukan:

```text
python tools/build_portable.py
```

Hasil dalam `dist/OwnVideoApps-Windows-x64.zip`. CI membina dan menguji runtime
di Windows pada push ke main, tanpa branch/tag atau GitHub Release baharu.
