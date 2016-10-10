# -*- coding: utf-8 -*-
from DateTime import DateTime
from plone import api
from plone.rfc822 import constructMessage
from plone.rfc822.defaultfields import BaseFieldMarshaler
from plone.rfc822.interfaces import IFieldMarshaler
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.rfc822 import marshall
from venusianconfiguration import configure
from zope import schema
from zope.interface import implementer
from zope.interface import Interface
from zope.schema import getFieldNamesInOrder

import Acquisition
import json
import logging


# plone/app/contenttypes/migration/topics.py
# by mauritsvanrees, jensens, pbauer

logger = logging.getLogger('transmogrifier')
prefix = 'plone.app.querystring'

INVALID_OPERATION = 'Invalid operation %s for criterion: %s'


# Converters

# noinspection PyMethodMayBeStatic
class CriterionConverter(object):

    # Last part of the code for the dotted operation method,
    # e.g. 'string.contains'.
    operator_code = ''
    # alternative code, possibly used if the first code does not work.
    alt_operator_code = ''

    def get_query_value(self, value, index, criterion):
        # value may contain a query and some parameters, but in the
        # simple case it is simply a value.
        return value

    def get_operation(self, value, index, criterion):
        # Get dotted operation method.  This may depend on value.
        return '%s.operation.%s' % (prefix, self.operator_code)

    def get_alt_operation(self, value, index, criterion):
        # Get dotted operation method.  This may depend on value.
        return '%s.operation.%s' % (prefix, self.alt_operator_code)

    def is_index_known(self, registry, index):
        # Is the index registered as criterion index?
        key = '%s.field.%s' % (prefix, index)
        try:
            registry.get(key)
        except KeyError:
            logger.warn('Index %s is no criterion index. Registry gives '
                        'KeyError: %s', index, key)
            return False
        return True

    def is_index_enabled(self, registry, index):
        # Is the index enabled as criterion index?
        key = '%s.field.%s' % (prefix, index)
        index_data = registry.get(key)
        if index_data.get('enabled'):
            return True
        logger.warn('Index %s is not enabled as criterion index. ', index)
        return False

    def switch_type_to_portal_type(self, value, criterion):
        # 'portal_type' is the object id of the FTI in portal_types.
        # 'Type' is the title of that object.
        # For example:
        # - portal_type 'Document' has Type 'Page'.
        # - portal_type 'Topic' has Type 'Collection (old)'.
        if isinstance(value, dict):
            values = value.get('query', [])
        else:
            values = value
        if not values:
            return value
        new_values = []
        types_tool = api.portal.get_tool('portal_types')
        type_to_portal_type = {}
        portal_types = types_tool.objectIds()
        for portal_type, Type in types_tool.listTypeTitles().items():
            type_to_portal_type[Type] = portal_type
        for Type in values:
            portal_type = type_to_portal_type.get(Type)
            if not portal_type:
                if Type in portal_types:
                    portal_type = Type
                else:
                    logger.warn('Cannot switch Type %r to portal_type.', Type)
                    continue
            new_values.append(portal_type)
        new_values = tuple(new_values)
        if isinstance(value, dict):
            value['query'] = new_values
        else:
            value = new_values
        return value

    def get_valid_operation(self, registry, index, value, criterion):
        key = '%s.field.%s.operations' % (prefix, index)
        operations = registry.get(key)
        operation = self.get_operation(value, index, criterion)
        if operation not in operations:
            operation = self.get_alt_operation(value, index, criterion)
            if operation not in operations:
                return

        return operation

    def add_to_form_query(self, form_query, index, operation, query_value):
        row = {'i': index,
               'o': operation}
        if query_value is not None:
            row['v'] = query_value
        form_query.append(row)

    def __call__(self, form_query, criterion, registry):
        criteria = criterion.getCriteriaItems()
        if not criteria:
            logger.warn('Ignoring empty criterion %s.', criterion)
            return
        for index, value in criteria:
            # Add unknown indexes to invalid form_query
            unknown_index = None

            # Check if the index is known and enabled as criterion index.
            if index == 'Type':
                # Try to replace Type by portal_type
                index = 'portal_type'
                value = self.switch_type_to_portal_type(value, criterion)

            if not self.is_index_known(registry, index):
                # if not known, handle like Subject
                unknown_index = index
                index = 'Subject'

            self.is_index_enabled(registry, index)
            # TODO: what do we do when this is False?  Raise an
            # Exception?  Continue processing the index and value
            # anyway, now that a warning is logged?  Continue with the
            # next criteria item?

            # Get the operation method.
            operation = self.get_valid_operation(
                registry,
                index,
                value,
                criterion
            )
            if not operation:
                logger.error(INVALID_OPERATION % (operation, criterion))
                # TODO: raise an Exception?
                continue

            # Get the value that we will query for.
            query_value = self.get_query_value(value, index, criterion)

            # Add a row to the formquery.
            if not unknown_index:
                self.add_to_form_query(form_query,
                                       index, operation, query_value)
            else:
                self.add_to_form_query(form_query,
                                       unknown_index, operation, query_value)


