# SwiftGet — Fast Software Downloader

## Basic Information

| Item | Details |
| --- | --- |
| Product Name | SwiftGet |
| Version | 1.0.0 |
| File Size | 23.2 MB (single portable executable) |
| Supported OS | Windows 10 / Windows 11 (64-bit) |
| Interface Language | Simplified Chinese |
| License | MIT License |
| Category | System Utilities / Download Tools |

---

## One-line Summary

Select the software you need, choose a folder, and SwiftGet handles the rest — an open-source Windows downloader built on the aria2 engine.

---

## Description

SwiftGet is a lightweight tool for downloading and installing multiple Windows applications in one go. It compresses the repetitive routine of "find the official site, download the installer, click Next seven times" into a single selection: pick the software you want from a card-based list, choose a destination folder, and the app will automatically pick a working download source, accelerate the transfer with multiple connections, verify the file, and run a silent installation when the download completes.

The download engine is built on the open-source aria2. Direct links are fetched using up to 16 parallel segmented connections, which noticeably improves throughput on servers that support HTTP Range requests. BitTorrent is also built in, so you can paste a magnet link or load a `.torrent` file and pull pieces from multiple peers over DHT.

SwiftGet ships as a single portable executable with every runtime component bundled. There is nothing to install, no Python environment to configure, and no redistributables to download — just double-click and run.

Twelve commonly used applications are included out of the box, covering browsers, messaging and office tools, security software, system utilities, and media players. The catalog can be edited locally or refreshed from a remote JSON endpoint, so a changed official download URL can be fixed without rebuilding the application.

---

## Key Features

**1. One-click batch download**
Twelve built-in applications presented as selectable cards, with category filters and select-all / clear-all controls. Multiple items can be downloaded in parallel.

**2. Dual acceleration engines**
- Direct links: multi-threaded segmented downloading with 16 connections by default.
- BitTorrent: magnet links and `.torrent` files, using DHT and Peer Exchange to fetch from multiple peers simultaneously.

**3. Automatic source failover**
Each application carries several download sources. They are probed before downloading and the first reachable one is used, so a single dead mirror does not break the flow.

**4. Silent installation**
For installers that support silent switches, the package is installed in the background with no user interaction. Only the initial elevation prompt requires a click.

**5. Optional installer language**
For packages that expose a language switch (such as VLC), you can choose a Simplified Chinese or English installer. Other packages follow the system language, and the UI states this clearly.

**6. Live progress feedback**
Each card shows download progress, transferred size, current speed, active connections, and peer count, then a final status when the task ends.

**7. Maintainable catalog**
The built-in catalog can be exported to JSON for manual editing, or refreshed from a remote URL. No repackaging is required when a link changes.

**8. Portable and clean**
No installation, no system-wide registry writes (user settings are stored in `%APPDATA%`), and removal is as simple as deleting the executable.

---

## Bundled Applications

| Category | Application | Installation Mode |
| --- | --- | --- |
| Browser | Google Chrome | Fully silent |
| Communication | WeChat | Fully silent |
| Communication | QQ | Fully silent |
| Communication | DingTalk | Fully silent |
| Office | WPS Office | Installer wizard launched automatically |
| Security | 360 Total Security | Installer wizard launched automatically |
| Security | Huorong Security | Fully silent |
| Utilities | 7-Zip | Fully silent |
| Utilities | Everything | Fully silent |
| Utilities | Bandizip | Installer wizard launched automatically |
| Utilities | Notepad++ | Fully silent |
| Media | VLC media player | Fully silent |

> Note: whether an application can install completely silently is decided by the vendor's installer. The three entries marked "installer wizard launched automatically" ship official installers that always display a user interface; SwiftGet downloads the package and opens the wizard for you, so there is no need to locate the file manually.

---

## How to Use

1. Double-click `SwiftGet.exe`. No installation required.
2. On the **Common Software** page, select the applications you need. Category filters are available.
3. Choose a destination folder (defaults to `Downloads\SwiftGet`) and an installer language.
4. Click **Start Download**. SwiftGet probes sources, downloads, verifies, and installs automatically.
5. Windows will ask for administrator permission before the first installation. Approve it once — the application itself runs with standard user rights.
6. To download anything else, switch to the **Link / P2P** page and paste a direct URL, a magnet link, or choose a `.torrent` file.

---

## Technical Details

- Language: Python 3.13
- UI framework: CustomTkinter
- Download engine: aria2 1.37, embedded and controlled over JSON-RPC
- Packaging: PyInstaller single-file build with a Per-Monitor DPI manifest
- Privilege model: runs as a standard user; elevation is requested only when an installer is launched

---

## Notes

- SwiftGet only automates downloading and installation. All installers come directly from official vendor sites or public mirrors; no proxy server is involved and no package contents are modified.
- Please use the software in compliance with each vendor's license terms.
- The application has no external runtime dependencies, but installing software itself requires administrator rights.
- Some official download URLs change between releases. If you see "all download sources are unavailable", export the catalog via **Settings → Advanced → Export Catalog**, edit the URLs, or configure a remote catalog endpoint.

---

## Open Source

SwiftGet is released under the MIT License. Source code review, issue reports, and pull requests are welcome. Because executables packaged with PyInstaller are frequently flagged by heuristic scanners, you are encouraged to review the source and rebuild the binary yourself if your security software raises an alert.

---

**Contact / Project URL**: (to be filled in)
