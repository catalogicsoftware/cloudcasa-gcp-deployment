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
templates_dir = Path(__file__).absolute().parent.joinpath("templates")
timestamp = int(time.time())
deployment_name = f"cloudcasa-deployment-{timestamp}"

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

def deploy_basic_cloudcasa_template():
    print_info("Deploying basic CloudCasa template...")

    template = templates_dir.joinpath("cloudcasa_base_gcp_template.py")
    gcloud_cmd = f"gcloud deployment-manager deployments create {deployment_name} --template {template}"
    res = subprocess.run(gcloud_cmd, shell=True)
    if res.returncode != 0:
        print_error("The CloudCasa deployment has failed. Please check if all required APIs were enabled")

    print_success("Successfully deployed CloudCasa template.")

def deploy_native_persistent_disk_support_template():
    print_info("Deploying CloudCasa template with support for native Google Persistent Disk...")

    template = templates_dir.joinpath("cloudcasa_native_pd_support_template.py")
    gcloud_cmd = f"gcloud deployment-manager deployments create {deployment_name} --template {template}"
    res = subprocess.run(gcloud_cmd, shell=True)
    if res.returncode != 0:
        print_error("The CloudCasa deployment with support for native Google Persistent Disk has failed. Please check if all required APIs were enabled")

    print_success("Successfully deployed CloudCasa template with support for native Google Persistent Disk.")

def mark_cloudaccount_as_active(pd_support):
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
        "persistent_disk_support": pd_support
    }
    cc_callback_body = {
        "project_id": f"{gcp_project_id}",
        "project_name": f"{gcp_project_name}",
        "template_version": "1.0.0",
        "deployment_name": deployment_name,
        "features": features
    }

    res = requests.post(cc_callback_uri, json=cc_callback_body)
    if res.status_code != 200:
        print_error("The CloudCasa callback failed. Please contact our support at home.cloudcasa.io.")
    print_success("Successfully invoked CloudCasa callback. The Cloud Account should be marked as active soon.")

def main():
    validate_environment()

    support_native_gce_pd_input = input("Enable support for native Google Persistent Disk snapshot (y/n): ")
    if support_native_gce_pd_input not in ["y", "n"]:
        print_error("Supported inputs are only \"y\" and \"n\".")

    support_native_gce_pd = True if support_native_gce_pd_input == "y" else False
    # Deploy the right template
    if support_native_gce_pd:
        deploy_native_persistent_disk_support_template()
    else:
        deploy_basic_cloudcasa_template()

    mark_cloudaccount_as_active(pd_support=support_native_gce_pd)


if __name__ == "__main__":
    main()