class ATDateCriteriaConverter(CriterionConverter):
    """Handle date criteria.

    Note that there is also ATDateRangeCriterion, which is much
    simpler as it just has two dates.

    In our case we have these valid operations:

    ['plone.app.querystring.operation.date.lessThan',
     'plone.app.querystring.operation.date.largerThan',
     'plone.app.querystring.operation.date.between',
     'plone.app.querystring.operation.date.lessThanRelativeDate',
     'plone.app.querystring.operation.date.largerThanRelativeDate',
     'plone.app.querystring.operation.date.today',
     'plone.app.querystring.operation.date.beforeToday',
     'plone.app.querystring.operation.date.afterToday']

    This code is based on the getCriteriaItems method from
    Products/ATContentTypes/criteria/date.py.  We check the field
    values ourselves instead of translating the values back and forth.
    """

    def __call__(self, form_query, criterion, registry):  # noqa
        if criterion.value is None:
            logger.warn('Ignoring empty criterion %s.', criterion)
            return
        field = criterion.Field()
        value = criterion.Value()

        # Check if the index is known and enabled as criterion index.
        if not self.is_index_known(registry, field):
            return
        self.is_index_enabled(registry, field)

        # Negate the value for 'old' days
        if criterion.getDateRange() == '-':
            value = -value

        date = DateTime() + value

        # Get the possible operation methods.
        key = '%s.field.%s.operations' % (prefix, field)
        operations = registry.get(key)

        def add_row(operation, value=None):
            if operation not in operations:
                # TODO just ignore it?
                raise ValueError(INVALID_OPERATION % (operation, criterion))

            # Add a row to the formquery.
            row = {'i': field,
                   'o': operation}
            if value is not None:
                row['v'] = value
            form_query.append(row)

        operation = criterion.getOperation()
        if operation == 'within_day':
            if date.isCurrentDay():
                new_operation = '%s.operation.date.today' % prefix
                add_row(new_operation)
                return
            date_range = (date.earliestTime(), date.latestTime())
            new_operation = '%s.operation.date.between' % prefix
            add_row(new_operation, date_range)
            return
        if operation == 'more':
            if value != 0:
                new_operation = ('{0}.operation.date.'
                                 'largerThanRelativeDate'.format(prefix))
                add_row(new_operation, value)
                return
            else:
                new_operation = '{0}.operation.date.afterToday'.format(prefix)
                add_row(new_operation)
                return
        if operation == 'less':
            if value != 0:
                new_operation = ('{0}.operation.date.'
                                 'lessThanRelativeDate'.format(prefix))
                add_row(new_operation, value)
                return
            else:
                new_operation = '{0}.operation.date.beforeToday'.format(prefix)
                add_row(new_operation)
                return


class ATSimpleStringCriterionConverter(CriterionConverter):
    operator_code = 'string.contains'
    # review_state could be a string criterion, but should become a selection.
    alt_operator_code = 'selection.is'


class ATCurrentAuthorCriterionConverter(CriterionConverter):
    operator_code = 'string.currentUser'


class ATSelectionCriterionConverter(CriterionConverter):
    operator_code = 'selection.is'

    def get_query_value(self, value, index, criterion):
        values = value['query']
        if value.get('operator') == 'and' and len(values) > 1:
            logger.warn('Cannot handle selection operator 'and'. Using 'or'. '
                        '%r', value)
        values = value['query']
        # Special handling for portal_type=Topic.
        if index == 'portal_type' and 'Topic' in values:
            values = list(values)
            values[values.index('Topic')] = 'Collection'
            values = tuple(values)
        return values


