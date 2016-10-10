# -*- coding: utf-8 -*-
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier.utils import pformat_msg
from venusianconfiguration import configure

import logging


@configure.transmogrifier.blueprint.component(name='plone.dump')
class Dump(ConditionalBlueprint):
    def __iter__(self):
        logger = logging.getLogger(self.options.get('name', 'transmogrifier'))

        contents = {}
        for item in self.previous:
            if self.condition(item):
                contents[item['_path']] = item
            yield item

        # Set log level
        level = self.options.get(
            'level', logging.getLevelName(logger.level))
        level = getattr(logging, level, None)
        if level is None:
            # Assume it's an integer:
            level = int(level)

        logger.log(level, '\n' + pformat_msg(contents))
