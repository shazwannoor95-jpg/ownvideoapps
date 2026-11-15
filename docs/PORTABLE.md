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
5. Buka Google AI Studio dan login sendiri. Semak editor, kemudian luluskan
   penjanaan Ludo. Memerlukan internet, akses model dan kuota akaun Google.
   Jika Google menolak embedded browser, gunakan AI Studio dalam pelayar biasa
   dan salin WAV Ludo ke `audio/s01.wav`, `s02.wav` dan seterusnya.
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

Dari kod sumber, Python 3.12+ dan pip pada mesin pembina diperlukan:

```text
python tools/build_portable.py
```

Hasil dalam `dist/OwnVideoApps-Windows-x64.zip`. CI membina dan menguji runtime
di Windows pada push ke main, tanpa branch/tag atau GitHub Release baharu.
