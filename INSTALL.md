# Safe installation and rollback

This guide assumes you already have a **working rEFInd installation** and working
OS bootloaders on an x86-64 UEFI PC. This does not install Windows or Batocera.
Do not overwrite the working rEFInd, delete OS loaders, or disable Secure Boot
without understanding the security and BitLocker recovery implications.
The provided binary is unsigned and the tested setup has Secure Boot **off**.

## 1. Verify your loader paths and partition names

The release configuration uses **example FAT partition labels**, not personal
partition identifiers:

- Windows: volume `SYSTEM`, loader `\EFI\Microsoft\Boot\bootmgfw.efi`.
- Batocera: volume `BATOCERA`, loader `\EFI\batocera\grubx64.efi`.

Verify these labels and paths for **your** installation before proceeding.
In Batocera:

```sh
lsblk -f
find /boot/EFI -maxdepth 3 -type f -iname '*.efi'
efibootmgr -v
```

You may replace `volume` with a verified GPT partition GUID (PARTUUID).
Do not confuse it with a filesystem UUID. Leave Windows first and Batocera
second, with those names in the entry titles: artwork follows that order.
Using the wrong path can boot another installation or fail to boot.

**Do not use Batocera's fallback `EFI/BOOT/BOOTX64.EFI` merely because it exists.**
On the tested device it invoked Boot Option Restoration and reset the default
firmware entry. Direct GRUB fixed that. If your installation doesn't have the
GRUB path above, find and verify its actual boot chain first.

## 2. Copy to a separate EFI folder from Windows

Extract the release ZIP somewhere in Windows. Open Command Prompt as administrator:

```cmd
mountvol R: /S
```

Use another unused drive letter if R: is occupied. Verify this is the EFI
partition containing your working `EFI\refind` folder. Back up that folder to
your Windows drive using a new backup destination:

```cmd
xcopy R:\EFI\refind "%USERPROFILE%\Desktop\refind-backup-before-split\" /E /I /H
```

Copy the extracted **refind-split folder**, not the ZIP, into `R:\EFI\`:

```cmd
xcopy "C:\path\to\refind-split" R:\EFI\refind-split\ /E /I
```

Stop if that destination already contains unknown files. Edit the new
`R:\EFI\refind-split\refind.conf` to use the verified volumes and loader paths.
The images and icons must stay beside the executable as packaged.

## 3. Copy the working controller driver

If your existing rEFInd needs a gamepad driver, copy the verified version:

```cmd
mkdir R:\EFI\refind-split\drivers_x64
copy R:\EFI\refind\drivers_x64\UsbXbox360Dxe.efi R:\EFI\refind-split\drivers_x64\
```

Only do this if the source file exists and is the driver you already use.
Do not download arbitrary EFI programs into the drivers folder.

A nested test can inherit the driver's already-loaded input protocols, masking a
missing driver in the new folder. **Direct firmware boot needs its own driver.**

## 4. Add a test entry to the ORIGINAL rEFInd

```cmd
notepad R:\EFI\refind\refind.conf
```

Append (replace `SYSTEM` with the label/GUID of the partition holding the new binary):

```text
menuentry "Split-screen TEST" {
    volume "SYSTEM"
    loader \EFI\refind-split\refind_x64.efi
}
```

If an existing `scanfor` directive is active, ensure it includes `manual`.
If `default_selection +` is active, temporarily use `default_selection Windows`
so selecting the test does not become the parent's remembered default.

Save and unmount:

```cmd
mountvol R: /D
```

Restart and choose Split-screen TEST in the **original** rEFInd. Test left/right,
A/Enter, both OS boots, audio, Wi-Fi, and then a cold start. Mouse/touch are
disabled in the sample. No automatic boot timeout is enabled.

## 5. Make it a firmware entry ONLY after successful testing

In Batocera or another Linux system, identify the disk and EFI partition again:

```sh
lsblk -f
efibootmgr -v
```

Example only, for EFI on `/dev/nvme0n1p1`:

```sh
efibootmgr -c -d /dev/nvme0n1 -p 1 -L "Ally Split Launcher" -l '\EFI\refind-split\refind_x64.efi'
```

This **changes firmware NVRAM** and normally puts the new entry first. Run it
once, inspect `efibootmgr -v`, and record the original and new entry numbers.
Don't copy another person's entry numbers: firmware assigns them.

Before restarting, verify the executable AND controller driver exist on that
EFI partition. Then restart and test the direct boot path. In BIOS, the name is
**Ally Split Launcher**, not the folder name `refind-split`.

On the tested Ally, holding Volume Down during startup opens firmware setup,
where the original rEFInd remains available as a fallback.

## Rollback

Boot the original rEFInd from firmware setup. Put its recorded boot number first
in the BIOS boot order, or use `efibootmgr -o` with your actual current entries.
Remove the added Split-screen TEST stanza from the original configuration.
The new folder may remain unused. No OS boot files need deleting or renaming.

If the screen shows **Boot Option Restoration**, interrupt its countdown and
choose Continue boot for that session, then check the Batocera loader path in
the split configuration and restore your desired firmware order.

## Optional settings after testing

In the split folder's `refind.conf`, `timeout 0` waits indefinitely.
`timeout 20` boots the default after 20 seconds, but this renderer deliberately
hides the countdown. Keep `timeout 0` if you want an explicit choice.
`default_selection +` remembers the last selected entry in the folder's `vars`
directory with `use_nvram false`.
