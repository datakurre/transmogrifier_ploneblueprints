from venusianconfiguration import configure
from transmogrifier.blueprints import Blueprint
from transmogrifier.blueprints import ConditionalBlueprint
from Products.Archetypes.interfaces import IReferenceable as \
    ATIReferenceable
from Products.Archetypes.config import UUID_ATTR as AT_UID_ATTR
from plone.app.referenceablebehavior.referenceable import IReferenceable as \
    DXIReferenceable
from plone.uuid.interfaces import ATTRIBUTE_NAME as DX_UID_ATTR, IUUID


@configure.transmogrifier.blueprint.component(name='plone.get_uuid')
class GetUUID(ConditionalBlueprint):
    def __iter__(self):
        key = self.options.get('key')
        for item in self.previous:
            if self.condition(item):
                ob = item.get(key)
                if ob is not None and IUUID.providedBy(ob):
                    item['_uid'] = IUUID(ob)
            yield item


# sc/transmogrifier/sections/universal_uid_updater.py
#by jsbueno

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

            # if not uid:
            #     import pdb; pdb.set_trace()

            at_uid = ATIReferenceable.providedBy(obj)
            dx_uid = DXIReferenceable.providedBy(obj)
            try:
                old_uid = IUUID(obj)
            except TypeError:
                import pdb; pdb.set_trace()
            if old_uid != uid:
                # Code from plone.app.transmogrifier used for AT objects:
                if at_uid:
                    if not old_uid:
                        setattr(obj, AT_UUID_ATTR, uid)
                    else:
                        obj._setUID(uid)
                else:
                    setattr(obj, DX_UID_ATTR, uid)
                # else: #Don't ask, JUST DO IT!
                #     # If the attribute is not used as UID, it
                #     # is not used as anything else as well,
                #     # and at least the desired UID value stays recorded in the
                #     # object, allowing for a post-migration retrieval
                #     setattr(obj, DEFAULT_UID_ATTR, uid)

    # OPTIONS = [("uidkey", "_uid", "string")]

