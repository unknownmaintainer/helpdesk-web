# HelpDeskPro: Technical System Documentation

This document provides a comprehensive technical overview of the **HelpDeskPro: IT Support & Security Incident Tracker** system, detailing its architectural layout, database models, security controls, and API endpoints.

---

## 1. System Architecture
HelpDeskPro is built on a **Model-View-Template (MVT)** architecture using Django, integrated with a stateless REST API layer via the Django REST Framework (DRF).

```
   [ Client Browser ]  ◄──►  [ HTTP / WSGI Server ]
                                    │
    ┌───────────────────────────────┼──────────────────────────────┐
    │ django-ratelimit              ▼                              │
    │                       [ urls.py Routing ]                    │
    │                               │                              │
    │           ┌───────────────────┴───────────────────┐          │
    │           ▼                                       ▼          │
    │   [ Django Views ]                       [ DRF REST Views ]  │
    │   - Web HTML Templates                   - JWT Security Check│
    │   - Session Authentication               - Serializer Parsing│
    │           │                                       │          │
    │           └───────────────────┬───────────────────┘          │
    │                               ▼                              │
    │                       [ django-axes (Lockout) ]              │
    │                               ▼                              │
    │                    [ Database Models ORM ]                   │
    └───────────────────────────────┬──────────────────────────────┘
                                    ▼
                          [ SQLite / PostgreSQL ]
```

---

## 2. Directory Structure Layout
```text
IT Helpdesk & Security Incident Tracker/
│
├── helpdesk_project/              # Project Configuration Directory
│   ├── __init__.py
│   ├── settings.py                # Security, Logging, and Database configurations
│   ├── urls.py                    # Root URL router mapping helpdesk app
│   └── wsgi.py                    # Web Server Gateway Interface entry point
│
├── helpdesk/                      # Main Application Directory
│   ├── migrations/                # Database migration schemas
│   ├── templates/helpdesk/        # HTML templates for user interfaces
│   ├── api_views.py               # REST API endpoints (JWT Authorized)
│   ├── serializers.py             # Data serialization & field masking rules
│   ├── models.py                  # Database tables/models
│   ├── views.py                   # User interface view handlers (MVT)
│   ├── urls.py                    # App URL router
│   ├── tests.py                   # Automated security & layout test suite
│   ├── decorators.py              # Custom RBAC decorator filters
│   └── utils.py                   # IP resolvers and helper functions
│
├── logs/                          # Security audit and application log files
│   └── helpdesk.log
├── staticfiles/                   # Compiled static files for production
├── setup_data.py                  # Seeding script for default users & tickets
├── render.yaml                    # Infrastructure-as-Code deployment blueprint
├── requirements.txt               # Dependencies listing
└── postman_collection.json        # Pre-configured Postman requests suite
```

---

## 3. Database Schema & Models
The application database consists of seven main tables defined via the Django ORM:

1. **`CustomUser` (Extends `AbstractUser`)**:
   * Stores user details, including `role` (`employee`, `manager`), `department`, `profile_picture`, and notification preferences (`notify_tickets`, `notify_security`).
2. **`Ticket`**:
   * The core record representing support tickets or incidents. Contains `title`, `description`, `status`, `priority`, `category`, `nist_stage`, and relationships to `created_by` (Employee) and `assigned_to` (Manager).
3. **`TicketUpdate`**:
   * Logs comments, resolution notes, and status changes made to tickets by managers.
4. **`LoginAttempt`**:
   * Records secure auditing details of successful and failed user logins.
5. **`TicketLog`**:
   * A global audit log tracking user profile edits, user deactivations, and system actions.
6. **`IncidentAuditLog`**:
   * A per-ticket audit trail rendering incident progression details.
7. **`MileageReport`**:
   * Stores telemetry data for drivers, subject to Serializer-level data masking for non-managers.

---

## 4. Security & Compliance Controls

### A. Brute Force Protection (`django-axes`)
* **Cool-off Period:** 1 minute (`AXES_COOLOFF_TIME`).
* **Failed Attempts Limit:** 5 consecutive failures before lockout.
* **Granular Lockout:** Combination of IP address and Username (`AXES_LOCKOUT_PARAMETERS`). Prevent blockings of corporate gateways.
* **Audit Trail:** Custom lockout events are captured and recorded in the audit log.

### B. Rate Limiting (`django-ratelimit`)
* Submitting tickets and security incident forms is rate-limited to **5 requests per minute per IP address** to prevent denial-of-service (DoS) attempts on database inserts.

---

## 5. REST API & Field-Level Masking

### A. JWT Token Authentication
Authentication for external tools (e.g. SIEM alerts) is handled via stateless **JSON Web Tokens (JWT)**.
* **Token Request:** `POST /api/token/`
* **Token Refresh:** `POST /api/token/refresh/`

### B. Serializer Data Masking
To prevent unauthorized access to sensitive financial parameters (e.g. `fleet_valuation`, `procurement_cost`) in the Mileage API:
* **Managers:** Receive full, unmasked decimal values.
* **Standard Employees:** The serializer interceptor replaces values dynamically with masked string formats (e.g., `"$*,***,***.**"`).

---

## 6. Workflows & NIST Incident Response Stages
Tickets flow through logical progressions mapped directly to the **NIST SP 800-61 Rev. 2** lifecycle stages:

1. **Preparation / Reported:** Logged by user, status set to `Open` or `Reported`.
2. **Detection & Analysis / Containment:** Under investigation by IT, status set to `In Progress` or `Investigating`.
3. **Eradication & Recovery / Fixed:** Action taken by manager, status set to `Resolved` or `Fixed`.
4. **Post-Incident Review / Closed:** Ticket closed, status set to `Closed`.
