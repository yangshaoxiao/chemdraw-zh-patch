# SPDX-License-Identifier: MIT
"""Regression checks for MFC status/tooltip separators and tool names."""
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'localization'))
from translate import translate

class TooltipTests(unittest.TestCase):
    def test_double_bond_prompt(self):
        result=translate('Double bond tool\nDouble Bond')
        self.assertEqual(result,'双键工具\n双键')
    def test_empty_status_keeps_tooltip_separator(self):
        self.assertEqual(translate('\nClear'),'\n清除')
    def test_unrelated_postscript_not_rewritten(self):
        self.assertEqual(translate('showpage\n'),'showpage\n')
    def test_rotation_shortcuts_remain(self):
        source='Rotate. X|Y|Z: About axes; Alt: Track ball; V|B|N: About the selected bond\nRotate'
        result=translate(source)
        self.assertEqual(result.split('\n')[-1],'旋转')
        for key in ('X|Y|Z','Alt','V|B|N'):self.assertIn(key,result)

if __name__=='__main__':unittest.main()
