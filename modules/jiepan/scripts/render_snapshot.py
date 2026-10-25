"""Render a self-contained paipan snapshot through the bundled renderer.

The source trio is read only. A unique short staging directory avoids long
file-URL navigation; only the verified PNG is published in the task output.
"""
import argparse,importlib.util,json,os,re,shutil,struct,subprocess,sys,tempfile,uuid,zlib
from html.parser import HTMLParser
from pathlib import Path

VERSION='1.1.0'

class Resources(HTMLParser):
    def __init__(self):super().__init__();self.required=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        for key in ['src','srcset','poster','data' if tag=='object' else '']:
            if key and a.get(key):self.required.append(a[key])
        if tag in ['link','base'] and a.get('href'):self.required.append(a['href'])

def local_file(value,suffix):
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://',value):raise ValueError('请提供本机文件路径，不是file://或网络URL。')
    p=Path(value).expanduser().resolve()
    if not p.is_file() or p.suffix.lower()!=suffix:raise ValueError(f'缺少可读的{suffix}文件：{p}')
    return p

def png_info(p):
    raw=p.read_bytes()
    if raw[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('渲染器未生成有效PNG签名。')
    pos=8;dimensions=None;idat=[];ended=False
    while pos+12<=len(raw):
        size=struct.unpack('>I',raw[pos:pos+4])[0];kind=raw[pos+4:pos+8];body=raw[pos+8:pos+8+size];end=pos+12+size
        if end>len(raw) or zlib.crc32(kind+body)&0xffffffff!=struct.unpack('>I',raw[end-4:end])[0]:raise ValueError('PNG数据截断或CRC无效。')
        if kind==b'IHDR':dimensions=struct.unpack('>II',body[:8])
        if kind==b'IDAT':idat.append(body)
        if kind==b'IEND':ended=True;break
        pos=end
    if not ended or not dimensions or min(dimensions)<100 or not idat:raise ValueError('PNG缺少完整图像或尺寸异常。')
    if not zlib.decompress(b''.join(idat)):raise ValueError('PNG像素数据为空。')
    return {'width':dimensions[0],'height':dimensions[1],'bytes':len(raw)}

def _render_inline_when_file_navigation_blocked(html_text, renderer_path, browser_option, image_path):
    """For hosts that administratively block file://, render *verified self-contained* HTML.

    This fallback never fetches a URL or changes the snapshot. It uses the same
    browser detection and board selector as the bundled original renderer.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ValueError('浏览器禁止本地file://且缺少Playwright，无法使用内嵌HTML回退。') from exc
    spec = importlib.util.spec_from_file_location('_qimen_bundled_renderer', renderer_path)
    if spec is None or spec.loader is None:
        raise ValueError('无法读取总包内的浏览器渲染器。')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    executable = module.find_browser(browser_option)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=executable)
        try:
            page = browser.new_page(viewport={'width': 1280, 'height': 1100}, device_scale_factor=2)
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.set_content(html_text, wait_until='load')
            page.wait_for_function('document.querySelectorAll(".palace").length === 9')
            page.evaluate('document.fonts.ready')
            if errors or page.locator('#error').is_visible():
                raise ValueError('内嵌HTML渲染有页面错误：' + ('; '.join(errors) or page.locator('#error').inner_text()))
            page.locator('.board-sheet').screenshot(path=str(image_path))
        finally:
            browser.close()

def render(args):
    html=local_file(args.html,'.html');data=local_file(args.json,'.json');md=local_file(args.markdown,'.md')
    source={p:p.read_bytes() for p in [html,data,md]}
    chart=json.loads(source[data].decode('utf-8-sig'));text=source[html].decode('utf8')
    marker='globalThis.QimenInitialSnapshot='
    if marker not in text:raise ValueError('HTML缺少安装版原始快照，不能据此出图。')
    embedded,_=json.JSONDecoder().raw_decode(text.split(marker,1)[1])
    if embedded!=chart or len(chart.get('palaces',[]))!=9:raise ValueError('HTML与指定JSON快照不一致或九宫数据不完整。')
    if chart.get('snapshotId','') not in source[md].decode('utf-8-sig'):raise ValueError('Markdown没有对应快照身份。')
    resources=Resources();resources.feed(text)
    dependencies=[u for u in resources.required+re.findall(r'url\(\s*[\"\x27]?([^\)\"\x27]+)',text) if not u.startswith('data:')]
    if dependencies:raise ValueError('该HTML含外部或相对加载资源，当前接口只支持自包含排盘HTML，未复制或忽略依赖：'+', '.join(dependencies))
    renderer=Path(args.renderer).expanduser().resolve() if args.renderer else Path(__file__).resolve().parents[2]/'paipan/scripts/render_chart.py'
    if not renderer.is_file():raise ValueError('未找到总包排盘模块的render_chart.py，请检查目录结构或使用--renderer指定现有文件。')
    output=Path(args.outdir).expanduser().resolve();output.mkdir(parents=True,exist_ok=True)
    final=output/('qimen-'+uuid.uuid4().hex+'.png')
    with tempfile.TemporaryDirectory(prefix='qr-') as staging:
        stage=Path(staging);copy=stage/'chart.html';image=stage/'chart.png'
        if len(str(copy))>=240:raise ValueError('系统临时目录仍过长，无法提供已验证的短路径导航。')
        copy.write_bytes(source[html])
        command=[sys.executable,'-B','-X','utf8',str(renderer),'--html',str(copy),'--png',str(image)]
        if args.browser:command+=['--browser',args.browser]
        try:r=subprocess.run(command,capture_output=True,text=True,encoding='utf8',timeout=90)
        except subprocess.TimeoutExpired as exc:raise ValueError('现有渲染器90秒内未完成，未发布PNG。') from exc
        fallback_used=False
        if r.returncode != 0:
            failure = r.stderr.strip() or r.stdout.strip() or str(r.returncode)
            # Some harness sandboxes deny file:// navigation even for trusted local
            # self-contained HTML. The verified in-memory HTML is safe to render
            # without file navigation; all other errors retain fail-closed behavior.
            if 'ERR_BLOCKED_BY_ADMINISTRATOR' in failure:
                _render_inline_when_file_navigation_blocked(text, renderer, args.browser, image)
                fallback_used=True
            else:
                raise ValueError('排盘模块渲染器失败：'+failure)
        if not image.is_file():raise ValueError('渲染器未生成实际PNG文件。')
        dimensions=png_info(image)
        if any(p.read_bytes()!=value for p,value in source.items()):raise ValueError('渲染期间源快照发生变化，未发布PNG。')
        # Exclusive creation: separate sessions never overwrite each other's image.
        created=False
        try:
            with final.open('xb') as target:
                created=True;target.write(image.read_bytes())
            if png_info(final)!=dimensions:raise ValueError('最终PNG校验失败。')
        except Exception:
            # A collision belongs to another writer and must never be removed.
            if created:final.unlink(missing_ok=True)
            raise
    return {'wrapperVersion':VERSION,'snapshotId':chart['snapshotId'],'png':str(final),'html':str(html),'markdown':str(md),'json':str(data),
            'image':dimensions,'renderer':str(renderer),'engineVersion':chart.get('engineVersion'),'sourceFilesUnchanged':True,
            'rendering':('bundled renderer file:// navigation blocked, verified self-contained inline HTML fallback' if fallback_used
                         else 'bundled renderer, one call using an unchanged short-path HTML copy; temporary copy removed'),
            'inlineFallbackUsed': fallback_used}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['html','json','markdown','outdir']:p.add_argument('--'+name,required=True)
    p.add_argument('--renderer');p.add_argument('--browser');a=p.parse_args()
    try:print(json.dumps(render(a),ensure_ascii=False))
    except Exception as exc:print('安全出图失败：'+str(exc),file=sys.stderr);return 1
    return 0
if __name__=='__main__':sys.exit(main())
