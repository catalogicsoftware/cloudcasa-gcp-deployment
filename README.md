## About CloudCasa integration with GCP
CloudCasa supports direct integration with Google Cloud Platform on a per-project basis using a custom role. It uses the integration to automatically discover all GKE clusters within the given project and to provide advanced backup and restore features. These include backup of GKE cluster configuration parameters and automatic creation or re-creation of clusters on restore.


## Choose Google Cloud project to link
Select the Google Cloud project that you want to connect to with CloudCasa:
```
gcloud config set project <project-id>
```

## Enable the required APIs
Once the project ID is set, [**enable the required APIs**](https://console.cloud.google.com/flows/enableapi?apiid=iam.googleapis.com,deploymentmanager.googleapis.com,compute.googleapis.com,cloudresourcemanager.googleapis.com). These are the iam, deploymentmanager, computeengine, and cloudresourcemanager APIs.


## Assign the "Owner" role to the "Google APIs Service Agent" principal
Since we deploy a custom role and bind it to a Service Account, before the final step we need to make sure that Google Cloud Shell has the right permissions.
1. In the Google Cloud console, [**Go to the IAM page**](https://console.cloud.google.com/iam-admin/iam).
2. From the list of principals, locate the principal with the name **Google APIs Service Agent**.
3. Edit the service account's roles by clicking the **Edit** button, then add the **Roles > Owner** role.
4. Click **Save** to apply the role.

Once the template is deployed successfully, the "Owner" role can and should be removed from the "Google APIs Service Agent" principal.


## Connect your Google Cloud Project with CloudCasa
In order to complete the integration with your GCP project, execute the command displayed in the CloudCasa UI with the following format:
```
sh connect_with_cloudcasa.sh <cloudcasa-cloud-account-id>
```

Once the script finishes successfully, the Cloud Account in CloudCasa will be marked as active, and the resource inventory process will start.
In case of any errors, please contact [CloudCasa Support](https://cloudcasa.io/support/).
