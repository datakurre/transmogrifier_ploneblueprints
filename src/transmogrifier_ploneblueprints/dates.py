# -*- coding: utf-8 -*-
from DateTime import DateTime
from plone import api
from plone.api.exc import InvalidParameterError
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.utils import resolve_object
from venusianconfiguration import configure

import pkg_resources


try:
    pkg_resources.get_distribution('plone.app.contenttypes')
except pkg_resources.DistributionNotFound:
    HAS_PAC = False
else:
    from plone.event.utils import pydt
    from pytz import timezone
    HAS_PAC = True


@configure.transmogrifier.blueprint.component(name='plone.dates.set')
class SetAndFixKnownDates(ConditionalBlueprint):
    def __iter__(self):
        context = self.transmogrifier.context
        default_timezone = self.options.get('default_timezone') or 'UTC'
        if HAS_PAC:
            try:
                tz = api.portal.get_registry_record('plone.portal_timezone')
            except InvalidParameterError:
                tz = None
            if tz is not None:
                tz = timezone(tz)
            else:
                tz = timezone(default_timezone)

        for item in self.previous:
            if self.condition(item):
                obj = resolve_object(context, item)
                if 'creation_date' in item:
                    try:
                        obj.setCreationDate(item['creation_date'])
                    except AttributeError:
                        # dexterity content does not have setCreationDate
                        obj.creation_date = item['creation_date']
                if 'modification_date' in item:
                    obj.setModificationDate(item['modification_date'])
                if 'effective_date' in item:
                    obj.setModificationDate(item['effective_date'])
                if 'expiration_date' in item:
                    obj.setModificationDate(item['expiration_date'])

                if HAS_PAC and item.get('_type') == 'Event':
                    obj = resolve_object(context, item)
                    obj.start = pydt(DateTime(obj.start)).astimezone(tz)
                    obj.end = pydt(DateTime(obj.end)).astimezone(tz)

            yield item
