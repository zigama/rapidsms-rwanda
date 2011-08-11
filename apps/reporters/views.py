#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
import csv
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseServerError
from django.template import RequestContext
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404
from django.db import transaction

from rapidsms.webui.utils import *
from reporters.models import *
from ubuzima.models import *
from ubuzima.views import *
from locations.models import *
from logger.models import *
from reporters.utils import *


def message(req, msg, link=None):
    return render_to_response(req,
        "message.html", {
            "message": msg,
            "link": link
    })


@permission_required('reporters.can_view')
@require_GET
def index(req):
    return render_to_response(req,
        "reporters/index.html", {"locations":Location.objects.filter(type__name__in=['Province','District','Hospital','Health Centre']),
        "reporters": paginated(req, Reporter.objects.all(), prefix="rep"),
        "groups":    paginated(req, ReporterGroup.objects.flatten(), prefix="grp"),
    })

def reporters_by_location(req,pk):
    location = get_object_or_404(Location, pk=pk)
    locations=Location.descendants(location)
    
    if len(locations)==0:
        repos=Reporter.objects.filter(location=location)
    else:
        repos=Reporter.objects.filter(location__in=locations)
    return render_to_response(req,
        "reporters/index.html", {"chws":len(repos.filter(groups__title='CHW')),"sups":len(repos.filter(groups__title='Supervisor')),
        "locations":Location.objects.filter(type__name__in=['Province','District','Hospital','Health Centre']),
        "location":location,
        "reporters": paginated(req,repos , prefix="rep"),
        "groups":    paginated(req, ReporterGroup.objects.flatten(), prefix="grp")
    })

def find_reporter(req):
    conn=get_object_or_404(PersistantConnection, identity='+25'+req.REQUEST['repid'])    
    reporter = get_object_or_404(Reporter, pk=conn.reporter.pk)
    ans=[]
    if reporter:
        ans.append(reporter)
    return render_to_response(req,
        "reporters/index.html", {
        "locations":Location.objects.filter(type__name__in=['Province','District','Hospital','Health Centre']),
        "reporters": paginated(req, ans , prefix="rep"),
        "groups":    paginated(req, ReporterGroup.objects.flatten(), prefix="grp"),
    })

#Inactive reporters
def default_reporter_location(req):
    try:
        dst = int(req.REQUEST['district'])
        loc = int(req.REQUEST['location']) if req.REQUEST.has_key('location') else 1
        reps = matching_reporters(req, True).select_related('location')
        return Location.objects.filter(type__id=5,id__in = [x.location.id for x in \
                reps]).extra(select = {'selected':'id = %d' % (loc,)}).order_by('name')
    except KeyError:
        return []

def matching_reporters(req, alllocs = False):
    rez = {}
    pst = None
    
    try:
        if alllocs: raise KeyError
        loc = int(req.REQUEST['location'])
        rez['location__id'] = loc
    except KeyError:
        try:
            lox = LocationShorthand.objects.filter(district = int(req.REQUEST['district']))
            rez['location__in'] = [x.original for x in lox]
        except KeyError:
            try:
                lox = LocationShorthand.objects.filter(province = int(req.REQUEST['province']))
                rez['location__in'] = [x.original for x in lox]
            except KeyError:
                pass
    if rez:
        ans = Reporter.objects.filter(**rez)
    else:
       ans = Reporter.objects.all()
	
    if pst:
        ans = ans.filter(pst)
    return ans


def inactive_reporters(rez):
    inactive_reps=[]
    reps=Reporter.objects.filter(groups__title='CHW',**rez)
    for rep in reps:
        if rep.is_expired():
            inactive_reps.append(rep)
    return inactive_reps
#end of inactive reporters
#Active reporters
def active_reporters(rez):
    active_reps=[]
    reps=Reporter.objects.filter(groups__title='CHW',**rez).order_by('id')
    for rep in reps:
        if rep.is_expired():
            pass
        elif rep.last_seen():
            active_reps.append(rep)
    return active_reps

