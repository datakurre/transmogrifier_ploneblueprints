# -*- coding: utf-8 -*-
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier.utils import pformat_msg
from venusianconfiguration import configure

import logging


@configure.transmogrifier.blueprint.component(name='plone.analyze')
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
