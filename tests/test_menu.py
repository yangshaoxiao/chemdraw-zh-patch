# SPDX-License-Identifier: MIT
"""Check that translated menus preserve command identity and binary framing."""
import pathlib,struct,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'localization'))
from resources import menu_fields,rebuild_menu

class MenuTests(unittest.TestCase):
    def sample(self):
        def text(s):return (s+'\0').encode('utf-16le')
        return (struct.pack('<HH',0,2)+b'XY'+struct.pack('<H',0x90)+text('&File')+
                struct.pack('<HH',0,51)+text('Open\tCtrl+O')+
                struct.pack('<HH',0x80,99)+text('Exit')+b'TRAILER')
    def test_offset_trailer_and_identity(self):
        blob=self.sample();self.assertEqual(rebuild_menu(blob,{}),blob)
        fixed=rebuild_menu(blob,{'&File':'文件(&F)','Open\tCtrl+O':'打开\tCtrl+O'})
        self.assertEqual(fixed[:6],blob[:6]);self.assertTrue(fixed.endswith(b'TRAILER'))
        def framing(b):
            out=b;fields=list(menu_fields(b))
            for start,end,_,_ in reversed(fields):out=out[:start]+b'\0\0'+out[end+2:]
            return out
        self.assertEqual(framing(blob),framing(fixed))
        self.assertIn('打开\tCtrl+O',[t for _,_,t,_ in menu_fields(fixed)])
    def test_reject_truncation_invalid_offset_and_missing_end(self):
        for blob in (b'\0',struct.pack('<HH',0,99),self.sample()[:12],
                     struct.pack('<HHHH',0,0,0,1)+b'A\0\0\0'):
            with self.assertRaises(ValueError):list(menu_fields(blob))

if __name__=='__main__':unittest.main()
