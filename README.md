# Products Tree Structure

A Django-based web application for managing hierarchical sensor/product tree structures with Excel import capabilities, note management, and fault tracking system.

## 📋 Project Overview

### Purpose
The Products Tree Structure system is designed to:
- Import and visualize hierarchical product/sensor data from Excel files
- Provide a tree-based interface for navigating complex product structures
- Enable note-taking and problem tracking for individual nodes
- Support fault categorization and search functionality
- Manage user access with role-based permissions

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Django API    │    │   PostgreSQL    │
│   (HTML/JS)     │◄──►│   (REST/Views)  │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Excel Files   │
                       │   (Upload/Import)│
                       └─────────────────┘
```

### Core Modules
- **Authentication**: User login/logout with role-based access control
- **Tree Management**: Hierarchical data structure visualization and navigation
- **Excel Integration**: File upload and data import from Excel spreadsheets
- **Notes System**: Node-specific note editing with tracking and metadata
- **Fault Tracking**: Problem categorization, search, and resolution tracking
- **File Management**: Upload handling and temporary file storage

### Technologies Used

#### Backend
- **Framework**: Django 5.2.6 with Django REST Framework 3.16.1
- **Database**: PostgreSQL (production) / SQLite (development)
- **Python**: 3.13
- **Server**: Gunicorn WSGI server
- **Authentication**: Django's built-in auth system with custom permissions

#### Frontend
- **Templates**: Django HTML templates with JavaScript
- **Styling**: CSS with static file management
- **UI Components**: Custom tree visualization components

#### DevOps & Deployment
- **Containerization**: Docker & Docker Compose
- **Web Server**: Nginx (reverse proxy)
- **Process Management**: Gunicorn with multiple workers
- **Static Files**: WhiteNoise middleware for static file serving

#### Data Processing
- **Excel Handling**: pandas, openpyxl
- **Data Manipulation**: numpy
- **File Processing**: Python's built-in file I/O with temporary storage

## 🔄 System Flow & Logic

### Request Flow Architecture

```
User Request → Nginx → Django Middleware → View → Business Logic → Database → Response
                    ↓
                 Static Files (WhiteNoise)
```

### Key Workflows

#### 1. Authentication Flow
```
Login Request → user_login() → Authentication Check → Permission Validation → Session Creation → Redirect to Tree View
```

#### 2. Excel Import Process
```
File Upload → upload_excel() → Excel Parsing → Tree Structure Building → Database Population → Response
```

#### 3. Tree Data Retrieval
```
Tree Request → get_tree_data() → Database Query → Tree Construction → Note Integration → JSON Response
```

#### 4. Note Management
```
Note Edit → NoteEditorView → Form Validation → Note Save (with metadata) → Database Update → Tree Refresh
```

### Key Functions & Responsibilities

#### Core Views (`treeapi/views.py`)
- **`sensor_tree_view()`**: Main tree visualization interface
- **`user_login()` / `user_logout()`**: Authentication handling
- **`get_tree_data()`**: Tree structure API endpoint
- **`upload_excel()`**: Excel file processing and database import
- **`NoteEditorView`**: Note editing functionality
- **`problem_search_view()`**: Fault search and filtering

#### Utility Functions (`treeapi/utils.py`)
- **`build_tree_from_excel()`**: Convert Excel data to hierarchical structure
- **`populate_nodes_from_excel()`**: Database population from Excel
- **`split_path_preserving_brackets()`**: Path parsing for hierarchical data
- **`_generate_note_hash()`**: Duplicate prevention for note imports

#### Models (`treeapi/models.py`)
- **`Node`**: Core tree structure element
- **`Note`**: Node-specific notes with metadata and problem tracking
- **`AllowedUser`**: User permission management
- **`ExcelUploadTracker`**: One-time upload tracking

### Data Flow Between Components

1. **Excel Import**: Excel file → pandas DataFrame → Node objects → Database storage
2. **Tree Rendering**: Database query → Tree structure → JSON API → Frontend visualization
3. **Note Updates**: User input → Form validation → Metadata addition → Database save → Tree refresh

## 🚀 Setup & Installation

### Prerequisites
- **Python**: 3.13+
- **Database**: PostgreSQL 16+ (production) or SQLite (development)
- **Docker**: Latest version (for containerized deployment)
- **Docker Compose**: Latest version
- **Node.js**: Not required (pure Django frontend)

### Environment Variables

Create a `.env` file in the project root:

```bash
# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True  # Set to False in production
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database Configuration (PostgreSQL)
DB_NAME=sensor_db
DB_USER=sensor_user
DB_PASSWORD=your-secure-password
DB_HOST=localhost  # or 'db' when using Docker
DB_PORT=5432
DATABASE_URL=postgresql://user:password@host:port/dbname  # Alternative

