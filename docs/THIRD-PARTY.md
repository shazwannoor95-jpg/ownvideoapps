# Komponen pihak ketiga

- Electron 45.3.1, MIT dan lesen Chromium: `LICENSE` dan
  `LICENSES.chromium.html` dalam folder aplikasi. Sumber:
  https://github.com/electron/electron/tree/v45.3.1
- Python 3.12.10 daripada pakej rasmi NuGet `python`, PSF:
  `resources/runtime/python/LICENSE.txt`. Sumber dan binaan:
  https://github.com/python/cpython/tree/v3.12.10
- FFmpeg/FFprobe static Windows x64 b6.1.1, GPLv3; lihat `FFMPEG-LICENSE.txt`.
  Binaan dan rujukan sumber/konfigurasi upstream:
  https://github.com/eugeneware/ffmpeg-static/releases/tag/b6.1.1 dan
  https://github.com/eugeneware/ffmpeg-static/tree/b6.1.1
- NumPy, SciPy, Pillow dan pypdf: lesen asal dikekalkan dalam
  `resources/runtime/python/Lib/site-packages/*dist-info/`.
- Fon Outfit, SIL OFL: `resources/engine/tools/template/local_resources/OFL.txt`.
- Ikon: lesen dalam `resources/engine/tools/template/assets/icons/LICENSE.txt`.
- Logo/aset UiTM berasal daripada templat import; rujukan sumber dan nota
  penggunaan dikekalkan dalam folder `assets/brand/`.

SHA256 komponen binaan dipinkan dalam skrip pembina. SHA256 Electron sepadan
dengan SHASUMS256 rasmi; hash komponen lain dipinkan daripada muat turun TLS.
Wheel Python disahkan dengan hash metadata PyPI. `SHA256SUMS.json` menyenaraikan
fail binaan yang diedarkan; fail pengguna dalam Data tidak termasuk selepas
aplikasi digunakan. Pakej ini belum ditandatangani dengan sijil Windows.
