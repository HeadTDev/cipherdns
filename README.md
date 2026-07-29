# 🛡️ CipherDNS

**CipherDNS** is a modern, high-performance desktop application for managing **DNS over HTTPS (DoH)** encryption and DNS providers on Windows 10 and Windows 11.

It directly interfaces with native Windows network subsystems and registry parameters to enforce secure, encrypted DNS resolution without third-party VPN drivers or proxy overhead.

---

## ✨ Features

- **🔒 Native Windows 11 DoH Sync**: Fully configures `DohFlags`, `DohTemplate`, and `EnableAutoDoh` registry keys so Windows Settings (Gépház) natively verifies your connection as *"Encrypted (DoH)"*.
- **⚡ Auto-Select Lowest Latency**: Runs background multi-sample RTT latency benchmarks across all providers to automatically select and apply the fastest resolver.
- **🔄 Smart Auto-Switch (Network Memory)**: Remembers your preferred DNS provider for each Wi-Fi SSID and Ethernet network, automatically switching settings when you change location.
- **🛡️ Deep Security & Diagnostics Check**:
  - **DNSSEC Validation Enforcement**: Tests if your resolver validates digital domain signatures (`dnssec-failed.org`).
  - **DoH TLS Endpoint Inspector**: Inspects TLS 1.3 handshake, cipher suite, and connection round-trip latency.
  - **Ad-Blocking / Tracking Shield**: Evaluates network-level tracker blocking.
- **🧹 1-Click DNS Cache Flush**: Instantly flushes local OS resolver cache (`Clear-DnsClientCache`) from the UI and System Tray.
- **🚀 System Tray & Silent Boot**: Minimizes quietly to system tray and supports native Windows auto-startup (`--autostart`).
- **📝 Real-time Execution Log Modal**: Pops up live step-by-step transaction logs on every DNS change.
- **🌐 100% English & Language-Independent**: Uses native CIM/JSON PowerShell queries that work on any Windows display language without string parsing errors.

---

## 🌐 Included DNS Providers

| Provider | Features | IPv4 / IPv6 | DoH Endpoint |
| :--- | :--- | :--- | :--- |
| **Quad9** | ⛨ Malware | `9.9.9.9` / `2620:fe::fe` | `https://dns.quad9.net/dns-query` |
| **Cloudflare** | ⚡ Fast (1.1.1.1) | `1.1.1.1` / `2606:4700:4700::1111` | `https://cloudflare-dns.com/dns-query` |
| **AdGuard** | ⛨ Malware • ⊘ Ads • ◉ Trackers | `94.140.14.14` / `2a10:50c0::ad1:ff` | `https://dns.adguard-dns.com/dns-query` |
| **Mullvad** | ⛨ Malware • ⊘ Ads • ◉ Trackers | `194.242.2.3` / `2a07:e340::3` | `https://adblock.doh.mullvad.net/dns-query` |
| **Google** | 🌐 Global (8.8.8.8) | `8.8.8.8` / `2001:4860:4860::8888` | `https://dns.google/dns-query` |
| **NextDNS** | ⛨ Malware • ⊘ Ads • ◉ Trackers • ♥ Family | Configurable ID | `https://dns.nextdns.io/{ID}` |
| **Custom DNS** | User-defined | User-defined | User-defined |
| **System Default** | Original DHCP | Automatic | Provider Default |

---

## 📦 Downloads & Installation

Pre-built binary executables can be downloaded from the **[GitHub Releases](https://github.com/HeadTDev/cipherdns/releases)** page or compiled locally into the `dist/` directory:

- **Portable Executable**: `CipherDNS_Portable.exe`
  *Single standalone binary. No installation required. Saves settings to `%APPDATA%\CipherDNS`.*
- **Setup Installer**: `CipherDNS_Setup.exe`
  *Official installer wizard with Start Menu shortcuts, Desktop icon, and Control Panel Uninstaller.*
  *Fully compatible with **Windows x64** and **Windows 11 ARM64** (via Prism emulation).*

---

## 🛠️ Building from Source

### Prerequisites
- Windows 10 or Windows 11 (Run as Administrator)
- Python 3.10+ or [`uv`](https://github.com/astral-sh/uv)

### Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/HeadTDev/cipherdns.git
   cd cipherdns
   ```

2. **Install dependencies**:
   ```bash
   uv pip install customtkinter pystray pillow pyinstaller
   ```

3. **Run locally**:
   ```bash
   uv run run.pyw
   ```

4. **Build Portable Executable**:
   ```bash
   uv run pyinstaller --noconsole --onefile --uac-admin --icon=assets/app_icon.ico --add-data "assets;assets" --add-data "data/profiles.json;data" --collect-all customtkinter --name "CipherDNS_Portable" run.pyw
   ```

5. **Build Setup Installer**:
   ```powershell
   & "C:\Users\headtdev\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer.iss
   ```

---

## ⚖️ Requirements & Permissions

- **Administrator Privileges (`runas`)**: Modifying Windows DNS server addresses and DoH registry parameters requires elevated administrator rights.
- **Operating System**: Windows 10 (Version 2004+) or Windows 11.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for details.
