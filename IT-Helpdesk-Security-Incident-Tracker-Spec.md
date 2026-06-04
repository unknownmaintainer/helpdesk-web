# HelpDeskPro: IT Support and Security Incident Tracker

## 1. System Overview

### Project Title
**HelpDeskPro: IT Support and Security Incident Tracker**

### Project Description
HelpDeskPro is a beginner-friendly, enterprise-inspired web system for employees to submit IT support tickets and simple security reports.

Employees can report common issues, track ticket status, and see updates in one centralized dashboard. IT staff can manage tickets, add notes, and resolve requests. Administrators can assign tickets, generate reports, and manage users.

This version is intentionally simplified for a capstone/project presentation: it uses easy-to-understand ticket status flows, straightforward roles, and polished UI elements without complex cybersecurity integrations.

---

## 2. Main Objectives

### General Objective
Build a clean, professional helpdesk platform that supports ticket tracking and basic incident reporting.

### Specific Objectives
- Let employees submit helpdesk tickets and security reports.
- Show ticket and incident progress clearly.
- Allow IT staff to update and resolve tickets.
- Enable administrators to manage users and assign work.
- Keep a simple audit trail of ticket actions.
- Present a professional dashboard for monitoring activity.

---

## 3. User Roles

### Employee
Can:
- Submit tickets.
- Submit security reports.
- View their own tickets.
- Check ticket status.

### IT Staff
Can:
- View all tickets.
- Update ticket status.
- Add notes.
- Resolve tickets.

### Administrator
Can:
- Manage users.
- Assign tickets.
- Generate reports.
- Close tickets.
- View dashboard statistics.

---

## 4. Ticket Status Workflows

### Helpdesk Ticket Status
- Open
- In Progress
- Resolved
- Closed

### Security Incident Status
- Reported
- Investigating
- Fixed
- Closed

These workflows are easy for beginners and still support clear issue tracking.

---

## 5. Key Features

### Dashboard
Display:
- Total Tickets
- Open Tickets
- Resolved Tickets
- Security Reports

Example:
```
------------------------------------
| 12 Open Tickets                  |
| 25 Resolved Tickets              |
| 5 Security Reports               |
------------------------------------
```

### Submit Ticket
Fields:
- Title
- Description
- Category
- Priority (Low / Medium / High)
- Attachment
- Submit button

### Submit Security Incident
Fields:
- Incident Title
- Description
- Incident Type (Suspicious Email, Malware, Unauthorized Access, Lost Device)
- Attachment
- Submit Report button

### Ticket List
- Search bar
- Status filters: Open / In Progress / Resolved / Closed
- Ticket table with ID, Title, Status, Priority

### Ticket Details
Show:
- Ticket information
- Title and description
- Priority and current status
- Comments / notes
- Attachments

### Admin Panel
Includes:
- Assign ticket
- Update status
- Close ticket
- View reports
- Manage users

---

## 6. Simplified Security Requirements

### Login Authentication
- Only registered users can access the system.

### Role-Based Access
- Employees cannot edit other users' tickets.
- IT staff and admins have the appropriate level of access.

### Activity Logs
Record events such as:
- Ticket created
- Ticket updated
- Ticket closed

### Rate Limiting
Protect submissions with a simple limit, for example:
- 5 ticket submissions per minute

---

## 7. Database Tables

### Users
Fields:
- ID
- Name
- Email
- Password
- Role

### Tickets
Fields:
- Ticket ID
- Title
- Description
- Category
- Priority
- Status
- Created By
- Assigned To
- Date Created

### Security Reports
Fields:
- Report ID
- Title
- Description
- Incident Type
- Status
- Reported By
- Date Reported

### Activity Logs
Fields:
- Log ID
- User
- Action
- Timestamp

---

## 8. UI Plan

### Layout Principles
- Clean spacing
- Clear visual hierarchy
- Simple navigation
- Consistent card-based layout
- Soft corporate palette with bold status colors

### Login Page
```
------------------
     HelpDeskPro

 Email
 Password

 [ Login ]
------------------
```

### Dashboard
```
---------------------------------
| Open Tickets | 12            |
| Resolved     | 25            |
| Incidents    | 5             |
---------------------------------

Recent Tickets
Recent Incidents
```

### Sidebar Menu
- Dashboard
- Tickets
- Security Reports
- Users
- Reports
- Logout

### Ticket List Page
- Search bar
- Status filter buttons
- Compact table rows
- Action button per ticket

### Ticket Details Page
- Ticket summary block
- Notes and attachments section
- Status card with current state

### Admin Page
- Assignment card
- Status update controls
- Report summary widgets

---

## 9. Recommended Color Theme
- Blue → primary
- White → background
- Light gray → cards
- Green → resolved
- Orange → in progress
- Red → high priority

This structure keeps the system simple, polished, and beginner-friendly while still feeling enterprise-inspired.
