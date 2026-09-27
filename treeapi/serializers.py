from rest_framework import serializers


class UploadSerializer(serializers.Serializer):
    """Serializer for Excel file upload."""
    file = serializers.FileField()