# Security Settings
USE_PROD_SECURITY=False  # Enable in production
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1



# Application Settings
ALLOWED_EXCEL_DIRS=  # Comma-separated list of allowed directories
EXCEL_DEFAULT_PATH=  # Default Excel file path (optional)
```

### Installation Steps

#### Option 1: Docker Deployment (Recommended)

1. **Clone the repository**
```bash
git clone <repository-url>
cd ProductsTreeStructure
```

2. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Build and start services**
```bash
make build
make up
```

4. **Create superuser**
```bash
make createsuperuser
```

#### Option 2: Local Development

1. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure database**
```bash
# For PostgreSQL: Create database and user
# For SQLite: No setup needed (uses db.sqlite3)
```

4. **Run migrations**
```bash
python manage.py migrate
```

5. **Create superuser**
```bash
python manage.py createsuperuser
```

6. **Start development server**
```bash
python manage.py runserver
```

## 📖 Usage Guide

### Running the System

#### Docker Deployment
```bash
# Start all services
make up

# View logs
make logs

# Access containers
make shell          # Django shell
make bash           # Backend container bash

# Stop services
make down
```

#### Local Development
```bash
# Start development server
python manage.py runserver

# Run specific commands
python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser
```

### Accessing the Application

1. **Main Application**: `http://localhost:80` (Docker) or `http://localhost:8000` (local)
2. **Admin Panel**: `http://localhost:80/admin/` (superuser only)
3. **API Endpoints**: Available at `/tree/`, `/notes/`, `/faults/`



### Expected Outputs

#### Tree Data Response
```json
{
  "roots": [
    {
      "id": "root_node_1",
      "name": "Root Node 1",
      "children": [
        {
          "id": "child_node_1",
          "name": "Child Node 1",
          "note": "Sample note content",
          "children": []
        }
      ]
    }
  ]
}
```

#### Upload Response
```json
{
  "status": "success",
  "message": "Excel file processed successfully",
  "nodes_created": 150,
  "notes_imported": 25
}
```

## 🏗️ Codebase Walkthrough for Junior Developers

### Directory Structure

```
ProductsTreeStructure/
├── server/                 # Django project configuration
│   ├── settings.py        # Main Django settings
│   ├── urls.py            # Root URL configuration
│   └── wsgi.py            # WSGI application entry point
├── treeapi/               # Main Django app
│   ├── models.py          # Database models
│   ├── views.py           # View functions and classes
│   ├── urls.py            # App-specific URLs
│   ├── forms.py           # Django forms
│   ├── utils.py           # Utility functions
│   ├── admin.py           # Django admin configuration
│   ├── permissions.py     # Custom permissions
│   └── migrations/        # Database migrations
├── templates/             # HTML templates
│   ├── sensor_tree.html   # Main tree visualization
│   ├── login.html         # Login page
│   └── note_editor.html   # Note editing interface
├── static/                # Static files (CSS, JS, images)
├── media/                 # User-uploaded files
├── logs/                  # Application logs
├── tmp_uploads/           # Temporary upload storage
├── nginx/                 # Nginx configuration
├── scripts/               # Utility scripts
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker Compose configuration
├── Makefile              # Common commands
├── requirements.txt       # Python dependencies
└── .env                  # Environment variables
```

