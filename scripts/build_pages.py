"""Create a portable static Pages artifact using only an explicit file allowlist."""
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scenarios import examples

ASSETS=('index.html','app.js','engine.js','style.css')
DOCS={'answer':'README.md','digest':'docs/digest.md','launch':'docs/launch.md','demo':'docs/demo.md','architecture':'docs/architecture.md'}


def inline(text):
    text=html.escape(text)
    text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
    return re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',text)


def render_markdown(text):
    result=[];paragraph=[];code=[];fenced=False
    def flush():
        if paragraph:
            result.append('<p>'+inline(' '.join(paragraph))+'</p>');paragraph.clear()
    for line in text.splitlines():
        if line.startswith('```'):
            flush()
            if fenced:result.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>');code=[]
            fenced=not fenced
        elif fenced:code.append(line)
        elif not line.strip():flush()
        elif re.match(r'^#{1,3} ',line):
            flush();level=len(line.split(' ',1)[0]);result.append(f'<h{level}>'+inline(line[level+1:])+f'</h{level}>')
        elif re.match(r'^(?:- |\d+\. )',line):
            flush();result.append('<p>'+inline(line)+'</p>')
        else:paragraph.append(line)
    flush()
    return '\n'.join(result)


def build(destination=None):
    destination=Path(destination or ROOT/'dist')
    destination.mkdir(parents=True,exist_ok=True)
    allowed=set(ASSETS)|{'examples.json','.nojekyll'}|{f'docs/{name}.html' for name in DOCS}
    for path in destination.rglob('*'):
        if path.is_symlink() or (path.is_file() and path.relative_to(destination).as_posix() not in allowed):
            raise ValueError('Unexpected output file; use a fresh build directory')
    # No recursive copying: source docs, Git, secrets and local files cannot leak.
    for name in ASSETS:shutil.copyfile(ROOT/'web'/name,destination/name)
    (destination/'examples.json').write_text(json.dumps(examples(),ensure_ascii=False),encoding='utf-8')
    (destination/'.nojekyll').write_text('',encoding='utf-8')
    (destination/'docs').mkdir(exist_ok=True)
    for name,source in DOCS.items():
        content=render_markdown((ROOT/source).read_text(encoding='utf-8'))
        page='<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Материалы решения</title><link rel="stylesheet" href="../style.css"></head><body><main class="document"><a href="../index.html">← Вернуться к демо</a>'+content+'</main></body></html>'
        (destination/'docs'/f'{name}.html').write_text(page,encoding='utf-8')
    return destination


if __name__=='__main__':print(build())