def view_active_reporters(req,**flts):
    
    filters = {'period':default_period(req),
             'location':default_reporter_location(req),
             'province':default_province(req),
             'district':default_district(req)}
    lox, lxn = 0, location_name(req)
    if req.REQUEST.has_key('location') and req.REQUEST['location'] != '0':
        lox = int(req.REQUEST['location'])
        lxn = Location.objects.get(id = lox)
        lxn=lxn.name+' '+lxn.type.name+', '+lxn.parent.parent.name+' '+lxn.parent.parent.type.name+', '+lxn.parent.parent.parent.name+' '+lxn.parent.parent.parent.type.name
    rez=match_inactive(req,filters)
    return render_to_response(req,
        "reporters/active.html", {
        "reporters": paginated(req, active_reporters(rez), prefix="rep"),'start_date':date.strftime(filters['period']['start'], '%d.%m.%Y'),
         'end_date':date.strftime(filters['period']['end'], '%d.%m.%Y'),'filters':filters,'locationname':lxn,'postqn':(req.get_full_path().split('?', 2) + [''])[1]
          })
#end of active reporters

#View inactive reporters
def view_inactive_reporters(req,**flts):
    
    filters = {'period':default_period(req),
             'location':default_reporter_location(req),
             'province':default_province(req),
             'district':default_district(req)}
    lox, lxn = 0, location_name(req)
    if req.REQUEST.has_key('location') and req.REQUEST['location'] != '0':
        lox = int(req.REQUEST['location'])
        lxn = Location.objects.get(id = lox)
        lxn=lxn.name+' '+lxn.type.name+', '+lxn.parent.parent.name+' '+lxn.parent.parent.type.name+', '+lxn.parent.parent.parent.name+' '+lxn.parent.parent.parent.type.name
    rez=match_inactive(req,filters)
    return render_to_response(req,
        "reporters/inactive.html", {
        "reporters": paginated(req, inactive_reporters(rez), prefix="rep"),'start_date':date.strftime(filters['period']['start'], '%d.%m.%Y'),
         'end_date':date.strftime(filters['period']['end'], '%d.%m.%Y'),'filters':filters,'locationname':lxn,'postqn':(req.get_full_path().split('?', 2) + [''])[1]
          })

def view_inactive_reporters_csv(req,**flts):
    filters = {'period':default_period(req),
             'location':default_reporter_location(req),
             'province':default_province(req),
             'district':default_district(req)}
    lox, lxn = 0, location_name(req)
    if req.REQUEST.has_key('location') and req.REQUEST['location'] != '0':
        lox = int(req.REQUEST['location'])
        lxn = Location.objects.get(id = lox)
        lxn=lxn.name+' '+lxn.type.name+', '+lxn.parent.parent.name+' '+lxn.parent.parent.type.name+', '+lxn.parent.parent.parent.name+' '+lxn.parent.parent.parent.type.name
    rez=match_inactive(req,filters)
    
    rsp = HttpResponse()
    rsp['Content-Type'] = 'text/csv; encoding=%s' % (getdefaultencoding(),)
    wrt = csv.writer(rsp, dialect = 'excel-tab')
    wrt.writerows([[x.pk,x.connection().identity,x.alias,x.location,x.last_seen(),[ str(y.connection().identity) for y in x.reporter_sups()] ] for x in inactive_reporters(rez)])
    return rsp
#end of viewing inactive reporters
def match_inactive(req,diced,alllocs=False):
    rez = {}
    pst = None
    
    try:
        if alllocs: raise KeyError
        loc = int(req.REQUEST['location'])
        rez['location__id'] = loc
    except KeyError:
        try:
            lox = LocationShorthand.objects.filter(district = int(req.REQUEST['district']))
            rez['location__in'] = [x.original for x in lox]
        except KeyError:
            try:
                lox = LocationShorthand.objects.filter(province = int(req.REQUEST['province']))
                rez['location__in'] = [x.original for x in lox]
            except KeyError:
                pass

    return rez

