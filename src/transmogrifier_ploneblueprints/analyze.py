# -*- coding: utf-8 -*-
from io import BytesIO
from pprint import pprint
import logging
from transmogrifier.utils import pformat_msg

from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint


@configure.transmogrifier.blueprint.component(name='plone.export.analyze')
class Analyze(ConditionalBlueprint):
    def __iter__(self):
        logger = logging.getLogger(self.options.get('name', 'transmogrifier'))

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
        logger.log(level, pformat_msg(types))
