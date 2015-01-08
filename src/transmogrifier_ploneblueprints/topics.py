# -*- coding: utf-8 -*-

# plone/app/contenttypes/migration/topics.py
# by mauritsvanrees, jensens, pbauer
import json
from plone.rfc822 import constructMessage
from plone.rfc822.defaultfields import BaseFieldMarshaler
from plone.rfc822.interfaces import IFieldMarshaler
from zope.schema import getFieldNamesInOrder

from transmogrifier.blueprints import ConditionalBlueprint
from venusianconfiguration import configure

from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from zope.dottedname.resolve import resolve

from zope import schema
from zope.interface import Interface, implementer

import logging

logger = logging.getLogger('transmogrifier')
prefix = "plone.app.querystring"

INVALID_OPERATION = 'Invalid operation %s for criterion: %s'

# Converters

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
        return "%s.operation.%s" % (prefix, self.operator_code)

    def get_alt_operation(self, value, index, criterion):
        # Get dotted operation method.  This may depend on value.
        return "%s.operation.%s" % (prefix, self.alt_operator_code)

    def is_index_known(self, registry, index):
        # Is the index registered as criterion index?
        key = '%s.field.%s' % (prefix, index)
        try:
            registry.get(key)
        except KeyError:
            logger.warn("Index %s is no criterion index. Registry gives "
                        "KeyError: %s", index, key)
            return False
        return True

    def is_index_enabled(self, registry, index):
        # Is the index enabled as criterion index?
        key = '%s.field.%s' % (prefix, index)
        index_data = registry.get(key)
        if index_data.get('enabled'):
            return True
        logger.warn("Index %s is not enabled as criterion index. ", index)
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
        ttool = getToolByName(criterion, 'portal_types')
        type_to_portal_type = {}
        portal_types = ttool.objectIds()
        for portal_type, Type in ttool.listTypeTitles().items():
            type_to_portal_type[Type] = portal_type
        for Type in values:
            portal_type = type_to_portal_type.get(Type)
            if not portal_type:
                if Type in portal_types:
                    portal_type = Type
                else:
                    logger.warn("Cannot switch Type %r to portal_type.", Type)
                    continue
            new_values.append(portal_type)
        new_values = tuple(new_values)
        if isinstance(value, dict):
            value['query'] = new_values
        else:
            value = new_values
        return value

    def is_operation_valid(self, registry, operation):

        # don't do the check
        # as we might not have plone.app.querystring
        return True

        # Check that the operation exists.
        op_info = registry.get(operation)
        if op_info is None:
            logger.error("Operation %r is not defined.", operation)
            return False
        op_function_name = op_info.get('operation')
        try:
            resolve(op_function_name)
        except ImportError:
            logger.error("ImportError for operation %r: %s",
                         operation, op_function_name)
            return False
        return True

    def get_valid_operation(self, registry, index, value, criterion):
        key = '%s.field.%s.operations' % (prefix, index)
        operations = registry.get(key)
        operation = self.get_operation(value, index, criterion)
        if operation not in operations:
            operation = self.get_alt_operation(value, index, criterion)
            if operation not in operations:
                return

        if self.is_operation_valid(registry, operation):
            return operation

        return operation

    def add_to_formquery(self, formquery, index, operation, query_value):
        row = {'i': index,
               'o': operation}
        if query_value is not None:
            row['v'] = query_value
        formquery.append(row)

    def __call__(self, formquery, criterion, registry):
        criteria = criterion.getCriteriaItems()
        if not criteria:
            logger.warn("Ignoring empty criterion %s.", criterion)
            return
        for index, value in criteria:
            # Check if the index is known and enabled as criterion index.
            if index == 'Type':
                # Try to replace Type by portal_type
                index = 'portal_type'
                value = self.switch_type_to_portal_type(value, criterion)

            if not self.is_index_known(registry, index):
                # if not known, Subject might suffice
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

            # Add a row to the form query.
            self.add_to_formquery(formquery, index, operation, query_value)


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

    def __call__(self, formquery, criterion, registry):
        if criterion.value is None:
            logger.warn("Ignoring empty criterion %s.", criterion)
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
            if not self.is_operation_valid(registry, operation):
                raise ValueError(INVALID_OPERATION % (operation, criterion))

            # Add a row to the form query.
            row = {'i': field,
                   'o': operation}
            if value is not None:
                row['v'] = value
            formquery.append(row)

        operation = criterion.getOperation()
        if operation == 'within_day':
            if date.isCurrentDay():
                new_operation = "%s.operation.date.today" % prefix
                add_row(new_operation)
                return
            date_range = (date.earliestTime(), date.latestTime())
            new_operation = "%s.operation.date.between" % prefix
            add_row(new_operation, date_range)
            return
        if operation == 'more':
            if value != 0:
                new_operation = ("{0}.operation.date."
                                 "largerThanRelativeDate".format(prefix))
                add_row(new_operation, value)
                return
            else:
                new_operation = "{0}.operation.date.afterToday".format(prefix)
                add_row(new_operation)
                return
        if operation == 'less':
            if value != 0:
                new_operation = ("{0}.operation.date."
                                 "lessThanRelativeDate".format(prefix))
                add_row(new_operation, value)
                return
            else:
                new_operation = "{0}.operation.date.beforeToday".format(prefix)
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
            logger.warn("Cannot handle selection operator 'and'. Using 'or'. "
                        "%r", value)
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

    def add_to_formquery(self, formquery, index, operation, query_value):
        if query_value is None:
            return
        for value in query_value:
            row = {'i': index,
                   'o': operation,
                   'v': value}
            formquery.append(row)


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
            logger.warn("Unknown value for boolean criterion. "
                        "Falling back to True. %r", value)
            code = 'isTrue'
        return "%s.operation.boolean.%s" % (prefix, code)

    def __call__(self, formquery, criterion, registry):
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
            # Add a row to the form query.
            row = {'i': index,
                   'o': operation}
            formquery.append(row)


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
            logger.warn("Cannot handle non-recursive path search. "
                        "Allowing recursive search. %r", value)
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
            logger.warn("min:max direction not supported for integers. %r",
                        value)
            return
        else:
            logger.warn("Unknown direction for integers. %r", value)
            return
        return "{0}.operation.int.{1}".format(prefix, code)

    def get_query_value(self, value, index, criterion):
        if isinstance(value['query'], tuple):
            logger.warn("More than one integer is not supported. %r", value)
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

