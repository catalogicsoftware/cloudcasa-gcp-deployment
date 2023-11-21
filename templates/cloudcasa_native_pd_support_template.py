cloudcasa_sa_name = "serviceAccount:cloudcasa-poc@wired-ripsaw-330217.iam.gserviceaccount.com"

def GenerateConfig(context):
    project_id = context.env["project"]

    """Generate configuration."""
    cloudcasa_custom_role = {
        "name": "cloudcasa-role",
        "type": "gcp-types/iam-v1:projects.roles",
        "properties": {
            "parent": f"projects/{project_id}",
            "roleId": "CloudCasa",
            "role": {
                "title": "CloudCasa",
                "description": "CloudCasa role used for GKE cluster autodiscovery and restore",
                "stage": "ALPHA",
                "includedPermissions": [
                    "container.clusters.create",
                    "container.clusters.update",
                    "container.clusters.delete",
                    "container.clusters.get",
                    "container.clusters.getCredentials",
                    "container.clusters.list",
                    "container.serviceAccounts.create",
                    "container.serviceAccounts.get",
                    "container.serviceAccounts.update",
                    "container.deployments.create",
                    "container.deployments.get",
                    "container.deployments.list",
                    "container.deployments.update",
                    "container.namespaces.create",
                    "container.namespaces.get",
                    "container.namespaces.update",
                    "container.clusterRoleBindings.create",
                    "container.clusterRoleBindings.get",
                    "container.clusterRoleBindings.update",
                    "container.clusterRoles.bind",
                    "container.clusterRoles.create",
                    "container.clusterRoles.escalate",
                    "container.operations.get",
                    "container.pods.list",
                    "container.events.list",
                    "container.customResourceDefinitions.create",
                    "container.customResourceDefinitions.get",
                    "container.thirdPartyObjects.create",
                    "container.thirdPartyObjects.get",
                    "container.daemonSets.create",
                    "container.secrets.create",
                    "compute.disks.list",
                    "compute.regions.get",
                    "compute.regions.list",
                    "compute.zones.get",
                    "compute.zones.list",
                    "compute.machineTypes.get",
                    "compute.machineTypes.list",
                    "compute.networks.list",
                    "compute.networks.get",
                    "compute.networks.create",
                    "compute.networks.updatePolicy",
                    "compute.networks.delete",
                    "compute.subnetworks.get",
                    "compute.subnetworks.create",
                    "compute.subnetworks.delete",
                    "compute.globalAddresses.list",
                    "compute.globalAddresses.create",
                    "compute.globalAddresses.delete",
                    "iam.serviceAccounts.actAs",
                ]
            }
        }
    }

    iam_member_cloud_casa = {
        "name": "cloudcasa-iam-member-project",
        "type": "gcp-types/cloudresourcemanager-v1:virtual.projects.iamMemberBinding",
        "properties": {
            "resource": project_id,
            "member": cloudcasa_sa_name,
            "role": f"projects/{project_id}/roles/CloudCasa"
        },
        "metadata": {
            "dependsOn": [
                "cloudcasa-role"
            ]
        }
    }

    cloud_casa_native_gce_pd_support_role = {
        "name": "CloudCasa native Persistent Disk support role",
        "type": "gcp-types/iam-v1:projects.roles",
        "properties": {
            "parent": f"projects/{project_id}",
            "roleId": "CloudCasaNativePdSupportRole",
            "role": {
                "title": "CloudCasa native Persistent Disk volume support",
                "description": "This role is used to support backup and restore of native Google Persistent Disk volumes",
                "stage": "ALPHA",
                "includedPermissions": [
                    "compute.disks.get",
                    "compute.disks.create",
                    "compute.disks.createSnapshot",
                    "compute.snapshots.get",
                    "compute.snapshots.create",
                    "compute.snapshots.useReadOnly",
                    "compute.snapshots.delete",
                    "compute.zones.get"
                ]
            }
        }
    }

    # Service account for which temp credentials are generated by CloudCasa service account.
    cloud_casa_native_gce_pd_support_sa_id = "cloudcasa-native-pd-support"
    cloud_casa_native_gce_pd_support_sa = {
        "name": "cloudcasa-native-pd-support-sa",
        "type": "gcp-types/iam-v1:projects.serviceAccounts",
        "properties": {
            "accountId": cloud_casa_native_gce_pd_support_sa_id,
            "displayName": "CloudCasa native Persistent Disk volume support"
        },
        "accessControl": {
            "gcpIamPolicy": {
                "bindings": [
                    {
                        "role": "roles/iam.serviceAccountTokenCreator",
                        "members": [
                            cloudcasa_sa_name
                        ]
                    }
                ]
            }
        },
        "metadata": {
            "dependsOn": [
                cloud_casa_native_gce_pd_support_role["name"]
            ]
        }
    }

    iam_member_cloud_casa_native_pd = {
        "name": "cloudcasa-compute-disk-access-iam-member-project",
        "type": "gcp-types/cloudresourcemanager-v1:virtual.projects.iamMemberBinding",
        "properties": {
            "resource": project_id,
            "member": "serviceAccount:{}@{}.iam.gserviceaccount.com".format(cloud_casa_native_gce_pd_support_sa_id, project_id),
            "role": "projects/{}/roles/{}".format(project_id, cloud_casa_native_gce_pd_support_role["properties"]["roleId"])
        },
        "metadata": {
            "dependsOn": [
                cloud_casa_native_gce_pd_support_sa["name"]
            ]
        }
    }

    resources = []
    # Standard support for GCP
    resources.append(cloudcasa_custom_role)
    resources.append(iam_member_cloud_casa)

    resources.append(cloud_casa_native_gce_pd_support_role)
    resources.append(cloud_casa_native_gce_pd_support_sa)
    resources.append(iam_member_cloud_casa_native_pd)

    return {"resources": resources}
