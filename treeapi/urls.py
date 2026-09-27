from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    
    # Main sensor tree visualization
    path("sensor-tree/", views.sensor_tree_view, name="sensor-tree"),
    
    # Tree API endpoints
    path("tree/data/", views.get_tree_data, name="tree-data"),

    path("tree/from-file/", views.tree_from_file, name="tree-from-file"),
    path("tree/upload/", views.upload_excel_view, name="upload-excel-view"),  # For viewing only
    path("tree/upload-permanent/", views.upload_excel, name="upload-excel"),  # For permanent database save
    path("tree/ping/", views.ping, name="ping"),
    # Fault search/schema endpoints
    path("faults/schema/", views.fault_schema_view, name="fault-schema"),
    path("faults/counts/", views.fault_counts_view, name="fault-counts"),
    path("search/problems/", views.problem_search_view, name="problem-search"),
    
    # Notes
    path("notes/<path:node_id>/", views.NoteEditorView.as_view(), name="note-editor"),
]