MOCK_OPERATIONS = {'boolean': {'isFalse': {'description': None,
                                           'operation': u'plone.app.querystring.queryparser._isFalse',
                                           'title': u'Ei',
                                           'widget': None},
                               'isTrue': {'description': None,
                                          'operation': u'plone.app.querystring.queryparser._isTrue',
                                          'title': u'Kyll\xe4',
                                          'widget': None}},
                   'date': {'afterToday': {'description': u'After the current day',
                                           'operation': u'plone.app.querystring.queryparser._afterToday',
                                           'title': u'After today',
                                           'widget': None},
                            'beforeToday': {'description': u'Before the current day',
                                            'operation': u'plone.app.querystring.queryparser._beforeToday',
                                            'title': u'Before today',
                                            'widget': None},
                            'between': {'description': u'Please use YYYY/MM/DD.',
                                        'operation': u'plone.app.querystring.queryparser._between',
                                        'title': u'Between dates',
                                        'widget': u'DateRangeWidget'},
                            'largerThan': {'description': u'Please use YYYY/MM/DD.',
                                           'operation': u'plone.app.querystring.queryparser._largerThan',
                                           'title': u'After date',
                                           'widget': u'DateWidget'},
                            'largerThanRelativeDate': {'description': u'Please enter the number in days.',
                                                       'operation': u'plone.app.querystring.queryparser._moreThanRelativeDate',
                                                       'title': u'Within last',
                                                       'widget': u'RelativeDateWidget'},
                            'lessThan': {'description': u'Please use YYYY/MM/DD.',
                                         'operation': u'plone.app.querystring.queryparser._lessThan',
                                         'title': u'Before date',
                                         'widget': u'DateWidget'},
                            'lessThanRelativeDate': {'description': u'Please enter the number in days.',
                                                     'operation': u'plone.app.querystring.queryparser._lessThanRelativeDate',
                                                     'title': u'Within next',
                                                     'widget': u'RelativeDateWidget'},
                            'today': {'description': u'The current day',
                                      'operation': u'plone.app.querystring.queryparser._today',
                                      'title': u'Today',
                                      'widget': None}},
                   'int': {'is': {'description': None,
                                  'operation': u'plone.app.querystring.queryparser._equal',
                                  'title': u'Equals',
                                  'widget': u'StringWidget'},
                           'largerThan': {'description': None,
                                          'operation': u'plone.app.querystring.queryparser._largerThan',
                                          'title': u'Larger than',
                                          'widget': u'StringWidget'},
                           'lessThan': {'description': None,
                                        'operation': u'plone.app.querystring.queryparser._lessThan',
                                        'title': u'Less than',
                                        'widget': u'StringWidget'}},
                   'list': {'contains': {'description': None,
                                         'operation': u'plone.app.querystring.queryparser._contains',
                                         'title': u'Contains',
                                         'widget': u'ReferenceWidget'}},
                   'path': {'isWithin': {'description': None,
                                         'operation': u'plone.app.querystring.queryparser._pathContains',
                                         'title': u'Is within',
                                         'widget': u'ReferenceWidget'},
                            'isWithinRelative': {'description': None,
                                                 'operation': u'plone.app.querystring.queryparser._pathContainsRelative',
                                                 'title': u'Is within (relative)',
                                                 'widget': u'RelativePathWidget'}},
                   'reference': {'is': {'description': None,
                                        'operation': u'plone.app.querystring.queryparser._referenceIs',
                                        'title': u'Equals',
                                        'widget': u'ReferenceWidget'}},
                   'selection': {'is': {'description': u'Tip: you can use * to autocomplete.',
                                        'operation': u'plone.app.querystring.queryparser._equal',
                                        'title': u'Is',
                                        'widget': u'MultipleSelectionWidget'}},
                   'string': {'contains': {'description': None,
                                           'operation': u'plone.app.querystring.queryparser._contains',
                                           'title': u'Contains',
                                           'widget': u'StringWidget'},
                              'currentUser': {'description': u'The user viewing the querystring results',
                                              'operation': u'plone.app.querystring.queryparser._currentUser',
                                              'title': u'Current logged in user',
                                              'widget': None},
                              'is': {'description': u'Tip: you can use * to autocomplete.',
                                     'operation': u'plone.app.querystring.queryparser._equal',
                                     'title': u'Is',
                                     'widget': u'StringWidget'},
                              'path': {'description': u'Location in the site structure',
                                       'operation': u'plone.app.querystring.queryparser._path',
                                       'title': u'Absolute path',
                                       'widget': u'ReferenceWidget'},
                              'relativePath': {'description': u"Use '../' to navigate to parent objects.",
                                               'operation': u'plone.app.querystring.queryparser._relativePath',
                                               'title': u'Relative path',
                                               'widget': u'RelativePathWidget'},
                              'showInactive': {'description': u'The user roles which are allowed to see inactive content',
                                               'operation': u'plone.app.querystring.queryparser._showInactive',
                                               'title': u'Show Inactive',
                                               'widget': u'MultipleSelectionWidget'}}}

