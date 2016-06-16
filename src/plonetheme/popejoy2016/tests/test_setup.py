# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from plonetheme.popejoy2016.testing import PLONETHEME_POPEJOY2016_INTEGRATION_TESTING  # noqa
from plone import api

import unittest


class TestSetup(unittest.TestCase):
    """Test that plonetheme.popejoy2016 is properly installed."""

    layer = PLONETHEME_POPEJOY2016_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """Test if plonetheme.popejoy2016 is installed."""
        self.assertTrue(self.installer.isProductInstalled(
            'plonetheme.popejoy2016'))

    def test_browserlayer(self):
        """Test that IPlonethemePopejoy2016Layer is registered."""
        from plonetheme.popejoy2016.interfaces import (
            IPlonethemePopejoy2016Layer)
        from plone.browserlayer import utils
        self.assertIn(IPlonethemePopejoy2016Layer, utils.registered_layers())


class TestUninstall(unittest.TestCase):

    layer = PLONETHEME_POPEJOY2016_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')
        self.installer.uninstallProducts(['plonetheme.popejoy2016'])

    def test_product_uninstalled(self):
        """Test if plonetheme.popejoy2016 is cleanly uninstalled."""
        self.assertFalse(self.installer.isProductInstalled(
            'plonetheme.popejoy2016'))

    def test_browserlayer_removed(self):
        """Test that IPlonethemePopejoy2016Layer is removed."""
        from plonetheme.popejoy2016.interfaces import IPlonethemePopejoy2016Layer
        from plone.browserlayer import utils
        self.assertNotIn(IPlonethemePopejoy2016Layer, utils.registered_layers())