### Important Files and Their Roles

#### Core Configuration Files
- **`server/settings.py`**: Main Django configuration, database settings, middleware
- **`requirements.txt`**: Python package dependencies
- **`docker-compose.yml`**: Container orchestration configuration
- **`.env`**: Environment-specific configuration

#### Application Logic Files
- **`treeapi/models.py`**: Database schema and business logic
- **`treeapi/views.py`**: HTTP request handling and response logic
- **`treeapi/utils.py`**: Shared utility functions and data processing
- **`treeapi/forms.py`**: Form validation and processing

#### Frontend Files
- **`templates/sensor_tree.html`**: Main user interface
- **`templates/note_editor.html`**: Note editing interface
- **`static/`**: CSS, JavaScript, and image assets

### Naming Conventions

#### Python/Django
- **Models**: PascalCase (e.g., `ExcelUploadTracker`, `AllowedUser`)
- **Functions**: snake_case (e.g., `build_tree_from_excel`, `get_tree_data`)
- **Variables**: snake_case (e.g., `node_id`, `user_permissions`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `SECRET_KEY`, `DEBUG`)

#### Database
- **Tables**: snake_case (e.g., `treeapi_note`, `treeapi_node`)
- **Fields**: snake_case (e.g., `created_at`, `last_modified_by`)
- **Foreign Keys**: `{model}_id` pattern (e.g., `user_id`, `node_id`)

#### URLs
- **Paths**: kebab-case (e.g., `/sensor-tree/`, `/upload-permanent/`)
- **Query Parameters**: snake_case (e.g., `category=hardware`, `resolved=false`)

### Common Workflows

#### Adding a New Feature

1. **Model Changes**:
   ```bash
   # 1. Modify models.py
   # 2. Create migration
   python manage.py makemigrations
   # 3. Apply migration
   python manage.py migrate
   ```

2. **Add View Logic**:
   - Create view function in `views.py`
   - Add URL pattern in `urls.py`
   - Create template if needed

3. **Testing**:
   ```bash
   python manage.py test
   ```

#### Debugging Process

1. **Check Logs**:
   ```bash
   make logs  # Docker
   tail -f logs/django.log  # Local
   ```

2. **Django Shell**:
   ```bash
   make shell  # Docker
   python manage.py shell  # Local
   ```

3. **Database Inspection**:
   ```python
   from treeapi.models import Node, Note
   Node.objects.all().count()
   Note.objects.filter(node__node_id="example").first()
   ```

#### Testing API Endpoints

1. **Development Server**:
   ```bash
   python manage.py runserver
   ```

2. **API Testing**:
   ```bash
   # Test authentication
   curl -X POST http://localhost:8000/login/ \
     -d "username=admin&password=password"
   
   # Test API endpoints
   curl -X GET http://localhost:8000/tree/data/
   ```

## 🎯 Best Practices & Contribution Guide

### Code Quality Standards

#### Python/Django Best Practices
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings for all functions and classes
- Keep functions small and focused on single responsibilities
- Use Django's built-in security features (CSRF, XSS protection)

#### Database Best Practices
- Always use migrations for schema changes
- Use `select_related()` and `prefetch_related()` for query optimization
- Add database indexes for frequently queried fields
- Use transactions for multi-table operations

#### Security Best Practices
- Never commit sensitive data to version control
- Use environment variables for configuration
- Validate all user inputs
- Use Django's permission system for access control
- Enable security headers in production

### Testing Strategy

#### Unit Tests
```python
# treeapi/tests.py
from django.test import TestCase
from treeapi.models import Node, Note

class NodeModelTest(TestCase):
    def setUp(self):
        self.node = Node.objects.create(
            node_id="test_node",
            display_name="Test Node"
        )
    
    def test_node_str_representation(self):
        self.assertEqual(str(self.node), "test_node")
```

