"""Interaction regressions for the Control presentation; no system changes."""
import gc
import time
import tkinter as tk
import unittest
import test_home
from ccslib import home, homeui, ui

class ControlInteractionTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk(); self.root.geometry('1100x780+20+20')
        self.ticker=ui.Ticker(self.root); self.actions=[]
        self.page=homeui.HomePage(self.root,self.ticker,self.actions.append); self.page.pack(fill='both',expand=True)
        self.view=home.build(test_home.state(),test_home.facts())
        self.page.render(self.view); self.root.update()

    def tearDown(self):
        self.ticker.set_enabled(False)
        self.root.destroy(); self.page=None; self.root=None; gc.collect()

    def pump(self,seconds):
        end=time.perf_counter()+seconds
        while time.perf_counter()<end:
            self.root.update(); time.sleep(.008)

    def test_primary_action_is_visible_and_dispatches_once(self):
        self.assertTrue(self.page.h1.winfo_ismapped())
        self.assertTrue(self.page.ring.winfo_ismapped())
        self.assertTrue(self.page.btn_primary.winfo_ismapped())
        self.page.btn_primary.invoke(); self.assertEqual(self.actions,['turn_on'])

    def test_drawer_reversal_preserves_presentation_position_and_velocity(self):
        drawer=self.page.drawer; drawer.show(self.view['settings']); self.pump(.065)
        x,v=drawer._offset,drawer._velocity
        self.assertGreater(x,0); self.assertLess(x,ui.S(drawer.W))
        drawer.hide(); self.assertEqual(drawer._offset,x); self.assertEqual(drawer._velocity,v)
        self.pump(.55); self.assertFalse(drawer.winfo_ismapped())
        drawer.show(self.view['settings']); self.pump(.55)
        self.assertTrue(drawer.is_open); self.assertAlmostEqual(drawer._offset,0,delta=.5)

    def test_reduced_motion_sets_drawer_directly_without_animation_jobs(self):
        self.ticker.set_enabled(False); drawer=self.page.drawer
        drawer.show(self.view['settings']); self.root.update()
        self.assertEqual(drawer._offset,0); self.assertNotIn('drawer',self.ticker.jobs)
        drawer.hide(); self.root.update(); self.assertFalse(drawer.winfo_ismapped())

    def test_sidebar_supports_keyboard_and_preserves_download_selection(self):
        nav=self.page.rail_items['open_download']
        self.assertTrue(nav.bind('<Return>')); self.assertTrue(nav.bind('<space>'))
        nav.command(); self.assertEqual(self.actions,['open_download'])
        self.page.show_page('download'); self.assertTrue(nav.sel)
        self.page.show_page('home'); self.assertTrue(self.page.rail_items['back_home'].sel)

    def test_small_window_keeps_primary_action_within_content(self):
        self.root.geometry('1040x720'); self.root.update(); self.page.render(self.view); self.root.update()
        button=self.page.btn_primary
        self.assertGreaterEqual(button.winfo_rootx(),self.page.main.winfo_rootx())
        self.assertLessEqual(button.winfo_rootx()+button.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width())
        self.assertGreaterEqual(button.winfo_rooty(),self.root.winfo_rooty())
        self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())

    def test_wide_advanced_content_can_be_scrolled_into_view(self):
        self.page.pack_forget(); scroll=ui.Scroll(self.root); scroll.pack(fill='both',expand=True)
        label=tk.Label(scroll.body,text='WIDE CONTENT',width=200); label.pack()
        self.root.update(); scroll._fit(); self.root.update()
        self.assertTrue(scroll.xsb.winfo_ismapped())
        self.assertGreater(scroll.body.winfo_width(),scroll.cv.winfo_width())
        scroll.cv.xview_moveto(1); self.root.update(); self.assertGreater(scroll.cv.xview()[0],0)
