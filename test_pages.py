import json
import re
import tempfile
import unittest
from pathlib import Path

from digest import build, timestamp
from scripts.build_pages import ASSETS, DOCS, ROOT, build as build_pages, render_markdown

TMP=ROOT/'tmp'
TMP.mkdir(exist_ok=True)


class PagesTests(unittest.TestCase):
    def test_static_artifact_allowlist(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            out=build_pages(folder)
            expected=set(ASSETS)|{'examples.json','.nojekyll'}|{f'docs/{name}.html' for name in DOCS}
            self.assertEqual({p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()},expected)
            presets=json.loads((out/'examples.json').read_text(encoding='utf-8'))
            self.assertEqual(set(presets),{'original','confirmed','uncertain'})
            self.assertEqual(len(build(presets['original'])['cases']),4)

    def test_basepath_assets_are_relative(self):
        page=(ROOT/'web/index.html').read_text(encoding='utf-8')
        urls=re.findall(r'(?:src|href)="([^"]+)"',page)
        self.assertTrue(urls)
        self.assertTrue(all(value.startswith('./') for value in urls))

    def test_stale_output_cannot_be_published(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            (Path(folder)/'private.txt').write_text('must not publish',encoding='utf-8')
            with self.assertRaises(ValueError):build_pages(folder)

    def test_html_is_escaped(self):
        self.assertNotIn('<script>',render_markdown('# Title\n\n<script>alert(1)</script>'))

    def test_launch_has_six_sentences(self):
        lines=(ROOT/'docs/launch.md').read_text(encoding='utf-8').splitlines()[2:]
        self.assertEqual(len([line for line in lines if line.strip()]),6)
        self.assertTrue(all(line.endswith('.') for line in lines if line.strip()))

    def test_strict_time_and_utc_equivalence(self):
        self.assertEqual(timestamp('2026-10-19T07:00:00Z'),timestamp('2026-10-19T10:00:00+03:00'))
        for value in ['2026-10-19T10:00:00+01:60','2026-02-30T10:00:00Z','2026-10-19T10:00:00.1234567Z']:
            with self.subTest(value=value),self.assertRaises(ValueError):timestamp(value)


if __name__=='__main__':unittest.main()