def inactive_reporters_location(req,pk):
    location = get_object_or_404(Location, pk=pk)
    reps=inactive_reporters()
    ans=[]
    for an in reps:
        if an.location==location:
            ans.append(an)
    return render_to_response(req,
        "reporters/inactive.html", {
        "reporters": paginated(req,ans, prefix="rep"),
          })

def inactive_reporters_sup(req,pk):
    sup = get_object_or_404(Reporter, pk=pk)
    reps=inactive_reporters()
    ans=[]
    for an in reps:
        if sup in an.reporter_sups():
            ans.append(an)
    return render_to_response(req,
        "reporters/inactive.html", {
        "reporters": paginated(req,ans, prefix="rep"),
          })

def check_reporter_form(req):
    
    # verify that all non-blank
    # fields were provided
    missing = [
        field.verbose_name
        for field in Reporter._meta.fields
        if req.POST.get(field.name, "") == ""
           and field.blank == False]
    
    # TODO: add other validation checks,
    # or integrate proper django forms
    return {
        "missing": missing }


def update_reporter(req, rep):
    
    # as default, we will delete all of the connections
    # and groups from this reporter. the loops will drop
    # objects that we SHOULD NOT DELETE from these lists
    del_conns = list(rep.connections.values_list("pk", flat=True))
    del_grps = list(rep.groups.values_list("pk", flat=True))


    # iterate each of the connection widgets from the form,
    # to make sure each of them are linked to the reporter
    connections = field_bundles(req.POST, "conn-backend", "conn-identity")
    for be_id, identity in connections:
        
        # skip this pair if either are missing
        if not be_id or not identity:
            continue
        
        # create the new connection - this could still
        # raise a DoesNotExist (if the be_id is invalid),
        # or an IntegrityError or ValidationError (if the
        # identity or report is invalid)
        conn, created = PersistantConnection.objects.get_or_create(
            backend=PersistantBackend.objects.get(pk=be_id),
            identity=identity)
        
        # update the reporter separately, in case the connection
        # exists, and is already linked to another reporter
        conn.reporter = rep
        conn.save()
        
        # if this conn was already
        # linked, don't delete it!
        if conn.pk in del_conns:
            del_conns.remove(conn.pk)


    # likewise for the group objects
    groups = field_bundles(req.POST, "group")	
    for grp_id, in groups:
        
        # skip this group if it's empty
        # (an empty widget is displayed as
        # default, which may be ignored here)
        if not grp_id:
            continue
        
        # link this group to the reporter
        grp = ReporterGroup.objects.get(pk=grp_id)
        rep.groups.add(grp)
        
        # if this group was already
        # linked, don't delete it!
        if grp.pk in del_grps:
            del_grps.remove(grp.pk)
    
    
    # delete all of the connections and groups 
    # which were NOT in the form we just received
    rep.connections.filter(pk__in=del_conns).delete()
    rep.groups.filter(pk__in=del_grps).delete()

@permission_required('reporters.can_view')
def error_list(req,**flts):
    filters = {'period':default_period(req),
             'location':default_reporter_location(req),
             'province':default_province(req),
             'district':default_district(req)}
    lox, lxn = 0, location_name(req)
    if req.REQUEST.has_key('location') and req.REQUEST['location'] != '0':
        lox = int(req.REQUEST['location'])
        lxn = Location.objects.get(id = lox)
        lxn=lxn.name+' '+lxn.type.name+', '+lxn.parent.parent.name+' '+lxn.parent.parent.type.name+', '+lxn.parent.parent.parent.name+' '+lxn.parent.parent.parent.type.name
    rez={}
    l=match_inactive(req,filters)
    
    if 'location__id' in l.keys(): rez['errby__location__id']=l['location__id']
    elif 'location__in' in l.keys(): rez['errby__location__in']=l['location__in']
    try:
        rez['created__gte'] = filters['period']['start']
        rez['created__lte'] = filters['period']['end']+timedelta(1)
    except KeyError:
        pass
    return render_to_response(req,
        'reporters/errors.html', {
        'errors': paginated(req, ErrorNote.objects.filter(**rez).order_by('-created'), prefix='err'),'start_date':date.strftime(filters['period']['start'], '%d.%m.%Y'),
         'end_date':date.strftime(filters['period']['end'], '%d.%m.%Y'),'l':l,'filters':filters,'locationname':lxn,'postqn':(req.get_full_path().split('?', 2) + [''])[1]
    })

