# Status pengujian

Binaan 0.2.1, 15 November 2026.

## Disahkan pada hos Linux

- 18 ujian Node lulus: had masa halaman Google, pemeliharaan halaman login,
  import WAV tanpa menimpa audio, cache, penolakan narasi yang berubah selepas ada
  audio, ID babak, cap masa, folder projek dan panggilan Python daripada desktop.
- 9 ujian Python lulus: ekstrak DOCX/PPTX, urutan slaid, projek/versi tanpa Git,
  penolakan path repo asal sebelum pembacaan, sekatan publish, dan render sebenar.
- Render fixture satu babak dengan nada sintetik menghasilkan MP4, muzik, SRT,
  trek sari kata dan laporan dengan 11 semakan teknikal lulus. Ini bukan Ludo
  sebenar dan tidak mengesahkan sebutan.
- ZIP Windows dibina di Linux daripada Electron/CPython/FFmpeg Windows x64 dan
  wheel Windows; integriti ZIP, magic PE dan hash komponen diperiksa.
- Tiada `.git`, profil login atau fail `.env` dimasukkan ke dalam ZIP.
- Ujian UI Chromium dengan backend mock lulus: keadaan awal, import, sunting,
  keperluan simpan sebelum penjanaan dan kawalan render; tiada ralat JavaScript.
- 7 pemeriksaan Electron fixture lulus dalam mod headless: preload dashboard,
  pengasingan Node, pengesanan editor, pemilihan suara/ekstrak WAV fixture dan
  penolakan suara tiada, kuota gagal serta editor tidak sedia. Google sebenar
  tidak dihubungi oleh ujian ini.

## Ujian Windows

Semakan EXE kini juga memanggil IPC import bahan dengan tajuk kosong, import WAV,
penolakan WAV pendua, dan pembukaan pelayar biasa melalui shell mock. Pemilih
fail dan pelayar distub untuk CI; ini tidak membuktikan login Google berjaya.

Workflow `Windows portable` pada `main` menjalankan ujian Node serta skrip
`Semak-Portable.ps1` terhadap pembukaan EXE sebenar, pengasingan Node dashboard,
Python, FFmpeg, FFprobe dan render MP4 menggunakan
komponen yang dibundel. Lihat keputusan run GitHub Actions untuk status sebenar;
binaan ZIP pada Linux sahaja tidak bermakna EXE telah dijalankan pada Windows.

## Belum disahkan

- Login Google, pemilihan Ludo dan penjanaan WAV sebenar dalam aplikasi portable.
- Pengalaman pengguna pada PC Windows fizikal, pemacu USB dan Windows SmartScreen.
- Semakan manusia terhadap fakta, visual, sebutan dan penjajaran sari kata.

Kod diimport melalui salinan bebas. Tiada arahan Git dijalankan terhadap repo
asal `ownvideo`; semua commit/push projek ini hanya untuk `ownvideoapps/main`.