class ATListCriterionConverter(ATSelectionCriterionConverter):
    pass


class ATReferenceCriterionConverter(ATSelectionCriterionConverter):
    # Note: the new criterion is disabled by default.  Also, it
    # needs the _referenceIs function in the plone.app.querystring
    # queryparser and that function is not defined.
    operator_code = 'reference.is'


class ATPathCriterionConverter(CriterionConverter):
    operator_code = 'string.path'

    def get_query_value(self, value, index, criterion):
        raw = criterion.getRawValue()
        if not raw:
            return
        # Is this a recursive query?  Could check depth in the value
        # actually, but Recurse is the canonical way.  Also, the only
        # possible values for depth are -1 and 1.
        if not criterion.Recurse():
            for index, path in enumerate(raw):
                raw[index] = path + '::1'
        return raw

    def add_to_form_query(self, form_query, index, operation, query_value):
        if query_value is None:
            return
        for value in query_value:
            row = {'i': index,
                   'o': operation,
                   'v': value}
            form_query.append(row)


class ATBooleanCriterionConverter(CriterionConverter):

    def get_operation(self, value, index, criterion):
        # Get dotted operation method.
        # value is one of these beauties:
        # value = [1, True, '1', 'True']
        # value = [0, '', False, '0', 'False', None, (), [], {}, MV]
        if True in value:
            code = 'isTrue'
        elif False in value:
            code = 'isFalse'
        else:
            logger.warn('Unknown value for boolean criterion. '
                        'Falling back to True. %r', value)
            code = 'isTrue'
        return '%s.operation.boolean.%s' % (prefix, code)

    def __call__(self, form_query, criterion, registry):
        criteria = criterion.getCriteriaItems()
        if not criteria:
            return
        for index, value in criteria:
            if index == 'is_folderish':
                fieldname = 'isFolderish'
            elif index == 'is_default_page':
                fieldname = 'isDefaultPage'
            else:
                fieldname = index
            # Check if the index is known and enabled as criterion index.
            if not self.is_index_known(registry, fieldname):
                continue
            self.is_index_enabled(registry, fieldname)
            # Get the operation method.
            operation = self.get_valid_operation(
                registry, fieldname, value, criterion)
            if not operation:
                logger.error(INVALID_OPERATION % (operation, criterion))
                # TODO: raise an Exception?
                continue
            # Add a row to the formquery.
            row = {'i': index,
                   'o': operation}
            form_query.append(row)


class ATDateRangeCriterionConverter(CriterionConverter):
    operator_code = 'date.between'

    def get_query_value(self, value, index, criterion):
        return value['query']


class ATPortalTypeCriterionConverter(CriterionConverter):
    operator_code = 'selection.is'

    def get_query_value(self, value, index, criterion):
        # Special handling for portal_type=Topic.
        if 'Topic' in value:
            value = list(value)
            value[value.index('Topic')] = 'Collection'
            value = tuple(value)
        return value


class ATRelativePathCriterionConverter(CriterionConverter):
    # We also have path.isWithinRelative, but its function is not defined.
    operator_code = 'string.relativePath'

    def get_query_value(self, value, index, criterion):
        if not criterion.Recurse():
            logger.warn('Cannot handle non-recursive path search. '
                        'Allowing recursive search. %r', value)
        return criterion.getRelativePath()


class ATSimpleIntCriterionConverter(CriterionConverter):
    # Also available: int.lessThan, int.largerThan.
    operator_code = 'int.is'

    def get_operation(self, value, index, criterion):
        # Get dotted operation method.
        direction = value.get('range')
        if not direction:
            code = 'is'
        elif direction == 'min':
            code = 'largerThan'
        elif direction == 'max':
            code = 'lessThan'
        elif direction == 'min:max':
            logger.warn('min:max direction not supported for integers. %r',
                        value)
            return
        else:
            logger.warn('Unknown direction for integers. %r', value)
            return
        return '{0}.operation.int.{1}'.format(prefix, code)

    def get_query_value(self, value, index, criterion):
        if isinstance(value['query'], tuple):
            logger.warn('More than one integer is not supported. %r', value)
            return
        return value['query']


