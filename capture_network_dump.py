#!/usr/bin/env python3
"""
Capture full network activity for an authenticated target page.

This script is intended as a troubleshooting helper similar to the browser
Network tab. It records:
- request URL/method/headers/post data
- response URL/status/headers/content-type
- response body size and saved body files (optional)

Usage:
  python capture_network_dump.py --login-url "https://site/login" --target-url "https://site/page" --manual-login
"""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


def safe_name(value: str, fallback: str) -> str:
    text = (value or "").strip()
    text = re.sub(r"[^\w.\- ]+", "_", text)
    text = re.sub(r"\s+", "_", text).strip("._")
    return text or fallback


def click_tab(page, tab_name: str, timeout_ms: int = 10_000) -> bool:
    selectors = [
        f'role=tab[name="{tab_name}"]',
        f'text="{tab_name}"',
        f'button:has-text("{tab_name}")',
        f'a:has-text("{tab_name}")',
    ]
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            if loc.count() > 0:
                loc.click(timeout=timeout_ms)
                page.wait_for_timeout(1200)
                return True
        except Exception:
            continue
    return False


def click_tab_fuzzy(page, tab_name: str) -> bool:
    target = (tab_name or "").strip().lower()
    if not target:
        return False
    script = """
    (tabText) => {
      const wanted = (tabText || '').toLowerCase().trim();
      const candidates = Array.from(document.querySelectorAll('button, a, [role="tab"], div, span'));
      for (const el of candidates) {
        const txt = (el.innerText || el.textContent || '').toLowerCase().trim();
        if (!txt) continue;
        if (txt === wanted || txt.includes(wanted)) {
          try { el.click(); return true; } catch (e) {}
        }
      }
      return false;
    }
    """
    try:
        ok = bool(page.evaluate(script, target))
        if ok:
            page.wait_for_timeout(1200)
        return ok
    except Exception:
        return False


def guess_ext_from_content_type(content_type: str) -> str:
    ctype = (content_type or "").lower()
    if "application/pdf" in ctype:
        return ".pdf"
    if "application/json" in ctype:
        return ".json"
    if "text/html" in ctype:
        return ".html"
    if "text/plain" in ctype:
        return ".txt"
    if "javascript" in ctype:
        return ".js"
    if "image/png" in ctype:
        return ".png"
    if "image/jpeg" in ctype:
        return ".jpg"
    if "application/vnd.apple.mpegurl" in ctype:
        return ".m3u8"
    if "video/mp2t" in ctype:
        return ".ts"
    if "video/" in ctype:
        return ".mp4"
    return ".bin"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture full network dump for a target page.")
    parser.add_argument("--login-url", default="", help="Login page URL")
    parser.add_argument("--target-url", default="", help="Single target page URL")
    parser.add_argument("--target-urls", nargs="*", default=[], help="Multiple target page URLs")
    parser.add_argument("--targets-file", default="", help="Text file with one target URL per line")
    parser.add_argument("--manual-login", action="store_true", help="Login manually in browser and press Enter")
    parser.add_argument("--username", default="", help="Optional username for auto-login")
    parser.add_argument("--password", default="", help="Optional password for auto-login")
    parser.add_argument("--username-selector", default='input[type="email"], input[name="email"], input[name="username"], input[name="mobile"], input[type="tel"], input[placeholder*="Email"], input[placeholder*="email"], input[placeholder*="Mobile"], input[placeholder*="mobile"], input[type="text"]')
    parser.add_argument("--password-selector", default='input[type="password"], input[name="password"]')
    parser.add_argument("--submit-selector", default="", help="Optional selector for login button")
    parser.add_argument("--login-wait-seconds", type=int, default=20, help="How long to wait for login form")
    parser.add_argument("--notes-tab-name", default="Notes", help='Notes tab label (default: "Notes")')
    parser.add_argument("--capture-seconds", type=int, default=35, help="How long to capture after target opens")
    parser.add_argument("--scroll-steps", type=int, default=40, help="Auto-scroll steps during capture")
    parser.add_argument("--save-bodies", action="store_true", help="Save response bodies to disk")
    parser.add_argument("--max-body-bytes", type=int, default=8_000_000, help="Skip body save if larger than this")
    parser.add_argument("--include-images", action="store_true", help="Include image requests/responses in dump")
    parser.add_argument("--out-dir", default="network_dump", help="Output folder")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    return parser.parse_args()


def prompt_if_missing(args: argparse.Namespace) -> None:
    if not args.login_url:
        args.login_url = input("Login URL: ").strip()
    if not args.manual_login:
        if not args.username:
            args.username = input("Username / Email / Mobile: ").strip()
        if not args.password:
            args.password = getpass.getpass("Password: ")
    if not args.target_url and not args.target_urls and not args.targets_file:
        print("Enter target URLs one by one. Leave blank and press Enter to finish.")
        collected: list[str] = []
        while True:
            u = input(f"Target URL #{len(collected) + 1}: ").strip()
            if not u:
                break
            collected.append(u)
        args.target_urls = collected
    if not args.notes_tab_name:
        args.notes_tab_name = input('Notes tab name [Notes]: ').strip() or "Notes"


