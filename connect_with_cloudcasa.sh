#!/bin/bash

# Colors
RED='\033[0;31m';
GREEN='\033[0;32m';
NC='\033[0m';

CC_TEMPLATE_FILE=cloudcasa_gcp_deployment.jinja;
GCP_PROJECT_ID=${DEVSHELL_PROJECT_ID};
CLOUDACCOUNT_ID=$1;

CC_APISERVER_URL="https://api.staging.cloudcasa.io";
CC_CALLBACK_URI="${CC_APISERVER_URL}/api/v1/cloudaccounts/${CLOUDACCOUNT_ID}/action/move-to-active";
CC_CALLBACK_BODY="{\"project_id\": \"${GCP_PROJECT_ID}\", \"template_version\": \"1.0.0\"}"
CC_CALLBACK_HEADERS="Content-Type: application/json";

if [[ -z ${GCP_PROJECT_ID} ]]; then
	printf "${RED}[ERROR] GCP Project is not set.${NC} Please set the project using \"gcloud config set project <project-id>\" command.\n";
	exit 1
fi

if [[ ! -f ${CC_TEMPLATE_FILE} ]]; then
	printf "${RED}[ERROR] CloudCasa template file $CC_TEMPLATE_FILE does not exist${NC}\n";
	printf "Please make sure all files were pulled from the repository\n";
	exit 1;
fi

if [[ -z ${CLOUDACCOUNT_ID} ]]; then
	printf "${RED}[ERROR] CloudCasa Cloud Account ID was not given.${NC} Please run the script as follows: \"./connect_with_cloudcasa.sh <cloudaccount-id>\".\n";
	exit 1;
fi


printf "[INFO] Deploying CloudCasa custom role in project...\n";
TIMESTAMP=$(date +%s)
gcloud deployment-manager deployments create cloudcasa-deployment-${TIMESTAMP} --template ${CC_TEMPLATE_FILE}
if [ $? -ne 0 ]; then
	printf "${RED}[ERROR] The CloudCasa deployed has failed.${NC} Please check with the tutorial if all required APIs were enabled.\n";
	exit 1;
fi

printf "${GREEN}[SUCCESS] Successfully deployed CloudCasa custom role in the project.${NC}\n";

printf "[INFO] Calling CloudCasa callback to mark the Cloud Account as active...\n";
STATUS_CODE=$(curl -X POST -d "${CC_CALLBACK_BODY}" -H "${CC_CALLBACK_HEADERS}" -w "%{http_code}" --silent --output /dev/null "$CC_CALLBACK_URI");
if [[ ${STATUS_CODE} -ne 200 ]]; then
	printf "${RED}[ERROR] The CloudCasa callback failed.${NC} Please contact our support at home.cloudcasa.io.\n";
	exit 1;
fi
printf "${GREEN}[SUCCESS] Successfully invoked CloudCasa callback. The Cloud Account should be marked as ACTIVE soon.${NC}\n";
