"""Original CC0 test document. No commercial rulebook content or dependencies."""
from pathlib import Path


def fixture():
    pages=[['LANTERN - Original rule fixture',
        'Initial energy is 3. An attempt requires positive energy.',
        'An attempt spends 1 energy and rolls two six-sided dice.',
        'When energy reaches zero, exhaustion becomes true.'],
        ['RESULT TABLE - Original test example','Dice total             Result',
         '2 to 6                 Failure','7 to 12                Success'],
        ['PRIVATE-UNSELECTED-PAGE-DO-NOT-SEND'],[]]
    font=3+2*len(pages)
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',
        ('<< /Type /Pages /Count '+str(len(pages))+' /Kids ['+' '.join(str(3+2*i)+' 0 R' for i in range(len(pages)))+'] >>').encode()]
    for i,lines in enumerate(pages):
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font} 0 R >> >> /Contents {4+2*i} 0 R >>'.encode())
        content=('BT /F1 12 Tf 50 740 Td '+' 0 -24 Td '.join('('+s.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')+') Tj' for s in lines)+' ET').encode()
        objects.append(b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'\nendstream')
    objects.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    result=b'%PDF-1.4\n';offsets=[0]
    for number,obj in enumerate(objects,1):
        offsets.append(len(result));result+=str(number).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
    xref=len(result)
    result+=b'xref\n0 '+str(len(offsets)).encode()+b'\n0000000000 65535 f \n'
    result+=b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    result+=f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    return result


if __name__=='__main__':
    target=Path(__file__).resolve().parents[1]/'test_fixtures'/'rule-source-example.pdf'
    target.write_bytes(fixture());print(f'Original PDF fixture: {target.name}, {target.stat().st_size} bytes')
