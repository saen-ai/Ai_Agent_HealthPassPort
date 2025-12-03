# Fix GCP Bucket Permissions

## Issue
The service account `healthpassport@upbeat-plating-475419-k3.iam.gserviceaccount.com` does not have the necessary permissions to access the `healthpassport` bucket.

## Solution: Grant Permissions in GCP Console

### Option 1: Grant Permissions via Bucket IAM (Recommended)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **Cloud Storage** > **Buckets**
3. Click on the bucket name: **healthpassport**
4. Click on the **Permissions** tab
5. Click **Grant Access**
6. In the **New principals** field, enter:
   ```
   healthpassport@upbeat-plating-475419-k3.iam.gserviceaccount.com
   ```
7. In the **Select a role** dropdown, choose one of:
   - **Storage Admin** (full access - recommended for development)
   - **Storage Object Admin** (can create/delete objects but not manage bucket settings)
8. Click **Save**

### Option 2: Grant Permissions via Project IAM

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **IAM & Admin** > **IAM**
3. Find or search for: `healthpassport@upbeat-plating-475419-k3.iam.gserviceaccount.com`
4. If it doesn't exist, click **Grant Access** and add it
5. Click the pencil icon (Edit) next to the service account
6. Add role: **Storage Admin** or **Storage Object Admin**
7. Click **Save**

### Option 3: Use gcloud CLI (If you have it installed)

```bash
# Grant Storage Object Admin role to the service account on the bucket
gsutil iam ch serviceAccount:healthpassport@upbeat-plating-475419-k3.iam.gserviceaccount.com:roles/storage.objectAdmin gs://healthpassport

# Or grant Storage Admin role (more permissions)
gsutil iam ch serviceAccount:healthpassport@upbeat-plating-475419-k3.iam.gserviceaccount.com:roles/storage.admin gs://healthpassport
```

## Required Permissions

The service account needs at minimum:
- `storage.objects.create` - To upload files
- `storage.objects.get` - To read/access files
- `storage.objects.delete` - To delete files (optional, for future cleanup)

These are included in:
- **Storage Object Admin** role (recommended minimum)
- **Storage Admin** role (full access)

## Verify Permissions

After granting permissions:

1. Restart your backend server
2. Try uploading a profile picture again
3. Check the logs - you should see "Successfully uploaded profile picture" instead of permission errors

## Troubleshooting

If you still get permission errors after granting access:

1. **Wait a few minutes** - IAM changes can take up to 5 minutes to propagate
2. **Check the bucket name** - Ensure it's exactly `healthpassport` (case-sensitive)
3. **Verify service account email** - Must match exactly: `healthpassport@upbeat-plating-475419-k3.iam.gserviceaccount.com`
4. **Check project** - Ensure you're in the correct project: `upbeat-plating-475419-k3`
5. **Try Storage Admin role** - If Storage Object Admin doesn't work, try Storage Admin
