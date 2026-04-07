#!/usr/bin/env python3
"""
Discover API endpoints after authenticated login.

Features:
- Login once (manual or auto)
- Visit one or more target pages
- Capture API endpoints from live network traffic
- Optional lightweight probing for common API docs/routes
- Export results to JSON + TXT
"""

from __future__ import annotations

import argparse
import getpass
import json
import re
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright


COMMON_PROBE_PATHS = [
    "/api",
    "/api/",
    "/api/docs",
    "/api/swagger",
    "/api/swagger.json",
    "/api/openapi.json",
    "/api/v1",
    "/api/health",
    "/api/status",
]


def clean_cli_value(value: str) -> str:
    v = (value or "").strip()
    if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
        v = v[1:-1].strip()
    return v


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover authenticated API endpoints from browser network traffic.")
    parser.add_argument("--login-url", default="", help="Login page URL")
    parser.add_argument("--target-url", default="", help="Single target page URL")
    parser.add_argument("--target-urls", nargs="*", default=[], help="Multiple target page URLs")
    parser.add_argument("--targets-file", default="", help="Text file with one target URL per line")
    parser.add_argument("--api-url", default="", help="API base URL, e.g. https://portal.example.com/api")
    parser.add_argument("--manual-login", action="store_true", help="Login manually in browser and press Enter")
    parser.add_argument("--username", default="", help="Username/email/mobile for auto login")
    parser.add_argument("--password", default="", help="Password for auto login")
    parser.add_argument("--username-selector", default='input[type="email"], input[name="email"], input[name="username"], input[name="mobile"], input[type="tel"], input[type="text"]')
    parser.add_argument("--password-selector", default='input[type="password"], input[name="password"]')
    parser.add_argument("--submit-selector", default="", help="Optional selector for login button")
    parser.add_argument("--login-wait-seconds", type=int, default=20, help="How long to wait for login form")
    parser.add_argument("--capture-seconds", type=int, default=20, help="Capture time per target")
    parser.add_argument("--scroll-steps", type=int, default=25, help="Scroll steps per target")
    parser.add_argument("--probe-common", action="store_true", help="Probe common API/doc endpoints")
    parser.add_argument("--download-notes", action="store_true", help="Download discovered note PDFs")
    parser.add_argument("--out-dir", default="api_discovery", help="Output folder")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    return parser.parse_args()


def prompt_if_missing(args: argparse.Namespace) -> None:
    if not args.login_url:
        args.login_url = clean_cli_value(input("Login URL: "))
    if not args.manual_login:
        if not args.username:
            args.username = input("Username / Email / Mobile: ").strip()
        if not args.password:
            args.password = getpass.getpass("Password: ")
    if not args.target_url and not args.target_urls and not args.targets_file and not args.api_url:
        args.api_url = clean_cli_value(input("API URL (e.g. https://portal.example.com/api): "))
    if not args.target_url and not args.target_urls and not args.targets_file:
        print("No target URLs provided. The script will discover from API URL/probing only.")


def load_targets(args: argparse.Namespace) -> list[str]:
    targets = []
    if args.target_url:
        targets.append(clean_cli_value(args.target_url))
    for u in args.target_urls:
        u = clean_cli_value(u)
        if u:
            targets.append(u)
    if args.targets_file:
        p = Path(args.targets_file)
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    targets.append(clean_cli_value(line))
    dedup = []
    seen = set()
    for t in targets:
        if t not in seen:
            seen.add(t)
            dedup.append(t)
    return dedup


def first_visible_locator(page_or_frame, selector: str):
    loc = page_or_frame.locator(selector)
    count = loc.count()
    for i in range(count):
        item = loc.nth(i)
        try:
            if item.is_visible():
                return item
        except Exception:
            continue
    return loc.first


def find_login_fields(page, user_selector: str, pass_selector: str, timeout_ms: int = 20_000):
    end_at = time.time() + timeout_ms / 1000.0
    while time.time() < end_at:
        scopes = [page]
        try:
            scopes.extend(page.frames)
        except Exception:
            pass
        for scope in scopes:
            try:
                u = first_visible_locator(scope, user_selector)
                p = first_visible_locator(scope, pass_selector)
                if u.count() > 0 and p.count() > 0:
                    return scope, u, p
            except Exception:
                continue
        page.wait_for_timeout(300)
    return None, None, None


