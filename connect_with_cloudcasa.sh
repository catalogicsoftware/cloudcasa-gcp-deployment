#!/bin/bash

# Colors
red='\033[0;31m';
green='\033[0;32m';
nc='\033[0m';

cloudaccount_id=$1;
timestamp=$(date +%s);
deployment_name=cloudcasa-deployment-${timestamp};
gcp_project_id=${DEVSHELL_PROJECT_ID};

cc_apiserver_url="https://api.staging.cloudcasa.io";
cc_callback_uri="${cc_apiserver_url}/api/v1/cloudaccounts/${cloudaccount_id}/action/move-to-active";
cc_callback_headers="Content-Type: application/json";
cc_template_file=cloudcasa_gcp_deployment.jinja;

if [[ -z ${gcp_project_id} ]]; then
	printf "${red}[ERROR] GCP Project is not set.${nc} Please set the project using \"gcloud config set project <project-id>\" command.\n";
	exit 1
fi

gcp_project_number=$(gcloud projects describe ${gcp_project_id} --format="value(projectNumber)");
gcp_project_name=$(gcloud projects describe ${gcp_project_id} --format="value(name)");

# Check is all required APIs were enabled
gcp_iam_api_name="projects/${gcp_project_number}/services/iam.googleapis.com";
gcp_deployment_manager_api_name="projects/${gcp_project_number}/services/deploymentmanager.googleapis.com";
gcp_compute_engine_api_name="projects/${gcp_project_number}/services/compute.googleapis.com";
gcp_cloud_resource_manager_api_name="projects/${gcp_project_number}/services/cloudresourcemanager.googleapis.com";

if [[ -z $(gcloud services list --format="value(name)" --enabled --project=${gcp_project_id} --filter="name=${gcp_iam_api_name}") ]]; then
	printf "${red}[ERROR] Identity and Access Management (IAM) API is not enabled${nc}\n";
	printf "Please enable the IAM API with the following command: \"gcloud services enable iam.googleapis.com --project ${gcp_project_id}\"\n";
	exit 1;
fi

if [[ -z $(gcloud services list --format="value(name)" --enabled --project=${gcp_project_id} --filter="name=${gcp_deployment_manager_api_name}") ]]; then
	printf "${red}[ERROR] Deployment Manager API is not enabled${nc}\n";
	printf "Please enable the Deployment Manager API with the following command: \"gcloud services enable deploymentmanager.googleapis.com --project ${gcp_project_id}\"\n";
	exit 1;
fi

if [[ -z $(gcloud services list --format="value(name)" --enabled --project=${gcp_project_id} --filter="name=${gcp_compute_engine_api_name}") ]]; then
	printf "${red}[ERROR] Compute Engine API is not enabled${nc}\n";
	printf "Please enable the Compute Engine API with the following command: \"gcloud services enable compute.googleapis.com --project ${gcp_project_id}\"\n";
	exit 1;
fi

if [[ -z $(gcloud services list --format="value(name)" --enabled --project=${gcp_project_id} --filter="name=${gcp_cloud_resource_manager_api_name}") ]]; then
	printf "${red}[ERROR] Cloud Resource Manager API is not enabled${nc}\n";
	printf "Please enable the Cloud Resource Manager API with the following command: \"gcloud services enable cloudresourcemanager.googleapis.com --project ${gcp_project_id}\"\n";
	exit 1;
fi

if [[ ! -f ${cc_template_file} ]]; then
	printf "${red}[ERROR] CloudCasa template file $cc_template_file does not exist${nc}\n";
	printf "Please make sure all files were pulled from the repository\n";
	exit 1;
fi

if [[ -z ${cloudaccount_id} ]]; then
	printf "${red}[ERROR] CloudCasa Cloud Account ID was not given.${nc} Please run the script as follows: \"./connect_with_cloudcasa.sh <cloudaccount-id>\".\n";
	exit 1;
fi


printf "[INFO] Deploying CloudCasa custom role in project...\n";
gcloud deployment-manager deployments create ${deployment_name} --template ${cc_template_file}
if [ $? -ne 0 ]; then
	printf "${red}[ERROR] The CloudCasa deployed has failed.${nc} Please check with the tutorial if all required APIs were enabled.\n";
	exit 1;
fi

printf "${green}[SUCCESS] Successfully deployed CloudCasa custom role in the project.${nc}\n";

cc_callback_body="{\"project_id\": \"${gcp_project_id}\", \"project_name\":\"${gcp_project_name}\", \"template_version\": \"1.0.0\", \"deployment_name\": \"${deployment_name}\"}"

printf "[INFO] Calling CloudCasa callback to mark the Cloud Account as active...\n";
status_code=$(curl -X POST -d "${cc_callback_body}" -H "${cc_callback_headers}" -w "%{http_code}" --silent --output /dev/null "$cc_callback_uri");
if [[ ${status_code} -ne 200 ]]; then
	printf "${red}[ERROR] The CloudCasa callback failed.${nc} Please contact our support at home.cloudcasa.io.\n";
	exit 1;
fi
printf "${green}[SUCCESS] Successfully invoked CloudCasa callback. The Cloud Account should be marked as ACTIVE soon.${nc}\n";
