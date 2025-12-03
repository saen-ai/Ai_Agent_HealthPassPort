# GCP Cloud Storage Setup Guide

This guide will help you set up Google Cloud Platform (GCP) Cloud Storage for profile picture uploads.

## Step 1: Create a GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "New Project"
4. Enter project name: `health-passport` (or your preferred name)
5. Click "Create"
6. Wait for the project to be created and select it

## Step 2: Enable Cloud Storage API

1. In the GCP Console, go to "APIs & Services" > "Library"
2. Search for "Cloud Storage API"
3. Click on it and click "Enable"

## Step 3: Create a Storage Bucket

1. Go to "Cloud Storage" > "Buckets" in the left sidebar
2. Click "Create Bucket"
3. Configure the bucket:
   - **Name**: `health-passport-profiles` (must be globally unique, so you may need to add numbers/random string)
   - **Location type**: Choose "Region" and select a region closest to your users (e.g., `us-central1`, `europe-west1`, `asia-southeast1`)
   - **Storage class**: Standard
   - **Access control**: Uniform (recommended)
   - **Protection tools**: Leave defaults or configure as needed
4. Click "Create"

## Step 4: Create a Service Account

1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Enter details:
   - **Service account name**: `health-passport-storage`
   - **Service account ID**: Will auto-populate
   - **Description**: "Service account for Health Passport file uploads"
4. Click "Create and Continue"
5. Grant role: Select "Storage Admin" (or "Storage Object Admin" for more restricted access)
6. Click "Continue" then "Done"

## Step 5: Create and Download Service Account Key

1. Click on the service account you just created
2. Go to the "Keys" tab
3. Click "Add Key" > "Create new key"
4. Select "JSON" format
5. Click "Create"
6. The JSON key file will download automatically - **SAVE THIS FILE SECURELY**

## Step 6: Configure Bucket Permissions (Optional but Recommended)

1. Go to "Cloud Storage" > "Buckets"
2. Click on your bucket name
3. Go to "Permissions" tab
4. Click "Grant Access"
5. Add the service account email (from Step 4)
6. Select role: "Storage Object Admin"
7. Click "Save"

## Step 7: Make Bucket Public for Profile Pictures (Optional)

If you want profile pictures to be publicly accessible:

1. Go to your bucket
2. Click on "Permissions" tab
3. Click "Add Principal"
4. Add `allUsers` as principal
5. Select role: "Storage Object Viewer"
6. Click "Save"
7. Confirm the warning about making objects public

**Note**: Alternatively, you can use signed URLs for private access (more secure but requires additional implementation).

## Step 8: Configure Environment Variables

Add these to your `.env` file in the backend directory:

```env
# GCP Storage Configuration
GCP_STORAGE_BUCKET_NAME=health-passport-profiles
GCP_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
```

**Important Notes:**
- Replace `your-project-id` with your actual GCP project ID
- Replace `/path/to/your/service-account-key.json` with the absolute path to the JSON key file you downloaded
- On Windows, use forward slashes or double backslashes: `C:/path/to/key.json` or `C:\\path\\to\\key.json`
- For production, consider storing the key file securely and using environment variables or a secrets manager

## Step 9: Install Dependencies

The required dependencies are already in `pyproject.toml`. Install them:

```bash
cd Backend_Health_passport
uv sync
```

Or if using pip:
```bash
pip install google-cloud-storage pillow
```

## Step 10: Test the Setup

1. Start your backend server
2. Try uploading a profile picture through the account page
3. Check the GCP Console > Cloud Storage > Buckets > your-bucket-name to see if the file was uploaded
4. Verify the file is accessible via the public URL returned

## Troubleshooting

### Error: "Could not automatically determine credentials"
- Make sure `GOOGLE_APPLICATION_CREDENTIALS` points to the correct JSON key file path
- Verify the JSON key file is valid and not corrupted
- Check that the service account has the correct permissions

### Error: "Bucket not found"
- Verify `GCP_STORAGE_BUCKET_NAME` matches your bucket name exactly
- Check that the bucket exists in the correct project
- Ensure the service account has access to the bucket

### Error: "Permission denied"
- Verify the service account has "Storage Admin" or "Storage Object Admin" role
- Check bucket permissions in the GCP Console

### Files not publicly accessible
- If using public access, ensure you've added `allUsers` with "Storage Object Viewer" role
- Check that `blob.make_public()` is being called in the upload service
- Verify CORS settings if accessing from a web browser

## Security Best Practices

1. **Don't commit the service account key file to git** - Add it to `.gitignore`
2. **Use least privilege** - Only grant necessary permissions to the service account
3. **Consider signed URLs** - For production, use signed URLs instead of public access
4. **Set up bucket lifecycle policies** - Automatically delete old/unused files
5. **Enable bucket versioning** - For backup and recovery
6. **Monitor access** - Use Cloud Audit Logs to track access

## Cost Considerations

- Cloud Storage pricing is based on:
  - Storage amount (per GB/month)
  - Network egress (data transfer out)
  - Operations (read/write requests)
- For profile pictures, costs should be minimal
- Consider setting up budget alerts in GCP Console
