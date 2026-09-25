# Google Cloud Setup for Student Data Verification Portal

This document outlines how to set up the Google Cloud infrastructure required for the Google Sign-In (OAuth 2.0 / OpenID Connect) integration used by the Student Data Verification Portal.

## 1. Prerequisites
- The Google Cloud SDK (`gcloud` CLI) installed and available in your `PATH`.
- A Google account that you wish to use as the owner/administrator for the project.

## 2. Checking the Active Account
To see which account is currently authenticated in your CLI, run:
```bash
gcloud auth list
```
The active account will have an asterisk (`*`) next to it.

## 3. Switching Accounts
If you need to perform the setup using a different Google Cloud account (e.g., your official Poornima Workspace account), log in by running:
```bash
gcloud auth login
```
This will open a browser window for you to authenticate.

## 4. Listing and Selecting Projects
To list existing projects associated with your account:
```bash
gcloud projects list
```
To set an existing project as the default for your terminal session:
```bash
gcloud config set project [YOUR_PROJECT_ID]
```

## 5. Creating a New Project (Automated)
The project for the Student Data Verification Portal has been created automatically.

**Project Details:**
- **Google Account Used:** `piyushagarwalnew@gmail.com`
- **Project Display Name:** Student Data Portal Auth
- **Project ID:** `student-data-portal-auth-7317`
- **Project Number:** `232766992613`

The command used to create and select the project was:
```bash
PROJECT_ID="student-data-portal-auth-$RANDOM"
gcloud projects create $PROJECT_ID --name="Student Data Portal Auth"
gcloud config set project $PROJECT_ID
gcloud projects describe $PROJECT_ID
```

To re-select this project in the future, run:
```bash
gcloud config set project student-data-portal-auth-7317
```

## 6. Required APIs/Services
Google OAuth for simple Sign-In is largely available by default, but it relies on Identity and Access Management APIs and the Cloud Resource Manager API in some workflows. No special paid APIs or heavy services are required.

## 7. OAuth Configuration Requirements
Setting up the OAuth Consent Screen and creating the OAuth Client Credentials requires configuring the visual presentation of the app and explicitly trusting origins.

## 8. Internal vs. External Application
**The application MUST be configured as an External application.**

*Why?* An Internal application restricts access exclusively to users who share the identical Google Workspace organization as the Google Cloud project's creator. Since the application explicitly serves `poornima.edu.in` and `poornima.org`, any project created outside of their primary Workspace (or created via a personal `@gmail.com` or alternative organization like `hellop4747-org`) will strictly block these users if set to Internal. Using External allows any Google user to try logging in, while our FastAPI backend strictly enforces the allowed domains and automatically blocks unauthorized access.

## 9. Required Authorized Origins
When creating the OAuth Client ID, you must specify authorized JavaScript origins so the frontend can securely initiate the flow.
- **Local Development:** `http://localhost:5173`

## 10. Required Redirect URIs
The redirect URI must match exactly where the user is sent after authenticating.
- **Local Development:** `http://localhost:5173` and `http://localhost:5173/auth/callback` (Add both for development flexibility).

## 11. Required OAuth Scopes
Only the absolute minimum identity scopes are needed (do NOT request Gmail, Drive, etc.).
- `openid`
- `.../auth/userinfo.email`
- `.../auth/userinfo.profile`

## 12. OAuth Client ID Handling
The OAuth Client ID is safe to be public (it is used by the browser to initiate the login).
- Add it to the **Frontend** `.env.local` file as `VITE_GOOGLE_CLIENT_ID`.
- Add it to the **Backend** `.env` file as `GOOGLE_CLIENT_ID`.

## 13. OAuth Client Secret Handling Securely
The OAuth Client Secret is a highly sensitive credential used by the backend to securely exchange codes for tokens.
- Add it **ONLY** to the **Backend** `.env` file as `GOOGLE_CLIENT_SECRET`.
- **Never** commit it to Git.
- **Never** expose it to the frontend code or browser.

## 14. Required Environment Variables
Ensure the following files are populated locally (both are gitignored):

**Backend (`backend/.env`):**
```env
GOOGLE_CLIENT_ID="<your-oauth-client-id>"
GOOGLE_CLIENT_SECRET="<your-oauth-client-secret>"
GOOGLE_REDIRECT_URI="http://localhost:5173"
```

**Frontend (`frontend/.env.local`):**
```env
VITE_GOOGLE_CLIENT_ID="<your-oauth-client-id>"
```

## 15. Reproducing the Setup Later
If you want to use another Google account later:
1. Run `gcloud auth login` and sign in with the target account.
2. Follow the project creation step (Section 5).
3. Proceed to the manual steps below using the Google Cloud Console.
4. Update your `.env` files with the newly generated Client ID and Secret.

## 16. Manual Steps (Cannot be fully automated via `gcloud`)
The `gcloud` CLI does not natively support creating standard Web Application OAuth credentials or configuring the visual OAuth Consent Screen without heavily leveraging the Identity-Aware Proxy (IAP) REST API, which is brittle and overkill for a simple web app. 

You must perform these final steps in the Google Cloud Console:
1. Visit the [Google Cloud Console](https://console.cloud.google.com/).
2. Select your newly created project (e.g., `$PROJECT_ID`).
3. Navigate to **APIs & Services > OAuth consent screen**.
    - Select **External**.
    - Fill out the App name, User support email, and Developer contact information.
    - Add the required scopes (`openid`, `email`, `profile`).
4. Navigate to **APIs & Services > Credentials**.
    - Click **Create Credentials > OAuth client ID**.
    - Select **Web application** as the application type.
    - Add the **Authorized JavaScript origins** and **Authorized redirect URIs** (Sections 9 & 10).
    - Click **Create**.
5. Copy the provided Client ID and Client Secret into your `.env` files (Section 14).
