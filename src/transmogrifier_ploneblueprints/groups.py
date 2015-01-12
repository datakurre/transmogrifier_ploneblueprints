# -*- coding: utf-8 -*-
from plone import api
from transmogrifier.blueprints import Blueprint, ConditionalBlueprint
from venusianconfiguration import configure


@configure.transmogrifier.blueprint.component(name='plone.groups.get')
class GetGroups(Blueprint):
    def __iter__(self):
        for item in self.previous:
            yield item
       
        portal = api.portal.get()
        pas = portal.acl_users
        source_groups = pas.source_groups

        for group_id in source_groups.getGroupIds():
            properties = pas['mutable_properties']._storage.get(group_id)
            roles = pas.portal_role_manager._principal_roles.get(group_id)
            members = source_groups.getGroupMembers(group_id)

            # ensure isGroup is True, properties is None for default groups
            if properties is not None:
                properties['isGroup'] = True

            item = {
                'id': group_id,
                'properties': properties,
                'roles': roles,
                'members': members
            }
            yield item

@configure.transmogrifier.blueprint.component(name='plone.groups.set')
class SetGroups(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        pas = portal.acl_users
        
        for item in self.previous:
            if self.condition(item):
                group_id = item['id']
                roles = item['roles']
                members = item['members']
                properties = item['properties']
               
                if group_id not in pas.source_groups.getGroupIds():
                    pas.source_groups.addGroup(group_id)

                pas.portal_role_manager.assignRolesToPrincipal(roles, 
                                                               group_id)

                for member in members:
                    pas.source_groups.addPrincipalToGroup(member, group_id)

                # properties None for default groups
                if properties is not None:
                    pas.mutable_properties._storage[group_id] = properties
                    pas.source_groups.updateGroup(group_id, 
                                                  properties['title'], 
                                                  properties['description'])
            yield item
