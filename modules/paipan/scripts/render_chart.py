"""Render only the nine-palace sheet using an existing local browser."""
import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


def find_browser(explicit):
    if explicit:
        file = Path(explicit).expanduser().resolve()
        if not file.is_file():
            raise ValueError(f'浏览器不存在：{file}')
        return str(file)
    candidates = []
    for variable in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
        base = os.environ.get(variable)
        if base:
            candidates.extend(Path(base) / part for part in (
                'Google/Chrome/Application/chrome.exe', 'Microsoft/Edge/Application/msedge.exe'))
    candidates.extend((Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
                       Path('/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge')))
    for file in candidates:
        if file.is_file():
            return str(file)
    for name in ('google-chrome', 'chromium', 'chromium-browser', 'microsoft-edge'):
        executable = shutil.which(name)
        if executable:
            return executable
    raise ValueError('没有找到现成 Chrome/Edge/Chromium。请用 --browser 指定路径，或用已有浏览器工具截图。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html', required=True)
    parser.add_argument('--png', required=True)
    parser.add_argument('--browser')
    args = parser.parse_args()
    html = Path(args.html).expanduser().resolve()
    png = Path(args.png).expanduser().resolve()
    if not html.is_file():
        raise ValueError(f'HTML 不存在：{html}')
    if png == html or png.suffix.lower() != '.png':
        raise ValueError('图片输出必须是独立的 .png 文件。')
    if png.exists():
        raise ValueError(f'图片已存在，不覆盖：{png}')
    executable = find_browser(args.browser)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise ValueError('当前 Python 没有 Playwright；HTML 已可直接查看，可用已有浏览器工具截图。') from error
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=executable)
        page = browser.new_page(viewport={'width': 1280, 'height': 1100}, device_scale_factor=2)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(html.as_uri(), wait_until='load')
        page.wait_for_function('document.querySelectorAll(".palace").length === 9')
        page.evaluate('document.fonts.ready')
        if errors or page.locator('#error').is_visible():
            raise ValueError('页面排盘出错：' + ('; '.join(errors) or page.locator('#error').inner_text()))
        png.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(prefix='.qimen-png-', suffix='.png', dir=png.parent)
        os.close(descriptor)
        temp = Path(temp_name)
        try:
            page.locator('.board-sheet').screenshot(path=str(temp))
            # Same-directory hard link publishes the complete image without overwriting.
            os.link(temp, png)
        finally:
            temp.unlink(missing_ok=True)
        browser.close()
    print(json.dumps({'png': str(png)}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'出图失败：{error}', file=sys.stderr)
        sys.exit(1)
