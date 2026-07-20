# -*- coding: utf-8 -*-
"""Tests de la logique pure de classification (aucun réseau requis).

Lance : python3 -m unittest -v   (ou : make test)
"""
import unittest

import classify
import config


class TestNormalizeEmail(unittest.TestCase):
    def test_lowercase_and_trim(self):
        self.assertEqual(classify.normalize_email("  Contact@Pharma.GMAIL.com "),
                         ("contact@pharma.gmail.com", "pharma.gmail.com"))

    def test_strips_mailto_prefix(self):
        self.assertEqual(classify.normalize_email("mailto:jean@gmail.com"),
                         ("jean@gmail.com", "gmail.com"))

    def test_domain_is_last_segment(self):
        _, domain = classify.normalize_email("a.b+tag@sub.orange.fr")
        self.assertEqual(domain, "sub.orange.fr")

    def test_invalid_returns_none(self):
        for bad in ["", None, "pas-un-email", "a@b", "deux@@arobases.fr", "espace @gmail.com"]:
            self.assertIsNone(classify.normalize_email(bad), bad)


class TestClassifyDomain(unittest.TestCase):
    def test_grand_public(self):
        for d in ["gmail.com", "orange.fr", "wanadoo.fr", "laposte.net", "sfr.fr", "icloud.com"]:
            self.assertEqual(classify.classify_domain(d), config.CAT_GRAND_PUBLIC, d)

    def test_mssante_takes_priority(self):
        # Un sous-domaine opérateur MSSanté ne doit jamais être « grand public ».
        self.assertEqual(classify.classify_domain("mssante.fr"), config.CAT_MSSANTE)
        self.assertEqual(classify.classify_domain("aura.mssante.fr"), config.CAT_MSSANTE)

    def test_professionnel_is_default(self):
        for d in ["pharmacie-du-centre.fr", "grande-pharmacie.pro", "chu-lyon.fr"]:
            self.assertEqual(classify.classify_domain(d), config.CAT_PRO, d)

    def test_not_substring_matched(self):
        # « notgmail.com » n'est pas gmail.com : match exact attendu.
        self.assertEqual(classify.classify_domain("notgmail.com"), config.CAT_PRO)


if __name__ == "__main__":
    unittest.main()