def is_image_response(resource_type: str, content_type: str, url: str) -> bool:
    rt = (resource_type or "").lower()
    ct = (content_type or "").lower()
    low = (url or "").lower()
    if rt == "image":
        return True
    if ct.startswith("image/"):
        return True
    return low.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".bmp", ".avif"))


def get_request_post_payload(req) -> tuple[str, str]:
    # Playwright may fail decoding binary/gzip request body as UTF-8 on req.post_data.
    try:
        text = req.post_data
        if text is None:
            return "", ""
        return text, ""
    except Exception:
        pass

    try:
        buf = req.post_data_buffer
        if callable(buf):
            buf = buf()
        if isinstance(buf, (bytes, bytearray)):
            return "", base64.b64encode(bytes(buf)).decode("ascii")
    except Exception:
        pass
    return "", ""


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
    end_at = time.time() + (timeout_ms / 1000.0)
    while time.time() < end_at:
        scopes = [page]
        try:
            scopes.extend(page.frames)
        except Exception:
            pass
        for scope in scopes:
            try:
                user_loc = first_visible_locator(scope, user_selector)
                pass_loc = first_visible_locator(scope, pass_selector)
                if user_loc.count() > 0 and pass_loc.count() > 0:
                    return scope, user_loc, pass_loc
            except Exception:
                continue
        page.wait_for_timeout(300)
    return None, None, None


def dismiss_success_popup(page, timeout_ms: int = 4_000) -> None:
    ok_selectors = [
        'role=button[name="OK"]',
        'button:has-text("OK")',
        'button:has-text("Ok")',
        'text="OK"',
    ]
    end_at = time.time() + (timeout_ms / 1000.0)
    while time.time() < end_at:
        for selector in ok_selectors:
            try:
                loc = page.locator(selector).first
                if loc.count() > 0 and loc.is_visible():
                    loc.click(timeout=700)
                    page.wait_for_timeout(300)
                    break
            except Exception:
                continue
        page.wait_for_timeout(200)


def load_targets(args: argparse.Namespace) -> list[str]:
    targets: list[str] = []
    if args.target_url:
        targets.append(args.target_url.strip())
    for u in args.target_urls:
        u = (u or "").strip()
        if u:
            targets.append(u)
    if args.targets_file:
        p = Path(args.targets_file)
        if not p.exists():
            raise FileNotFoundError(f"targets file not found: {p}")
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                targets.append(line)
    deduped: list[str] = []
    seen: set[str] = set()
    for t in targets:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    if not deduped:
        raise ValueError("Provide at least one target URL via --target-url, --target-urls, or --targets-file.")
    return deduped


def do_auto_login(page, args: argparse.Namespace) -> None:
    page.wait_for_timeout(1200)
    scope, user, pwd = find_login_fields(
        page, args.username_selector, args.password_selector, timeout_ms=args.login_wait_seconds * 1000
    )
    if not scope or not user or not pwd or user.count() == 0 or pwd.count() == 0:
        raise RuntimeError("Could not find login fields. Use --manual-login or provide selectors.")
    user.fill(args.username)
    pwd.fill(args.password)
    if args.submit_selector:
        first_visible_locator(scope, args.submit_selector).click()
    else:
        pwd.press("Enter")
    dismiss_success_popup(page)
    page.wait_for_timeout(2500)


def write_outputs(entries: list[dict], out_dir: Path, bodies_dir: Path) -> tuple[Path, Path]:
    dump_file = out_dir / "network_dump.json"
    dump_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")

    by_status: dict[str, int] = {}
    largest = []
    for rec in entries:
        if rec.get("phase") != "response":
            continue
        st = str(rec.get("status", ""))
        by_status[st] = by_status.get(st, 0) + 1
        size = rec.get("body_size_bytes")
        if isinstance(size, int):
            largest.append((size, rec.get("url", ""), rec.get("content_type", "")))
    largest.sort(reverse=True)
    largest = largest[:15]

    summary = {
        "total_events": len(entries),
        "response_status_counts": by_status,
        "largest_responses_top15": [
            {"size_bytes": s, "url": u, "content_type": ct} for s, u, ct in largest
        ],
        "dump_file": str(dump_file),
        "bodies_dir": str(bodies_dir),
    }
    summary_file = out_dir / "summary.json"
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return dump_file, summary_file


