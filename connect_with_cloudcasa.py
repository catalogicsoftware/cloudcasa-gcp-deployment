import os
import time
import sys
import subprocess
import requests
from pathlib import Path

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_error(*args, exit=True):
    print(bcolors.BOLD+bcolors.FAIL, end="")
    print("[ERROR]", *args, bcolors.END)
    if exit:
        sys.exit(1)

def print_success(*args):
    print(bcolors.BOLD+bcolors.OKGREEN, end="")
    print("[SUCCESS]", *args, bcolors.END)

def print_info(*args):
    print(bcolors.BOLD, end="")
    print("[INFO]", *args, bcolors.END)


cc_api_url = "https://api.staging.cloudcasa.io"
if os.getenv("CC_API_URL"):
    cc_api_url = os.environ["CC_API_URL"]

templates_dir = Path(__file__).absolute().parent.joinpath("templates")
timestamp = int(time.time())
deployment_name = f"cloudcasa-deployment"

required_gcloud_apis = {
    "iam": {
        "display_name": "Identity and Access Management (IAM)",
        "gcloud_service_name": "iam.googleapis.com"
    },
    "deployment_manager": {
        "display_name": "Deployment Manager",
        "gcloud_service_name": "deploymentmanager.googleapis.com"
    },
    "compute_engine": {
        "display_name": "Compute Engine",
        "gcloud_service_name": "compute.googleapis.com"
    },
    "cloud_resource_manager": {
        "display_name": "Cloud Resource Manager",
        "gcloud_service_name": "cloudresourcemanager.googleapis.com"
    },
}


