# Deployment Guide

This guide covers deploying the Polyurethane Observatory Platform to Streamlit Cloud.

## Prerequisites

1. **GitHub Repository**: Your code must be pushed to GitHub
2. **Streamlit Cloud Account**: Sign up at https://share.streamlit.io
3. **Supabase Project**: Set up your database and get credentials
4. **OpenAI Account**: Get API key and create Assistant

## Step-by-Step Deployment

### 1. Prepare Your Repository

Ensure all necessary files are committed:
- ✅ All Python files (`*.py`)
- ✅ `requirements.txt`
- ✅ `Background Documentation/` folder with logos
- ✅ `.streamlit/config.toml` (optional)
- ✅ `README.md`
- ❌ `.env` file (NEVER commit this)
- ❌ `admin_users.json` (contains passwords)

### 2. Set Up Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with your GitHub account
3. Click **"New app"**
4. Select your repository: `stefanhermes-code/Observatory`
5. Choose the branch: `main` (or your default branch)

### 3. Deploy Each App Separately

You need to deploy each app as a separate Streamlit Cloud app:

#### App 1: Configurator
- **Main file path**: `configurator_app.py`
- **App URL**: Will be generated (e.g., `https://observatory-configurator.streamlit.app`)

#### App 2: Admin
- **Main file path**: `admin_app.py`
- **App URL**: Will be generated (e.g., `https://observatory-admin.streamlit.app`)

#### App 3: Generator
- **Main file path**: `generator_app.py`
- **App URL**: Will be generated (e.g., `https://observatory-generator.streamlit.app`)

### 4. Configure Secrets

For each app, go to **Settings → Secrets** and add:

```toml
[secrets]
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key-here"
OPENAI_API_KEY = "sk-..."
OPENAI_ASSISTANT_ID = "asst_..."
OPENAI_VECTOR_STORE_ID = "vs_..."  # Optional
OWNER_EMAIL = "admin@example.com"
OWNER_PASSWORD = "your-secure-password"
```

**Important:** These secrets are encrypted and only accessible to your app at runtime.

### 5. Verify File Paths

The apps reference these files:
- `Background Documentation/PU Observatory logo V3.png`
- `Logo in blue steel no BG.png`
- `Background Documentation/Signature.jpg` (for invoices)

Ensure these files are committed to GitHub. If they're not, the apps will still work but logos won't display.

### 6. Test Deployment

After deployment:
1. Visit each app URL
2. Test basic functionality
3. Check logs in Streamlit Cloud dashboard if errors occur

## Troubleshooting

### Common Issues

#### 1. "Module not found" errors
- **Solution**: Ensure `requirements.txt` includes all dependencies
- Check that all `core/` modules are committed

#### 2. "Supabase connection failed"
- **Solution**: Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` in secrets
- Check Supabase project is active

#### 3. "Logo not found"
- **Solution**: Ensure `Background Documentation/` folder is committed
- Check file paths match exactly (case-sensitive)

#### 4. "OpenAI API error"
- **Solution**: Verify `OPENAI_API_KEY` and `OPENAI_ASSISTANT_ID` in secrets
- Check API key has sufficient credits

#### 5. "Authentication failed"
- **Solution**: Verify `OWNER_EMAIL` and `OWNER_PASSWORD` in secrets
- Check admin user exists in database

### Viewing Logs

In Streamlit Cloud:
1. Go to your app dashboard
2. Click **"Manage app"**
3. Click **"Logs"** tab
4. Check for error messages

### Updating Apps

1. Push changes to GitHub
2. Streamlit Cloud automatically redeploys
3. Check deployment status in dashboard

## Environment-Specific Configuration

### Local Development
- Uses `.env` file (not committed)
- Runs on `localhost:8501/8502/8503`

### Streamlit Cloud
- Uses secrets from Streamlit Cloud settings
- Runs on `*.streamlit.app` domains
- Automatically handles HTTPS and scaling

## Security Best Practices

1. **Never commit secrets** to GitHub
2. **Use Streamlit Cloud secrets** for all sensitive data
3. **Rotate passwords** regularly
4. **Monitor audit logs** in Admin app
5. **Review access logs** in Streamlit Cloud dashboard

## Next Steps

After deployment:
1. Test all three apps thoroughly
2. Set up custom domains (if needed)
3. Configure monitoring and alerts
4. Document your app URLs for users

## Support

For deployment issues:
- Check Streamlit Cloud documentation: https://docs.streamlit.io/streamlit-cloud
- Review app logs in Streamlit Cloud dashboard
- Open an issue on GitHub

