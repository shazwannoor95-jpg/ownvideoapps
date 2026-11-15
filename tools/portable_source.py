"""Local document extraction; no services, Git or model downloads."""
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

def extract(source):
    source=Path(source)
    ext=source.suffix.lower()
    if ext in {'.txt','.md'}:
        text=source.read_text(encoding='utf-8-sig')
    elif ext=='.pdf':
        from pypdf import PdfReader
        reader=PdfReader(source)
        text='\n\n'.join(f'# Halaman {i}\n'+(p.extract_text() or '') for i,p in enumerate(reader.pages,1))
        if not any((p.extract_text() or '').strip() for p in reader.pages):
            raise ValueError('PDF imbasan tiada teks. Jalankan OCR sebelum import.')
    elif ext=='.docx':
        with zipfile.ZipFile(source) as z:
            root=ET.fromstring(z.read('word/document.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        text='\n'.join(''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in root.findall('.//w:p',ns))
    elif ext=='.pptx':
        ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
            'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
            'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
        with zipfile.ZipFile(source) as z:
            presentation=ET.fromstring(z.read('ppt/presentation.xml'))
            rels=ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
            targets={r.attrib['Id']:r.attrib['Target'] for r in rels if r.attrib.get('TargetMode')!='External'}
            parts=[]
            for i,slide in enumerate(presentation.findall('p:sldIdLst/p:sldId',ns),1):
                target=targets[slide.attrib['{'+ns['r']+'}id']]
                name=target.lstrip('/') if target.startswith('/') else 'ppt/'+target
                root=ET.fromstring(z.read(name))
                parts.append(f'# Slaid {i}\n'+'\n'.join(''.join(t.text or '' for t in p.findall('.//a:t',ns)) for p in root.findall('.//a:p',ns)))
            text='\n\n'.join(parts)
    else:
        raise ValueError('Format disokong: TXT, MD, PDF berteks, DOCX dan PPTX.')
    if not text.strip():raise ValueError('Tiada teks ditemui dalam sumber.')
    return text