CONVERTERS = {
    # Create an instance of each converter.
    'ATBooleanCriterion': ATBooleanCriterionConverter(),
    'ATCurrentAuthorCriterion': ATCurrentAuthorCriterionConverter(),
    'ATDateCriteria': ATDateCriteriaConverter(),
    'ATDateRangeCriterion': ATDateRangeCriterionConverter(),
    'ATListCriterion': ATListCriterionConverter(),
    'ATPathCriterion': ATPathCriterionConverter(),
    'ATPortalTypeCriterion': ATPortalTypeCriterionConverter(),
    'ATReferenceCriterion': ATReferenceCriterionConverter(),
    'ATRelativePathCriterion': ATRelativePathCriterionConverter(),
    'ATSelectionCriterion': ATSelectionCriterionConverter(),
    'ATSimpleIntCriterion': ATSimpleIntCriterionConverter(),
    'ATSimpleStringCriterion': ATSimpleStringCriterionConverter(),
}

MOCK_OPERATIONS = {
    'boolean': {
        'isFalse': {
            'operation': u'plone.app.querystring.queryparser._isFalse',
            'widget': None
        },
        'isTrue': {
            'operation': u'plone.app.querystring.queryparser._isTrue',
            'widget': None
        }
    },
    'date': {
        'afterToday': {
            'operation': u'plone.app.querystring.queryparser._afterToday',
            'widget': None
        },
        'beforeToday': {
            'operation': u'plone.app.querystring.queryparser._beforeToday',
            'widget': None
        },
        'between': {
            'operation': u'plone.app.querystring.queryparser._between',
            'widget': u'DateRangeWidget'
        },
        'largerThan': {
            'operation': u'plone.app.querystring.queryparser._largerThan',
            'widget': u'DateWidget'
        },
        'largerThanRelativeDate': {
            'operation': u'plone.app.querystring.queryparser._moreThanRelativeDate',  # noqa
            'widget': u'RelativeDateWidget'
        },
        'lessThan': {
            'operation': u'plone.app.querystring.queryparser._lessThan',
            'widget': u'DateWidget'
        },
        'lessThanRelativeDate': {
            'operation': u'plone.app.querystring.queryparser._lessThanRelativeDate',  # noqa
            'widget': u'RelativeDateWidget'
        },
        'today': {
            'operation': u'plone.app.querystring.queryparser._today',
            'widget': None
        }
    },
    'int': {
        'is': {
            'operation': u'plone.app.querystring.queryparser._equal',
            'widget': u'StringWidget'
        },
        'largerThan': {
            'operation': u'plone.app.querystring.queryparser._largerThan',
            'widget': u'StringWidget'
        },
        'lessThan': {
            'operation': u'plone.app.querystring.queryparser._lessThan',
            'widget': u'StringWidget'
        }
    },
    'list': {
        'contains': {
            'operation': u'plone.app.querystring.queryparser._contains',
            'widget': u'ReferenceWidget'
        }
    },
    'path': {
        'isWithin': {
            'operation': u'plone.app.querystring.queryparser._pathContains',
            'widget': u'ReferenceWidget'
        },
        'isWithinRelative': {
            'operation': u'plone.app.querystring.queryparser._pathContainsRelative',  # noqa
            'widget': u'RelativePathWidget'
        }
    },
    'reference': {
        'is': {
            'operation': u'plone.app.querystring.queryparser._referenceIs',
            'widget': u'ReferenceWidget'
        }
    },
    'selection': {
        'is': {
            'operation': u'plone.app.querystring.queryparser._equal',
            'widget': u'MultipleSelectionWidget'
        }
    },
    'string': {
        'contains': {
            'operation': u'plone.app.querystring.queryparser._contains',
            'widget': u'StringWidget'
        },
        'currentUser': {
            'operation': u'plone.app.querystring.queryparser._currentUser',
            'widget': None
        },
        'is': {
            'operation': u'plone.app.querystring.queryparser._equal',
            'widget': u'StringWidget'
        },
        'path': {
            'operation': u'plone.app.querystring.queryparser._path',
            'widget': u'ReferenceWidget'
        },
        'relativePath': {
            'operation': u'plone.app.querystring.queryparser._relativePath',  # noqa
            'widget': u'RelativePathWidget'
        },
        'showInactive': {
            'operation': u'plone.app.querystring.queryparser._showInactive',  # noqa
            'widget': u'MultipleSelectionWidget'
        }
    }
}

