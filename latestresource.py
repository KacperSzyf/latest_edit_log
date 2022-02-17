#Imports
import uuid

#Django
from django.views.generic import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.shortcuts import render
from django.utils.translation import ugettext as _

#Core Arches
from arches.app.models.system_settings import settings
from arches.app.utils.betterJSONSerializer import JSONSerializer
from arches.app.utils.decorators import can_edit_resource_instance
from arches.app.models import models
from arches.app.models.resource import Resource
from arches.app.models.card import Card
from arches.app.views.base import BaseManagerView

#Decorators
@method_decorator(can_edit_resource_instance, name="dispatch")
class LatestEditLogView(BaseManagerView):
    def getEditConceptValue(self, values):
        if values is not None:
            for k, v in values.items():
                try:
                    uuid.UUID(v)
                    v = models.Value.objects.get(pk=v).value
                    values[k] = v
                except Exception as e:
                    pass
                try:
                    display_values = []
                    for val in v:
                        uuid.UUID(val)
                        display_value = models.Value.objects.get(pk=val).value
                        display_values.append(display_value)
                    values[k] = display_values
                except Exception as e:
                    pass

    def get(self, request, resourceid=None, view_template="views/resource/edit-log.htm"):
        if resourceid is None:
            recent_edits = (
                models.LatestResourceEdit.objects.all()
                .order_by("-timestamp")[:100]
            )
            edited_ids = list({edit.resourceinstanceid for edit in recent_edits})
            resources = Resource.objects.filter(resourceinstanceid__in=edited_ids)
            edit_type_lookup = {
                "create": _("Resource Created"),
                "delete": _("Resource Deleted"),
                "tile delete": _("Tile Deleted"),
                "tile create": _("Tile Created"),
                "tile edit": _("Tile Updated"),
                "delete edit": _("Edit Deleted"),
                "bulk_create": _("Resource Created"),
            }
            deleted_instances = [e.resourceinstanceid for e in recent_edits if e.edittype == "delete"]
            graph_name_lookup = {str(r.resourceinstanceid): r.graph.name for r in resources}
            for edit in recent_edits:
                edit.friendly_edittype = edit_type_lookup[edit.edittype]
                edit.resource_model_name = None
                edit.deleted = edit.resourceinstanceid in deleted_instances
                if edit.resourceinstanceid in graph_name_lookup:
                    edit.resource_model_name = graph_name_lookup[edit.resourceinstanceid]

            context = self.get_context_data(main_script="views/latest-edits", recent_edits=recent_edits)

            context["nav"]["title"] = _("Latest Edits")

            return render(request, "views/latest-edits.htm", context)
        else:
            resource_instance = models.ResourceInstance.objects.get(pk=resourceid)
            edits = models.LatestResourceEdit.objects.filter(resourceinstanceid=resourceid)
            permitted_edits = []
            for edit in edits:
                if edit.nodegroupid is not None:
                    if request.user.has_perm("read_nodegroup", edit.nodegroupid):
                        if edit.newvalue is not None:
                            self.getEditConceptValue(edit.newvalue)
                        if edit.oldvalue is not None:
                            self.getEditConceptValue(edit.oldvalue)
                        permitted_edits.append(edit)
                else:
                    permitted_edits.append(edit)

            resource = Resource.objects.get(pk=resourceid)
            displayname = resource.displayname
            displaydescription = resource.displaydescription
            cards = Card.objects.filter(nodegroup__parentnodegroup=None, graph=resource_instance.graph)
            graph_name = resource_instance.graph.name
            if displayname == "undefined":
                displayname = _("Unnamed Resource")

            context = self.get_context_data(
                main_script="views/resource/edit-log",
                cards=JSONSerializer().serialize(cards),
                resource_type=graph_name,
                resource_description=displaydescription,
                iconclass=resource_instance.graph.iconclass,
                edits=JSONSerializer().serialize(permitted_edits),
                resourceid=resourceid,
                displayname=displayname,
            )

            context["nav"]["res_edit"] = True
            context["nav"]["icon"] = resource_instance.graph.iconclass
            context["nav"]["title"] = graph_name

            return render(request, view_template, context)

        return HttpResponseNotFound()