MOCK_FIELDS = {'Creator': {'description': u'The person that created an item',
                           'enabled': True,
                           'group': u'Metadata',
                           'operations': ['plone.app.querystring.operation.string.is',
                                          'plone.app.querystring.operation.string.currentUser'],
                           'sortable': True,
                           'title': u'Tekij\xe4',
                           'vocabulary': None},
               'Description': {'description': u"An item's description",
                               'enabled': True,
                               'group': u'Teksti',
                               'operations': ['plone.app.querystring.operation.string.contains'],
                               'sortable': False,
                               'title': u'Kuvaus',
                               'vocabulary': None},
               'SearchableText': {'description': u'Tekstihaku kohteen sis\xe4ll\xf6st\xe4',
                                  'enabled': True,
                                  'group': u'Teksti',
                                  'operations': ['plone.app.querystring.operation.string.contains'],
                                  'sortable': False,
                                  'title': u'Searchable text',
                                  'vocabulary': None},
               'Subject': {'description': u'Tags are used for organization of content',
                           'enabled': True,
                           'group': u'Teksti',
                           'operations': ['plone.app.querystring.operation.selection.is'],
                           'sortable': True,
                           'title': u'Tag',
                           'vocabulary': u'plone.app.vocabularies.Keywords'},
               'Title': {'description': u'Tekstihaku kohteen nimikkeist\xe4',
                         'enabled': True,
                         'group': u'Teksti',
                         'operations': ['plone.app.querystring.operation.string.contains'],
                         'sortable': False,
                         'title': u'Nimike',
                         'vocabulary': None},
               'created': {'description': u'The date an item was created',
                           'enabled': True,
                           'group': u'Dates',
                           'operations': ['plone.app.querystring.operation.date.lessThan',
                                          'plone.app.querystring.operation.date.largerThan',
                                          'plone.app.querystring.operation.date.between',
                                          'plone.app.querystring.operation.date.lessThanRelativeDate',
                                          'plone.app.querystring.operation.date.largerThanRelativeDate',
                                          'plone.app.querystring.operation.date.today',
                                          'plone.app.querystring.operation.date.beforeToday',
                                          'plone.app.querystring.operation.date.afterToday'],
                           'sortable': True,
                           'title': u'Creation date',
                           'vocabulary': None},
               'effective': {'description': u'The time and date an item was first published',
                             'enabled': True,
                             'group': u'Dates',
                             'operations': ['plone.app.querystring.operation.date.lessThan',
                                            'plone.app.querystring.operation.date.largerThan',
                                            'plone.app.querystring.operation.date.between',
                                            'plone.app.querystring.operation.date.lessThanRelativeDate',
                                            'plone.app.querystring.operation.date.largerThanRelativeDate',
                                            'plone.app.querystring.operation.date.today',
                                            'plone.app.querystring.operation.date.beforeToday',
                                            'plone.app.querystring.operation.date.afterToday'],
                             'sortable': True,
                             'title': u'Effective date',
                             'vocabulary': None},
               'effectiveRange': {'description': u'Querying this is undefined',
                                  'enabled': False,
                                  'group': u'Dates',
                                  'operations': [],
                                  'sortable': False,
                                  'title': u'Effective range',
                                  'vocabulary': None},
               'end': {'description': u'Tapahtuman loppumisajankohta',
                       'enabled': True,
                       'group': u'Dates',
                       'operations': ['plone.app.querystring.operation.date.lessThan',
                                      'plone.app.querystring.operation.date.largerThan',
                                      'plone.app.querystring.operation.date.between',
                                      'plone.app.querystring.operation.date.lessThanRelativeDate',
                                      'plone.app.querystring.operation.date.largerThanRelativeDate',
                                      'plone.app.querystring.operation.date.today',
                                      'plone.app.querystring.operation.date.beforeToday',
                                      'plone.app.querystring.operation.date.afterToday'],
                       'sortable': True,
                       'title': u'Event end date',
                       'vocabulary': None},
               'expires': {'description': u'The time and date an item was expired',
                           'enabled': True,
                           'group': u'Dates',
                           'operations': ['plone.app.querystring.operation.date.lessThan',
                                          'plone.app.querystring.operation.date.largerThan',
                                          'plone.app.querystring.operation.date.between',
                                          'plone.app.querystring.operation.date.lessThanRelativeDate',
                                          'plone.app.querystring.operation.date.largerThanRelativeDate',
                                          'plone.app.querystring.operation.date.today',
                                          'plone.app.querystring.operation.date.beforeToday',
                                          'plone.app.querystring.operation.date.afterToday'],
                           'sortable': True,
                           'title': u'Expiration date',
                           'vocabulary': None},
               'getId': {'description': u'Sis\xe4ll\xf6n tunniste (k\xe4ytet\xe4\xe4n kohteen verkko-osoitteessa)',
                         'enabled': True,
                         'group': u'Metadata',
                         'operations': ['plone.app.querystring.operation.string.is'],
                         'sortable': True,
                         'title': u'Short name (id)',
                         'vocabulary': None},
               'getObjPositionInParent': {'description': u'Sis\xe4ll\xf6n j\xe4rjestys kansiossaan',
                                          'enabled': False,
                                          'group': u'Metadata',
                                          'operations': ['plone.app.querystring.operation.int.is',
                                                         'plone.app.querystring.operation.int.lessThan',
                                                         'plone.app.querystring.operation.int.largerThan'],
                                          'sortable': False,
                                          'title': u'J\xe4rjestys kansiossa',
                                          'vocabulary': None},
               'getRawRelatedItems': {'description': u'Hae valintoihin liittyv\xe4\xe4 sis\xe4lt\xf6\xe4',
                                      'enabled': False,
                                      'group': u'Metadata',
                                      'operations': ['plone.app.querystring.operation.reference.is'],
                                      'sortable': False,
                                      'title': u'Liittyy t\xe4h\xe4n',
                                      'vocabulary': None},
               'isDefaultPage': {'description': u'Etsi sis\xe4lt\xf6\xe4, joka on kansionsa oletusn\xe4kym\xe4n\xe4.',
                                 'enabled': False,
                                 'group': u'Metadata',
                                 'operations': ['plone.app.querystring.operation.boolean.isTrue',
                                                'plone.app.querystring.operation.boolean.isFalse'],
                                 'sortable': False,
                                 'title': u'Oletussivu',
                                 'vocabulary': None},
               'isFolderish': {'description': u'Etsi sellaisia sis\xe4lt\xf6kohteita, jotka voivat sis\xe4lt\xe4\xe4 muuta sis\xe4lt\xf6\xe4.',
                               'enabled': False,
                               'group': u'Metadata',
                               'operations': ['plone.app.querystring.operation.boolean.isTrue',
                                              'plone.app.querystring.operation.boolean.isFalse'],
                               'sortable': False,
                               'title': u'Kansiomainen',
                               'vocabulary': None},
               'modified': {'description': u'Sis\xe4ll\xf6n viimeisin muokkausajankohta',
                            'enabled': True,
                            'group': u'Dates',
                            'operations': ['plone.app.querystring.operation.date.lessThan',
                                           'plone.app.querystring.operation.date.largerThan',
                                           'plone.app.querystring.operation.date.between',
                                           'plone.app.querystring.operation.date.lessThanRelativeDate',
                                           'plone.app.querystring.operation.date.largerThanRelativeDate',
                                           'plone.app.querystring.operation.date.today',
                                           'plone.app.querystring.operation.date.beforeToday',
                                           'plone.app.querystring.operation.date.afterToday'],
                            'sortable': True,
                            'title': u'Modification date',
                            'vocabulary': None},
               'path': {'description': u'The location of an item ',
                        'enabled': True,
                        'group': u'Metadata',
                        'operations': ['plone.app.querystring.operation.string.relativePath',
                                       'plone.app.querystring.operation.string.path'],
                        'sortable': False,
                        'title': u'Sijainti',
                        'vocabulary': None},
               'portal_type': {'description': u'Sis\xe4ll\xf6n tyyppi (esim. Tapahtuma)',
                               'enabled': True,
                               'group': u'Metadata',
                               'operations': ['plone.app.querystring.operation.selection.is'],
                               'sortable': False,
                               'title': u'Type',
                               'vocabulary': u'plone.app.vocabularies.ReallyUserFriendlyTypes'},
               'review_state': {'description': u'Sis\xe4ll\xf6n ty\xf6kulun tila (esim. julkaistu)',
                                'enabled': True,
                                'group': u'Metadata',
                                'operations': ['plone.app.querystring.operation.selection.is'],
                                'sortable': True,
                                'title': u'Review state',
                                'vocabulary': u'plone.app.vocabularies.WorkflowStates'},
               'show_inactive': {'description': u'Select which roles have the permission to view inactive objects',
                                 'enabled': True,
                                 'group': u'Metadata',
                                 'operations': ['plone.app.querystring.operation.string.showInactive'],
                                 'sortable': False,
                                 'title': u'Show Inactive',
                                 'vocabulary': u'plone.app.vocabularies.Roles'},
               'sortable_title': {'description': u"The item's title, transformed for sorting",
                                  'enabled': False,
                                  'group': u'Teksti',
                                  'operations': ['plone.app.querystring.operation.string.contains',
                                                 'plone.app.querystring.operation.string.is'],
                                  'sortable': True,
                                  'title': u'J\xe4rjestett\xe4v\xe4 otsikko',
                                  'vocabulary': None},
               'start': {'description': u'Tapahtuman aloitusajankohta',
                         'enabled': True,
                         'group': u'Dates',
                         'operations': ['plone.app.querystring.operation.date.lessThan',
                                        'plone.app.querystring.operation.date.largerThan',
                                        'plone.app.querystring.operation.date.between',
                                        'plone.app.querystring.operation.date.lessThanRelativeDate',
                                        'plone.app.querystring.operation.date.largerThanRelativeDate',
                                        'plone.app.querystring.operation.date.today',
                                        'plone.app.querystring.operation.date.beforeToday',
                                        'plone.app.querystring.operation.date.afterToday'],
                         'sortable': True,
                         'title': u'Event start date',
                         'vocabulary': None}}


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

