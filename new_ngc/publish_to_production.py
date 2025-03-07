# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

import os
import re
import subprocess
import sys

from logging_utils import logger
from yaml import FullLoader, dump, load


def process_publishing_configs(files):
    # Read the list of files added
    with open(files, "r") as f:
        files_list = f.readlines()

    logger.info(f"file={files_list}")

    clean_file_list = list()
    for file in files_list:
        clean_file = file.strip()
        file_name = f"../{clean_file}"
        clean_file_list.append(file_name)

    # call the publishing MR only if there was
    # atleast 1 publishing_config.yaml added/modified
    if len(clean_file_list) > 0:
        create_publishing_mr(clean_file_list)


def create_publishing_mr(yaml_files):
    """
    This function reads a yaml file and programmatically creates an MR against NGC publishing,
    This MR when approved and merged will publish nim images to public registry.

    Args:
        yaml_files (list): The path to files containing yaml configs used in publishing.

    Returns:
        None
    """
    logger.info(f"yaml_files{yaml_files}")

    try:
        ci_job_id = os.getenv("CI_JOB_ID")

        GITLAB_ACCESS_PUBLISHING_TOKEN = os.getenv("GITLAB_ACCESS_PUBLISHING_TOKEN")
        if not GITLAB_ACCESS_PUBLISHING_TOKEN:
            raise EnvironmentError("GITLAB_ACCESS_PUBLISHING_TOKEN variable is not set")

        container_nspect_id = os.environ.get("CONTAINER_NSPECT_ID", "")
        container_nspect_program_name = os.environ.get(
            "CONTAINER_NSPECT_PROGRAM_NAME", ""
        )
        model_nspect_id = os.environ.get("MODEL_NSPECT_ID", "")
        model_nspect_program_name = os.environ.get("MODEL_NSPECT_PROGRAM_NAME", "")
        model_nspect_version = os.environ.get("MODEL_NSPECT_VERSION", "")
        model_state = "PROD"
        container_nspect_version = os.environ.get("RELEASE_VERSION", "")
        container_state = "PROD"
        backend_type = os.environ.get("TRACE_NIM_BACKEND_TYPE", "")

        nim_factory_pipeline_id = os.environ.get("TRACE_NIM_FACTORY_PIPELINE_ID", "")

        subprocess.run(["git", "checkout", "-b", f"{ci_job_id}"])

        ngc_publisher = os.getenv("GITLAB_USER_LOGIN")
        sub_dir = f"configs/{ngc_publisher}"
        subprocess.run(["mkdir", "-p", sub_dir], check=True)

        for suffix, yaml_file in enumerate(yaml_files):
            logger.info(f"now processing yaml_file='{yaml_file}'...")

            file_path = f"configs/{ngc_publisher}/{ci_job_id}{suffix}.yaml"

            subprocess.run(
                ["cp", yaml_file, file_path],
                check=True,
            )

            logger.info(
                f"writing nim_traceability section to {ngc_publisher}/{ci_job_id}{suffix}.yaml"
            )
            kind = "MODEL" if "model" in yaml_file.lower() else "CONTAINER"

            add_to_yaml = {
                "nim_traceability": {
                    "kind": kind,
                    "container_nspect_id": container_nspect_id,
                    "container_nspect_version": container_nspect_version,
                    "container_nspect_program_name": container_nspect_program_name,
                    "container_state": container_state,
                    "model_nspect_id": model_nspect_id,
                    "model_nspect_version": model_nspect_version,
                    "model_nspect_program_name": model_nspect_program_name,
                    "model_state": model_state,
                    "nim_factory_pipeline_id": nim_factory_pipeline_id,
                    "backend_type": backend_type,
                }
            }

            # Add author's email address to YAML if present.
            # The environment variable CI_COMMIT_AUTHOR is set automatically by gitlab.
            # It is a string in the format: "First Last <name@nvidia.com>"
            # If the env variable is not set, that's ok, because the following is a safe check.
            commit_author = re.search(r"<(.*)>", os.environ.get("CI_COMMIT_AUTHOR", ""))
            if commit_author:
                email_address = commit_author.group(1)

                add_to_yaml |= {"email_to_notify": email_address}

            if add_to_yaml:
                existing_yaml = {}

                with open(file_path, "r") as f:
                    existing_yaml = load(f, Loader=FullLoader)
                    existing_yaml.update(add_to_yaml)

                if existing_yaml:
                    with open(file_path, "w") as f:
                        dump(
                            existing_yaml,
                            f,
                            explicit_start=True,
                            explicit_end=True,
                            sort_keys=False,
                        )

            subprocess.run(["cat", file_path])

            subprocess.run(
                ["git", "add", file_path],
                check=True,
            )

        ngc_publisher_username = os.getenv("GITLAB_USER_NAME")
        subprocess.run(
            [
                "git",
                "config",
                "--local",
                "--replace-all",
                "user.name",
                f"{ngc_publisher_username}",
            ],
            check=True,
        )

        ngc_publisher_user_email = os.getenv("CI_COMMIT_AUTHOR")
        subprocess.run(
            [
                "git",
                "config",
                "--local",
                "--replace-all",
                "user.email",
                f"{ngc_publisher_user_email}",
            ],
            check=True,
        )

        logger.info(
            f"ngc_publisher_user_email={ngc_publisher_user_email} ngc_publisher_username={ngc_publisher_username} ngc_publisher={ngc_publisher} "
        )

        # commit
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "chore: for NVAIE team publishing images",
                "--author",
                f"'{ngc_publisher_user_email}'",
            ],
            check=True,
        )

        subprocess.run(["git", "log", "-n1", "--format=fuller"], check=True)

        subprocess.run(["git", "push", "origin", "-u", f"{ci_job_id}"], check=True)

        # NGC publishing project_id
        PUBLISHING_PROJECT_ID = 123069

        ci_api_v4_url = os.getenv("CI_API_V4_URL")

        curl_mr = f"curl -X POST --header 'PRIVATE-TOKEN: {GITLAB_ACCESS_PUBLISHING_TOKEN}' --url '{ci_api_v4_url}/projects/{PUBLISHING_PROJECT_ID}/merge_requests?source_branch={ci_job_id}&target_branch=main&title=nim_factory_publishing'"

        subprocess.run(curl_mr, check=True, shell=True)

    except subprocess.CalledProcessError as e:
        logger.error(
            f"Failed to process yaml_files '{yaml_files} and create the MR': {e}"
        )
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error(
            "Failed to provide the path to the publishing yaml files as arguments."
        )
        sys.exit(1)

    config_files = sys.argv[1]
    process_publishing_configs(config_files)

