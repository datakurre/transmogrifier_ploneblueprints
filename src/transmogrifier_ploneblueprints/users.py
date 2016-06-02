# -*- coding: utf-8 -*-
from plone import api
from transmogrifier.blueprints import Blueprint
from transmogrifier.blueprints import ConditionalBlueprint
from venusianconfiguration import configure


@configure.transmogrifier.blueprint.component(name='plone.users.get')
class GetUsers(Blueprint):
    def __iter__(self):
        for item in self.previous:
            yield item

        portal = api.portal.get()
        pas = portal.acl_users
        source_users = pas.source_users

        for user_id in source_users.getUserIds():
            properties = pas['mutable_properties']._storage.get(user_id)
            roles = pas.portal_role_manager._principal_roles.get(user_id)

            # ensure isUser is True, properties is None for default users
            if properties is not None:
                properties['isGroup'] = False

            item = {
                'id': user_id,
                'login': source_users.getLoginForUserId(user_id),
                'properties': properties,
                'roles': roles
            }
            yield item


@configure.transmogrifier.blueprint.component(name='plone.users.set')
class SetUsers(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        pas = portal.acl_users

        for item in self.previous:
            if self.condition(item):
                user_id = item['id']
                login = item['login']
                roles = item['roles']
                properties = item['properties']

                if user_id not in pas.source_users.getUserIds():
                    pas.source_users.addUser(user_id, login, '')

                pas.portal_role_manager.assignRolesToPrincipal(roles,
                                                               user_id)

                # properties None for default users
                if properties is not None:
                    pas.mutable_properties._storage[user_id] = properties

            yield item
