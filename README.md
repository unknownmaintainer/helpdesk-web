# HelpDeskPro: IT Support & Security Incident Tracker

HelpDeskPro is a clean, responsive, and secure Django-based web application designed for corporate environments. It allows employees to submit IT support tickets and security incident reports, tracks ticket progress using simple workflows inspired by NIST incident response stages, and enables IT staff/managers and administrators to handle support requests efficiently.

---

## ── Table of Contents ──
1. [Key Features](#1-key-features)
2. [Technology Stack](#2-technology-stack)
3. [User Roles & Permissions](#3-user-roles--permissions)
4. [Workflows & NIST Stages](#4-workflows--nist-stages)
5. [Database Architecture & Models](#5-database-architecture--models)
6. [Security & Rate Limiting](#6-security--rate-limiting)
7. [Developer API Integration](#7-developer-api-integration)
8. [Installation & Setup](#8-installation--setup)
9. [Automated Testing](#9-automated-testing)
10. [Recent UI/UX & Mobile Responsiveness Improvements](#10-recent-uiux--mobile-responsiveness-improvements)

---

## 1. Key Features
*   **Centralized Dashboard**: Personalized metrics based on user roles (total, open, resolved, and closed tickets).
*   **Interactive Ticket Submission**: Guided form handling categories (Hardware, Software, Network, Account, Security) and priorities.
*   **NIST-Aligned Incident Tracking**: Visual timeline tracker mapping tickets to NIST Incident Response stages.
*   **Audit Logging**: Detailed database audit logs tracking status adjustments, profile edits, and user creations.
*   **API Integrations**: Fully functional REST APIs with JWT authentication for remote monitoring tools and driver telemetry logs.
*   **Role-Based Data Masking**: Sensitive mileage report parameters (fleet valuation and procurement costs) are automatically masked for drivers/employees, while remaining fully visible to IT managers and admins.
*   **UI Customization**: Supports Light & Dark theme modes (persisted in localStorage).

---

## 2. Technology Stack
*   **Backend Framework**: Django 6.0.5 (Python 3.13+)
*   **Database**: SQLite (local development) / PostgreSQL compatibility (configured via `dj_database_url`)
*   **API Framework**: Django REST Framework (DRF) + SimpleJWT for JWT Authentication
*   **Security Middleware**: Django-Axes (login protection) + Django-Ratelimit (view rate limiting)
*   **Frontend UI**: Vanilla CSS + Bootstrap 5.3 + FontAwesome 6.4 (Outfit/Inter Google Fonts)
*   **File Storage**: Cloudinary (integrated for ticket attachments & user avatars)

---

## 3. User Roles & Permissions
*   **Employee / Driver**: Can register, submit support requests and security incident reports, submit mileage telemetry logs, view/edit their own tickets while open, and update notification preferences.
*   **IT Manager (IT Staff)**: Can view all tickets, update ticket statuses, add resolution notes, deactivate/activate users, and view unmasked driver mileage logs.
*   **Administrator**: Full access to all controls including manager tools, user management, and advanced system metrics.

---

## 4. Workflows & NIST Stages
Tickets are categorized into two types, each with its own simplified lifecycle:
*   **IT Support Ticket Workflow**: `Open` ➔ `In Progress` ➔ `Resolved` ➔ `Closed`
*   **Security Incident Workflow**: `Reported` ➔ `Investigating` ➔ `Fixed` ➔ `Closed`

Additionally, tickets are mapped to a visual stepper displaying the **NIST Incident Response Stages**:
1.  **Preparation** / **Open** (Initial logging)
2.  **Detection & Analysis / Containment** (Investigation by IT staff)
3.  **Eradication & Recovery** (Resolution applied)
4.  **Post-Incident Review / Closed** (Formal closure and archive)

---

## 5. Database Architecture & Models
The system consists of seven main relational database models:
1.  **`CustomUser`**: Extends Django's `AbstractUser` with support for custom profile pictures, work departments, user roles (`employee`, `manager`), and notification toggles (`notify_tickets`, `notify_security`).
2.  **`Ticket`**: Represents support tickets or security incidents. It contains fields for description, status, priority, category, attachments, assignment, and tracking fields like `nist_stage`.
3.  **`TicketUpdate`**: Holds comments, progress updates, or resolution notes added to tickets by managers.
4.  **`LoginAttempt`**: Records successful and unsuccessful login attempts for security auditing.
5.  **`TicketLog`**: An audit trail record logging exact changes (e.g., status changes, field updates) made to tickets or user profiles.
6.  **`IncidentAuditLog`**: A rich, per-ticket audit trail shown on the ticket detail page.
7.  **`MileageReport`**: Stores driver mileage logs and dashboard alerts, including sensitive fields `fleet_valuation` and `procurement_cost` which are subject to role-based masking.

---

## 6. Security & Rate Limiting

### Brute Force Login Protection (`django-axes`)
To protect against brute force login attacks, `django-axes` is integrated with the following custom security configurations:
*   **1-Minute Lockout**: The lockout cool-off period is set to 1 minute (`AXES_COOLOFF_TIME = timedelta(minutes=1)`).
*   **Failure Limit**: Users/connections are locked out after 5 consecutive failed attempts (`AXES_FAILURE_LIMIT = 5`).
*   **IP-User Combination Lockout**: Configured to lock out the specific **combination of the username and IP address** (`AXES_LOCKOUT_PARAMETERS = [["ip_address", "username"]]`). This ensures that a brute-force attempt on a single account from one IP does not block other legitimate users logging in from the same office connection, loopback, or proxy.
*   **Proxy-Aware IP Resolution**: Utilizes a custom resolver `get_client_ip` to extract client IPs from header chains (like `HTTP_X_FORWARDED_FOR` behind Render load balancers), preventing the backend from accidentally locking out the reverse proxy's internal IP.

### Request Rate Limiting (`django-ratelimit`)
*   Protects form submissions (such as ticket creation) by limiting IP addresses to a maximum of **5 ticket creations per minute**.

---

## 7. Developer API Integration
HelpDeskPro exposes token-based API endpoints allowing external tools (like SIEMs, routers, or servers) to automatically report events, as well as driver-related telemetry APIs.

### API Versioning (v1)
All API endpoints are accessible via standard paths (e.g., `/api/...`) and their versioned counterparts under `/api/v1/` for backward compatibility.

### API Endpoints

#### Authentication
*   `POST /api/token/` (or `/api/v1/token/`) - Returns a JWT access token.
*   `POST /api/token/refresh/` (or `/api/v1/token/refresh/`) - Refreshes an existing JWT token.

#### Ticket Management
*   `GET /api/tickets/` (or `/api/v1/tickets/`) - Lists tickets for the authenticated user/manager.
*   `POST /api/tickets/create/` (or `/api/v1/tickets/create/`) - Submits a support or incident ticket (requires `Authorization: Bearer <Token>`).

#### Driver Telemetry (Driver Mileage API)
*   `GET /api/mileage/` (or `/api/v1/mileage/`) - Lists mileage reports.
    *   **Manager/Superuser Access**: Returns all reports with unmasked `fleet_valuation` and `procurement_cost` values.
    *   **Driver/Employee Access**: Returns only the driver's own reports with masked values.
*   `POST /api/mileage/` (or `/api/v1/mileage/`) - Submits a new mileage report (linked automatically to the authenticated driver).
*   `GET /api/mileage/<int:pk>/` (or `/api/v1/mileage/<int:pk>/`) - Retrieves a specific mileage report.
*   `PUT` / `PATCH` / `DELETE` `/api/mileage/<int:pk>/` (or `/api/v1/mileage/<int:pk>/`) - Modifies or deletes a mileage report.

### Role-Based Field-Level Masking
To protect sensitive financial and operational data, the Mileage API employs field-level masking:
*   **Managers & Admins**: Can view full, raw values of `fleet_valuation` and `procurement_cost` (e.g., `1250000.00` and `45000.00`).
*   **Drivers / Standard Employees**: The serialized JSON output is automatically masked at the view/serializer layer:
    *   `fleet_valuation` is masked to `"$*,***,***.**"`
    *   `procurement_cost` is masked to `"$**,***.**"`

### Access Token Generation
Users can generate a JWT token directly under **Settings ➔ Developer API Integration** to authorize external scripts or API clients.

### Postman API Collection
Ang [postman_collection.json](file:///c:/Users/Dion/Desktop/IT%20Helpdesk/postman_collection.json) ay parang **remote control** o **test cheat-sheet** para sa system natin. Imbes na manual mong i-type ang code sa command line, pwede mong gamitin ang app na **Postman** para i-test ang website features gamit ang simple clicks.

#### Paano I-import at Gamitin:
1. Buksan ang **Postman** app.
2. I-click ang **Import** (top-left) at piliin ang file na [postman_collection.json](file:///c:/Users/Dion/Desktop/IT%20Helpdesk/postman_collection.json) mula sa project folder.
3. May lalabas na collection na **HelpDeskPro Driver & Security API** na may 3 folders:
   *   **Authentication**: Dito ka "maglo-login" para kumuha ng **Access Token** (isang pansamantalang 'key' o 'pass' para makapasok sa secured pages).
   *   **Driver Mileage API**: Para sa pag-submit at pagtingin ng mileage logs (biyahe ng driver).
   *   **Security Incidents & Tickets API**: Para sa paggawa at pag-list ng IT support tickets.
4. Paano mag-auth/login sa Postman:
   *   Pumunta sa **Authentication** folder, i-click ang **Obtain JWT Token** at i-click ang **Send**.
   *   Kopyahin ang mahabang code na ibabalik sa iyo (tinatawag itong `access` token).
   *   I-click ang pangalan ng collection (HelpDeskPro Driver & Security API) sa kaliwa, pumunta sa **Variables** tab, at i-paste ang code sa variable na `jwt_token`.
5. **Mahalagang Paalala sa Slash `/` sa dulo ng link:**
   *   Ang system (Django) ay napaka-strict sa slash `/` sa dulo ng link (halimbawa: `/api/token/` at HINDI `/api/token`).
   *   Kapag walang `/` sa dulo ang link mo, magkakaroon ng error at hindi matatanggap ng system ang ipinapadalang data.
   *   Naka-setup na ito nang tama sa Postman collection na ito para hindi mo na kailangang intindihin pa.

### Curl Command Examples

#### 1. Submit an Incident Ticket
```bash
curl -X POST http://127.0.0.1:8000/api/tickets/create/ \
  -H "Authorization: Bearer YOUR_JWT_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Suspicious DB Spikes",
    "description": "High volume database query load detected from unusual IP.",
    "ticket_type": "Security Incident",
    "priority": "High"
  }'
```

#### 2. Submit a Mileage Report
```bash
curl -X POST http://127.0.0.1:8000/api/mileage/ \
  -H "Authorization: Bearer YOUR_JWT_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mileage": 145.20,
    "dashboard_alert": "Low tire pressure warning activated on route 4."
  }'
```

---

## 8. Installation & Setup

1.  **Clone the Repository** and navigate to the project root:
    ```bash
    git clone https://github.com/unknownmaintainer/helpdesk-web.git
    cd "helpdesk-web"
    ```

2.  **Create and Activate Virtual Environment**:
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Create a `.env` file in the root directory:
    ```env
    SECRET_KEY=your-django-secret-key-here
    DEBUG=True
    ALLOWED_HOSTS=127.0.0.1,localhost
    ```

5.  **Run Database Migrations**:
    ```bash
    python manage.py migrate
    ```

6.  **Seed Initial Database Data**:
    A built-in data seeder creates default users, sample tickets, and updates for testing:
    ```bash
    python setup_data.py
    ```
    *Seed Accounts created:*
    *   **IT Manager (Superuser)**: username: `admin` | email: `admin@gmail.com` (password: `admin123`)
    *   **Employee**: username: `employee` | email: `employee@gmail.com` (password: `password123`)
    *   **Developer**: username: `dev` | email: `dev@gmail.com` (password: `password123`)

7.  **Start Development Server**:
    ```bash
    python manage.py runserver
    ```
    Open `http://127.0.0.1:8000` in your web browser.

---

## 9. Automated Testing
Verify the backend, APIs, security settings, and lockout rules by running the Django unit tests:
```bash
python manage.py test
```

---

## 10. Recent UI/UX & Mobile Responsiveness Improvements
*   **Overlap Resolution**: Removed conflicting Bootstrap classes from the sidebar brand container. This lets the custom CSS top-padding of `85px` take effect on mobile screens, successfully shifting the "IT Helpdesk" logo below the floating hamburger close button (`menu-toggle`) to prevent overlaps.
*   **Recent Activity Polish**: Redesigned the activity list under `helpdesk/templates/helpdesk/profile.html` to dynamically stack into a vertical column on extra small screens and realign dates smoothly, ensuring readability on all mobile phone viewports.

# helpdesk-web
