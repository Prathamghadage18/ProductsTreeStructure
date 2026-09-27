from urllib.parse import unquote
import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import FormView
from rest_framework.decorators import api_view
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q

from .forms import NoteForm
from .models import AllowedUser, ExcelUploadTracker, Node, Note
from .permissions import allowed_user_required
from .serializers import UploadSerializer
from .utils import build_tree_from_excel, populate_nodes_from_excel, get_fault_schema, get_keywords_for, split_path_preserving_brackets


def _add_notes_to_tree(tree_nodes):
    """
    Recursively add notes information to tree nodes.
    tree_nodes can be a list of root nodes or a single node.
    """
    notes_data = {}
    for note in Note.objects.select_related('node').all():
        notes_data[note.node.node_id] = {
            'has_content': bool(note.content_without_metadata().strip()),
            'content': note.content_without_metadata()
        }

    def _add_notes_recursive(node):
        node_id = node.get('id', '')
        if node_id in notes_data:
            node['note'] = notes_data[node_id]['content'] if notes_data[node_id]['has_content'] else ""
        else:
            node['note'] = ""
        if 'children' in node:
            for child in node['children']:
                _add_notes_recursive(child)

    if isinstance(tree_nodes, list):
        for node in tree_nodes:
            _add_notes_recursive(node)
    else:
        _add_notes_recursive(tree_nodes)

@ensure_csrf_cookie
@allowed_user_required
def sensor_tree_view(request):
    return render(request, 'sensor_tree.html', {
        'user': request.user,
        'is_superuser': request.user.is_superuser
    })

@login_required
def tree_from_file(request):
    """Deprecated: path-based Excel loading is no longer supported."""
    return JsonResponse(
        {
            "error": "Loading Excel files by path is no longer supported. Upload an Excel file instead.",
            "code": "path_upload_deprecated",
        },
        status=410,
    )

def ping(request):
    return JsonResponse({"status": "ok"})


