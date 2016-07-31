import itertools
from Acquisition import aq_inner
from Acquisition import aq_parent
from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.i18nl10n import ulocalized_time as orig_ulocalized_time
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from Products.CMFPlone.utils import safe_callable
from calendar import monthrange
from datetime import date
from datetime import datetime
from datetime import timedelta
from persistent.dict import PersistentDict
from plone.app.event.interfaces import ISO_DATE_FORMAT
from plone.app.layout.navigation.root import getNavigationRootObject
from plone.event.interfaces import IEvent
from plone.event.interfaces import IEventAccessor
from plone.event.interfaces import IEventRecurrence
from plone.event.interfaces import IRecurrenceSupport
from plone.event.utils import default_timezone as fallback_default_timezone
from plone.event.utils import is_date
from plone.event.utils import is_datetime
from plone.event.utils import is_same_day
from plone.event.utils import is_same_time
from plone.event.utils import pydt
from plone.event.utils import dt2int
from plone.event.utils import validated_timezone
from plone.registry.interfaces import IRegistry
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.component.hooks import getSite
from zope.component.interfaces import ISite
from plone.app.event.base import _prepare_range
from plone.app.event.base import start_end_query
from plone.app.event.base import filter_and_resort
from plone.app.event.base import _obj_or_acc



import pytz


DEFAULT_END_DELTA = 1  # hours
FALLBACK_TIMEZONE = 'UTC'

# Sync strategies
SYNC_NONE = 0
SYNC_KEEP_NEWER = 1
SYNC_KEEP_MINE = 2
SYNC_KEEP_THEIRS = 3

# Return modes for get_events
RET_MODE_BRAINS = 1
RET_MODE_OBJECTS = 2
RET_MODE_ACCESSORS = 3

# Map for ambiguous timezone abbreviations to their most common non-ambigious
# timezone name. E.g CST is ambiguous and is used for U.S./Canada Central
# Standard Time, Australian Central Standard Time, China Standard Time.
# TODO: incomplete map.
# TODO: do we need this at all or shouldn't we just fail with ambiguous
#       timezones?
replacement_zones = {
    'CET': 'Europe/Vienna',    # Central European Time
    'MET': 'Europe/Vienna',    # Middle European Time
    'EET': 'Europe/Helsinki',  # East European Time
    'WET': 'Europe/Lisbon',    # West European Time
}

# RETRIEVE EVENTS

def get_events(context, start=None, end=None, limit=None,
               ret_mode=RET_MODE_BRAINS, expand=False,
               sort='start', sort_reverse=False, **kw):
    """Return all events as catalog brains, possibly within a given
    timeframe.

    :param context: [required] A context object.
    :type context: Content object

    :param start: Date, from which on events should be searched.
    :type start: Python datetime.

    :param end: Date, until which events should be searched.
    :type end: Python datetime

    :param limit: Number of items to be returned.
    :type limit: integer

    :param ret_mode: Return type of search results. These options are
                     available:

                         * 1 (brains): Return results as catalog brains.
                         * 2 (objects): Return results as IEvent and/or
                                        IOccurrence objects.
                         * 3 (accessors): Return results as IEventAccessor
                                          wrapper objects.
    :type ret_mode: integer [1|2|3]

    :param expand: Expand the results to all occurrences (within a timeframe,
                   if given). With this option set to True, the resultset also
                   includes the event's recurrence occurrences and is sorted by
                   the start date.
                   Only available in ret_mode 2 (objects) and 3 (accessors).
    :type expand: boolean

    :param sort: Catalog index id to sort on.
    :type sort: string

    :param sort_reverse: Change the order of the sorting.
    :type sort_reverse: boolean

    :returns: Portal events, matching the search criteria.
    :rtype: catalog brains, event objects or IEventAccessor object wrapper,
            depending on ret_mode.
    """
    start, end = _prepare_range(context, start, end)

    query = {}
    query['object_provides'] = IEvent.__identifier__
    query['object_provides'] = 'Products.ATContentTypes.interfaces.event.IATEvent'

    query.update(start_end_query(start, end))

    if 'path' not in kw:
        # limit to the current navigation root, usually (not always) site
        portal = getSite()
        navroot = getNavigationRootObject(context, portal)
        query['path'] = '/'.join(navroot.getPhysicalPath())
    else:
        query['path'] = kw['path']

    # Sorting
    # In expand mode we sort after calculation of recurrences again. But we
    # need to leave this sorting here in place, since no sort definition could
    # lead to arbitrary results when limiting with sort_limit.
    query['sort_on'] = sort
    if sort_reverse:
        query['sort_order'] = 'reverse'

    # cannot limit before resorting or expansion, see below

    query.update(kw)

    cat = getToolByName(context, 'portal_catalog')
    result = cat(**query)

    # unfiltered catalog results are already sorted correctly on brain.start
    # filtering on start/end requires a resort, see docstring below and
    # p.a.event.tests.test_base_module.TestGetEventsDX.test_get_event_sort
    if sort in ('start', 'end'):
        result = filter_and_resort(context, result,
                                   start, end,
                                   sort, sort_reverse)

        # Limiting a start/end-sorted result set is possible here
        # and provides an important optimization BEFORE costly expansion
        if limit:
            result = result[:limit]

    if ret_mode in (RET_MODE_OBJECTS, RET_MODE_ACCESSORS):
        if expand is False:
            result = [_obj_or_acc(it.getObject(), ret_mode) for it in result]
        else:
            result = expand_events(result, ret_mode, start, end, sort,
                                   sort_reverse)

    # Limiting a non-start-sorted result set can only happen here
    if limit:
        result = result[:limit]

    return result



def construct_calendar(events, start=None, end=None):
    """Return a dictionary with dates in a given timeframe as keys and the
    actual occurrences for that date for building calendars.
    Long lasting events will occur on every day until their end.

    :param events: List of IEvent and/or IOccurrence objects, to construct a
                   calendar data structure from.
    :type events: list

    :param start: An optional start range date.
    :type start: Python datetime or date

    :param end: An optional start range date.
    :type end: Python datetime or date

    :returns: Dictionary with isoformat date strings as keys and event
              occurrences as values.
    :rtype: dict

    """
    if start:
        if is_datetime(start):
            start = start.date()
        assert is_date(start)
    if end:
        if is_datetime(end):
            end = end.date()
        assert is_date(end)

    cal = {}

    def _add_to_cal(cal_data, event, date):
        date_str = date.isoformat()
        if date_str not in cal_data:
            cal_data[date_str] = [event]
        else:
            cal_data[date_str].append(event)
        return cal_data

    for event in events:
        # acc = IEventAccessor(event)
        # start_date = acc.start.date()
        # end_date = acc.end.date()

        start_date = event.startDate.asdatetime().date()
        end_date = event.endDate.asdatetime().date()

        # day span between start and end + 1 for the initial date
        range_days = (end_date - start_date).days + 1
        for add_day in range(range_days):
            next_start_date = start_date + timedelta(add_day)  # initial = 0

            # avoid long loops
            if start and end_date < start:
                break  # if the date is completly outside the range
            if start and next_start_date < start:
                continue  # if start_date is outside but end reaches into range
            if end and next_start_date > end:
                break  # if date is outside range

            _add_to_cal(cal, event, next_start_date)
    return cal