@permission_required('reporters.can_view')
def error_list_csv(req,**flts):
    filters = {'period':default_period(req),
             'location':default_reporter_location(req),
             'province':default_province(req),
             'district':default_district(req)}
    lox, lxn = 0, location_name(req)
    if req.REQUEST.has_key('location') and req.REQUEST['location'] != '0':
        lox = int(req.REQUEST['location'])
        lxn = Location.objects.get(id = lox)
        lxn=lxn.name+' '+lxn.type.name+', '+lxn.parent.parent.name+' '+lxn.parent.parent.type.name+', '+lxn.parent.parent.parent.name+' '+lxn.parent.parent.parent.type.name
    rez={}
    l=match_inactive(req,filters)
    
    if 'location__id' in l.keys(): rez['errby__location__id']=l['location__id']
    elif 'location__in' in l.keys(): rez['errby__location__in']=l['location__in']
    try:
        rez['created__gte'] = filters['period']['start']
        rez['created__lte'] = filters['period']['end']+timedelta(1)
    except KeyError:
        pass
    rsp     = HttpResponse()
    rsp['Content-Type'] = 'text/csv; encoding=%s' % (getdefaultencoding(),)
    wrt = csv.writer(rsp, dialect = 'excel-tab')
    wrt.writerows([[r.errby.connection().identity, r.errmsg, r.errby.location, r.created] for r in ErrorNote.objects.filter(**rez).order_by('-created')])
    return rsp

    

@require_http_methods(["GET", "POST"])
def add_reporter(req):
    def get(req):
        
        # maybe pre-populate the "connections" field
        # with a connection object to convert into a
        # reporter, if provided in the query string
        connections = []
        if "connection" in req.GET:
            connections.append(
                get_object_or_404(
                    PersistantConnection,
                    pk=req.GET["connection"]))
        
        return render_to_response(req,
            "reporters/reporter.html", {
                
                # display paginated reporters in the left panel
                "reporters": paginated(req, Reporter.objects.all()),
                
                # maybe pre-populate connections
                "connections": connections,
                
                # list all groups + backends in the edit form
                "all_groups": ReporterGroup.objects.flatten(),
                "all_backends": PersistantBackend.objects.all() })

    @transaction.commit_manually
    def post(req):
        
        # check the form for errors
        errors = check_reporter_form(req)
        
        # if any fields were missing, abort. this is
        # the only server-side check we're doing, for
        # now, since we're not using django forms here
        if errors["missing"]:
            transaction.rollback()
            return message(req,
                "Missing Field(s): %s" %
                    ", ".join(missing),
                link="/reporters/add")
        
        try:
            # create the reporter object from the form
            rep = insert_via_querydict(Reporter, req.POST)
            rep.save()
            
            # every was created, so really
            # save the changes to the db
            update_reporter(req, rep)
            transaction.commit()
            
            # full-page notification
            return message(req,
                "Reporter %d added" % (rep.pk),
                link="/reporters")
        
        except Exception, err:
            transaction.rollback()
            raise
    
    # invoke the correct function...
    # this should be abstracted away
    if   req.method == "GET":  return get(req)
    elif req.method == "POST": return post(req)


