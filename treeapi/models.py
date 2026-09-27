from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class ExcelUploadTracker(models.Model):
    """Tracks Excel file uploads by superusers."""
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    file_name = models.CharField(max_length=255, blank=True)
    is_uploaded = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Excel Upload Status"
        verbose_name_plural = "Excel Upload Status"

    def __str__(self):
        return f"Upload status: {self.is_uploaded}"


class AllowedUser(models.Model):
    """
    Predefined normal users allowed to log in.
    Only these users (plus superusers) can access the system.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='allowed_user_profile')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Allowed User"
        verbose_name_plural = "Allowed Users"

    def __str__(self):
        return self.user.username


class Node(models.Model):
    """Represents a node in the hierarchical tree structure."""
    node_id = models.CharField(max_length=512, unique=True)
    display_name = models.CharField(max_length=512, blank=True, default='')
    external_ref = models.JSONField(blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, default='')

    def __str__(self):
        return self.node_id


class Note(models.Model):
    """
    Stores notes for nodes. Notes can be edited by both superusers and normal users.
    Normal user modifications are tracked with username and timestamp.
    """
    node = models.OneToOneField(Node, on_delete=models.CASCADE, related_name="note")
    # Content is indexed for faster icontains searches used by problem-based search
    content = models.TextField(blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    problem_category = models.CharField(max_length=255, blank=True, default="")
    problem_subcategory = models.CharField(max_length=255, blank=True, default="")
    problem_date = models.DateField(null=True, blank=True)
    fault_resolved = models.BooleanField(default=False)
    # Deterministic hashes of (node_id + note_content + column_name) to prevent duplicate imports
    imported_hashes = models.JSONField(default=list, blank=True)

    def _strip_header_metadata(self, value: str) -> str:
        """Strip metadata header lines from the top of the note content."""
        txt = (value or "").lstrip("\n")
        lines = txt.splitlines()

        i = 0
        # Remove one optional "[Modified by: ...]" line
        if i < len(lines) and lines[i].strip().startswith("[Modified by:"):
            i += 1

        # Remove any blank lines immediately after header
        while i < len(lines) and lines[i].strip() == "":
            i += 1

        return "\n".join(lines[i:]).rstrip("\n")

    def _strip_timestamp(self, value: str) -> str:
        """Strip the legacy 'Last updated:' footer timestamp from content."""
        txt = (value or "").rstrip()
        lines = txt.splitlines()
        if lines and lines[-1].startswith("Last updated:"):
            lines = lines[:-1]
        return "\n".join(lines).rstrip("\n")
    
    def _strip_modification_metadata(self, value: str) -> str:
        """Strip all modification metadata lines from content."""
        txt = self._strip_header_metadata(value)
        txt = self._strip_timestamp(txt)
        lines = (txt or "").splitlines()
        filtered_lines = [
            line
            for line in lines
            if not line.strip().startswith("[Modified by:")
            and not line.strip().startswith("[Problem:")
            and not line.strip().startswith("Last updated:")
        ]
        return "\n".join(filtered_lines).rstrip("\n")
    
    def _strip_only_modified_by(self, value: str) -> str:
        """Strip only [Modified by:] lines, keeping [Problem:] lines visible."""
        txt = (value or "").rstrip()
        lines = txt.splitlines()
        filtered_lines = [
            line
            for line in lines
            if not line.strip().startswith("[Modified by:")
            and not line.strip().startswith("Last updated:")
        ]
        return "\n".join(filtered_lines).rstrip("\n")

    def save(self, *args, **kwargs):
        """
        Automatically prepends modification metadata and appends a timestamp on save.
        Pass modified_by=<User> in kwargs to track who modified the note.
        """
        user = kwargs.pop('modified_by', None)
        base = self._strip_modification_metadata(self.content)

        problem_lines = []
        if self.problem_category or self.problem_subcategory or self.problem_date:
            problem_parts = []
            if self.problem_category:
                problem_parts.append(f"Category: {self.problem_category}")
            if self.problem_subcategory:
                problem_parts.append(f"Sub: {self.problem_subcategory}")
            if self.problem_date:
                problem_parts.append(f"Date: {self.problem_date}")
            problem_lines.append(f"[Problem: {' | '.join(problem_parts)}]")

        now = timezone.localtime(timezone.now())
        modified_ts = now.strftime("%Y-%m-%d %H:%M:%S IST")
        updated_ts = now.strftime("%Y-%m-%d %H:%M IST")

        top_lines = []
        if user:
            top_lines.append(f"[Modified by: {user.username} at {modified_ts}]")

        body_lines = []
        if problem_lines:
            body_lines.extend(problem_lines)
        if base.strip():
            if body_lines:
                body_lines.append("")
            body_lines.append(base.strip())

        footer_lines = [f"Last updated: {updated_ts}"]

        parts = []
        if top_lines:
            parts.append("\n".join(top_lines))
        if body_lines:
            if parts:
                parts.append("")
            parts.append("\n".join(body_lines))
        if footer_lines:
            if parts:
                parts.append("")
            parts.append("\n".join(footer_lines))

        self.content = "\n".join(parts).rstrip() + "\n"

        if user:
            self.last_modified_by = user

        super().save(*args, **kwargs)

    def content_without_timestamp(self) -> str:
        """Return content without the timestamp line."""
        txt = self._strip_header_metadata(self.content)
        return self._strip_timestamp(txt)

    def content_without_metadata(self) -> str:
        """Return content without timestamp and modification metadata."""
        return self._strip_modification_metadata(self.content)

    def content_for_editing(self) -> str:
        """Return full content including Problem info and modification tracking for display in the editor."""
        return self.content.rstrip()