def validate_environment():
    print_info("Checking if all the required steps were completed...")
    if len(sys.argv) != 2:
        print_error("Unexpected number of arguments received. Please make sure the command has the following format: python3 connect_with_cloudcasa.py <cloudaccount-id>")

    if not os.getenv("DEVSHELL_PROJECT_ID"):
        print_error("GCP Project is not set. Please set the project using \"gcloud config set project <project-id>\" command")

    gcp_project_id = os.environ["DEVSHELL_PROJECT_ID"]

    gcp_project_number_cmd = f"gcloud projects describe {gcp_project_id} --format=\"value(projectNumber)\""
    gcp_project_number = subprocess.run(
            gcp_project_number_cmd, check=True, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode("utf-8").strip()

    # Check if all required APIs were enabled
    for api in required_gcloud_apis.values():
        gcp_api_name = "projects/{}/services/{}".format(gcp_project_number, api["gcloud_service_name"])
        service_cmd = f"gcloud services list --format=\"value(name)\" --enabled --project={gcp_project_id} --filter=\"name={gcp_api_name}\""
        service_cmd_output= subprocess.run(service_cmd, check=False, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if not service_cmd_output.stdout.decode("utf-8").strip():
            service_api_display_name = api["display_name"]
            service_name = api["gcloud_service_name"]
            print_error(f"{service_api_display_name} API is not enabled", exit=False)
            print(f"Please enable the {service_api_display_name} API with the following command: \"gcloud services enable {service_name}  --project {gcp_project_id}")

    cloudaccount_id = sys.argv[1]
    if not cloudaccount_id:
        print_error("CloudCasa Cloud Account ID is not given.", exit=False)
        print("Please run the script as follows: \"python3 connect_with_cloudcasa.py <cloudaccount-id>\"")

def deploy_basic_cloudcasa_template(deployment_exists=False):
    print_info("Deploying basic CloudCasa template...")

    operation_type = "update" if deployment_exists else "create"
    template = templates_dir.joinpath("cloudcasa_base_gcp_template.py")
    gcp_project_id = os.environ["DEVSHELL_PROJECT_ID"]

    # If a custom service account is specified, use it in the deployment file
    sa_name = os.getenv("CC_SERVICE_ACCOUNT")
    if sa_name:
        update_variable(template.absolute().as_posix(), "cloudcasa_sa_name", f"\"serviceAccount:{sa_name}\"")

    gcloud_cmd = f"gcloud deployment-manager deployments {operation_type} {deployment_name} --template {template} --project={gcp_project_id}"
    res = subprocess.run(gcloud_cmd, shell=True)
    if res.returncode != 0:
        print_error("The CloudCasa deployment has failed. Please check if all required APIs were enabled")

    print_success("Successfully deployed CloudCasa template.")

def deploy_native_persistent_disk_support_template(deployment_exists=False):
    print_info("Deploying CloudCasa template with support for native Google Persistent Disk...")

    template = templates_dir.joinpath("cloudcasa_native_pd_support_template.py")
    operation_type = "update" if deployment_exists else "create"
    gcp_project_id = os.environ["DEVSHELL_PROJECT_ID"]

    # If a custom service account is specified, use it in the deployment file
    sa_name = os.getenv("CC_SERVICE_ACCOUNT")
    if sa_name:
        update_variable(template.absolute().as_posix(), "cloudcasa_sa_name", f"\"serviceAccount:{sa_name}\"")

    gcloud_cmd = f"gcloud deployment-manager deployments {operation_type} {deployment_name} --template {template} --project={gcp_project_id}"
    res = subprocess.run(gcloud_cmd, shell=True)
    if res.returncode != 0:
        print_error("The CloudCasa deployment with support for native Google Persistent Disk has failed. Please check if all required APIs were enabled")

    # NOTE: Backward compatiblity only and it should be removed with version newer
    # than v1.0.1
    # Update the CloudCasa role with the compute.disks.list.
    add_permissions_to_role("CloudCasa", ["compute.disks.list"])

    print_success("Successfully deployed CloudCasa template with support for native Google Persistent Disk.")

def add_permissions_to_role(role: str, permissions: list):
    formatted_permissions = ",".join(permissions)
    gcp_project_id = os.environ["DEVSHELL_PROJECT_ID"]
    role_update_cmd = f"gcloud iam roles update {role} --project={gcp_project_id} --add-permissions={formatted_permissions}"
    res = subprocess.Popen(role_update_cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    res.communicate(input='y'.encode())[0]
    if res.returncode != 0:
        print_error("Failed to add \"{permissions}\" to \"{role}\" role. Please add these roles manually.")

def mark_cloudaccount_as_active(pd_support=False, lb_support=False, workload_identity_support=False):
    print_info("Calling CloudCasa callback to mark the Cloud Account as active...")

    gcp_project_id = os.environ["DEVSHELL_PROJECT_ID"]

    gcp_project_name_cmd = f"gcloud projects describe {gcp_project_id} --format=\"value(name)\""
    gcp_project_name = subprocess.run(
            gcp_project_name_cmd, check=True, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode("utf-8").strip()

    # Create payload based on the enabled features
    cloudaccount_id = sys.argv[1]
    cc_callback_uri= f"{cc_api_url}/api/v1/cloudaccounts/{cloudaccount_id}/action/move-to-active"
    features = {
        "persistent_disk_support": pd_support,
        "load_balancers_support": lb_support,
        "velero_workload_identity_support": workload_identity_support
    }
    cc_callback_body = {
        "project_id": f"{gcp_project_id}",
        "project_name": f"{gcp_project_name}",
        "template_version": "v1.2.1-dev",
        "deployment_name": deployment_name,
        "features": features
    }

    # Skip TLS verification is required
    verify = not str_to_bool(os.getenv("SKIP_TLS", ""))
    res = requests.post(cc_callback_uri, json=cc_callback_body, verify=verify)
    if res.status_code != 200:
        print_error("The CloudCasa callback failed. Please contact our support at home.cloudcasa.io.")
    print_success("Successfully invoked CloudCasa callback. The Cloud Account should be marked as active soon.")

def cleanup_old_deployments():
    old_cc_deployments = []
    gcp_project_id = os.environ["DEVSHELL_PROJECT_ID"]
    gcloud_cmd = f"gcloud deployment-manager deployments list --project={gcp_project_id} --format=json | jq '.[] | .name' | grep 'cloudcasa-deployment-'"
    try:
        res = subprocess.check_output(gcloud_cmd, shell=True)
        old_cc_deployments = res.decode("utf-8").replace('"', "").strip().split("\n")
    except:
        pass

    if len(old_cc_deployments) > 0:
        print_info("Deleting old CloudCasa deployments")
    for i, cc_deployment in enumerate(old_cc_deployments):
        print_info(f"({i+1}/{len(old_cc_deployments)}) Deleting old CloudCasa deployment \"{cc_deployment}\"")
        delete_deployment_cmd = f"gcloud deployment-manager deployments delete --project={gcp_project_id} {cc_deployment} --delete-policy=ABANDON --async"
        res = subprocess.Popen(delete_deployment_cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        res.communicate(input='y'.encode())[0]

def undelete_cloudcasa_role(role_id: str):
    gcp_project_id = os.environ["DEVSHELL_PROJECT_ID"]
    gcloud_cmd = f"gcloud iam roles undelete {role_id} --project={gcp_project_id}"
    subprocess.run(gcloud_cmd, shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def update_variable(file_path: str, variable_name: str, new_value: str):
    with open(file_path, "r") as f:
        lines = f.readlines()

    with open(file_path, "w") as f:
        for line in lines:
            if line.startswith(variable_name):
                line = f"{variable_name} = {new_value}\n"
            f.write(line)

def str_to_bool(s: str) -> bool:
   return s.lower() in ['true', '1', 't', 'y', 'yes']

def main():
    validate_environment()

    support_native_gce_pd_input = input("Enable support for native Google Persistent Disk snapshot (y/n): ")
    if support_native_gce_pd_input not in ["y", "n"]:
        print_error("Supported inputs are only \"y\" and \"n\".")

    support_load_balancers_input = input("Enable support for Load Balancers backup (y/n): ")
    if support_native_gce_pd_input not in ["y", "n"]:
        print_error("Supported inputs are only \"y\" and \"n\".")

    support_velero_workload_identity_input = input("Enable support for Velero clusters restores with Workload Identity authentication (y/n): ")
    if support_native_gce_pd_input not in ["y", "n"]:
        print_error("Supported inputs are only \"y\" and \"n\".")

    support_native_gce_pd = True if support_native_gce_pd_input == "y" else False
    support_load_balancers_backup = True if support_load_balancers_input == "y" else False
    support_velero_workload_identity = True if support_velero_workload_identity_input == "y" else False

    # NOTE: BACKWARD COMPATIBLITY
    # From v1.0.1 we are using only one deployment. We need to clean up the deployments
    # that were created before this one.
    cleanup_old_deployments()

    # Check if deployments needs to be created or updated
    deployment_exists = True
    gcloud_cmd = f"gcloud deployment-manager deployments describe {deployment_name}"
    res = subprocess.run(gcloud_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode != 0:
        deployment_exists = False

    # There might be a case where the user has deleted the deployment with resources.
    # In such case, it might be possible that the roles needs to be "undeleted".
    undelete_cloudcasa_role("CloudCasa")

    # Deploy the right template
    if support_native_gce_pd:
        undelete_cloudcasa_role("CloudCasaNativePdSupportRole")
        deploy_native_persistent_disk_support_template(deployment_exists)
    else:
        deploy_basic_cloudcasa_template(deployment_exists)

    if support_load_balancers_backup:
        print_info("Adding required permissions for Load Balancers backups...")
        required_permissions = [
            "compute.networks.get",
            "compute.networkEndpointGroups.get",
            "compute.networkEndpointGroups.use",
            "compute.urlMaps.list",
            "compute.urlMaps.get",
            "compute.urlMaps.create",
            "compute.urlMaps.delete",
            "compute.urlMaps.use",
            "compute.backendServices.get",
            "compute.backendServices.create",
            "compute.backendServices.delete",
            "compute.backendServices.use",
            "compute.backendServices.update",
            "compute.healthChecks.useReadOnly",
            "compute.healthChecks.get",
            "compute.healthChecks.create",
            "compute.healthChecks.delete",
            "compute.firewalls.list",
            "compute.firewalls.get",
            "compute.firewalls.create",
            "compute.firewalls.delete",
            "compute.targetHttpProxies.list",
            "compute.targetHttpProxies.get",
            "compute.targetHttpProxies.create",
            "compute.targetHttpProxies.delete",
            "compute.targetHttpProxies.use",
            "compute.globalForwardingRules.list",
            "compute.globalForwardingRules.get",
            "compute.globalForwardingRules.create",
            "compute.globalForwardingRules.delete",
            "compute.globalAddresses.list",
            "compute.globalAddresses.get",
            "compute.globalAddresses.create",
            "compute.globalAddresses.delete",
            "compute.globalAddresses.use",
            "compute.instanceGroups.get",
            "compute.instances.get"
        ]
        add_permissions_to_role("CloudCasa", permissions=required_permissions)
        print_success("Successfully enabled support for Load Balancers backups.")

    if support_velero_workload_identity:
        print_info("Adding required permissions for Velero Workload Identity restores...")
        required_permissions = [
            "iam.serviceAccounts.list",
            "iam.serviceAccounts.getIamPolicy",
            "iam.serviceAccounts.setIamPolicy"
        ]
        add_permissions_to_role("CloudCasa", permissions=required_permissions)
        print_success("Successfully enabled support for Velero Workload Identity cluster restores.")

    mark_cloudaccount_as_active(
        pd_support=support_native_gce_pd,
        lb_support=support_load_balancers_backup,
        workload_identity_support=support_velero_workload_identity
    )


if __name__ == "__main__":
    main()