@require_http_methods(["GET", "POST"])  
def edit_reporter(req, pk):
    rep = get_object_or_404(Reporter, pk=pk)
    
    def get(req):
        return render_to_response(req,
            "reporters/reporter.html", {
                
                # display paginated reporters in the left panel
                "reporters": paginated(req, Reporter.objects.all()),

                #   Errors in the right. (Revence)
                'errors': paginated(req, ErrorNote.objects.filter(errby = rep).order_by('-created'), prefix='err'),
                "locations":Location.objects.filter(type__name__in=['Province','District','Hospital','Health Centre']),
                # list all groups + backends in the edit form
                "all_groups": ReporterGroup.objects.flatten(),
                "all_backends": PersistantBackend.objects.all(),
                
                # split objects linked to the editing reporter into
                # their own vars, to avoid coding in the template
                "connections": rep.connections.all(),
                "groups":      rep.groups.all(),
                "reporter":    rep })
    
    @transaction.commit_manually
    def post(req):
        
        # if DELETE was clicked... delete
        # the object, then and redirect
        if req.POST.get("delete", ""):
            pk = rep.pk
            rep.delete()
            
            transaction.commit()
            return message(req,
                "Reporter %d deleted" % (pk),
                link="/reporters")
                
        else:
            # check the form for errors (just
            # missing fields, for the time being)
            errors = check_reporter_form(req)
            
            # if any fields were missing, abort. this is
            # the only server-side check we're doing, for
            # now, since we're not using django forms here
            if errors["missing"]:
                transaction.rollback()
                return message(req,
                    "Missing Field(s): %s" %
                        ", ".join(errors["missing"]),
                    link="/reporters/%s" % (rep.pk))
            
            try:
                # automagically update the fields of the
                # reporter object, from the form
                update_via_querydict(rep, req.POST).save()
                update_reporter(req, rep)
                
                # no exceptions, so no problems
                # commit everything to the db
                transaction.commit()
                
                # full-page notification
                return message(req,
                    "Reporter %d updated" % (rep.pk),
                    link="/reporters")
            
            except Exception, err:
                transaction.rollback()
                raise
        
    # invoke the correct function...
    # this should be abstracted away
    if   req.method == "GET":  return get(req)
    elif req.method == "POST": return post(req)


@require_http_methods(["GET", "POST"])
def add_group(req):
    if req.method == "GET":
        return render_to_response(req,
            "reporters/group.html", {
                "all_groups": ReporterGroup.objects.flatten(),
                "groups": paginated(req, ReporterGroup.objects.flatten()) })
        
    elif req.method == "POST":
        
        # create a new group using the flat fields,
        # then resolve and update the parent group
        # TODO: resolve foreign keys in i_via_q
        grp = insert_via_querydict(ReporterGroup, req.POST)
        parent_id = req.POST.get("parent_id", "")
        if parent_id:
            grp.parent = get_object_or_404(
                ReporterGroup, pk=parent_id)
        
        grp.save()
        
        return message(req,
            "Group %d added" % (grp.pk),
            link="/reporters")


@require_http_methods(["GET", "POST"])
def edit_group(req, pk):
    grp = get_object_or_404(ReporterGroup, pk=pk)
    
    if req.method == "GET":
        
        # fetch all groups, to be displayed
        # flat in the "parent group" field
        all_groups = ReporterGroup.objects.flatten()
        
        # iterate the groups, to mark one of them
        # as selected (the editing group's parent)
        for this_group in all_groups:
            if grp.parent == this_group:
                this_group.selected = True
        
        return render_to_response(req,
            "reporters/group.html", {
                "groups": paginated(req, ReporterGroup.objects.flatten()),
                "all_groups": all_groups,
                "group": grp })
    
    elif req.method == "POST":
        # if DELETE was clicked... delete
        # the object, then and redirect
        if req.POST.get("delete", ""):
            pk = grp.pk
            grp.delete()
            
            return message(req,
                "Group %d deleted" % (pk),
                link="/reporters")

        # otherwise, update the flat fields of the group
        # object, then resolve and update the parent group
        # TODO: resolve foreign keys in u_via_q
        else:
            update_via_querydict(grp, req.POST)
            parent_id = req.POST.get("parent_id", "")
            if parent_id:
                grp.parent = get_object_or_404(
                    ReporterGroup, pk=parent_id)
            
            # if no parent_id was passed, we can assume
            # that the field was cleared, and remove it
            else: grp.parent = None
            grp.save()
            
            return message(req,
                "Group %d saved" % (grp.pk),
                link="/reporters")