#### Integration Tests
```python
class TreeAPITest(TestCase):
    def test_tree_data_endpoint(self):
        response = self.client.get('/tree/data/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('roots', response.json())
```

#### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test treeapi

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Logging and Error Handling

#### Logging Configuration
The application uses structured logging with multiple handlers:
- **Console Logging**: Development environment
- **File Logging**: Production environment (when writable)
- **Error Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

#### Error Handling Patterns
```python
# In views.py
try:
    result = risky_operation()
    return JsonResponse({"status": "success", "data": result})
except SpecificException as e:
    logger.error(f"Specific error occurred: {e}")
    return JsonResponse({"error": "Operation failed"}, status=400)
except Exception as e:
    logger.critical(f"Unexpected error: {e}")
    return JsonResponse({"error": "Internal server error"}, status=500)
```

#### Custom Exception Classes
```python
# treeapi/exceptions.py
class ExcelImportError(Exception):
    """Raised when Excel file import fails."""
    pass

class NodeNotFoundError(Exception):
    """Raised when requested node is not found."""
    pass
```

### Contribution Guidelines

#### Before Contributing
1. Fork the repository
2. Create a feature branch from `main`
3. Set up your development environment
4. Run existing tests to ensure they pass

#### Making Changes
1. Follow the existing code style and patterns
2. Add tests for new functionality
3. Update documentation if needed
4. Ensure all tests pass
5. Keep commits small and focused

#### Submitting Changes
1. Push changes to your fork
2. Create a pull request with:
   - Clear description of changes
   - Related issue numbers
   - Testing instructions
   - Screenshots if applicable

#### Code Review Process
- All changes require code review
- Reviews focus on: functionality, security, performance, and maintainability
- Address review feedback promptly
- Maintain professional and constructive communication

## 📝 Additional Notes

### Known Limitations

1. **Excel File Size**: Large Excel files (>50MB) may cause memory issues
2. **Concurrent Users**: Limited support for simultaneous Excel uploads
3. **Tree Depth**: Very deep hierarchies (>100 levels) may impact performance
4. **Search Performance**: Text search on large note collections can be slow
5. **File Upload**: Only Excel (.xlsx, .xls) files are supported

### Future Improvements

#### Planned Features
- **Real-time Updates**: WebSocket support for live tree updates
- **Advanced Search**: Full-text search with Elasticsearch integration
- **Bulk Operations**: Batch note editing and node management
- **Export Functionality**: PDF/Excel export of tree structures
- **API Versioning**: Versioned API endpoints for backward compatibility
- **Caching**: Redis integration for improved performance

#### Technical Improvements
- **Microservices Architecture**: Split into separate services
- **Database Optimization**: Query optimization and indexing strategy
- **Frontend Framework**: React/Vue.js for better user experience
- **Testing**: Increase test coverage to >90%
- **CI/CD**: Automated testing and deployment pipeline
- **Monitoring**: Application performance monitoring (APM)

#### Security Enhancements
- **Two-Factor Authentication**: Enhanced security for user accounts
- **Audit Logging**: Track all user actions and data changes
- **Rate Limiting**: API rate limiting to prevent abuse
- **Data Encryption**: Encrypt sensitive data at rest

### References and Documentation

#### Official Documentation
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)

#### Useful Tools
- **Django Debug Toolbar**: Development debugging
- **Postman**: API testing
- **pgAdmin**: PostgreSQL administration
- **Docker Desktop**: Container management

#### Community Resources
- [Django Project Website](https://www.djangoproject.com/)
- [Stack Overflow Django Tag](https://stackoverflow.com/questions/tagged/django)
- [Reddit r/django](https://www.reddit.com/r/django/)

---

## 📞 Support

For questions, issues, or contributions:
- Create an issue in the project repository
- Contact the development team
- Check the existing documentation and FAQs

---

**Last Updated**: January 2026  
**Version**: 1.0.0  
**Maintainer**: Development Team
