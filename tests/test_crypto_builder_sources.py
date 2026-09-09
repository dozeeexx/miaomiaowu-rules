#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_crypto_custom.py"


class CryptoBuilderSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("crypto_builder", BUILDER)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot import scripts/build_crypto_custom.py")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_retired_lurixo_sources_are_not_configured(self) -> None:
        source_text = BUILDER.read_text(encoding="utf-8")
        self.assertNotIn("lurixo/sing-box-rules", source_text)
        self.assertNotIn("SUPPLEMENT_LURIXO_GEOSITE_SOURCES", source_text)
        self.assertNotIn("parse_lurixo_geosite_url", source_text)

    def test_remaining_crypto_sources_are_explicit_and_nonempty(self) -> None:
        sources = self.module.SUPPLEMENT_CLASSICAL_SOURCES
        self.assertEqual(
            set(sources),
            {
                "blackmatrix7/Cryptocurrency",
                "blackmatrix7/Binance",
                "blackmatrix7/OKX",
                "enriquephl/Web3",
            },
        )
        self.assertTrue(all(url.startswith("https://") for url in sources.values()))


if __name__ == "__main__":
    unittest.main()
