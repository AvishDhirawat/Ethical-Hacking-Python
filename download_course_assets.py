#!/usr/bin/env python3
"""
Download embedded lesson video and notes PDF from an authenticated page.

Usage example:
python download_course_assets.py ^
  --login-url "https://example.com/login" ^
  --target-url "https://example.com/course/page" ^
  --username "my_user" ^
  --password "my_pass" ^
  --out-dir "downloads"

Install dependencies:
  pip install playwright
  playwright install chromium
"""

from __future__ import annotations

import argparse
import getpass
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".m3u8")
PDF_HINTS = (".pdf", "application/pdf")


def safe_name(value: str, fallback: str) -> str:
    text = (value or "").strip()
    text = re.sub(r"[^\w.\- ]+", "_", text)
    text = re.sub(r"\s+", "_", text).strip("._")
    return text or fallback


def guess_filename_from_url(url: str, fallback: str) -> str:
    try:
        path = urlparse(url).path
        candidate = Path(path).name
        if candidate:
            return safe_name(candidate, fallback)
    except Exception:
        pass
    return fallback


def unique_file(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for i in range(1, 10_000):
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError("Unable to create unique filename.")


def click_tab(page, tab_name: str, timeout_ms: int = 10_000) -> bool:
    tab_regex = re.escape(tab_name.strip())
    selectors = [
        f'role=tab[name="{tab_name}"]',
        f"text=/{tab_regex}/i",
        f'text="{tab_name}"',
        f'button:has-text("{tab_name}")',
        f'a:has-text("{tab_name}")',
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() > 0:
                locator.click(timeout=timeout_ms)
                page.wait_for_timeout(1500)
                return True
        except Exception:
            continue
    return False


def auto_scroll(page, steps: int = 10, pause_ms: int = 400) -> None:
    for _ in range(steps):
        try:
            page.mouse.wheel(0, 1200)
        except Exception:
            pass
        page.wait_for_timeout(pause_ms)


def collect_candidate_urls(page):
    urls: set[str] = set()
    attr_selectors = [
        "video[src]",
        "source[src]",
        "iframe[src]",
        "embed[src]",
        "object[data]",
        "a[href]",
    ]
    for selector in attr_selectors:
        attr = "data" if selector.startswith("object") else ("href" if selector.startswith("a") else "src")
        try:
            loc = page.locator(selector)
            count = loc.count()
            for i in range(count):
                val = loc.nth(i).get_attribute(attr)
                if val and val.startswith("http"):
                    urls.add(val)
        except Exception:
            continue
    return urls


def pick_video_url(urls: set[str]) -> str | None:
    for ext in VIDEO_EXTENSIONS:
        for url in urls:
            if ext in url.lower():
                return url
    return None


def pick_pdf_url(urls: set[str]) -> str | None:
    for url in urls:
        low = url.lower()
        if ".pdf" in low:
            return url
    return None


def extract_pdf_like_urls(url: str) -> set[str]:
    candidates: set[str] = set()
    if not url:
        return candidates

    stack = [url]
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        low = current.lower()
        if ".pdf" in low:
            candidates.add(current)
        try:
            parsed = urlparse(current)
            query = parse_qs(parsed.query, keep_blank_values=False)
            for values in query.values():
                for val in values:
                    decoded = unquote(val)
                    if decoded.startswith("http"):
                        stack.append(decoded)
                    elif ".pdf" in decoded.lower():
                        candidates.add(decoded)
        except Exception:
            continue
    return candidates


def collect_network_urls(page, duration_ms: int = 6_000, do_scroll: bool = False) -> set[str]:
    seen_urls: set[str] = set()

    def on_response(resp):
        try:
            url = resp.url or ""
            content_type = (resp.headers or {}).get("content-type", "").lower()
            low = url.lower()
            if (
                any(ext in low for ext in VIDEO_EXTENSIONS)
                or ".pdf" in low
                or "application/pdf" in content_type
            ):
                seen_urls.add(url)
        except Exception:
            pass

    page.on("response", on_response)
    try:
        loops = max(1, duration_ms // 500)
        for _ in range(loops):
            if do_scroll:
                auto_scroll(page, steps=1, pause_ms=200)
            page.wait_for_timeout(500)
    finally:
        page.remove_listener("response", on_response)
    return seen_urls


def collect_network_pdf_candidates(page, duration_ms: int = 12_000, do_scroll: bool = True) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def add_url(candidate: str) -> None:
        if candidate and candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)

    def on_response(resp):
        try:
            url = resp.url or ""
            headers = resp.headers or {}
            ctype = headers.get("content-type", "").lower()
            cdisp = headers.get("content-disposition", "").lower()
            status = resp.status
            if status >= 400:
                return
            low_url = url.lower()
            if (
                ".pdf" in low_url
                or "application/pdf" in ctype
                or ".pdf" in cdisp
                or "/notes/file/" in low_url
                or "filename=" in cdisp
            ):
                for u in extract_pdf_like_urls(url):
                    add_url(u)
                add_url(url)
        except Exception:
            pass

    page.on("response", on_response)
    try:
        loops = max(1, duration_ms // 400)
        for _ in range(loops):
            if do_scroll:
                auto_scroll(page, steps=1, pause_ms=150)
            page.wait_for_timeout(400)
    finally:
        page.remove_listener("response", on_response)
    return ordered


def capture_pdf_response_body(page, out_dir: Path, duration_ms: int = 12_000, do_scroll: bool = True, debug: bool = False):
    saved_pdf: Path | None = None
    seen_urls: list[str] = []

    def on_response(resp):
        nonlocal saved_pdf
        if saved_pdf is not None:
            return
        try:
            url = resp.url or ""
            headers = resp.headers or {}
            ctype = headers.get("content-type", "").lower()
            cdisp = headers.get("content-disposition", "").lower()
            low_url = url.lower()
            if resp.status >= 400:
                return
            if (
                ".pdf" in low_url
                or "application/pdf" in ctype
                or ".pdf" in cdisp
                or "/notes/file/" in low_url
            ):
                seen_urls.append(url)
                body = resp.body()
                if not body:
                    return
                if body.startswith(b"%PDF") or "application/pdf" in ctype or ".pdf" in low_url:
                    pdf_name = guess_filename_from_url(url, "notes.pdf")
                    if not pdf_name.lower().endswith(".pdf"):
                        pdf_name += ".pdf"
                    out_file = unique_file(out_dir / pdf_name)
                    out_file.write_bytes(body)
                    saved_pdf = out_file
                    if debug:
                        print(f"[debug] Saved PDF directly from response: {url}")
        except Exception:
            pass

    page.on("response", on_response)
    try:
        loops = max(1, duration_ms // 400)
        for _ in range(loops):
            if do_scroll:
                auto_scroll(page, steps=1, pause_ms=150)
            page.wait_for_timeout(400)
            if saved_pdf is not None:
                break
    finally:
        page.remove_listener("response", on_response)
    return saved_pdf, seen_urls


def save_via_authenticated_request(context, url: str, out_file: Path, timeout_ms: int = 90_000, referer: str = "", origin: str = "") -> bool:
    try:
        headers = {}
        if referer:
            headers["Referer"] = referer
        if origin:
            headers["Origin"] = origin
        response = context.request.get(url, timeout=timeout_ms, headers=headers)
        if not response.ok:
            return False
        body = response.body()
        out_file.write_bytes(body)
        return True
    except Exception:
        return False


def save_video_with_fallback(context, video_url: str, out_dir: Path, fallback_name: str, referer: str = "", origin: str = "") -> Path | None:
    ext = ".mp4"
    for candidate_ext in VIDEO_EXTENSIONS:
        if candidate_ext in video_url.lower():
            ext = ".m3u8" if candidate_ext == ".m3u8" else candidate_ext
            break

    video_name = guess_filename_from_url(video_url, f"{fallback_name}{ext}")
    video_file = unique_file(out_dir / video_name)
    if save_via_authenticated_request(context, video_url, video_file, referer=referer, origin=origin):
        if ext == ".m3u8":
            ffmpeg_path = shutil.which("ffmpeg")
            if ffmpeg_path:
                mp4_file = unique_file(out_dir / f"{video_file.stem}.mp4")
                cmd = [
                    ffmpeg_path,
                    "-y",
                    "-i",
                    str(video_file),
                    "-c",
                    "copy",
                    str(mp4_file),
                ]
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return mp4_file
                except Exception:
                    return video_file
        return video_file
    return None


def first_visible_locator(page, selector: str):
    loc = page.locator(selector)
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
        page.wait_for_timeout(400)
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
        clicked = False
        for selector in ok_selectors:
            try:
                loc = page.locator(selector).first
                if loc.count() > 0 and loc.is_visible():
                    loc.click(timeout=700)
                    page.wait_for_timeout(400)
                    clicked = True
                    break
            except Exception:
                continue
        if not clicked:
            page.wait_for_timeout(250)


def maybe_login(page, args) -> None:
    page.goto(args.login_url, wait_until="domcontentloaded")
    page.on("dialog", lambda d: d.accept())
    page.wait_for_timeout(1500)

    if args.manual_login:
        print("\nManual login mode enabled.")
        print("Log in inside the opened browser window, then press Enter here...")
        input()
        return

    scope, user_locator, pass_locator = find_login_fields(
        page, args.username_selector, args.password_selector, timeout_ms=args.login_wait_seconds * 1000
    )

    if not scope or not user_locator or not pass_locator or user_locator.count() == 0 or pass_locator.count() == 0:
        raise RuntimeError(
            "Could not find username/password inputs. "
            "Use --manual-login or provide correct selectors."
        )

    user_locator.fill(args.username)
    pass_locator.fill(args.password)

    if args.submit_selector:
        first_visible_locator(scope, args.submit_selector).click()
    else:
        pass_locator.press("Enter")

    dismiss_success_popup(page)
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except PlaywrightTimeoutError:
        pass


def prompt_if_missing(args) -> None:
    if not args.login_url:
        args.login_url = input("Login URL: ").strip()
    if not args.target_url:
        args.target_url = input("Target course page URL: ").strip()
    if not args.manual_login:
        if args.prompt_credentials or not args.username:
            args.username = input("Username / Email: ").strip()
        if args.prompt_credentials or not args.password:
            args.password = getpass.getpass("Password: ")
    if not args.lesson_tab_name:
        args.lesson_tab_name = input('Lesson tab name [Lesson]: ').strip() or "Lesson"
    if not args.notes_tab_name:
        args.notes_tab_name = input('Notes tab name [Notes]: ').strip() or "Notes"
    if not args.practice_tab_name:
        args.practice_tab_name = input('Practice tab name [Practice Test]: ').strip() or "Practice Test"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download lesson video and notes PDF from an authenticated target page."
    )
    parser.add_argument("--login-url", default="", help="Login page URL")
    parser.add_argument("--target-url", default="", help="Target page URL that has Lesson/Notes tabs")
    parser.add_argument("--username", default="", help="Login username/email")
    parser.add_argument("--password", default="", help="Login password")
    parser.add_argument("--manual-login", action="store_true", help="Log in manually in browser and press Enter")
    parser.add_argument("--prompt-credentials", action="store_true", help="Always ask username/password in terminal")
    parser.add_argument("--username-selector", default='input[type="email"], input[name="email"], input[name="username"], input[name="mobile"], input[type="tel"], input[placeholder*="Email"], input[placeholder*="email"], input[placeholder*="Mobile"], input[placeholder*="mobile"], input[type="text"]')
    parser.add_argument("--password-selector", default='input[type="password"], input[name="password"]')
    parser.add_argument("--submit-selector", default="", help="Optional selector for login button")
    parser.add_argument("--login-wait-seconds", type=int, default=20, help="How long to wait for login form")
    parser.add_argument("--lesson-tab-name", default="Lesson", help='Text/label of lesson tab (default: "Lesson")')
    parser.add_argument("--notes-tab-name", default="Notes", help='Text/label of notes tab (default: "Notes")')
    parser.add_argument("--practice-tab-name", default="Practice Test", help='Text/label of practice tab (default: "Practice Test")')
    parser.add_argument("--out-dir", default="downloads", help="Output folder")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument("--wait-seconds", type=float, default=3.0, help="Extra wait after tab click")
    parser.add_argument("--debug-network", action="store_true", help="Print candidate asset URLs captured from network")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    prompt_if_missing(args)

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        try:
            maybe_login(page, args)
            page.goto(args.target_url, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)

            if click_tab(page, args.lesson_tab_name):
                time.sleep(args.wait_seconds)
            else:
                print(f"Warning: Could not click lesson tab '{args.lesson_tab_name}'. Trying current view.")

            lesson_urls = collect_candidate_urls(page)
            lesson_urls.update(collect_network_urls(page, duration_ms=6_000, do_scroll=False))
            video_url = pick_video_url(lesson_urls)
            saved_video = None
            if video_url:
                target_origin = ""
                try:
                    target_origin = f"{urlparse(args.target_url).scheme}://{urlparse(args.target_url).netloc}"
                except Exception:
                    pass
                saved_video = save_video_with_fallback(
                    context, video_url, out_dir, "lesson_video", referer=args.target_url, origin=target_origin
                )
                if saved_video:
                    print(f"Saved lesson video: {saved_video}")
                else:
                    print(f"Found video URL but failed to download: {video_url}")
            else:
                print("No obvious direct video URL found in Lesson tab.")

            if click_tab(page, args.notes_tab_name):
                time.sleep(args.wait_seconds)
            else:
                print(f"Warning: Could not click notes tab '{args.notes_tab_name}'. Trying current view.")

            notes_urls = collect_candidate_urls(page)
            notes_urls.update(collect_network_urls(page, duration_ms=10_000, do_scroll=True))
            network_pdf_candidates = collect_network_pdf_candidates(page, duration_ms=12_000, do_scroll=True)
            captured_pdf_file, captured_pdf_urls = capture_pdf_response_body(
                page, out_dir, duration_ms=12_000, do_scroll=True, debug=args.debug_network
            )
            for candidate in network_pdf_candidates:
                notes_urls.add(candidate)
            for candidate in captured_pdf_urls:
                notes_urls.add(candidate)
            pdf_url = pick_pdf_url(notes_urls)
            saved_pdf = captured_pdf_file
            pdf_candidates_ordered = []
            if pdf_url:
                pdf_candidates_ordered.append(pdf_url)
            for candidate in network_pdf_candidates:
                if candidate not in pdf_candidates_ordered:
                    pdf_candidates_ordered.append(candidate)
            for candidate in sorted(notes_urls):
                if ".pdf" in candidate.lower() and candidate not in pdf_candidates_ordered:
                    pdf_candidates_ordered.append(candidate)

            for candidate in pdf_candidates_ordered:
                if args.debug_network:
                    print(f"[debug] PDF candidate: {candidate}")
                pdf_name = guess_filename_from_url(candidate, "notes.pdf")
                if not pdf_name.lower().endswith(".pdf"):
                    pdf_name += ".pdf"
                pdf_file = unique_file(out_dir / pdf_name)
                target_origin = ""
                try:
                    target_origin = f"{urlparse(args.target_url).scheme}://{urlparse(args.target_url).netloc}"
                except Exception:
                    pass
                if save_via_authenticated_request(
                    context, candidate, pdf_file, referer=args.target_url, origin=target_origin
                ):
                    saved_pdf = pdf_file
                    print(f"Saved notes PDF: {pdf_file}")
                    break
            if pdf_candidates_ordered and not saved_pdf:
                print(f"Found PDF candidate URLs but download failed for all ({len(pdf_candidates_ordered)} tries).")
            else:
                print("No obvious direct PDF URL found in Notes tab.")

            # Optional: click practice tab for future extension.
            if click_tab(page, args.practice_tab_name):
                time.sleep(args.wait_seconds)

            if not saved_video and not saved_pdf:
                print("\nNo downloadable direct links were found.")
                print("Tip: try --manual-login, custom tab names, and keep browser non-headless.")
                return 2

            print("\nDone.")
            return 0
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        raise SystemExit(130)
