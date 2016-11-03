# -*- coding: utf-8 -*-
from Acquisition import aq_base
from operator import itemgetter
from persistent.list import PersistentList
from plone import api
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.utils import resolve_object
from venusianconfiguration import configure


@configure.transmogrifier.blueprint.component(
    name='plone.workflow_history.set')
class SetWorkflow(ConditionalBlueprint):
    def __iter__(self):
        context = self.transmogrifier.context
        wf_tool = api.portal.get_tool('portal_workflow')
        for item in self.previous:
            if self.condition(item):
                obj = resolve_object(context, item)
                aq_base(obj).workflow_history = item['_workflow_history'] or {}
                for wf in wf_tool.getWorkflowsFor(obj):
                    wf.updateRoleMappingsFor(obj)
            yield item


def intranet_folder_workflow(history):
    action_mapping = {
        'hide': 'hide',
        'retract': 'hide',
        'publish': 'show_internally',
        'show_internally': 'show_internally',
        'show': 'show_internally',
        None: None
    }
    state_mapping = {
        'private': 'private',
        'internal': 'internal',
        'published': 'internal',
        'visible': 'internal',
        None: None
    }

    actions = {}
    for action in (list(history.get('folder_workflow') or ()) +
                   list(history.get('intranet_folder_workflow') or ())):
        actions[str(action.get('time'))] = action
    actions = sorted(actions.values(), key=itemgetter('time'))

    seen = []
    history = PersistentList()
    for action in actions:
        action = action.copy()
        action.update({
            'action': action_mapping[action.get('action')],
            'review_state': state_mapping[action.get('review_state')],
        })
        history.append(action)
        if action['time'] not in seen:
            history.append(action)
            seen.append(action['time'])
    return history


def intranet_workflow(history):
    action_mapping = {
        'hide': 'hide',
        'publish_externally': 'publish_externally',
        'publish_internally': 'publish_internally',
        'reject': 'reject',
        'retract': 'retract',
        'show_internally': 'show_internally',
        'submit': 'submit',
        'publish': 'publish_externally',
        'show': 'show_internally',
        None: None
    }
    state_mapping = {
        'external': 'external',
        'internal': 'internal',
        'internally_published': 'internally_published',
        'pending': 'pending',
        'private': 'private',
        'visible': 'internal',
        'published': 'external',
        None: None
    }

    actions = {}
    for action in (list(history.get('plone_workflow') or ()) +
                   list(history.get('intranet_workflow') or ())):
        actions[str(action.get('time'))] = action
    actions = sorted(actions.values(), key=itemgetter('time'))

    seen = []
    history = PersistentList()
    for action in actions:
        action = action.copy()
        action.update({
            'action': action_mapping[action.get('action')],
            'review_state': state_mapping[action.get('review_state')],
        })
        if action['time'] not in seen:
            history.append(action)
            seen.append(action['time'])
    return history


def simple_publication_workflow(history):
    action_mapping = {
        'hide': 'retract',
        'publish_externally': 'publish',
        'publish_internally': 'publish',
        'reject': 'reject',
        'retract': 'retract',
        'show_internally': 'publish',
        'submit': 'submit',
        'publish': 'publish',
        'show': 'publish',
        None: None
    }
    state_mapping = {
        'external': 'published',
        'internal': 'published',
        'internally_published': 'published',
        'pending': 'pending',
        'private': 'private',
        'visible': 'published',
        'published': 'published',
        None: None
    }

    actions = {}
    for action in (list(history.get('plone_workflow') or ()) +
                   list(history.get('folder_workflow') or ())):
        actions[str(action.get('time'))] = action
    actions = sorted(actions.values(), key=itemgetter('time'))

    seen = []
    history = PersistentList()
    for action in actions:
        action = action.copy()
        action.update({
            'action': action_mapping[action.get('action')],
            'review_state': state_mapping[action.get('review_state')],
        })
        if action['time'] not in seen:
            history.append(action)
            seen.append(action['time'])
    return history


# noinspection PyUnresolvedReferences
@configure.transmogrifier.blueprint.component(
    name='plone.workflow_history.plone_to_intranet')
class MigratePloneToIntranetWorkflow(ConditionalBlueprint):
    """Migrates 'plone/folder_workflow' to 'intranet[_folder]_workflow'"""
    def __iter__(self):
        context = self.transmogrifier.context
        wf_tool = api.portal.get_tool('portal_workflow')
        for item in self.previous:
            if self.condition(item):
                obj = resolve_object(context, item)

                try:
                    history = obj.workflow_history
                except AttributeError:
                    yield item
                    continue

                if 'folder_workflow' in history:
                    history['intranet_folder_workflow'] = \
                        intranet_folder_workflow(history)
                elif 'plone_workflow' in history:
                    history['intranet_workflow'] = \
                        intranet_workflow(history)
                for wf in wf_tool.getWorkflowsFor(obj):
                    wf.updateRoleMappingsFor(obj)

            yield item


# noinspection PyUnresolvedReferences
@configure.transmogrifier.blueprint.component(
    name='plone.workflow_history.plone_to_simple')
class MigratePloneToSimplePublicationWorkflow(ConditionalBlueprint):
    """Migrates 'plone/folder_workflow to simple_publication_workflow"""
    def __iter__(self):
        context = self.transmogrifier.context
        wf_tool = api.portal.get_tool('portal_workflow')
        for item in self.previous:
            if self.condition(item):
                obj = resolve_object(context, item)

                try:
                    history = obj.workflow_history
                except AttributeError:
                    yield item
                    continue

                if 'folder_workflow' in history:
                    history['simple_publication_workflow'] = \
                        simple_publication_workflow(history)
                elif 'plone_workflow' in history:
                    history['simple_publication_workflow'] = \
                        simple_publication_workflow(history)
                for wf in wf_tool.getWorkflowsFor(obj):
                    wf.updateRoleMappingsFor(obj)

            yield item
