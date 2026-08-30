"""Unit tests for Block-code Macros, MacroManager, and MacroRunner."""

import unittest
from PyQt6.QtWidgets import QApplication
from candle.models.macro_model import Macro, MacroBlock, BlockType, MacroManager
from candle.settings.storage import SettingsStorage

# Ensure QApplication exists for Qt tests
app = QApplication.instance() or QApplication([])


class TestMacros(unittest.TestCase):
    def test_macro_block_descriptions(self):
        b1 = MacroBlock(BlockType.HOME)
        self.assertIn("Home Machine", b1.description())

        b2 = MacroBlock(BlockType.SAFE_Z, {"clearance": 4.5})
        self.assertIn("4.5", b2.description())

        b3 = MacroBlock(BlockType.MOVE_TO, {"x": 10.0, "y": 20.0, "z": 5.0, "feed": 1500, "coords": "work"})
        self.assertIn("X=10.000", b3.description())
        self.assertIn("Y=20.000", b3.description())
        self.assertIn("Z=5.000", b3.description())

        b4 = MacroBlock(BlockType.PROBE_Z, {"thickness": 19.05, "distance": 25.0})
        self.assertIn("19.1", b4.description())

        b5 = MacroBlock(BlockType.SPINDLE, {"state": "CW", "rpm": 12000, "delay": 3.0})
        self.assertIn("12000 RPM", b5.description())

        b6 = MacroBlock(BlockType.RUN_FILE)
        self.assertIn("Begin Loaded G-Code File", b6.description())

    def test_macro_serialization(self):
        m = Macro(
            name="Test Macro Chain",
            color="#e91e63",
            blocks=[
                MacroBlock(BlockType.HOME),
                MacroBlock(BlockType.SAFE_Z, {"clearance": 3.0}),
                MacroBlock(BlockType.PROBE_Z, {"thickness": 15.0}),
                MacroBlock(BlockType.RUN_FILE)
            ]
        )

        d = m.to_dict()
        self.assertEqual(d["name"], "Test Macro Chain")
        self.assertEqual(d["color"], "#e91e63")
        self.assertEqual(len(d["blocks"]), 4)

        m2 = Macro.from_dict(d)
        self.assertEqual(m2.name, "Test Macro Chain")
        self.assertEqual(len(m2.blocks), 4)
        self.assertEqual(m2.blocks[0].block_type, BlockType.HOME)
        self.assertEqual(m2.blocks[1].block_type, BlockType.SAFE_Z)
        self.assertEqual(m2.blocks[2].block_type, BlockType.PROBE_Z)
        self.assertEqual(m2.blocks[3].block_type, BlockType.RUN_FILE)

    def test_macro_manager(self):
        storage = SettingsStorage()
        manager = MacroManager(storage)
        self.assertGreaterEqual(len(manager.macros()), 1)

        custom_m = Macro(name="Custom Chained Command", color="#ff9800", blocks=[MacroBlock(BlockType.UNLOCK)])
        manager.add_macro(custom_m)
        self.assertIn(custom_m, manager.macros())

        # Reload
        manager2 = MacroManager(storage)
        found = [m for m in manager2.macros() if m.name == "Custom Chained Command"]
        self.assertEqual(len(found), 1)

        # Remove
        manager2.remove_macro(custom_m.id)
        found_after = [m for m in manager2.macros() if m.name == "Custom Chained Command"]
        self.assertEqual(len(found_after), 0)

    def test_default_sample_macro_coordinates(self):
        storage = SettingsStorage()
        manager = MacroManager(storage)
        prep = [m for m in manager.macros() if m.id == "default-prep-run"][0]
        move_block = [b for b in prep.blocks if b.block_type == BlockType.MOVE_TO][0]
        self.assertEqual(move_block.params["x"], 35.90)
        self.assertEqual(move_block.params["y"], -271.00)
        self.assertEqual(move_block.params["z"], -30.00)
        self.assertEqual(move_block.params["coords"], "machine")
        self.assertEqual(move_block.params["feed"], 1200)


if __name__ == "__main__":
    unittest.main()