def maybe_login(page, args: argparse.Namespace) -> None:
    page.goto(args.login_url, wait_until="domcontentloaded")
    page.on("dialog", lambda d: d.accept())
    page.wait_for_timeout(1200)
    if args.manual_login:
        print("Manual login: complete login in browser, then press Enter here...")
        input()
        return
    scope, user, pwd = find_login_fields(
        page, args.username_selector, args.password_selector, timeout_ms=args.login_wait_seconds * 1000
    )
    if not scope or not user or not pwd or user.count() == 0 or pwd.count() == 0:
        raise RuntimeError("Could not find login fields. Use --manual-login or selectors.")
    user.fill(args.username)
    pwd.fill(args.password)
    if args.submit_selector:
        first_visible_locator(scope, args.submit_selector).click()
    else:
        pwd.press("Enter")
    page.wait_for_timeout(2500)


def normalize_endpoint(url: str) -> str:
    try:
        parsed = urlparse(url)
        path = parsed.path or "/"
        if parsed.query:
            return f"{path}?{parsed.query}"
        return path
    except Exception:
        return url


def filename_from_url(url: str, fallback: str) -> str:
    try:
        parsed = urlparse(url)
        name = Path(unquote(parsed.path)).name
        if name:
            return re.sub(r'[\\/:*?"<>|]+', "_", name)
    except Exception:
        pass
    return fallback


def add_video_chapter_from_url(url: str, out_set: set[str]) -> None:
    # Pattern: /api/student/myVideos/chapter/<course_id>/<chapter_id>
    m = re.search(r"/api/student/myVideos/chapter/([^/]+)/([^/?#]+)", url)
    if m:
        out_set.add(m.group(2))


def extract_urls_from_object(obj, out_urls: set[str]) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            extract_urls_from_object(v, out_urls)
        return
    if isinstance(obj, list):
        for v in obj:
            extract_urls_from_object(v, out_urls)
        return
    if isinstance(obj, str):
        text = obj.strip()
        if text.startswith("http://") or text.startswith("https://"):
            out_urls.add(text)
        for m in re.findall(r"https?://[^\s\"'<>]+", text):
            out_urls.add(m)


def append_auth_query(url: str, token: str) -> str:
    if not token:
        return url
    if "Authorization=Bearer" in url or "Authorization=Bearer%20" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}Authorization=Bearer%20{token}"


