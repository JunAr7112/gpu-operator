# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

import argparse
import datetime
import logging
import os
import sys
import time

import requests
from logging_utils import logger
from nspect_utils import SSAToken


class NSPECTManager:
    def __init__(self, token_manager: SSAToken, use_stage: bool = False) -> None:
        """Constructor for the NSPECTManager class.

        Args:
        - token_manager (SSAToken): The token manager to use for fetching the token.
        - use_stage (bool): Whether to use the stage environment or not. Default False.

        Returns:
        - None
        """
        self.token_manager = token_manager
        self.use_stage = use_stage
        self.nspect_url = (
            "https://nspect-stage.nvidia.com"
            if self.use_stage
            else "https://nspect.nvidia.com"
        )

    def check_job_status(
        self,
        status_url: str,
        max_attempts: int = 10,
        sleep_multiplier: int = 5,
    ) -> bool:
        """Get the job status from the status URL.

        Args:
            status_url (str): Status URL (example: "pm/api/v1.0/public/jobs/c724e7ab-7604-47fd-a27e-ac8be946fdce")
            max_attempts (int, optional): Max attempts number. Defaults to 10.
            sleep_multiplier (int, optional): Seconds to sleep before making a second call (attempt * sleep_multiplier). Defaults to 5.

        Returns:
            bool: Returns True if the job is finished successfully, False otherwise.
        """
        logger.info(
            f"Checking job status.. status_url = {status_url}, max_attempts = {max_attempts}, sleep_multiplier = {sleep_multiplier}"
        )

        token = self.token_manager.get_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        url = f"{self.nspect_url}/{status_url}"

        for attempt in range(1, max_attempts + 1):
            try:
                # Make the GET request
                response = requests.get(url, headers=headers, timeout=60)
                response.raise_for_status()
                results = response.json()

                logger.debug(f"Check job status response is: {results}")

                if results.get("success"):
                    job = results.get("data").get("job")

                    # Task finished - check if there are any errors in the results
                    if job.get("status") == "SUCCESS":
                        job_result = job.get("result")
                        if isinstance(job_result, dict):
                            logger.error(
                                f"Errors found in job (status_url = {status_url}): {job_result.get('errors')}"
                            )
                            return False

                        return True

                    if job.get("status") == "PENDING":
                        logger.info(
                            f"Job is pending retrying (attempt: {attempt}) after {attempt * sleep_multiplier} seconds... status_url = {status_url}"
                        )
                        time.sleep(attempt * sleep_multiplier)
                        continue

                    logger.error(
                        f"Job status is not SUCCESS or PENDING, status_url = {status_url}"
                    )
                    return False

            except requests.exceptions.HTTPError as err:
                logger.error(f"HTTP error occurred: {err}, status_url = {status_url}")
            except Exception as err:
                logger.error(
                    f"Unknown error occurred: {err}, status_url = {status_url}"
                )
                return False

        logger.error(
            f"Failed to get job status after maximum attempts ({max_attempts}), status_url = {status_url}."
        )
        return False

    def update_version(
        self,
        nspect_id: str,
        container_image: str,
        versionName: str,
        description: str = "Default description.",
        releaseDate: str = "2024-01-001 00:00:00",
        sourcePointer: str = "ssh://git@gitlab-master.nvidia.com:12051/pstooling/nspect.git",
        sourcePointerBranch: str = "main",
        sourcePointerComponentName: str = "ContainerSourceCode",
    ) -> bool:
        """
        Function to update the version of an nSpect program.

        Args:
        - nspect_id (str): The ID of the nSpect to update.
        - container_image (str): The container image URL to update.
        - versionName (str): The version name to update.
        - releaseDate (str): The release date of the version.
        - description (str): The description of the version.
        - sourcePointer (str): The source pointer for the repo that holds the source code for the nim.
        - sourcePointerBranch (str): The branch/tag/commit for the repo that the source code for the nim.
        - sourcePointerComponentName (str): The component name for the repo that the source code for the nim.

        Returns:
        - bool: True, if successful.

        """
        url = (
            f"{self.nspect_url}/pm/api/v1.0/public/programs/{nspect_id}/programVersions"
        )

        # link to docs: http://nv/nspect-update-docs on how to make this request.
        req = {
            "request": {
                "versionName": versionName,
                "description": description,
                "releaseType_id": 4,
                "releaseDate": releaseDate,
                "releaseLocations": ["NVIDIA NGC: NVAIE-Exclusive"],
                "labels": ["NIM FACTORY", "NIM"],
                "manualRepos": [
                    {
                        "sourcePointer": sourcePointer,
                        "branch": sourcePointerBranch,
                        "componentName": sourcePointerComponentName,
                    }
                ],
                "containerImages": [
                    {
                        "imageUrl": container_image,
                    }
                ],
            }
        }
        logger.info(f"Request is {req}")
        token = self.token_manager.get_token()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        response = self.post_request(url, headers, req)
        logger.info(f"Response is {response}")
        data = response.get("data")
        return self.check_job_status(status_url=data.get("status_url"))

    def post_request(self, url, headers, req):
        response = requests.post(url, headers=headers, json=req)
        return response.json()