def convert(topic):
    sort_reversed = False
    sort_on = None
    criteria = topic.listCriteria()
    data = {'plone': {'app': {'querystring': {'field': MOCK_FIELDS,
                                              'operation': MOCK_OPERATIONS}}}}
    registry = MockRegistry(data)
    formquery = []
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
        converter(formquery, criterion, registry)
    return formquery, sort_reversed, sort_on


@configure.transmogrifier.blueprint.component(name='plone.marshall_topics')
class MarshallTopics(ConditionalBlueprint):
    def __iter__(self):
        for item in self.previous:
            if self.condition(item) and item['_type'] == 'Topic':
                ob = item['_object']
                mock = MockCollection(*convert(ob))

                def iterFields(iface):
                    for name in getFieldNamesInOrder(iface):
                        yield name, iface[name]

                message = constructMessage(mock, iterFields(IMockCollection))
                for name, field in iterFields(IMockCollection):
                    item['message'].add_header(name, message[name].encode())
            yield item


class IMockCollection(Interface):
    query = schema.List(
        value_type=schema.Dict(value_type=schema.Field(),
                               key_type=schema.TextLine()),
    )
    sort_reversed = schema.Bool()
    sort_on = schema.TextLine()


@implementer(IMockCollection)
class MockCollection(object):

    def __init__(self, query, sort_reversed, sort_on, *args):
        self.query = query
        self.sort_reversed = sort_reversed
        self.sort_on = sort_on


@configure.adapter.factory(for_=(Interface, schema.Dict))
@implementer(IFieldMarshaler)
class DictionaryFieldMarshaler(BaseFieldMarshaler):
    ascii = True

    def encode(self, value, charset="utf-8", primary=False):
        if value:
            return json.dumps(value)
        else:
            return super(DictionaryFieldMarshaler, self).encode(
                value, charset=charset, primary=primary)

    def decode(self, value, message=None, charset="utf-8",
               contentType=None, primary=False):
        if value:
            return json.loads(value)
        else:
            return super(DictionaryFieldMarshaler, self).decode(
                value, message=message, charset=charset,
                contentType=contentType, primary=primary)