MOCK_FIELDS = {
    'Creator': {
        'enabled': True,
        'group': u'Metadata',
        'operations': ['plone.app.querystring.operation.string.is',
                       'plone.app.querystring.operation.string.currentUser'],
        'sortable': True,
        'vocabulary': None
    },
    'Description': {
        'enabled': True,
        'sortable': False,
        'vocabulary': None
    },
    'SearchableText': {
        'enabled': True,
        'group': u'Teksti',
        'operations': ['plone.app.querystring.operation.string.contains'],
        'sortable': False,
        'vocabulary': None
    },
    'Subject': {
        'enabled': True,
        'group': u'Teksti',
        'operations': ['plone.app.querystring.operation.selection.is'],
        'sortable': True,
        'vocabulary': u'plone.app.vocabularies.Keywords'
    },
    'Title': {
        'enabled': True,
        'group': u'Teksti',
        'operations': ['plone.app.querystring.operation.string.contains'],
        'sortable': False,
        'vocabulary': None
    },
    'created': {
        'enabled': True,
        'group': u'Dates',
        'operations': [
            'plone.app.querystring.operation.date.lessThan',
            'plone.app.querystring.operation.date.largerThan',
            'plone.app.querystring.operation.date.between',
            'plone.app.querystring.operation.date.lessThanRelativeDate',
            'plone.app.querystring.operation.date.largerThanRelativeDate',
            'plone.app.querystring.operation.date.today',
            'plone.app.querystring.operation.date.beforeToday',
            'plone.app.querystring.operation.date.afterToday'
        ],
        'sortable': True,
        'vocabulary': None
    },
    'effective': {
        'enabled': True,
        'group': u'Dates',
        'operations': [
            'plone.app.querystring.operation.date.lessThan',
            'plone.app.querystring.operation.date.largerThan',
            'plone.app.querystring.operation.date.between',
            'plone.app.querystring.operation.date.lessThanRelativeDate',
            'plone.app.querystring.operation.date.largerThanRelativeDate',
            'plone.app.querystring.operation.date.today',
            'plone.app.querystring.operation.date.beforeToday',
            'plone.app.querystring.operation.date.afterToday'],
        'sortable': True,
        'vocabulary': None
    },
    'effectiveRange': {
        'enabled': False,
        'group': u'Dates',
        'operations': [],
        'sortable': False,
        'vocabulary': None
    },
    'end': {
        'enabled': True,
        'group': u'Dates',
        'operations': [
            'plone.app.querystring.operation.date.lessThan',
            'plone.app.querystring.operation.date.largerThan',
            'plone.app.querystring.operation.date.between',
            'plone.app.querystring.operation.date.lessThanRelativeDate',
            'plone.app.querystring.operation.date.largerThanRelativeDate',
            'plone.app.querystring.operation.date.today',
            'plone.app.querystring.operation.date.beforeToday',
            'plone.app.querystring.operation.date.afterToday'],
        'sortable': True,
        'vocabulary': None
    },
    'expires': {
        'enabled': True,
        'group': u'Dates',
        'operations': [
            'plone.app.querystring.operation.date.lessThan',
            'plone.app.querystring.operation.date.largerThan',
            'plone.app.querystring.operation.date.between',
            'plone.app.querystring.operation.date.lessThanRelativeDate',
            'plone.app.querystring.operation.date.largerThanRelativeDate',
            'plone.app.querystring.operation.date.today',
            'plone.app.querystring.operation.date.beforeToday',
            'plone.app.querystring.operation.date.afterToday'
        ],
        'sortable': True,
        'vocabulary': None
    },
    'getId': {
        'enabled': True,
        'group': u'Metadata',
        'operations': ['plone.app.querystring.operation.string.is'],
        'sortable': True,
        'vocabulary': None
    },
    'getObjPositionInParent': {
        'enabled': False,
        'group': u'Metadata',
        'operations': ['plone.app.querystring.operation.int.is',
                       'plone.app.querystring.operation.int.lessThan',
                       'plone.app.querystring.operation.int.largerThan'],
        'sortable': False,
        'vocabulary': None
    },
    'getRawRelatedItems': {
        'enabled': False,
        'group': u'Metadata',
        'operations': ['plone.app.querystring.operation.reference.is'],
        'sortable': False,
        'vocabulary': None
    },
    'isDefaultPage': {
        'enabled': False,
        'group': u'Metadata',
        'operations': ['plone.app.querystring.operation.boolean.isTrue',
                       'plone.app.querystring.operation.boolean.isFalse'],
        'sortable': False,
        'vocabulary': None
    },
    'isFolderish': {
        'enabled': False,
        'group': u'Metadata',
        'operations': ['plone.app.querystring.operation.boolean.isTrue',
                       'plone.app.querystring.operation.boolean.isFalse'],
        'sortable': False,
        'vocabulary': None
    },
    'modified': {
        'enabled': True,
        'group': u'Dates',
        'operations': [
            'plone.app.querystring.operation.date.lessThan',
            'plone.app.querystring.operation.date.largerThan',
            'plone.app.querystring.operation.date.between',
            'plone.app.querystring.operation.date.lessThanRelativeDate',
            'plone.app.querystring.operation.date.largerThanRelativeDate',
            'plone.app.querystring.operation.date.today',
            'plone.app.querystring.operation.date.beforeToday',
            'plone.app.querystring.operation.date.afterToday'
        ],
        'sortable': True,
        'vocabulary': None
    },
    'path': {
        'enabled': True,
        'group': u'Metadata',
        'operations': ['plone.app.querystring.operation.string.relativePath',
                       'plone.app.querystring.operation.string.path'],
        'sortable': False,
        'vocabulary': None
    },
    'portal_type': {
        'enabled': True,
        'group': u'Metadata',
        'operations': ['plone.app.querystring.operation.selection.is'],
        'sortable': False,
        'vocabulary': u'plone.app.vocabularies.ReallyUserFriendlyTypes'
    },
    'review_state': {
        'enabled': True,
        'group': u'Metadata',
        'operations': ['plone.app.querystring.operation.selection.is'],
        'sortable': True,
        'vocabulary': u'plone.app.vocabularies.WorkflowStates'
    },
    'show_inactive': {
        'enabled': True,
        'group': u'Metadata',
        'operations': ['plone.app.querystring.operation.string.showInactive'],
        'sortable': False,
        'vocabulary': u'plone.app.vocabularies.Roles'
    },
    'sortable_title': {
        'enabled': False,
        'group': u'Teksti',
        'operations': ['plone.app.querystring.operation.string.contains',
                       'plone.app.querystring.operation.string.is'],
        'sortable': True,
        'vocabulary': None
    },
    'start': {
        'enabled': True,
        'group': u'Dates',
        'operations': [
            'plone.app.querystring.operation.date.lessThan',
            'plone.app.querystring.operation.date.largerThan',
            'plone.app.querystring.operation.date.between',
            'plone.app.querystring.operation.date.lessThanRelativeDate',
            'plone.app.querystring.operation.date.largerThanRelativeDate',
            'plone.app.querystring.operation.date.today',
            'plone.app.querystring.operation.date.beforeToday',
            'plone.app.querystring.operation.date.afterToday'],
        'sortable': True,
        'vocabulary': None
    }
}


