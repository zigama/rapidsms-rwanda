
from rapidsms.webui.utils import render_to_response
from models import *
from datetime import datetime, timedelta
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth.decorators import permission_required

@permission_required('reports.can_view')
@require_http_methods(["GET"])
def index(req):
    template_name="logger/index.html"
    incoming = IncomingMessage.objects.order_by('-received')
    outgoing = OutgoingMessage.objects.order_by('-sent')
    all = []
    [ all.append(msg) for msg in incoming[0:100] ]
    [ all.append(msg) for msg in outgoing[0:100] ]
    # sort by date, descending
    all.sort(lambda x, y: cmp(y.date, x.date))
    return render_to_response(req, template_name, { "messages": all})

