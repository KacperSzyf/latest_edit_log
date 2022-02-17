#Imports
from functools import total_ordering, wraps
import math
from datetime import datetime
from time import perf_counter, time
from venv import create

from django.views.generic import View
from django.http import JsonResponse, HttpResponse

from arches.app.models.system_settings import settings
from arches.app.utils.betterJSONSerializer import JSONSerializer

from arches.app.models.resource import Resource
from arches.app.models.models import LatestResourceEdit

from arches.app.models.models import Concept as modelConcept
from arches.app.models.concept import Concept
from arches.app.utils.skos import SKOSWriter, SKOSReader

#Decorators
def timer(func):
    '''
    Description:
    Times how long a function takes to execute

    Returns:
    :tuple: Returns a tuple with the results of a function and the time taken to perform as last element ([-1])
    '''
    @wraps(func)
    def wrap(*args, **kwargs):
        time_start = time()
        result = (func(*args, **kwargs))
        total_time = (time() - time_start,) #Comma at the end makes the result a tuple
        return result + total_time #Concatinating a tuple 
    return wrap  

class ChangesView(View):

    def get(self, request):
        #Timer start
        start_time = time()

        #Functions
        @timer
        def get_data(from_date, to_date, per_page, page):
            '''
            Get all edited resources from selected page

            Returns:
            :tuple: Where [0] contains all ID's, [1] total of all ID's, [2] number of pages
            '''
            #Get all edits within time range and exclude system settings changes
            edits_queryset = LatestResourceEdit.objects.filter(timestamp__range=(from_date, to_date)).order_by('timestamp').exclude(resourceinstanceid=settings.SYSTEM_SETTINGS_RESOURCE_ID)

            #get the length of unique resourceinstanceid in edits queryset, flat=True prevents the list from being returned at one-tuple
            total_resources = len(list(set(edits_queryset.values_list('resourceinstanceid', flat=True))))

            #Paginate results
            no_pages = math.ceil(total_resources/per_page)
            edits = edits_queryset[(page-1)*per_page:page*per_page]

            return (edits, total_resources, no_pages, edits_queryset)
       
           
        # def temp_name():
       
#        "metadata": {
# "from": "2022-01-01T06:21:05",
# "to": "2022-02-05T03:37:39",
# "totalNumberOfResources": 3096,
# "perPage": 100,
# "page": 1,
# "numberOfPages": 31,
# "timeElapsed": {
# "total": 1.2531540393829346,
# "dbQuery": 0.022358179092407227,
# "dataDownload": 1.2307958602905273
# }
# },

#TODO: Break down into functions
        @timer
        def download_data(edits, edits_queryset):
            '''
            Get all data as json
            Returns:
            :tuple: Returns all json data in a d tuple 
            '''
            data = []
            resource_data = Resource.objects.all()

            for edit in edits:
                resourceid=edit.resourceinstanceid
                if resource_data.filter(pk=resourceid).exists():
                    resource = resource_data.get(pk=resourceid)
                    resource.load_tiles()
                    if not(len(resource.tiles) == 1 and not resource.tiles[0].data):
                        #Check if the tile has a creation even and an edit even
                        if edits_queryset.filter(resourceinstanceid = resourceid).count() > 1:
                            #Check if the edit source is not of type 'create' ie.  modification / update
                            if edit.edittype != 'create':
                                #If not add the currents edits time stamp to modified
                                resource_json= {'modified':edit.timestamp.strftime('%d-%m-%YT%H:%M:%SZ')}
                                #and fetch the log of when the record was created
                                create_event = edits_queryset.get(resourceinstanceid = resourceid, edittype = 'create')
                                #append the the created time to log
                                resource_json['created'] = create_event.timestamp.strftime('%d-%m-%YT%H:%M:%SZ')
                                resource_json.update(JSONSerializer().serializeToPython(resource))
                                if resource_json['displaydescription'] == '<Description>': resource_json['displaydescription'] = None
                                if resource_json['map_popup'] == '<Name_Type>': resource_json['map_popup'] = None
                                if resource_json['displayname'] == '<NMRW_Name>' : resource_json['displayname'] = None
                                data.append(resource_json)
                        #Just a creation type event
                        else:
                            resource_json = {'modified':edit.timestamp.strftime('%d-%m-%YT%H:%M:%SZ')}
                            resource_json['created'] = edit.timestamp.strftime('%d-%m-%YT%H:%M:%SZ')
                            resource_json.update(JSONSerializer().serializeToPython(resource))
                            if resource_json['displaydescription'] == '<Description>': resource_json['displaydescription'] = None
                            if resource_json['map_popup'] == '<Name_Type>': resource_json['map_popup'] = None
                            if resource_json['displayname'] == '<NMRW_Name>' : resource_json['displayname'] = None
                            data.append(resource_json)
                #Resource with no tiles
                else:
                    data.append({'modified':edit.timestamp,'resourceinstance_id':resourceid, 'tiles':None})


            return (data,)      

        #Process input
        #Dates
        from_date = request.GET.get('from')
        to_date = request.GET.get('to')
        from_date = datetime.strptime(from_date, '%d-%m-%YT%H:%M:%SZ')
        to_date = datetime.strptime(to_date, '%d-%m-%YT%H:%M:%SZ')

        #Pages
        per_page = int(request.GET.get('perPage'))
        page = int(request.GET.get('page'))

        #Data
        #db_data[x] =     0         1               2           3
        #               edits, total_resources, no_pages, edits_queryset
        db_data = get_data(from_date, to_date, per_page, page)
        json_data = download_data(db_data[0], db_data[3])

        end_time = time()
        
        #Dictionaries

        time_elapsed = {
            'total' : db_data[-1]  + json_data[-1],
            'dbQuery': db_data[-1],
            'dataDownload': json_data[-1]
            }

        metadata = {
            'from': from_date,
            'to': to_date,
            'totalNumberOfResources': db_data[1],
            'perPage': per_page,
            'page': page,
            'numberOfPages': db_data[2],
            'timeElapsed': time_elapsed
        }

        response = {'metadata': metadata, 'results':json_data[0]}

        return JsonResponse(response, json_dumps_params={'indent': 2})

# download and append all xml thesauri
class ConceptsExportView(View):
    def get(self, request):
        conceptids = [str(c.conceptid) for c in modelConcept.objects.filter(nodetype='ConceptScheme')]
        concept_graphs = []
        for conceptid in conceptids:
            print(conceptid)
            concept_graphs.append(Concept().get(
                id=conceptid,
                include_subconcepts=True,
                include_parentconcepts=False,
                include_relatedconcepts=True,
                depth_limit=None,
                up_depth_limit=None))
        return HttpResponse(SKOSWriter().write(concept_graphs, format="pretty-xml"), content_type="application/xml")