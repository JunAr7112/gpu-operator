# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

import logging
import os

import coloredlogs


def configure_logging(level=logging.INFO) -> logging.Logger:
    """
    Configure the logging settings.

    Args:
        level (int): The logging level, e.g., logging.INFO, logging.DEBUG, etc.
    """
    # "coloredlogs" does not detect the CI terminal as supporting colors, so it disables them.
    # Check if we're in a CI job and explicitly enable colors if so. Take care to not set the
    # variable at when this is not a CI job.
    is_ci_job = os.getenv("CI", None)

    coloredlogs.install(
        level=level,
        fmt="[%(asctime)s] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        isatty=is_ci_job,
    )
    logline = logging.getLogger(__name__)
    return logline


# Default logger configuration
logger = configure_logging()

