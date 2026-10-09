"""MIT: format boundary tests runnable without any ChemDraw installation."""
import pathlib
import random
import struct
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from delta import MAGIC,apply_delta,make_delta


class DeltaTests(unittest.TestCase):
    def test_shift_insert_delete_and_repeat(self):
        rng=random.Random(713)
        source=bytes(rng.randrange(256) for _ in range(8192))+b'A'*4096
        target=b'prefix'+source[:1001]+'中文'.encode()+source[1400:]+b'tail'
        delta=make_delta(source,target)
        self.assertEqual(apply_delta(source,delta),target)
        self.assertLess(len(delta),len(target)//2)

    def test_empty_and_completely_different(self):
        for source,target in ((b'',b''),(b'',b'new'),(b'old',b''),(b'old',b'new')):
            self.assertEqual(apply_delta(source,make_delta(source,target)),target)

    def test_truncation_and_extra_data(self):
        delta=make_delta(b'old',b'new')
        for malformed in (delta[:-1],delta+b'\0',b'bad'):
            with self.assertRaises(ValueError):apply_delta(b'old',malformed)

    def test_copy_bounds_and_output_limit(self):
        for delta in (MAGIC+struct.pack('<Q',1)+b'\1'+struct.pack('<QQ',99,1)+b'\0',
                      MAGIC+struct.pack('<Q',1)+b'\2'+struct.pack('<I',2)+b'ab'+b'\0',
                      MAGIC+struct.pack('<Q',256*1024*1024+1)):
            with self.assertRaises(ValueError):apply_delta(b'x',delta)


if __name__=='__main__':unittest.main()