class MockRegistry(object):
    def __init__(self, data):
        self.data = data

    def get(self, key, data=None):
        parts = key.split('.')
        if data is None:
            data = self.data
        if key in data:
            return data[key]
        elif parts[0] in data:
            return self.get('.'.join(parts[1:]), data=data[parts[0]])
        else:
            raise KeyError(key)


def is_index_known(registry, index):
    # Is the index registered as criterion index?
    key = '%s.field.%s' % (prefix, index)
    try:
        registry.get(key)
    except KeyError:
        logger.warn('Index %s is no criterion index. Registry gives '
                    'KeyError: %s', index, key)
        return False
    return True


# noinspection PyUnresolvedReferences
def is_subtopic(ob):
    return bool(
        getattr(Acquisition.aq_base(Acquisition.aq_parent(ob)),
                'portal_type', None) == 'Topic'
    )


# noinspection PyUnresolvedReferences
def get_criteria(ob):
    if is_subtopic(ob):
        for criterion in get_criteria(Acquisition.aq_parent(ob)):
            yield criterion
    for criterion in ob.listCriteria():
        yield criterion


def convert(topic):
    sort_reversed = False
    sort_on = None
    criteria = list(get_criteria(topic))
    data = {'plone': {'app': {'querystring': {'field': MOCK_FIELDS,
                                              'operation': MOCK_OPERATIONS}}}}
    registry = MockRegistry(data)
    form_query = []

    for criterion in criteria:
        type_ = criterion.__class__.__name__
        if type_ == 'ATSortCriterion':
            # Sort order and direction are now stored in the Collection.
            sort_reversed = criterion.getReversed()
            sort_on = criterion.Field()
            continue

        converter = CONVERTERS.get(type_)
        if converter is None:
            msg = 'Unsupported criterion %s' % type_
            logger.error(msg)
            raise ValueError(msg)
        converter(form_query, criterion, registry)

    seen_indexes = []
    form_query_valid = []
    form_query_invalid = []

    for criterion in reversed(form_query):
        if criterion['i'] in seen_indexes:
            continue
        seen_indexes.append(criterion['i'])
        if is_index_known(registry, criterion['i']):
            form_query_valid.insert(0, criterion)
        else:
            form_query_invalid.insert(0, criterion)

    return form_query_valid, form_query_invalid, sort_reversed, sort_on


