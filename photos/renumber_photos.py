#!/usr/bin/env python3
import argparse, json, sys, re, hashlib, shutil, time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image

NUM_RE = re.compile(r"^(\d{3})\.jpg$", re.IGNORECASE)

def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def sanitize_alt(stem: str) -> str:
    s = re.sub(r"[_\-]+"," ", stem).strip()
    return s[:1].upper()+s[1:] if s else "Untitled"

def find_pairs(photos_dir: Path) -> List[Tuple[Path, Path]]:
    """Return list of (full, thumb) pairs inside photos_dir."""
    fulls = [p for p in photos_dir.glob("*.jpg") if not p.name.lower().endswith("-thumb.jpg")]
    thumbs = {p.name.lower(): p for p in photos_dir.glob("*-thumb.jpg")}
    pairs = []
    for f in fulls:
        tname = f"{f.stem}-thumb.jpg".lower()
        t = thumbs.get(tname)
        if t and t.exists():
            pairs.append((f, t))
    return pairs

def load_old_manifest(photos_dir: Path) -> Dict[str, Dict]:
    """Hash existing files referenced in old manifest to preserve alt/tone."""
    mpath = photos_dir / "manifest.json"
    mapping = {}
    if not mpath.exists():
        return mapping
    try:
        data = json.loads(mpath.read_text())
        for item in data.get("images", []):
            full = item.get("full","")
            # Expect absolute like /photos/001.jpg
            if full.startswith("/"):
                full_path = Path(full[1:])  # strip leading /
            else:
                full_path = photos_dir / full
            if not full_path.is_absolute():
                full_path = (photos_dir / Path(full).name)
            if full_path.exists():
                try:
                    h = sha1(full_path)
                    mapping[h] = {"alt": item.get("alt",""), "tone": item.get("tone","neutral")}
                except Exception:
                    pass
    except Exception:
        pass
    return mapping

def two_phase_rename(plan: List[Tuple[Path, Path, Path, Path]], dry: bool):
    """
    plan: list of tuples (full_src, thumb_src, full_dst, thumb_dst)
    Two-phase to avoid collisions.
    """
    tmp_suffix = f".renaming.{int(time.time())}"
    # Phase 1: move to temp
    temps = []
    for fsrc, tsrc, fdst, tdst in plan:
        ftmp = fsrc.with_name(fsrc.name + tmp_suffix)
        ttmp = tsrc.with_name(tsrc.name + tmp_suffix)
        if not dry:
            fsrc.rename(ftmp)
            tsrc.rename(ttmp)
        temps.append((ftmp, ttmp, fdst, tdst))
    # Phase 2: to final
    for ftmp, ttmp, fdst, tdst in temps:
        if not dry:
            ftmp.rename(fdst)
            ttmp.rename(tdst)

def main():
    ap = argparse.ArgumentParser(description="Renumber photos and rebuild manifest.json")
    ap.add_argument("project", help="Path to your local repo or photos dir")
    ap.add_argument("--sort", choices=["name","mtime"], default="name",
                    help="Order before renumbering (default: name)")
    ap.add_argument("--start", type=int, default=1, help="Start index (default 1)")
    ap.add_argument("--dry-run", action="store_true", help="Print actions, do not write")
    ap.add_argument("--default-tone", default="neutral", help="Tone used when unknown")
    args = ap.parse_args()

    root = Path(args.project).expanduser().resolve()
    photos_dir = root if (root.name == "photos" and root.is_dir()) else (root / "photos")
    if not photos_dir.exists():
        print(f"photos/ not found at: {photos_dir}", file=sys.stderr)
        sys.exit(1)

    pairs = find_pairs(photos_dir)
    if not pairs:
        print("No (full, thumb) pairs found like NNN.jpg + NNN-thumb.jpg")
        sys.exit(0)

    # sort
    if args.sort == "name":
        pairs.sort(key=lambda p: p[0].name.lower())
    else:
        pairs.sort(key=lambda p: p[0].stat().st_mtime)

    # preserve alt/tone by hashing current fulls vs old manifest
    old_map = load_old_manifest(photos_dir)
    current_meta: Dict[str, Dict] = {}
    for full, _ in pairs:
        try:
            current_meta[sha1(full)] = {"stem": full.stem}
        except Exception:
            pass

    # Build rename plan
    idx = args.start
    plan = []
    for full, thumb in pairs:
        id_str = f"{idx:03d}"
        fdst = photos_dir / f"{id_str}.jpg"
        tdst = photos_dir / f"{id_str}-thumb.jpg"
        plan.append((full, thumb, fdst, tdst))
        idx += 1

    # Show plan
    for fsrc, tsrc, fdst, tdst in plan:
        print(f"{fsrc.name}  ->  {fdst.name}")
        print(f"{tsrc.name}  ->  {tdst.name}")

    # Execute renames
    if args.dry_run:
        print("\nDRY RUN: no files renamed.")
    else:
        two_phase_rename(plan, dry=False)
        print("\nRenamed files.")

    # Rebuild manifest from the **new** state
    new_pairs = find_pairs(photos_dir)
    new_pairs.sort(key=lambda p: p[0].name.lower())

    images = []
    for full, thumb in new_pairs:
        try:
            h = sha1(full)
        except Exception:
            h = ""
        prev = old_map.get(h, {})
        alt = prev.get("alt") or sanitize_alt(full.stem)
        tone = prev.get("tone") or args.default_tone
        images.append({
            "id": full.stem,
            "thumb": f"/photos/{thumb.name}",
            "full": f"/photos/{full.name}",
            "alt": alt,
            "tone": tone
        })

    manifest_path = photos_dir / "manifest.json"
    manifest_json = json.dumps({"images": images}, indent=2)

    if args.dry_run:
        print(f"\nDRY RUN: would write manifest to {manifest_path}:\n{manifest_json}")
    else:
        # backup old manifest
        if manifest_path.exists():
            shutil.copy2(manifest_path, manifest_path.with_suffix(".json.bak"))
        manifest_path.write_text(manifest_json)
        print(f"Updated manifest: {manifest_path}")

if __name__ == "__main__":
    main()