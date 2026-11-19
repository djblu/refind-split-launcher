#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Package the compiled x86-64 split launcher with user-provided or bundled art."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import zipfile
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=ROOT / "artwork/background.png")
    parser.add_argument("--top", type=float, default=1108 / 1672)
    parser.add_argument("--bottom", type=float, default=482 / 1672)
    parser.add_argument("--dim", type=float, default=0.28)
    args = parser.parse_args()
    if not all(0 <= value <= 1 for value in (args.top, args.bottom, args.dim)):
        parser.error("--top, --bottom and --dim must be between zero and one")
    binary = ROOT / "refind/refind_x64.efi"
    if not binary.is_file():
        parser.error("Build the executable first: make gnuefi")
    if binary.read_bytes()[:2] != b"MZ":
        parser.error("The compiled executable is not a PE/EFI file")
    source = Image.open(args.image).convert("RGB")
    width, height = source.size
    mask = Image.new("L", source.size, 0)
    ImageDraw.Draw(mask).polygon(
        [(0, 0), (round(width * args.top), 0),
         (round(width * args.bottom), height - 1), (0, height - 1)], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(3))
    dimmed = source.point(lambda value: round(value * args.dim))
    theme = ROOT / "dist/refind-split"
    theme.mkdir(parents=True, exist_ok=True)
    for name, selection in [
        ("windows", mask), ("batocera", Image.eval(mask, lambda value: 255 - value))
    ]:
        result = Image.composite(source, dimmed, selection)
        result.resize((1920, 1080), Image.Resampling.LANCZOS).save(theme / f"split-{name}.png")
    shutil.copy2(binary, theme)
    shutil.copy2(ROOT / "split-tools/refind.conf", theme / "refind.conf")
    # Include icons so the stock-menu fallback remains graphical.
    shutil.copytree(ROOT / "icons", theme / "icons", dirs_exist_ok=True)
    names = ["README.md", "INSTALL.md", "COPYING.txt", "LICENSE.txt", "CREDITS.txt", "BUILDING.txt"]
    dist = ROOT / "dist"
    for name in names:
        shutil.copy2(ROOT / name, dist / name)
    shutil.copy2(ROOT / "artwork/NOTICE.md", dist / "ARTWORK-NOTICE.md")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    (dist / "BUILD-INFO.txt").write_text(
        f"Source: https://github.com/djblu/refind-split-launcher\nCommit: {revision}\n"
        "Experimental unsigned x86-64 GNU-EFI build.\n"
        "See INSTALL.md; configure verified volume labels and loader paths before testing.\n")
    paths = sorted(p for p in theme.rglob("*") if p.is_file())
    paths += [dist / name for name in names + ["ARTWORK-NOTICE.md", "BUILD-INFO.txt"]]
    checksum = dist / "SHA256SUMS"
    checksum.write_text("".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(dist).as_posix()}\n"
        for p in sorted(paths)))
    archive = dist / "refind-split-launcher.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as out:
        for path in paths + [checksum]:
            out.write(path, path.relative_to(dist))
    print(archive)


if __name__ == "__main__":
    main()
