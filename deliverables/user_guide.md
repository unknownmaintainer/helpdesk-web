# HelpDeskPro: User & Operator Guide

Welcome to the **HelpDeskPro User & Operator Guide**. This document provides detailed, step-by-step instructions on how to use and manage the HelpDeskPro system, categorized by user roles and workflows.

---

## 1. Getting Started

### Accessing the Web Portal
1. Open your web browser and navigate to the application URL:
   * **Local Server:** `http://127.0.0.1:8000/`
   * **Live Deployment (Render):** `https://helpdesk-web.onrender.com/` (or your specific live URL)
2. You will be greeted by the secure login screen.

### Default Seed Accounts
For testing and demonstration purposes, the system is pre-seeded with the following roles:
* **IT Manager / Administrator:** `admin@gmail.com` | Password: `admin123`
* **Employee (Regular User):** `employee@gmail.com` | Password: `password123`
* **Developer (Developer / Employee):** `dev@gmail.com` | Password: `password123`

---

## 2. Regular Employee Workflow

Ordinary employees use the system to request help, report security anomalies, and track progress.

### A. Submitting an IT Support Ticket
1. Navigate to **Submit Ticket** in the sidebar menu.
2. Fill out the form fields:
   * **Title:** Enter a short summary of the issue (e.g., *"Cannot connect to printers"*).
   * **Description:** Add detailed context (e.g., *"I tried printing from Word but it says offline"*).
   * **Category:** Choose from Hardware, Software, Network, or Account.
   * **Priority:** Select Low, Medium, or High depending on the urgency.
   * **Attachment (Optional):** Upload an image or diagnostic screenshot.
3. Click **Submit Ticket**.

### B. Reporting a Security Incident
1. Go to the same **Submit Ticket** page.
2. Select the **Security Incident** tab or choose the **Security** category.
3. Select the **Incident Type** (e.g., Suspicious Email, Malware, Unauthorized Access, Lost Device).
4. Provide a detailed description of the threat.
5. Click **Submit Report**.

### C. Tracking Progress & Dashboard
* **Dashboard Overview:** Displays your personalized metrics: Open Tickets, Resolved Tickets, and Recent Submissions.
* **My Tickets List:** View all tickets you have submitted. Click **View Ticket** to open the details view, see comments from IT managers, and view the visual **NIST Incident Response Timeline** showing where your ticket sits (e.g., *Preparation*, *Detection*, *Eradication*, *Post-Incident Review*).

---

## 3. IT Manager / Staff Workflow

IT Staff and Managers resolve tickets, coordinate workflows, and manage the user base.

### A. Managing Tickets & Updating NIST Stages
1. Go to **Tickets Queue** to see all active tickets submitted across the company.
2. Click **View Ticket** on any request to open its incident workspace:
   * **Add Progress Updates:** Write progress notes or resolutions.
   * **Update Ticket Status / NIST Stage:** Change the status (e.g., from *Open* to *In Progress* or *Resolved*). This automatically updates the visual stepper tracking the **NIST Incident Response Stage**.
   * **Add Resolution Notes:** Once fixed, input resolution notes and set the ticket to *Resolved*.

### B. User Activation & Deactivation
1. Navigate to **Users** in the sidebar.
2. Review the list of active IT Managers and Employees.
3. Click **Deactivate** on any user who leaves the department or company. Deactivated users cannot log in or generate new security incidents.
4. Click **Activate** to instantly restore a user's access.

---

## 4. Security & Integrations Workflow (Developer Tools)

If you are a Developer, Auditor, or API Integrator, you can interface with HelpDeskPro programmatically.

### A. System Integrations Page
1. Go to the **Integrations** page in the sidebar.
2. **API Status Badge:** Verifies that DRF endpoint listeners are active.
3. **Connected Services:** Lists external security tools (like firewalls or SIEM logs) connected via JWT.
4. **Live Alert Simulator:**
   * Under **Simulate Security Alert**, click any simulation button (e.g., *Simulate Malware Detection*).
   * The terminal console will print real-time diagnostic outputs showing the JWT API connection, automatic ticket generation (e.g., *Ticket #52*), and database record insertions.

### B. Postman Integration & JWT Generation
1. Export or locate the [postman_collection.json](file:///c:/Users/Dion/Desktop/IT%20Helpdesk/postman_collection.json) in the project directory.
2. Import the collection into Postman.
3. Follow the chronological folders:
   * **Folder 1 (Authentication):** Run the Login request. The test script will auto-extract the token.
   * **Folder 2 (Mileage API):** View driver mileage logs. Note the field-level masking in action (Employees see `***`, Managers see real prices).
   * **Folder 3 (Tickets API):** Test programmatic ticket submission.
