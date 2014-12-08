# -*- coding: utf-8 -*-
from venusianconfiguration import configure
from transmogrifier.blueprints import Blueprint

from transmogrifier.utils import defaultMatcher

from transmogrifier_ploneblueprints.utils import pathsplit
from transmogrifier_ploneblueprints.utils import traverse


# collective/transmogrifier/sections/folders.py
# by rpatterson, optilude

@configure.transmogrifier.blueprint.component(name='plone.folders')
class FoldersSection(Blueprint):
    def __iter__(self):
        path_key = defaultMatcher(self.options, 'path-key', self.name, 'path')

        new_path_key = self.options.get('new-path-key', None)
        new_type_key = self.options.get('new-type-key', '_type')

        folder_type = self.options.get('folder-type', 'Folder')
        cache = self.options.get('cache', 'true').lower() == 'true'

        seen = set()

        for item in self.previous:

            keys = item.keys()
            path_key = path_key(*keys)[0]

            if not path_key:  # not enough info
                yield item
                continue

            new_path_key = new_path_key or path_key
            new_type_key = new_type_key

            path = item[path_key]
            elements = path.strip('/').rsplit('/', 1)
            container, id_ = (len(elements) == 1
                              and ('', elements[0]) or elements)

            # This may be a new container
            if container not in seen:

                container_path_items = list(pathsplit(container))
                if container_path_items:

                    checked_elements = []

                    # Check each possible parent folder
                    obj = self.transmogrifier.context
                    for element in container_path_items:
                        checked_elements.append(element)
                        current_path = '/'.join(checked_elements)

                        if current_path and current_path not in seen:

                            if element and traverse(obj, element) is None:
                                # We don't have this path - yield to create a
                                # skeleton folder
                                yield {new_path_key: '/' + current_path,
                                       new_type_key: folder_type}
                            if cache:
                                seen.add(current_path)

                        obj = traverse(obj, element)

            if cache:
                seen.add('{0:s}/{1:s}'.format(container, id_, ))

            yield item