def main() -> int:
    args = parse_args()
    prompt_if_missing(args)
    targets = load_targets(args)
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    notes_dir = out_dir / "notes_pdfs"
    if args.download_notes:
        notes_dir.mkdir(parents=True, exist_ok=True)

    endpoint_map: dict[str, dict] = {}
    notes_urls: set[str] = set()
    embed_urls: set[str] = set()
    chapter_ids: set[str] = set()
    bunny_ids: set[str] = set()
    auth_token = ""
    base_host = ""
    downloaded = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context()
        page = context.new_page()

        def on_response(resp):
            try:
                req = resp.request
                url = resp.url
                if "/api/" not in url:
                    return
                parsed = urlparse(url)
                key = f"{req.method} {normalize_endpoint(url)}"
                endpoint_map[key] = {
                    "method": req.method,
                    "url": url,
                    "endpoint": normalize_endpoint(url),
                    "host": parsed.netloc,
                    "status": resp.status,
                    "content_type": (resp.headers or {}).get("content-type", ""),
                }
                low = url.lower()
                if "/api/student/notes/file/" in low or low.endswith(".pdf") or "application/pdf" in ((resp.headers or {}).get("content-type", "").lower()):
                    notes_urls.add(url)
                if "iframe.mediadelivery.net/embed/" in low:
                    embed_urls.add(url)
                add_video_chapter_from_url(url, chapter_ids)

                ctype = ((resp.headers or {}).get("content-type", "") or "").lower()
                if "application/json" in ctype:
                    try:
                        payload = resp.json()
                        found_urls: set[str] = set()
                        extract_urls_from_object(payload, found_urls)
                        for u in found_urls:
                            lu = u.lower()
                            if "/api/student/notes/file/" in lu:
                                notes_urls.add(u)
                            if "iframe.mediadelivery.net/embed/" in lu:
                                embed_urls.add(u)
                            add_video_chapter_from_url(u, chapter_ids)
                        if isinstance(payload, dict):
                            data = payload.get("data")
                            if isinstance(data, list):
                                for item in data:
                                    if not isinstance(item, dict):
                                        continue
                                    chapter = item.get("chapterID")
                                    if isinstance(chapter, str) and chapter.strip():
                                        chapter_ids.add(chapter.strip())
                                    bunny = item.get("bunnyID")
                                    if isinstance(bunny, str) and bunny.strip():
                                        bunny_ids.add(bunny.strip())
                                    secure = item.get("secureEmbedUrl")
                                    if isinstance(secure, str) and secure.strip():
                                        embed_urls.add(secure.strip())
                            elif isinstance(data, dict):
                                chapter = data.get("chapterID")
                                if isinstance(chapter, str) and chapter.strip():
                                    chapter_ids.add(chapter.strip())
                    except Exception:
                        pass
            except Exception:
                pass

        page.on("response", on_response)

        try:
            maybe_login(page, args)
            if args.api_url:
                args.api_url = clean_cli_value(args.api_url)
                parsed_api = urlparse(args.api_url)
                if parsed_api.scheme and parsed_api.netloc:
                    base_host = f"{parsed_api.scheme}://{parsed_api.netloc}"
            try:
                values = page.evaluate(
                    """
                    () => {
                      const vals = [];
                      try {
                        for (let i = 0; i < localStorage.length; i++) {
                          const k = localStorage.key(i);
                          vals.push(String(localStorage.getItem(k) || ""));
                        }
                      } catch (e) {}
                      try {
                        for (let i = 0; i < sessionStorage.length; i++) {
                          const k = sessionStorage.key(i);
                          vals.push(String(sessionStorage.getItem(k) || ""));
                        }
                      } catch (e) {}
                      return vals;
                    }
                    """
                ) or []
                jwt_re = re.compile(r"eyJ[A-Za-z0-9_\-]+?\.[A-Za-z0-9_\-]+?\.[A-Za-z0-9_\-]+")
                for raw in values:
                    if isinstance(raw, str):
                        m = jwt_re.search(raw)
                        if m:
                            auth_token = m.group(0)
                            break
            except Exception:
                pass
            for i, target in enumerate(targets, start=1):
                print(f"[{i}/{len(targets)}] Visiting {target}")
                page.goto(target, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
                parsed_target = urlparse(target)
                if parsed_target.scheme and parsed_target.netloc:
                    base_host = f"{parsed_target.scheme}://{parsed_target.netloc}"
                per_step_ms = max(100, int((args.capture_seconds * 1000) / max(1, args.scroll_steps)))
                for _ in range(args.scroll_steps):
                    page.mouse.wheel(0, 1200)
                    page.wait_for_timeout(per_step_ms)

            if args.probe_common and base_host:
                print("Probing common API paths...")
                for path in COMMON_PROBE_PATHS:
                    try:
                        u = base_host.rstrip("/") + path
                        r = context.request.get(u, timeout=15000)
                        key = f"GET {normalize_endpoint(u)}"
                        endpoint_map[key] = {
                            "method": "GET",
                            "url": u,
                            "endpoint": normalize_endpoint(u),
                            "host": urlparse(u).netloc,
                            "status": r.status,
                            "content_type": (r.headers or {}).get("content-type", ""),
                        }
                    except Exception:
                        continue
            elif not targets and args.api_url:
                # If user only provides API URL, still hit it once.
                try:
                    u = clean_cli_value(args.api_url)
                    r = context.request.get(u, timeout=15000)
                    key = f"GET {normalize_endpoint(u)}"
                    endpoint_map[key] = {
                        "method": "GET",
                        "url": u,
                        "endpoint": normalize_endpoint(u),
                        "host": urlparse(u).netloc,
                        "status": r.status,
                        "content_type": (r.headers or {}).get("content-type", ""),
                    }
                except Exception:
                    pass
            notes_list = sorted(notes_urls)
            if args.download_notes and notes_list:
                for idx, url in enumerate(notes_list, start=1):
                    try:
                        final_url = append_auth_query(url, auth_token)
                        headers = {}
                        if auth_token:
                            headers["Authorization"] = f"Bearer {auth_token}"
                        resp = context.request.get(final_url, timeout=30000, headers=headers)
                        if not resp.ok:
                            continue
                        body = resp.body()
                        ctype = (resp.headers or {}).get("content-type", "").lower()
                        if body and (body.startswith(b"%PDF") or "application/pdf" in ctype):
                            name = filename_from_url(url, f"note_{idx}.pdf")
                            if not name.lower().endswith(".pdf"):
                                name += ".pdf"
                            out_file = notes_dir / name
                            if out_file.exists():
                                out_file = notes_dir / f"{Path(name).stem}_{idx}.pdf"
                            out_file.write_bytes(body)
                            downloaded += 1
                    except Exception:
                        continue
        finally:
            browser.close()

    discovered = sorted(endpoint_map.values(), key=lambda x: (x["host"], x["endpoint"], x["method"]))
    data = {
        "total_endpoints": len(discovered),
        "endpoints": discovered,
    }
    json_file = out_dir / "api_endpoints.json"
    txt_file = out_dir / "api_endpoints.txt"
    json_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    txt_lines = [f'{e["method"]} {e["url"]} [status={e["status"]}]' for e in discovered]
    txt_file.write_text("\n".join(txt_lines), encoding="utf-8")

    notes_list = sorted(notes_urls)
    notes_json = out_dir / "notes_pdf_urls.json"
    notes_txt = out_dir / "notes_pdf_urls.txt"
    notes_json.write_text(json.dumps({"total": len(notes_list), "urls": notes_list}, indent=2, ensure_ascii=False), encoding="utf-8")
    notes_txt.write_text("\n".join(notes_list), encoding="utf-8")

    embed_list = sorted(embed_urls)
    chapters_list = sorted(chapter_ids)
    bunny_list = sorted(bunny_ids)
    embed_json = out_dir / "secure_embed_urls.json"
    embed_txt = out_dir / "secure_embed_urls.txt"
    chapter_json = out_dir / "chapter_ids.json"
    chapter_txt = out_dir / "chapter_ids.txt"
    bunny_json = out_dir / "bunny_ids.json"
    bunny_txt = out_dir / "bunny_ids.txt"
    embed_json.write_text(json.dumps({"total": len(embed_list), "urls": embed_list}, indent=2, ensure_ascii=False), encoding="utf-8")
    embed_txt.write_text("\n".join(embed_list), encoding="utf-8")
    chapter_json.write_text(json.dumps({"total": len(chapters_list), "chapter_ids": chapters_list}, indent=2, ensure_ascii=False), encoding="utf-8")
    chapter_txt.write_text("\n".join(chapters_list), encoding="utf-8")
    bunny_json.write_text(json.dumps({"total": len(bunny_list), "bunny_ids": bunny_list}, indent=2, ensure_ascii=False), encoding="utf-8")
    bunny_txt.write_text("\n".join(bunny_list), encoding="utf-8")

    print(f"Saved: {json_file}")
    print(f"Saved: {txt_file}")
    print(f"Saved: {notes_json}")
    print(f"Saved: {notes_txt}")
    print(f"Saved: {embed_json}")
    print(f"Saved: {embed_txt}")
    print(f"Saved: {chapter_json}")
    print(f"Saved: {chapter_txt}")
    print(f"Saved: {bunny_json}")
    print(f"Saved: {bunny_txt}")
    if args.download_notes:
        print(f"Downloaded note PDFs: {downloaded}")
    print(f"Total endpoints discovered: {len(discovered)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

