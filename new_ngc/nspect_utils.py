# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
import sys
import time
from threading import Lock

import requests
from jose import jwt
from logging_utils import logger


class SSAToken:
    """
    Used to fetch and store SSA token. Additionally refreshes the token.
    """

    def __init__(
        self,
        ssa_url: str,
        scopes: str,
        ssa_client: str,
        ssa_secret: str,
        refresh_buffer: int = 120,
    ):
        self.ssa_url = ssa_url
        self.scopes = scopes
        self.ssa_client = ssa_client
        self.ssa_secret = ssa_secret
        self.lock = Lock()
        self.token = None
        self.exp = None
        self.refresh_buffer = refresh_buffer

    def get_token(self) -> str:
        """
        This function is used to fetch the SSA token.
        If the token is already present and not expired, it returns the token.
        """
        with self.lock:
            if self.token and self.exp > int(time.time()):
                return self.token
            else:
                logger.info("Fetching SSA client token")
                try:
                    response = requests.post(
                        url=f"{self.ssa_url}/token",
                        data={"grant_type": "client_credentials", "scope": self.scopes},
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=120,
                        auth=(self.ssa_client, self.ssa_secret),
                    )
                    response.raise_for_status()
                    self.token = response.json()["access_token"]
                    unverified_payload = jwt.get_unverified_claims(self.token)
                    self.exp = unverified_payload.get("exp", 0) - self.refresh_buffer
                    logger.info("Successfully fetched SSA client token")
                except Exception:
                    logger.exception("Failed to fetch SSA client token")
                    raise
                return self.token

