#!/usr/bin/env python3
"""Validate the site's structured data and local static references."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DATE_PATTERN = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")
CSS_URL_PATTERN = re.compile(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)", re.IGNORECASE)
IGNORED_SCHEMES = {"data", "mailto", "tel", "javascript"}
PUBLICATION_FIELDS = ("date", "title", "type", "link", "display")
PHOTO_FIELDS = ("id", "thumb", "full", "alt", "tone")


class ReferenceParser(HTMLParser):
    """Collect static references and external-link attributes from HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str]] = []
        self.blank_links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value or "" for name, value in attrs}
        for attribute in ("href", "src", "poster"):
            if values.get(attribute):
                self.references.append((attribute, values[attribute]))

        if tag.lower() == "a" and values.get("target", "").lower() == "_blank":
            self.blank_links.append(values)


class Validation:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def load_json(self, relative_path: str) -> object | None:
        path = ROOT / relative_path
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            self.error(f"{relative_path}: unable to read valid JSON: {exc}")
            return None

    def validate_date(self, value: str, location: str) -> None:
        match = DATE_PATTERN.fullmatch(value)
        if not match:
            self.error(f"{location}: invalid date {value!r}; use YYYY, YYYY-MM, or YYYY-MM-DD")
            return

        year, month, day = (int(part) if part else None for part in match.groups())
        try:
            if day is not None:
                date(year, month or 1, day)
            elif month is not None:
                date(year, month, 1)
            else:
                date(year, 1, 1)
        except ValueError as exc:
            self.error(f"{location}: invalid calendar date {value!r}: {exc}")

    def validate_web_url(self, value: str, location: str) -> None:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            self.error(f"{location}: expected an absolute HTTP(S) URL, found {value!r}")
        elif parsed.scheme == "http":
            self.warn(f"{location}: legacy HTTP URL should be upgraded when HTTPS is verified: {value}")

    def validate_publications(self) -> None:
        payload = self.load_json("publications.json")
        if payload is None:
            return

        publications = payload if isinstance(payload, list) else payload.get("publications") if isinstance(payload, dict) else None
        if not isinstance(publications, list):
            self.error("publications.json: expected a publication array or an object with a publications array")
            return

        record_keys: list[tuple[str, ...]] = []
        links: list[str] = []
        for index, publication in enumerate(publications, start=1):
            location = f"publications.json publication #{index}"
            if not isinstance(publication, dict):
                self.error(f"{location}: expected an object")
                continue

            for field in PUBLICATION_FIELDS:
                value = publication.get(field)
                if not isinstance(value, str) or not value.strip():
                    self.error(f"{location}: missing non-empty string field {field!r}")

            if not all(isinstance(publication.get(field), str) for field in PUBLICATION_FIELDS):
                continue

            self.validate_date(publication["date"], f"{location} date")
            self.validate_web_url(publication["link"], f"{location} link")
            links.append(publication["link"].strip().casefold())
            record_keys.append(tuple(" ".join(publication[field].split()).casefold() for field in PUBLICATION_FIELDS))

        for key, count in Counter(record_keys).items():
            if count > 1:
                self.error(f"publications.json: duplicate publication record ({count} copies): {key[1]!r}")
        for link, count in Counter(links).items():
            if link and count > 1:
                self.error(f"publications.json: duplicate publication URL ({count} uses): {link}")

        print(f"Checked {len(publications)} publications.")

    def local_path(self, source: Path, reference: str) -> Path | None:
        reference = reference.strip()
        if not reference or reference.startswith(("#", "//")) or "{{" in reference or "${" in reference:
            return None

        parsed = urlsplit(reference)
        if parsed.scheme.lower() in IGNORED_SCHEMES or parsed.scheme or parsed.netloc:
            return None

        clean_path = unquote(parsed.path).replace("\\", "/")
        if not clean_path:
            return None
        if clean_path.startswith("/"):
            return ROOT / clean_path.lstrip("/")
        return source.parent / clean_path

    def validate_photos(self) -> None:
        payload = self.load_json("photos/manifest.json")
        if payload is None:
            return

        photos = payload if isinstance(payload, list) else payload.get("images") if isinstance(payload, dict) else None
        if not isinstance(photos, list):
            self.error("photos/manifest.json: expected an image array or an object with an images array")
            return

        unique_values: dict[str, list[str]] = {field: [] for field in ("id", "thumb", "full")}
        for index, photo in enumerate(photos, start=1):
            location = f"photos/manifest.json image #{index}"
            if not isinstance(photo, dict):
                self.error(f"{location}: expected an object")
                continue

            for field in PHOTO_FIELDS:
                value = photo.get(field)
                if not isinstance(value, str) or not value.strip():
                    self.error(f"{location}: missing non-empty string field {field!r}")

            for field in unique_values:
                value = photo.get(field)
                if isinstance(value, str) and value:
                    unique_values[field].append(value)

            for field in ("thumb", "full"):
                value = photo.get(field)
                if isinstance(value, str) and value:
                    path = self.local_path(ROOT / "photos" / "manifest.json", value)
                    if path is None or not path.is_file():
                        self.error(f"{location}: {field} file does not exist: {value}")

        for field, values in unique_values.items():
            for value, count in Counter(values).items():
                if count > 1:
                    self.error(f"photos/manifest.json: duplicate {field} ({count} uses): {value}")

        print(f"Checked {len(photos)} photo manifest entries.")

    def validate_html_and_css(self) -> None:
        html_files = sorted(ROOT.rglob("*.html"))
        css_files = sorted(ROOT.rglob("*.css"))

        for path in html_files:
            relative = path.relative_to(ROOT).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                self.error(f"{relative}: unable to read HTML: {exc}")
                continue

            parser = ReferenceParser()
            try:
                parser.feed(text)
            except Exception as exc:
                self.error(f"{relative}: unable to parse HTML: {exc}")
                continue

            head = text.split("</head>", 1)[0].lower()
            if 'rel="icon"' not in head and "rel='icon'" not in head:
                self.error(f"{relative}: missing favicon link in <head>")

            for attributes in parser.blank_links:
                rel = set(attributes.get("rel", "").lower().split())
                if not {"noopener", "noreferrer"}.issubset(rel):
                    self.error(f"{relative}: target=\"_blank\" link lacks rel=\"noopener noreferrer\": {attributes.get('href', '')}")

            for attribute, reference in parser.references:
                local = self.local_path(path, reference)
                if local is not None and not local.exists():
                    self.error(f"{relative}: broken local {attribute} reference: {reference}")

        for path in css_files:
            relative = path.relative_to(ROOT).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                self.error(f"{relative}: unable to read CSS: {exc}")
                continue

            for _, reference in CSS_URL_PATTERN.findall(text):
                local = self.local_path(path, reference)
                if local is not None and not local.exists():
                    self.error(f"{relative}: broken local CSS reference: {reference}")

        print(f"Checked {len(html_files)} HTML files and {len(css_files)} CSS files.")

    def report(self) -> int:
        for warning in self.warnings:
            print(f"WARNING: {warning}")
        for error in self.errors:
            print(f"ERROR: {error}", file=sys.stderr)

        if self.errors:
            print(f"Validation failed with {len(self.errors)} error(s) and {len(self.warnings)} warning(s).", file=sys.stderr)
            return 1

        print(f"Validation passed with {len(self.warnings)} warning(s).")
        return 0


def main() -> int:
    validation = Validation()
    validation.validate_publications()
    validation.validate_photos()
    validation.validate_html_and_css()
    return validation.report()


if __name__ == "__main__":
    raise SystemExit(main())