# Codex RTL

An unofficial local patch that displays Arabic Codex messages—including Arabic mixed with English—from right to left. Code blocks, links, email addresses, and other technical content remain left to right.

> [!WARNING]
> This project modifies the `app.asar` archive inside the ChatGPT/Codex desktop application. The installer creates a backup before making changes, but application updates may remove the patch. You may need to run the installer again after every update. This project is not affiliated with OpenAI.

## What it changes

- Detects Arabic characters in messages and the composer.
- Applies RTL direction and right alignment to Arabic and mixed Arabic-English content.
- Adjusts paragraphs, headings, lists, and tables for RTL layout.
- Keeps code, URLs, email addresses, and other technical content in LTR.
- Watches newly rendered and streaming messages and updates their direction automatically.

## Requirements

- Node.js 22.12 or newer.
- npm.
- Write access to the application's installation directory.
- ChatGPT/Codex must be fully closed before installation or restoration.

## Quick installation

```bash
git clone https://github.com/EngOREOO/Codex-RTL.git
cd Codex-RTL
npm install
npm run install-rtl
```

The installer searches for the application automatically. If it cannot find `app.asar`, provide its absolute path:

```bash
npm run install-rtl -- --asar="/path/to/app.asar"
```

Quit ChatGPT/Codex completely and reopen it after installation.

## macOS

The installer checks this default path:

```text
/Applications/ChatGPT.app/Contents/Resources/app.asar
```

Install the patch:

```bash
git clone https://github.com/EngOREOO/Codex-RTL.git
cd Codex-RTL
npm install
sudo npm run install-rtl
```

After modifying the archive, the installer applies an ad-hoc signature to the application. If the application is installed elsewhere, provide the archive path explicitly:

```bash
sudo npm run install-rtl -- --asar="/Applications/Your App.app/Contents/Resources/app.asar"
```

## Linux

Installation paths vary by package. The installer checks:

```text
/opt/ChatGPT/resources/app.asar
/usr/lib/chatgpt/resources/app.asar
/opt/Codex/resources/app.asar
/usr/lib/codex/resources/app.asar
```

Install the patch:

```bash
git clone https://github.com/EngOREOO/Codex-RTL.git
cd Codex-RTL
npm install
sudo npm run install-rtl
```

If the archive is elsewhere, locate it:

```bash
find /opt /usr/lib -name app.asar 2>/dev/null
```

Then pass the discovered path:

```bash
sudo npm run install-rtl -- --asar="/path/from/find/app.asar"
```

The installer does not modify a compressed AppImage directly. Extract the AppImage first, or use an installation that exposes `resources/app.asar` as a writable file.

## Windows

Open PowerShell with **Run as Administrator**, then run:

```powershell
git clone https://github.com/EngOREOO/Codex-RTL.git
Set-Location Codex-RTL
npm install
npm run install-rtl
```

The installer checks common locations under `LOCALAPPDATA` and `Program Files`. If the application is not found, search for the archive:

```powershell
Get-ChildItem "$env:LOCALAPPDATA\Programs","$env:ProgramFiles" -Filter app.asar -Recurse -ErrorAction SilentlyContinue
```

Then provide the resulting path:

```powershell
npm run install-rtl -- --asar="C:\Path\To\resources\app.asar"
```

Microsoft Store installations may be located inside the protected `WindowsApps` directory. Using a standard desktop installer is safer than changing permissions on `WindowsApps`.

## Restore the original application

The installer creates this backup beside the modified archive:

```text
app.asar.codex-rtl-backup
```

Restore it with:

```bash
npm run restore
```

Or provide the archive path explicitly:

```bash
npm run restore -- --asar="/path/to/app.asar"
```

On macOS, you may need `sudo`. The restore command applies an ad-hoc signature after replacing the archive.

## After an application update

1. Check whether RTL support disappeared.
2. Quit ChatGPT/Codex completely.
3. Pull the newest version of this repository.
4. Run `npm install`, followed by `npm run install-rtl`.

## Troubleshooting

### The installer cannot find `app.asar`

Locate the archive using the platform-specific commands above, then pass it with `--asar`.

### Permission denied

- macOS or Linux: rerun the installation with `sudo`.
- Windows: open PowerShell with **Run as Administrator**.

### RTL disappears after an update

Application updates may replace `app.asar`. Close the application and run the installer again.

### Restore reports that no backup exists

The restore command requires `app.asar.codex-rtl-backup` beside the active archive. Reinstalling or updating the application may remove that backup.

## Support boundaries

- The installation and restoration flow has been tested on macOS with the Electron-based ChatGPT/Codex desktop application.
- Linux and Windows paths depend on the installation method. Use `--asar` when automatic detection does not find the archive.
- Internal OpenAI UI changes may require updates to the selectors in `rtl-arabic-patch.js`.
- This is an unofficial local modification. Use it at your own risk.

## License

MIT. See [LICENSE](LICENSE).
