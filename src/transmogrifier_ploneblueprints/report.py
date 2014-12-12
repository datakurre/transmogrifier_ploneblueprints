from io import BytesIO
from pprint import pprint
from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint

import logging

logger = logging.getLogger('transmogrifier')


def get_pprint(obj):
    fp = BytesIO()
    pprint(obj, fp)
    return fp.getvalue()


@configure.transmogrifier.blueprint.component(name='plone.report')
class ReportSection(ConditionalBlueprint):
    def __iter__(self):
        types = {}

        for item in self.previous:
            if self.condition(item):
                type_ = item['_type']
                types[type_] = types.get(type_, 0) + 1
            yield item

        # Set log level
        level = self.options.get(
            'level', logging.getLevelName(logger.level))
        level = getattr(logging, level, None)
        if level is None:
            # Assume it's an integer:
            level = int(level)

        # Log the grand total
        logger.log(level, get_pprint(types))

