#!/usr/bin/env python
"""
Clear database script for fresh Excel upload
Deletes all Node, Note, and ExcelUploadTracker records
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from treeapi.models import Node, Note, ExcelUploadTracker

def clear_database():
    """Clear all tree-related data from database"""
    print("Clearing database...")
    
    # Delete all notes first (due to foreign key constraint)
    note_count = Note.objects.count()
    Note.objects.all().delete()
    print(f"✓ Deleted {note_count} Note records")
    
    # Delete all nodes
    node_count = Node.objects.count()
    Node.objects.all().delete()
    print(f"✓ Deleted {node_count} Node records")
    
    # Reset upload tracker so superuser can upload again
    upload_count = ExcelUploadTracker.objects.count()
    ExcelUploadTracker.objects.all().delete()
    print(f"✓ Deleted {upload_count} ExcelUploadTracker records")
    
    print("\n🎉 Database cleared! Ready for fresh Excel upload.")

if __name__ == "__main__":
    clear_database()