def user_login(request):
    """
    Custom login view that checks if user is allowed (predefined normal user or superuser).
    Redirects to tree view on successful login.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user is superuser or in allowed users list
            if user.is_superuser or AllowedUser.objects.filter(user=user).exists():
                login(request, user)
                messages.success(request, f'Welcome, {user.username}!')
                # Redirect to sensor tree visualization
                return redirect('sensor-tree')
            else:
                messages.error(request, 'You are not authorized to access this system.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login.html')


def user_logout(request):
    """
    Logout view.
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def get_tree_data(request):
    """
    Returns hierarchical tree data from the database as an array of manufacturer nodes.
    """
    if not request.user.is_superuser and not AllowedUser.objects.filter(user=request.user).exists():
        return JsonResponse({"error": "Not authorized"}, status=403)
    
    try:
        node_ids = Node.objects.all().values_list('node_id', flat=True)

        if not node_ids:
            return JsonResponse([], safe=False)

        manufacturers = {}

        notes_data = {}
        for note in Note.objects.select_related('node').all():
            notes_data[note.node.node_id] = {
                'has_content': bool(note.content_without_metadata().strip()),
                'content': note.content_without_metadata()
            }

        for node_id in node_ids:
            parts = split_path_preserving_brackets(node_id)

            if not parts:
                continue

            manufacturer_name = parts[0]

            if manufacturer_name not in manufacturers:
                manufacturers[manufacturer_name] = {
                    "id": manufacturer_name,
                    "name": manufacturer_name,
                    "type": "manufacturer",
                    "children": []
                }
                if manufacturer_name in notes_data:
                    manufacturers[manufacturer_name]["note"] = notes_data[manufacturer_name]['content'] if notes_data[manufacturer_name]['has_content'] else ""
                else:
                    manufacturers[manufacturer_name]["note"] = ""

            current = manufacturers[manufacturer_name]
            current_path = manufacturer_name

            for i in range(1, len(parts)):
                part = parts[i]
                current_path = f"{current_path}/{part}"

                if "children" not in current:
                    current["children"] = []

                child = next((c for c in current["children"] if c["name"] == part), None)
                if not child:
                    node_type = "sensor" if i == len(parts) - 1 else [
                        "segment", "site", "plant", "function",
                        "system", "machine", "stage"
                    ][min(i - 1, 6)]

                    child = {
                        "id": current_path,
                        "name": part,
                        "type": node_type,
                        "children": []
                    }

                    if node_type == "sensor":
                        child["status"] = "online"

                    if current_path in notes_data:
                        child["note"] = notes_data[current_path]['content'] if notes_data[current_path]['has_content'] else ""
                    else:
                        child["note"] = ""

                    current["children"].append(child)

                current = child
        
        def fix_node_types(node, depth=0):
            type_map = ["manufacturer", "segment", "site", "plant", "function", "system", "machine", "stage"]
            if 'children' in node and node['children']:
                if node.get('type') == 'sensor':
                    node['type'] = type_map[min(depth, len(type_map) - 1)]
                    if 'status' in node:
                        del node['status']
                for child in node['children']:
                    fix_node_types(child, depth + 1)
            else:
                if node.get('type') != 'manufacturer':
                    node['type'] = 'sensor'
                    node['status'] = 'online'

        for manufacturer in manufacturers.values():
            fix_node_types(manufacturer, depth=0)

        return JsonResponse(list(manufacturers.values()), safe=False)
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_view(['POST'])
@login_required
def upload_excel_view(request):
    """Upload Excel file for visualization only (does not save to database)."""
    serializer = UploadSerializer(data=request.data)
    if serializer.is_valid():
        file = serializer.validated_data['file']
        try:
            tree = build_tree_from_excel(file)
            _add_notes_to_tree(tree)
            return JsonResponse(tree, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse(serializer.errors, status=400)


@api_view(['POST'])
def upload_excel(request):
    """
    Upload Excel file, populate database, and return tree JSON.
    Superusers only. Nodes are reused (get_or_create), notes are appended
    with hash-based deduplication to prevent duplicates on re-upload.
    """
    if not request.user.is_superuser:
        return JsonResponse({"error": "Only superusers can upload Excel files to database."}, status=403)

    serializer = UploadSerializer(data=request.data)
    if serializer.is_valid():
        file = serializer.validated_data['file']
        try:
            tree = build_tree_from_excel(file)
            result = populate_nodes_from_excel(file, modified_by=request.user)

            ExcelUploadTracker.objects.create(
                is_uploaded=True,
                uploaded_by=request.user,
                file_name=file.name
            )

            _add_notes_to_tree(tree)

            return JsonResponse({
                "success": True,
                "message": f"Excel processed: {result.get('created', 0)} new nodes, {result.get('updated', 0)} existing nodes, {result.get('notes_added', 0)} new notes added.",
                "tree": tree,
                "stats": result,
            }, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse(serializer.errors, status=400)


class NoteEditorView(FormView):
    template_name = 'note_editor.html'
    form_class = NoteForm

    def _decoded_node_id(self) -> str:
        raw = self.kwargs.get('node_id', '')
        return unquote(raw)

    def get_success_url(self):
        return self.request.path

    def get_initial(self):
        initial = super().get_initial()
        node_id = self._decoded_node_id()
        node, _ = Node.objects.get_or_create(node_id=node_id)
        note = getattr(node, 'note', None)
        if note:
            initial['content'] = note.content_for_editing()
            initial['problem_category'] = note.problem_category
            initial['problem_subcategory'] = note.problem_subcategory
            initial['problem_date'] = note.problem_date
            initial['fault_resolved'] = note.fault_resolved
        else:
            initial['content'] = ''
            initial['problem_category'] = ''
            initial['problem_subcategory'] = ''
            initial['problem_date'] = None
            initial['fault_resolved'] = False
        return initial

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_superuser and not AllowedUser.objects.filter(user=request.user).exists():
            return HttpResponseForbidden("You are not authorized to access this page.")
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        node_id = self._decoded_node_id()
        node, _ = Node.objects.get_or_create(node_id=node_id)
        note = getattr(node, 'note', None)
        ctx['node'] = node
        ctx['node_id'] = node.node_id
        ctx['note'] = note
        ctx['last_updated'] = note.updated_at if note else None
        ctx['is_superuser'] = self.request.user.is_superuser
        ctx['fault_schema'] = json.dumps(get_fault_schema())
        return ctx

    def form_valid(self, form):
        node_id = self._decoded_node_id()
        node, _ = Node.objects.get_or_create(node_id=node_id)
        content = form.cleaned_data.get('content', '')
        problem_category = form.cleaned_data.get('problem_category', '')
        problem_subcategory = form.cleaned_data.get('problem_subcategory', '')
        problem_date = form.cleaned_data.get('problem_date')
        fault_resolved = form.cleaned_data.get('fault_resolved', False)
        
        note, _ = Note.objects.get_or_create(node=node)
        note.content = content
        note.problem_category = problem_category
        note.problem_subcategory = problem_subcategory
        note.problem_date = problem_date
        note.fault_resolved = fault_resolved
        
        note.save(modified_by=self.request.user)
        return super().form_valid(form)


@api_view(['GET'])
@login_required
def fault_schema_view(request):
    """Return the fault categories and subcategories schema for the UI."""
    if not request.user.is_superuser and not AllowedUser.objects.filter(user=request.user).exists():
        return JsonResponse({"error": "Not authorized"}, status=403)
    return JsonResponse({"categories": get_fault_schema()}, safe=False)


@api_view(['GET'])
@login_required
def problem_search_view(request):
    """
    Search notes by fault category/subcategory keywords.
    Query params: category, sub, page (default 1), page_size (default 20).
    Returns a paginated list of matching node IDs and note excerpts.
    """
    if not request.user.is_superuser and not AllowedUser.objects.filter(user=request.user).exists():
        return JsonResponse({"error": "Not authorized"}, status=403)

    category = request.GET.get('category')
    sub = request.GET.get('sub') or request.GET.get('subcategory')
    page = int(request.GET.get('page', '1') or 1)
    page_size = min(100, max(1, int(request.GET.get('page_size', '20') or 20)))

    if not category or not sub:
        return JsonResponse({"error": "Both 'category' and 'sub' are required."}, status=400)

    keywords = get_keywords_for(category, sub)
    if not keywords:
        return JsonResponse({
            "category": category,
            "subcategory": sub,
            "count": 0,
            "page": 1,
            "page_size": page_size,
            "num_pages": 0,
            "results": []
        }, status=200)

    query = Q()
    query |= Q(content__icontains=f"Category: {category}")
    query |= Q(content__icontains=f"Sub: {sub}")
    for kw in keywords:
        if kw:
            query |= Q(content__icontains=kw)

    notes_qs = Note.objects.select_related('node').filter(query).order_by('node__node_id')

    paginator = Paginator(notes_qs, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages or 1)

    def make_excerpt(text: str, kws):
        base = text or ""
        idx = -1
        low = base.lower()
        for k in kws:
            i = low.find(k.lower())
            if i != -1 and (idx == -1 or i < idx):
                idx = i
        if idx == -1:
            return base[:160]
        start = max(0, idx - 40)
        end = min(len(base), idx + 120)
        snippet = base[start:end]
        return ("..." if start > 0 else "") + snippet + ("..." if end < len(base) else "")

    results = []
    for note in page_obj.object_list:
        plain = note.content_without_metadata()
        results.append({
            "node_id": note.node.node_id,
            "note_excerpt": make_excerpt(plain, keywords)
        })

    return JsonResponse({
        "category": category,
        "subcategory": sub,
        "count": paginator.count,
        "page": page_obj.number,
        "page_size": page_obj.paginator.per_page,
        "num_pages": paginator.num_pages,
        "results": results,
    }, status=200)


@api_view(['GET'])
@login_required
def fault_counts_view(request):
    """Return counts of open and resolved faults (notes with a problem_category set)."""
    open_count = Note.objects.exclude(problem_category='').filter(fault_resolved=False).count()
    resolved_count = Note.objects.exclude(problem_category='').filter(fault_resolved=True).count()
    return JsonResponse({
        "open": open_count,
        "resolved": resolved_count,
    }, status=200)