def capture_target(page, args: argparse.Namespace, target_url: str, out_dir: Path, bodies_dir: Path) -> tuple[Path, Path]:
    entries: list[dict] = []
    seq = {"n": 0}

    def on_request(req):
        try:
            if not args.include_images and (req.resource_type or "").lower() == "image":
                return
            seq["n"] += 1
            rid = f"req_{seq['n']}"
            post_data_text, post_data_b64 = get_request_post_payload(req)
            rec = {
                "id": rid,
                "phase": "request",
                "time": time.time(),
                "url": req.url,
                "method": req.method,
                "resource_type": req.resource_type,
                "headers": req.headers,
                "post_data": post_data_text,
                "post_data_b64": post_data_b64,
            }
            entries.append(rec)
        except Exception as ex:
            entries.append(
                {
                    "phase": "request_error",
                    "time": time.time(),
                    "url": getattr(req, "url", ""),
                    "error": str(ex),
                }
            )

    def on_response(resp):
        try:
            req = resp.request
            ctype = (resp.headers or {}).get("content-type", "")
            if not args.include_images and is_image_response(req.resource_type, ctype, resp.url):
                return
            body_file = ""
            body_size = None
            body_b64 = ""
            if args.save_bodies:
                body = resp.body()
                body_size = len(body)
                if body_size <= args.max_body_bytes:
                    path_part = Path(urlparse(resp.url).path).name
                    base = safe_name(path_part, f"resp_{int(time.time() * 1000)}")
                    ext = Path(base).suffix or guess_ext_from_content_type(ctype)
                    file_name = f"{safe_name(Path(base).stem, 'resp')}_{int(time.time() * 1000)}{ext}"
                    out_file = bodies_dir / file_name
                    out_file.write_bytes(body)
                    body_file = str(out_file)
                else:
                    body_b64 = base64.b64encode(body[:2048]).decode("ascii")
            rec = {
                "phase": "response",
                "time": time.time(),
                "url": resp.url,
                "status": resp.status,
                "status_text": resp.status_text,
                "ok": resp.ok,
                "resource_type": req.resource_type,
                "method": req.method,
                "request_headers": req.headers,
                "response_headers": resp.headers,
                "content_type": ctype,
                "body_size_bytes": body_size,
                "body_file": body_file,
                "body_preview_b64": body_b64,
            }
            entries.append(rec)
        except Exception as ex:
            entries.append(
                {
                    "phase": "response_error",
                    "time": time.time(),
                    "url": getattr(resp, "url", ""),
                    "error": str(ex),
                }
            )

    page.on("request", on_request)
    page.on("response", on_response)
    try:
        page.goto(target_url, wait_until="domcontentloaded")
        print(f"Target page opened; capturing network: {target_url}")
        page.wait_for_timeout(2000)
        if click_tab(page, args.notes_tab_name) or click_tab_fuzzy(page, args.notes_tab_name):
            print(f"Opened notes tab: {args.notes_tab_name}")
            page.wait_for_timeout(1200)
        else:
            print(f"Warning: Could not click notes tab '{args.notes_tab_name}'. Capturing current view.")

        per_step_ms = max(120, int((args.capture_seconds * 1000) / max(1, args.scroll_steps)))
        for _ in range(args.scroll_steps):
            page.mouse.wheel(0, 1300)
            page.wait_for_timeout(per_step_ms)
        page.wait_for_timeout(2000)
    finally:
        page.remove_listener("request", on_request)
        page.remove_listener("response", on_response)

    return write_outputs(entries, out_dir, bodies_dir)


def main() -> int:
    args = parse_args()
    prompt_if_missing(args)
    targets = load_targets(args)
    root_out_dir = Path(args.out_dir).resolve()
    root_out_dir.mkdir(parents=True, exist_ok=True)
    run_summary: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.on("dialog", lambda d: d.accept())

        try:
            page.goto(args.login_url, wait_until="domcontentloaded")
            if args.manual_login:
                print("Manual login: complete login in browser, then press Enter here...")
                input()
            else:
                do_auto_login(page, args)

            print(f"Login done. Processing {len(targets)} target(s)...")
            for idx, target in enumerate(targets, start=1):
                target_slug = safe_name(Path(urlparse(target).path).name, f"target_{idx}")
                target_out_dir = root_out_dir / f"{idx:03d}_{target_slug}"
                target_bodies_dir = target_out_dir / "bodies"
                target_out_dir.mkdir(parents=True, exist_ok=True)
                target_bodies_dir.mkdir(parents=True, exist_ok=True)
                print(f"[{idx}/{len(targets)}] Capturing: {target}")
                dump_file, summary_file = capture_target(page, args, target, target_out_dir, target_bodies_dir)
                run_summary.append(
                    {
                        "target_url": target,
                        "out_dir": str(target_out_dir),
                        "dump_file": str(dump_file),
                        "summary_file": str(summary_file),
                    }
                )
        finally:
            browser.close()

    run_summary_file = root_out_dir / "run_summary.json"
    run_summary_file.write_text(json.dumps(run_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved: {run_summary_file}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

