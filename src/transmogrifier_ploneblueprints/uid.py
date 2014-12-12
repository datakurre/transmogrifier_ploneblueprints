from venusianconfiguration import configure
from transmogrifier.blueprints import Blueprint
from Products.Archetypes.interfaces import IReferenceable as \
    ATIReferenceable
from Products.Archetypes.config import UUID_ATTR as AT_UID_ATTR
from plone.app.referenceablebehavior.referenceable import IReferenceable as \
    DXIReferenceable
from plone.uuid.interfaces import ATTRIBUTE_NAME as DX_UID_ATTR, IUUID

# sc/transmogrifier/sections/universal_uid_updater.py
#by jsbueno


@configure.transmogrifier.blueprint.component(name='plone.uid')
class UniversalUIDUpdater(Blueprint):
    """Sets UID for both AT and DX content types
    The UID blueprint in collective.transmogrifier
    can't deal with dexterity content.
    Other possible exiting blueprints can't deal with
    ATContent.
    One Blueprint to UID-up them all
    """
    def __iter__(self):
        for item in self.previous:

            portal = self.transmogrifier.context
            path = "".join(portal.getPhysicalPath()) + item['_path']

            if isinstance(path, unicode):
                path = path.encode('UTF-8')

            obj = portal.unrestrictedTraverse(path)
            uid = item.get('_uid')

            if not uid:
                pass

            at_uid = ATIReferenceable.providedBy(obj)
            dx_uid = DXIReferenceable.providedBy(obj)

            old_uid = IUUID(obj)
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

            yield item

    # OPTIONS = [("uidkey", "_uid", "string")]

