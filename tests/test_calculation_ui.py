# SPDX-License-Identifier: MIT
import pathlib,sys,unittest,struct
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'localization'))
from build_calculations import ui_reference,legacy_driver_caption
from dotnet_resources import read7,write7
from native_calculation_caption import patch,SOURCE,TARGET
class CalculationUI(unittest.TestCase):
    def test_7bit_boundaries(self):
        for n in (0,127,128,16383,16384,1000000):
            b=write7(n);self.assertEqual(read7(b,0),(n,len(b)))
    def test_driver_bridge_round_trip(self):
        for caption in ('CONFLEX 接口','GAMESS 接口','Gaussian 接口','MOPAC 接口'):
            self.assertNotEqual(caption.encode('cp1252',errors='replace').decode('gbk'),caption)
            wire=legacy_driver_caption(caption)
            self.assertEqual(wire.encode('cp1252').decode('gbk'),caption)
    def test_command_keyword_not_ui(self):
        r=dict(File='CambridgeSoft.ChemOffice.GamessDriver.dll',Type='Driver',Method='Commands',Text='OPT',Next='Void Add(System.String)')
        self.assertFalse(ui_reference(r))
    def test_property_identity_not_ui(self):
        r=dict(File='CambridgeSoft.ChemOffice.GamessDriver.dll',Type='CambridgeSoft.ChemOffice.GamessDriver.TotalEnergy',Method='get_Name',Text='Total Energy',Next='')
        self.assertFalse(ui_reference(r))
    def test_driver_caption_ui(self):
        r=dict(File='CambridgeSoft.ChemOffice.GamessDriver.dll',Type='CambridgeSoft.ChemOffice.GamessDriver.Driver',Method='get_Name',Text='GAMESS Interface',Next='')
        self.assertTrue(ui_reference(r))
    def test_native_caption_exact_bounds(self):
        b=bytearray(512);struct.pack_into('<I',b,0x3c,64);struct.pack_into('<H',b,70,1);struct.pack_into('<H',b,84,0)
        b[88:96]=b'.rdata\0\0';struct.pack_into('<II',b,104,256,256);b[300:300+len(SOURCE)]=SOURCE
        out,row=patch(bytes(b));self.assertEqual(out[:300],b[:300]);self.assertEqual(out[300+len(SOURCE):],b[300+len(SOURCE):]);self.assertTrue(out[300:].startswith(TARGET));self.assertEqual(len(out),len(b))
    def test_native_duplicate_rejected(self):
        with self.assertRaises(ValueError):patch(SOURCE+SOURCE)
if __name__=='__main__':unittest.main()
