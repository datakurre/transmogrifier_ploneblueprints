# -*- coding: utf-8 -*-
import logging

from venusianconfiguration import configure

from transmogrifier.utils import pformat_msg
from transmogrifier.blueprints import ConditionalBlueprint


@configure.transmogrifier.blueprint.component(name='plone.import.dump')
class Dump(ConditionalBlueprint):
    def __iter__(self):
        logger = logging.getLogger(self.options.get('name', 'transmogrifier'))

        contents = {}
        for item in self.previous:
            if self.condition(item):
                contents[item['_path']] = item.__dict__
            yield item

        # Set log level
        level = self.options.get(
            'level', logging.getLevelName(logger.level))
        level = getattr(logging, level, None)
        if level is None:
            # Assume it's an integer:
            level = int(level)

        logger.log(level, pformat_msg(contents))

