## About CloudCasa integration with GCP
CloudCasa by Catalogic supports integration with Google Cloud. CloudCasa will automatically discover all GKE clusters within the given project.\
It does not only protect Kubernetes resources and PersistentVolume data, but it also does protect cluster configuration.\
CloudCasa implements advanced recovery by backing up the configuration of each GKE cluster, we could recreate them on the fly during data recoveries.

## Integrate GCP project with CloudCasa
In order to integrate your GCP project, please execute the following command in the Google Cloud Shell:
```
sh connect_with_cloudcasa.sh <cloudcasa-cloud-account-id>
```

Once the script finishes successfully, the Cloud Account in CloudCasa will be marked as active, and the resource inventory process will start.
In case of any errors, please contact CloudCasa support at [home.cloudcasa.io](https://home.cloudcasa.io/).