def main():
    parser = argparse.ArgumentParser(description="Fetch data from the nSpect API.")
    parser.add_argument("--nspect_id", help="The ID of the nSpect to query.")
    parser.add_argument(
        "--container_image", help="The container image related to the nSpect query."
    )
    parser.add_argument(
        "--version-name",
        help="The version name used in the NSPECT release version dropdown.",
    )
    parser.add_argument("--description", help="Description of the version.")
    parser.add_argument(
        "--source-pointer",
        help="Source Pointer is a pointer to the source code for the nim container.",
    )
    parser.add_argument(
        "--source-pointer-branch",
        help="Source Pointer branch is a the branch/tag/commit for the repo that holds the source code for the nim.",
    )
    parser.add_argument(
        "--source-pointer-component-name",
        help="Logical grouping on the NSPECT UI for the source code.",
    )
    parser.add_argument(
        "--use-stage", help="Use stage or not", default=False, action="store_true"
    )
    parser.add_argument(
        "--max-attempts",
        help="Max attempts to get the job status after making post request to nSpect",
        default=10,
    )
    parser.add_argument(
        "--sleep-multiplier",
        help="Seconds to sleep before making a second call (attempt * sleep_multiplier). Defaults to 5",
        default=5,
    )

    args = parser.parse_args()

    if args.source_pointer is None:
        logger.error("Source pointer is required.")
    elif "http" in args.source_pointer:
        raise ValueError(
            "Source pointer should not contain 'https'. Please use ssh://... instead."
        )

    logger.info("Starting nSpect registration")
    logger.info("nspect_id is %s", args.nspect_id)
    logger.info("container_image is %s", args.container_image)
    logger.info("version_name is %s", args.version_name)
    logger.info("Description is %s", args.description)
    logger.info("source_pointer is %s", args.source_pointer)
    logger.info("source_pointer_branch is %s", args.source_pointer_branch)
    logger.info(
        "source_pointer_component_name is %s", args.source_pointer_component_name
    )
    logger.info("Using stage is %s", args.use_stage)
    logger.info(f"max-attempts is {args.max_attempts}")
    logger.info(f"sleep-multiplier is {args.sleep_multiplier}")

    if not os.environ.get("SSA_CLIENT_ID"):
        logger.debug("SSA_CLIENT_ID is not set")
    else:
        logger.debug("SSA_CLIENT_ID is set")
    if not os.environ.get("SSA_CLIENT_SECRET"):
        logger.debug("SSA_CLIENT_SECRET is not set")
    else:
        logger.debug("SSA_CLIENT_SECRET is set")
    if not os.environ.get("SSA_STG_CLIENT_ID"):
        logger.debug("SSA_STG_CLIENT_ID is not set")
    else:
        logger.debug("SSA_STG_CLIENT_ID is set")
    if not os.environ.get("SSA_STG_CLIENT_SECRET"):
        logger.debug("SSA_STG_CLIENT_SECRET is not set")
    else:
        logger.debug("SSA_STG_CLIENT_SECRET is set")

    if args.use_stage:
        logger.info("Using stage SSA")
        ssa_url = (
            "https://hsxntwlenuyxjgvcdt5ifkp9x78g9spcncmtwuyoxws.stg.ssa.nvidia.com"
        )
        CLIENT_ID = "nvssa-prd-paIZAOWxlQyDLPO0pONiRkF22NO9uZmrOcLRzQV0xjo" #os.environ.get("SSA_STG_CLIENT_ID")
        CLIENT_SECRET = "ssap-8pLPFMsbv08qDk778Q5" #os.environ.get("SSA_STG_CLIENT_SECRET")
    else:
        logger.info("Using prod SSA")
        ssa_url = "https://4ubglassowmtsi7ogqwarmut7msn1q5ynts62fwnr1i.ssa.nvidia.com"
        CLIENT_ID = "nvssa-prd-paIZAOWxlQyDLPO0pONiRkF22NO9uZmrOcLRzQV0xjo" #os.environ.get("SSA_CLIENT_ID")
        CLIENT_SECRET = "ssap-8pLPFMsbv08qDk778Q5" #os.environ.get("SSA_CLIENT_SECRET")

    logger.info("creating token manager")
    token_manager = SSAToken(
        ssa_url=ssa_url,
        scopes="public.api:read public.api:write",
        ssa_client=CLIENT_ID,
        ssa_secret=CLIENT_SECRET,
    )

    nspect_manager = NSPECTManager(
        token_manager=token_manager, use_stage=args.use_stage
    )
    release_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.info(f"Updating version for nspect_id: {args.nspect_id}")
    response = nspect_manager.update_version(
        nspect_id=args.nspect_id,
        container_image=args.container_image,
        versionName=args.version_name,
        releaseDate=release_date,
        description=args.description,
        sourcePointer=args.source_pointer,
        sourcePointerBranch=args.source_pointer_branch,
        sourcePointerComponentName=args.source_pointer_component_name,
    )

    if response:
        logger.info("Version updated successfully!")
    else:
        raise ValueError("Version update failed")


if __name__ == "__main__":
    main()

