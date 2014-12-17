from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint
from Products.Archetypes.config import UUID_ATTR
from plone.uuid.interfaces import IUUID
from plone.uuid.interfaces import IMutableUUID


@configure.transmogrifier.blueprint.component(name='plone.get_uuid')
class GetUUID(ConditionalBlueprint):
    def __iter__(self):
        key = self.options.get('key')
        for item in self.previous:
            if self.condition(item):
                ob = item.get(key)
                uuid = IUUID(ob, None)
                if uuid is not None:
                    item['_uid'] = uuid
            yield item


# sc/transmogrifier/sections/universal_uid_updater.py
# by jsbueno

@configure.transmogrifier.blueprint.component(name='plone.set_uuid')
class SetUUID(ConditionalBlueprint):
    """Sets UID for both AT and DX content types
    The UID blueprint in collective.transmogrifier
    can't deal with dexterity content.
    Other possible exiting blueprints can't deal with
    ATContent.
    One Blueprint to UID-up them all
    """
    def __iter__(self):
        for item in self.previous:
            if self.condition(item):
                self._set_uuid(item)
            yield item

    def _set_uuid(self, item):
            portal = self.transmogrifier.context
            path = "".join(portal.getPhysicalPath()) + item['_path']

            obj = portal.unrestrictedTraverse(path)
            uid = item.get('_uid')

            adapter = IMutableUUID(obj, None)
            if adapter is not None:
                # DX
                adapter.set(uid)
            else:
                # AT
                import pdb; pdb.set_trace()
                setattr(obj, UUID_ATTR, uid)

            # if not uid:
            #     import pdb; pdb.set_trace()

#           at_uid = ATIReferenceable.providedBy(obj)
#           dx_uid = DXIReferenceable.providedBy(obj)
#           old_uid = IUUID(obj, None)
#           if old_uid != uid:
#               # Code from plone.app.transmogrifier used for AT objects:
#               if at_uid:
#                   if not old_uid:
#                       setattr(obj, AT_UUID_ATTR, uid)
#                   else:
#                       obj._setUID(uid)
#               else:
#                   setattr(obj, DX_UID_ATTR, uid)
#               # else: #Don't ask, JUST DO IT!
                #     # If the attribute is not used as UID, it
                #     # is not used as anything else as well,
                #     # and at least the desired UID value stays recorded in the
                #     # object, allowing for a post-migration retrieval
                #     setattr(obj, DEFAULT_UID_ATTR, uid)

    # OPTIONS = [("uidkey", "_uid", "string")]