class IMockCollection(Interface):
    query = schema.List(
        value_type=schema.Dict(value_type=schema.Field(),
                               key_type=schema.TextLine()),
    )
    query_invalid = schema.List(
        value_type=schema.Dict(value_type=schema.Field(),
                               key_type=schema.TextLine()),
    )
    sort_reversed = schema.Bool()
    sort_on = schema.TextLine()


@implementer(IMockCollection)
class MockCollection(object):

    def __init__(self, query, query_invalid, sort_reversed, sort_on, *args):
        self.query = query
        self.query_invalid = query_invalid
        self.sort_reversed = sort_reversed
        self.sort_on = sort_on


@configure.adapter.factory(for_=(Interface, schema.Dict))
@implementer(IFieldMarshaler)
class DictionaryFieldMarshaler(BaseFieldMarshaler):
    ascii = True

    def encode(self, value, charset='utf-8', primary=False):
        if value:
            return json.dumps(value)
        else:
            return super(DictionaryFieldMarshaler, self).encode(
                value, charset=charset, primary=primary)

    # noinspection PyPep8Naming
    def decode(self, value, message=None, charset='utf-8',
               contentType=None, primary=False):
        if value:
            return json.loads(value)
        else:
            return super(DictionaryFieldMarshaler, self).decode(
                value, message=message, charset=charset,
                contentType=contentType, primary=primary)


def marshall_topic_as_collection(ob):
    # noinspection PyPep8Naming
    def getNamesAndFieldsInOrder(iface):
        for field_name in getFieldNamesInOrder(iface):
            yield field_name, iface[field_name]

    return constructMessage(
        MockCollection(*convert(ob)),
        getNamesAndFieldsInOrder(IMockCollection)
    )


def has_subtopics(ob):
    # noinspection PyUnresolvedReferences
    return bool([
        sub_ob for sub_ob in
        map(Acquisition.aq_base, ob.objectValues())
        if getattr(sub_ob, 'portal_type', None) == 'Topic'
    ])


@configure.transmogrifier.blueprint.component(name='plone.rfc822.marshall_collection')  # noqa
class RFC822MarshallTopicsAsCollections(ConditionalBlueprint):
    def __iter__(self):
        key = self.options.get('key')
        for item in self.previous:
            if self.condition(item):
                if '_object' in item and key:
                    item[key] = marshall(item['_object'])

                # For Topics, also marshall required fields for collections
                if item['_type'] == 'Topic':
                    obj = item['_object']
                    message = marshall_topic_as_collection(obj)
                    for name in getFieldNamesInOrder(IMockCollection):
                        item[key][name] = message[name]

                    # Because sub-collections are not supported, re-create
                    # the main topic as separate collection...
                    if has_subtopics(obj):
                        id_ = item['_path'].split('/')[-1]
                        while id_ in obj.objectIds():
                            id_ += '-{0:s}'.format(id_)
                        item['_path'] += '/{0:s}'.format(id_)

            yield item
