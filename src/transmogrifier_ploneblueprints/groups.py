# -*- coding: utf-8 -*-
from plone import api
from transmogrifier.blueprints import Blueprint
from venusianconfiguration import configure


@configure.transmogrifier.blueprint.component(name='plone.groups.get')
class GetGroups(Blueprint):
    def __iter__(self):
        for item in self.previous:
            yield item

        portal = api.portal.get()
        groups = portal.acl_users.source_groups.getGroupIds()
        
        for group_id in groups:
            group = api.group.get(group_id)
            if group is None:
                continue

            item = {}
            item['name'] = group_id
            item['members'] = [(member.getUserName(), 
                                member.getProperty('email')) 
                               for member in group.getGroupMembers()]
            yield item 
