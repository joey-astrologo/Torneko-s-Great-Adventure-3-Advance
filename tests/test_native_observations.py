"""Do not weaken sequence checks when coalescing duplicate debugger events."""
import unittest
from tools.verify_items import distinct_glyph_observations, coalesce_empty_draw_observations


class NativeObservationTests(unittest.TestCase):
    def test_equal_letters_at_different_positions_remain_distinct(self):
        a = dict(draw_serial=1,caller=1,code=108,advance=3,x=0,y=0,font=0,spacing=0,window_origin=[0,0],window_width=192)
        b = dict(a,x=3)
        self.assertEqual(distinct_glyph_observations([a,a,b]),([a,b],1))

    def test_empty_draw_requires_exact_immediate_following_observation(self):
        a = dict(serial=0,phase="test",address="0x1",x=0,y=0,raw_hex="4100")
        b = dict(a,serial=1)
        self.assertEqual(coalesce_empty_draw_observations([a,b],[dict(draw_serial=1)]),([b],1))
        for changed in (dict(b,raw_hex="4200"),dict(b,x=1),dict(b,serial=2)):
            with self.assertRaises(RuntimeError):
                coalesce_empty_draw_observations([a,changed],[dict(draw_serial=changed["serial"])])
        with self.assertRaises(RuntimeError):
            coalesce_empty_draw_observations([a],[])
