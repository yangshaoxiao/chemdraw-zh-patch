# SPDX-License-Identifier: MIT
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'localization'))
from build_excel import excel_translate,selected
class ExcelLocalization(unittest.TestCase):
    def test_ribbon_caption(self):
        self.assertEqual(excel_translate('&New ChemOffice Worksheet'),'新建 ChemOffice 工作表(&N)')
        self.assertEqual(excel_translate('General'),'常规')
    def test_schema_and_ribbon_not_selected(self):
        for key in ('Ribbon','TableHeaderText','ExpReactantTableHeader','opt_ConnTabVersion1','>>BaseOKButton.Name'):
            self.assertFalse(selected(key),key)
    def test_ui_keys_selected(self):
        for key in ('Cmd_NewWorksheet','Ctl_RibbonGeneral','Ttp_LoadMolecule','lblExcelPrimaryKey.Text'):
            self.assertTrue(selected(key),key)
    def test_number_placeholder_preserved(self):
        self.assertEqual(excel_translate('of total {0} plates'),'共 {0} 块孔板')
    def test_brand_identifiers_retained(self):
        for source in ('InChI','SMILES','V3000'):self.assertEqual(excel_translate(source),source)
if __name__=='__main__':unittest.main()
