# Installation

### 1. `base-manager.htm`

copy the `base-manager.htm` into the root of `templates` folder

### 2. `latest-edits.htm`

copy `latest-edits.htm` into `templates -> views`

### 3. `populate_latest_resource_edit_table.py`

copy `populate_latest_resource_edit_table.py` into `managment -> commands` folder

### 4. `latestresource.py` and `ciimchanges.py`

`latestresrouce.py` and `ciimchanges.py` into the root of `views` folder

### 5.  `urls.py`

add the following to `urls.py`:
    - under the imports add  `from .views.ciimchanges import ChangesView` and `from .views.latestresource import LatestEditLogView`
    - in urlpatterns add `url(r"^resource/changes", ChangesView.as_view(), name="ChangesView"` and `url(r"^resource/latest$", LatestEditLogView.as_view(), name="latest_edits"),`
    

### 6. `models.py`

in `models.py` found in `arches -> app -> models` add the following class just under the `EditLog` class

```
    class LatestResourceEdit(models.Model):
    editlogid = models.UUIDField(primary_key=True, default=uuid.uuid1)
    resourceinstanceid = models.TextField(blank=True, null=True)
    edittype = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "latest_resource_edit"
```

### 7. `tiles.py`

in `tiles.py` found in `arches -> app -> models` add the following `if` ad the end og the `save_edit` function

```
  if LatestResourceEdit.objects.filter(resourceinstanceid=self.resourceinstanceid, edittype = 'create').exists():
                if LatestResourceEdit.objects.filter(resourceinstanceid = self.resourceinstanceid).exclude(edittype = 'create').exists():
                    LatestResourceEdit.objects.filter(resourceinstanceid = self.resourceinstanceid).exclude(edittype = 'create').delete()
                #Delete old verions and add latest edit
                latest_edit = LatestResourceEdit()
                latest_edit.resourceinstanceid = self.resourceinstanceid
                latest_edit.timestamp = timestamp
                latest_edit.user_username = getattr(user, "username", "")
                latest_edit.edittype = edit_type
                latest_edit.resourcedisplayname =  Resource.objects.get(resourceinstanceid=self.resourceinstanceid).displayname
                latest_edit.save()

        else:
            latest_edit = LatestResourceEdit()
            latest_edit.resourceinstanceid = self.resourceinstanceid
            latest_edit.timestamp = timestamp
            latest_edit.edittype = edit_type
            latest_edit.user_username = getattr(user,"username", "")
            latest_edit.resourcedisplayname =  Resource.objects.get(resourceinstanceid=self.resourceinstanceid).displayname
            latest_edit.save()
```

### 8. `resource.py`

in `resource.py` found in `arches -> app -> models` add the folllowing `if` at the end of the `save_edit` function

```
if LatestResourceEdit.objects.filter(resourceinstanceid=self.resourceinstanceid).exists():
        LatestResourceEdit.objects.get(resourceinstanceid=self.resourceinstanceid).delete()
        
    latest_edit = LatestResourceEdit()
    latest_edit.resourceinstanceid = self.resourceinstanceid
    latest_edit.timestamp = timestamp
    latest_edit.edittype = edit_type
    latest_edit.save()
```

### 9. commands

Finally run the following commands

```
python manage.py makemigrations
python manage.py migrate
python manage populate_latest_resource_edit_table
```
### add 
from .views.latestresource import LatestEditLogView
    url(r"^resource/latest$", LatestEditLogView.as_view(), name="latest_edits"),
