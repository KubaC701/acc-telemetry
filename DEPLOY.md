# Deployment Guide: Hugging Face Spaces

## Backend Deployment

1.  **Create a New Space**:
    *   Go to [huggingface.co/spaces](https://huggingface.co/spaces).
    *   Click **"Create new Space"**.
    *   **Name**: `acc-telemetry-backend` (or similar).
    *   **License**: MIT (or your choice).
    *   **SDK**: Select **Docker**.
    *   **Hardware**: Select **Free** (2 vCPU, 16GB RAM).
    *   Click **"Create Space"**.

2.  **Push Code**:
    *   You can clone the Space repository and copy your files into it, OR add the Space as a remote to your existing git repo.
    *   **Option A (Add Remote)**:
        ```bash
        git remote add space https://huggingface.co/spaces/YOUR_USERNAME/acc-telemetry-backend
        git push space main
        ```
        *(Note: You might need to force push `git push space main -f` if the history differs, or pull first).*

3.  **Wait for Build**:
    *   The "Building" status will appear on your Space page.
    *   Once "Running", your API is live at `https://YOUR_USERNAME-acc-telemetry-backend.hf.space`.

## Frontend Deployment (Vercel/Netlify)

1.  **Update API URL**:
    *   In your frontend code (`frontend/src/api/client.ts` or `.env`), update the backend URL to point to your new Hugging Face Space URL.
    *   Example: `https://YOUR_USERNAME-acc-telemetry-backend.hf.space` (Note: Ensure no trailing slash if your code appends paths).

2.  **Deploy**:
    *   Push your `frontend` folder changes to GitHub.
    *   Import the repository in Vercel/Netlify.
    *   Set the **Root Directory** to `frontend`.
    *   Deploy.

## Important Notes

*   **Ephemeral Storage**: Any videos uploaded to the backend will be **deleted** if the Space restarts (which happens after 48h of inactivity or new deployments).
*   **Public Access**: By default, your Space is public. Anyone can access your API. You can make it private in Settings, but then you'll need to handle authentication/tokens for your frontend to access it.
