# -*- coding: utf-8 -*-
"""Module where all interfaces, events and exceptions live."""

from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from plone.app.event.interfaces import IBrowserLayer


class IPlonethemePopejoy2016Layer(IBrowserLayer):
    """Marker interface that defines a browser layer."""
