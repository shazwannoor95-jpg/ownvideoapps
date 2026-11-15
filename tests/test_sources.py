import sys
from pathlib import Path
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from portable_source import extract

class SourceTests(unittest.TestCase):
    def test_docx_paragraphs_and_table_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'input.docx'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Perenggan.</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Isi jadual.</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
            self.assertEqual(extract(p),'Perenggan.\nIsi jadual.')

    def test_pptx_follows_presentation_order_not_zip_file_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'input.pptx'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('ppt/presentation.xml','<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId r:id="r2"/><p:sldId r:id="r1"/></p:sldIdLst></p:presentation>')
                z.writestr('ppt/_rels/presentation.xml.rels','<Relationships><Relationship Id="r1" Target="slides/slide1.xml"/><Relationship Id="r2" Target="slides/slide2.xml"/></Relationships>')
                for n,text in [(1,'Kedua'),(2,'Pertama')]:
                    z.writestr(f'ppt/slides/slide{n}.xml',f'<root xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:p><a:r><a:t>{text}</a:t></a:r></a:p></root>')
            self.assertEqual(extract(p),'# Slaid 1\nPertama\n\n# Slaid 2\nKedua')

    def test_empty_or_unknown_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'empty.txt';p.write_text('  ')
            with self.assertRaisesRegex(ValueError,'Tiada teks'):extract(p)
            with self.assertRaisesRegex(ValueError,'Format'):extract(Path(tmp)/'old.ppt')
