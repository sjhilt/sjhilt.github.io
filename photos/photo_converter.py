#!/usr/bin/env python3
import argparse, json, sys, re, hashlib
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image, ImageOps

LONG_EDGE = 2000       # px for web image
THUMB_LONG_EDGE = 600  # px for thumbnail
JPEG_QUALITY = 85

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}  # HEIC needs extra libs

def find_images(p: Path) -> List[Path]:
    if p.is_file():
        return [p] if p.suffix.lower() in IMG_EXTS else []
    imgs = []
    for ext in IMG_EXTS:
        imgs += list(p.rglob(f"*{ext}"))
    # stable ordering
    return sorted(imgs, key=lambda x: x.as_posix().lower())

def load_manifest(manifest_path: Path) -> dict:
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text())
        except Exception:
            pass
    return {"images": []}

def next_index(photos_dir: Path) -> int:
    # Look for already-numbered files like 001.jpg
    pattern = re.compile(r"^(\d{3})\.jpg$")
    existing_nums = []
    for p in photos_dir.glob("*.jpg"):
        m = pattern.match(p.name)
        if m:
            try:
                existing_nums.append(int(m.group(1)))
            except ValueError:
                pass
    return (max(existing_nums) + 1) if existing_nums else 1

def sanitize_alt(stem: str) -> str:
    # Turn file name into a readable caption
    s = re.sub(r"[_\-]+", " ", stem)
    s = re.sub(r"\s+", " ", s).strip()
    # Capitalize first letter
    return s[:1].upper() + s[1:] if s else "Untitled"

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def resize_to_long_edge(img: Image.Image, target: int) -> Image.Image:
    w, h = img.size
    if max(w, h) <= target:
        return img.copy()
    if w >= h:
        new_w = target
        new_h = int(h * (target / float(w)))
    else:
        new_h = target
        new_w = int(w * (target / float(h)))
    return img.resize((new_w, new_h), Image.LANCZOS)

def save_jpeg(img: Image.Image, path: Path):
    # Convert to sRGB 8-bit and strip metadata
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.save(path, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)

def hash_bytes(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:10]

def add_to_manifest(manifest: dict, id_str: str, thumb: str, full: str, alt: str):
    manifest.setdefault("images", [])
    manifest["images"].append({
        "id": id_str,
        "thumb": thumb,
        "full": full,
        "alt": alt,
        "tone": "neutral"  # optional tag you can hand-edit later
    })

def process_one(src: Path, out_dir: Path, start_idx: int) -> Tuple[int, Optional[str]]:
    # Open, orient via EXIF, make two sizes
    try:
        im = Image.open(src)
        im = ImageOps.exif_transpose(im)
    except Exception as e:
        return start_idx, f"Skip {src.name}: {e}"

    idx = start_idx
    id_str = f"{idx:03d}"
    web_path = out_dir / f"{id_str}.jpg"
    thumb_path = out_dir / f"{id_str}-thumb.jpg"

    # Create web size
    web = resize_to_long_edge(im, LONG_EDGE)
    save_jpeg(web, web_path)

    # Create thumb
    th = resize_to_long_edge(im, THUMB_LONG_EDGE)
    save_jpeg(th, thumb_path)

    return idx + 1, None

def main():
    ap = argparse.ArgumentParser(
        description="Make /photos assets and manifest.json for sjhilt.github.io"
    )
    ap.add_argument("input", help="Folder or image to ingest")
    ap.add_argument("project", help="Path to your local repo (sjhilt.github.io)")
    ap.add_argument("--alt-prefix", default="", help="Optional prefix for alt text")
    args = ap.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    project_path = Path(args.project).expanduser().resolve()

    if not project_path.exists():
        print(f"Project path not found: {project_path}", file=sys.stderr)
        sys.exit(1)

    photos_dir = project_path / "photos"
    ensure_dir(photos_dir)
    manifest_path = photos_dir / "manifest.json"
    manifest = load_manifest(manifest_path)

    imgs = find_images(input_path)
    if not imgs:
        print("No images found. Supported: " + ", ".join(sorted(IMG_EXTS)))
        sys.exit(1)

    idx = next_index(photos_dir)

    errors = []
    added = []
    for src in imgs:
        # process and write files
        new_idx, err = process_one(src, photos_dir, idx)
        if err:
            errors.append(err)
            continue

        id_str = f"{idx:03d}"
        web_rel = f"/photos/{id_str}.jpg"
        thumb_rel = f"/photos/{id_str}-thumb.jpg"

        # Build alt text
        alt = sanitize_alt(src.stem)
        if args.alt_prefix:
            alt = f"{args.alt_prefix.strip()} — {alt}"

        add_to_manifest(manifest, id_str, thumb_rel, web_rel, alt)
        added.append((src.name, id_str))
        idx = new_idx

    # Write manifest (stable order)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"Wrote manifest: {manifest_path}")

    for name, id_str in added:
        print(f"Added {name} -> {id_str}.jpg / {id_str}-thumb.jpg")

    if errors:
        print("\nSome files were skipped:")
        for e in errors:
            print("  -", e)

if __name__ == "__main__":
    main()