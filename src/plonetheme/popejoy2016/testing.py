# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

import plonetheme.popejoy2016


class PlonethemePopejoy2016Layer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        self.loadZCML(package=plonetheme.popejoy2016)

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'plonetheme.popejoy2016:default')


PLONETHEME_POPEJOY2016_FIXTURE = PlonethemePopejoy2016Layer()


PLONETHEME_POPEJOY2016_INTEGRATION_TESTING = IntegrationTesting(
    bases=(PLONETHEME_POPEJOY2016_FIXTURE,),
    name='PlonethemePopejoy2016Layer:IntegrationTesting'
)


PLONETHEME_POPEJOY2016_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(PLONETHEME_POPEJOY2016_FIXTURE,),
    name='PlonethemePopejoy2016Layer:FunctionalTesting'
)


PLONETHEME_POPEJOY2016_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        PLONETHEME_POPEJOY2016_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE
    ),
    name='PlonethemePopejoy2016Layer:AcceptanceTesting'
)
