import logging
import pathlib
import yaml
import tempfile
import shutil
import secrets
import subprocess
import string
from typing import Tuple, Optional
import threading
from datetime import datetime
from customdataclasses import ServerResult


class SFTPConfigurationError(Exception):
    """Custom exception for SFTP configuration errors"""

    pass


class SFTPManager:
    """Dedicated class for managing SFTP server configuration"""

    def __init__(self, sftp_base_path: Optional[pathlib.Path] = None):
        self.sftp_path = sftp_base_path or pathlib.Path(__file__).parent / "sftp"
        self.docker_compose_sftp = self.sftp_path / "docker-sftp.yml"
        self.users_conf = self.sftp_path / "users.conf"
        self.lock = threading.Lock()
        self.logger = logging.getLogger("game-server-setup")

        # Ensure directories exist
        self.sftp_path.mkdir(exist_ok=True)

        # Create default files if they don't exist
        self._ensure_config_files_exist()

    def _ensure_config_files_exist(self):
        """Create default configuration files if they don't exist"""
        if not self.docker_compose_sftp.exists():
            default_compose = {
                "version": "3.8",
                "services": {
                    "sftp": {
                        "image": "atmoz/sftp:latest",
                        "container_name": "sftpserver",
                        "ports": ["2222:22"],
                        "volumes": [f"{self.users_conf}:/etc/sftp/users.conf:ro"],
                        "restart": "unless-stopped",
                        "networks": ["gameserver-net"],
                    }
                },
                "networks": {"gameserver-net": {"external": True}},
            }
            with open(self.docker_compose_sftp, "w") as f:
                yaml.dump(default_compose, f, default_flow_style=False)

        if not self.users_conf.exists():
            self.users_conf.touch()

    def _generate_secure_password(self, length: int = 12) -> str:
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _get_next_user_ids(self) -> Tuple[int, int]:
        """Get next available UID and GID for new user"""
        try:
            with open(self.users_conf, "r") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            if not lines:
                return 1001, 101  # Start from 1001/101

            # Find highest UID and GID
            max_uid = 1000
            max_gid = 100

            for line in lines:
                if ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 4:
                        try:
                            uid = int(parts[2])
                            gid = int(parts[3])
                            max_uid = max(max_uid, uid)
                            max_gid = max(max_gid, gid)
                        except ValueError:
                            continue

            return max_uid + 1, max_gid + 1

        except Exception as e:
            self.logger.warning(f"Error reading users.conf, using default IDs: {e}")
            return 1001, 101

    def _user_exists(self, subscription_id: str) -> bool:
        """Check if user already exists in users.conf"""
        try:
            with open(self.users_conf, "r") as f:
                content = f.read()
                return f"{subscription_id}:" in content
        except FileNotFoundError:
            return False

    def _backup_config_files(self) -> Tuple[pathlib.Path, pathlib.Path]:
        """Create backup copies of configuration files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        compose_backup = self.sftp_path / f"docker-sftp.yml.backup.{timestamp}"
        users_backup = self.sftp_path / f"users.conf.backup.{timestamp}"

        shutil.copy2(self.docker_compose_sftp, compose_backup)
        shutil.copy2(self.users_conf, users_backup)

        return compose_backup, users_backup

    def _restore_from_backup(
        self, compose_backup: pathlib.Path, users_backup: pathlib.Path
    ):
        """Restore configuration files from backup"""
        try:
            shutil.copy2(compose_backup, self.docker_compose_sftp)
            shutil.copy2(users_backup, self.users_conf)
            self.logger.info("Configuration files restored from backup")
        except Exception as e:
            self.logger.error(f"Failed to restore from backup: {e}")

    def add_user_volume(self, game_type: str, subscription_id: str) -> ServerResult:
        """
        Add a new user and volume mapping to SFTP server configuration

        Args:
            game_type: Type of game server
            subscription_id: Unique subscription identifier

        Returns:
            ServerResult: Result of the operation
        """

        with self.lock:  # Ensure thread safety
            try:
                # Validate inputs
                if not subscription_id or not game_type:
                    return ServerResult(
                        action="sftp_update",
                        success=False,
                        subscription_id=subscription_id,
                        status="failed",
                        error="Invalid subscription_id or game_type",
                    )

                # Check if user already exists
                if self._user_exists(subscription_id):
                    self.logger.info(
                        f"SFTP user {subscription_id} already exists, skipping"
                    )
                    return ServerResult(
                        action="sftp_update",
                        success=True,
                        subscription_id=subscription_id,
                        status="already_exists",
                    )

                # Create backups before making changes
                compose_backup, users_backup = self._backup_config_files()

                try:
                    # Update docker-compose.yml
                    self._update_docker_compose(game_type, subscription_id)

                    # Add user to users.conf
                    password = self._add_user_to_conf(subscription_id)

                    # Restart SFTP server
                    restart_result = self._restart_sftp_server()

                    if not restart_result.success:
                        # Restore from backup on failure
                        self._restore_from_backup(compose_backup, users_backup)
                        return restart_result

                    # Clean up old backups (keep last 5)
                    self._cleanup_old_backups()

                    return ServerResult(
                        action="sftp_update",
                        success=True,
                        subscription_id=subscription_id,
                        status="completed",
                        metrics={
                            "username": subscription_id,
                            "password": password,
                            "mount_path": f"/home/{subscription_id}/{game_type}",
                            "server_path": f"/srv/allservers/{subscription_id}",
                        },
                    )

                except Exception as e:
                    # Restore from backup on any error
                    self._restore_from_backup(compose_backup, users_backup)
                    raise e

            except Exception as e:
                self.logger.error(f"Failed to update SFTP server: {e}")
                return ServerResult(
                    action="sftp_update",
                    success=False,
                    subscription_id=subscription_id,
                    status="failed",
                    error=str(e),
                )

    def _update_docker_compose(self, game_type: str, subscription_id: str):
        """Update docker-compose.yml with new volume mapping"""
        tmp_path = ""
        try:
            # Load current configuration
            with open(self.docker_compose_sftp, "r") as f:
                config = yaml.safe_load(f)

            # Ensure proper structure exists
            if "services" not in config:
                config["services"] = {}
            if "sftp" not in config["services"]:
                config["services"]["sftp"] = {}
            if "volumes" not in config["services"]["sftp"]:
                config["services"]["sftp"]["volumes"] = []

            # Create new volume mapping
            new_volume = f"/srv/allservers/{subscription_id}:/home/{subscription_id}/{game_type}:rw"

            # Check if volume already exists
            existing_volumes = config["services"]["sftp"]["volumes"]
            if not any(subscription_id in vol for vol in existing_volumes):
                existing_volumes.append(new_volume)

            # Write updated configuration atomically

            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, dir=self.sftp_path, suffix=".tmp"
            ) as tmp_file:
                yaml.dump(config, tmp_file, default_flow_style=False, indent=2)
                tmp_path = tmp_file.name

            # Atomic move
            shutil.move(tmp_path, self.docker_compose_sftp)
            self.logger.info(
                f"Updated docker-compose.yml with volume for {subscription_id}"
            )

        except Exception as e:
            # Clean up temp file if it exists
            if "tmp_path" in locals() and pathlib.Path(tmp_path).exists():
                pathlib.Path(tmp_path).unlink()
            raise SFTPConfigurationError(f"Failed to update docker-compose.yml: {e}")

    def _add_user_to_conf(self, subscription_id: str) -> str:
        """Add user to users.conf file"""
        tmp_path = ""
        try:
            # Generate secure password
            password = self._generate_secure_password()

            # Get next available UID/GID
            uid, gid = self._get_next_user_ids()

            # Create user configuration line
            # Format: username:password:uid:gid:home_dir:shell:chroot_dir
            user_line = (
                f"{subscription_id}:{password}:{uid}:{gid}:::{subscription_id}\n"
            )

            # Append to users.conf atomically
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, dir=self.sftp_path, suffix=".tmp"
            ) as tmp_file:
                # Copy existing content
                if self.users_conf.exists():
                    with open(self.users_conf, "r") as existing:
                        tmp_file.write(existing.read())

                # Add new user
                tmp_file.write(user_line)
                tmp_path = tmp_file.name

            # Atomic move
            shutil.move(tmp_path, self.users_conf)
            self.logger.info(f"Added SFTP user {subscription_id} with UID {uid}")

            return password

        except Exception as e:
            # Clean up temp file if it exists
            if "tmp_path" in locals() and pathlib.Path(tmp_path).exists():
                pathlib.Path(tmp_path).unlink()
            raise SFTPConfigurationError(f"Failed to add user to users.conf: {e}")

    def run_command(self, cmd: str) -> Tuple[int, str, str]:
        """Execute shell command"""
        try:
            self.logger.debug(f"Executing: {cmd}")
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate()
            return_code = process.returncode
            if return_code != 0:
                self.logger.warning(
                    f"Command {cmd} failed with code {return_code}: {stderr}"
                )
            return return_code, stdout, stderr
        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            return 1, "", str(e)

    def _restart_sftp_server(self) -> ServerResult:
        """Restart SFTP server with proper error handling"""
        try:
            # Stop existing container (ignore errors if not running)
            self.run_command("docker rm -f sftpserver")

            # Bring down compose stack
            down_cmd = f"docker compose -f {self.docker_compose_sftp} down"
            return_code, stdout, stderr = self.run_command(down_cmd)

            if return_code != 0:
                self.logger.warning(f"Docker compose down had non-zero exit: {stderr}")

            # Bring up compose stack
            up_cmd = f"docker compose -f {self.docker_compose_sftp} up -d"
            return_code, stdout, stderr = self.run_command(up_cmd)

            if return_code != 0:
                return ServerResult(
                    action="sftp_restart",
                    success=False,
                    subscription_id="",
                    status="failed",
                    error=f"Failed to start SFTP server: {stderr}",
                )

            # Verify container is running
            verify_cmd = "docker ps --filter name=sftpserver --format '{{.Status}}'"
            return_code, stdout, stderr = self.run_command(verify_cmd)

            if return_code == 0 and stdout.strip():
                self.logger.info("SFTP server restarted successfully")
                return ServerResult(
                    action="sftp_restart",
                    success=True,
                    subscription_id="",
                    status="running",
                )
            else:
                return ServerResult(
                    action="sftp_restart",
                    success=False,
                    subscription_id="",
                    status="failed",
                    error="SFTP container not running after restart",
                )

        except Exception as e:
            self.logger.error(f"Error restarting SFTP server: {e}")
            return ServerResult(
                action="sftp_restart",
                success=False,
                subscription_id="",
                status="failed",
                error=str(e),
            )

    def _cleanup_old_backups(self, keep_count: int = 5):
        """Clean up old backup files, keeping only the most recent ones"""
        try:
            compose_backups = list(self.sftp_path.glob("docker-sftp.yml.backup.*"))
            users_backups = list(self.sftp_path.glob("users.conf.backup.*"))

            for backup_list in [compose_backups, users_backups]:
                if len(backup_list) > keep_count:
                    # Sort by modification time (oldest first)
                    srt_func = lambda p: p.stat().st_mtime
                    backup_list.sort(key=srt_func)
                    # Remove oldest backups
                    for backup in backup_list[:-keep_count]:
                        backup.unlink()
                        self.logger.debug(f"Removed old backup: {backup}")

        except Exception as e:
            self.logger.warning(f"Error cleaning up old backups: {e}")

    def remove_user_volume(self, subscription_id: str) -> ServerResult:
        """
        Remove user and volume mapping from SFTP server configuration

        Args:
            subscription_id: Unique subscription identifier

        Returns:
            ServerResult: Result of the operation
        """
        with self.lock:
            try:
                if not self._user_exists(subscription_id):
                    return ServerResult(
                        action="sftp_remove",
                        success=True,
                        subscription_id=subscription_id,
                        status="not_found",
                    )

                # Create backups
                compose_backup, users_backup = self._backup_config_files()

                try:
                    # Remove from docker-compose.yml
                    self._remove_from_docker_compose(subscription_id)

                    # Remove from users.conf
                    self._remove_from_users_conf(subscription_id)

                    # Restart SFTP server
                    restart_result = self._restart_sftp_server()

                    if not restart_result.success:
                        self._restore_from_backup(compose_backup, users_backup)
                        return restart_result

                    return ServerResult(
                        action="sftp_remove",
                        success=True,
                        subscription_id=subscription_id,
                        status="removed",
                    )

                except Exception as e:
                    self._restore_from_backup(compose_backup, users_backup)
                    raise e

            except Exception as e:
                self.logger.error(f"Failed to remove SFTP user: {e}")
                return ServerResult(
                    action="sftp_remove",
                    success=False,
                    subscription_id=subscription_id,
                    status="failed",
                    error=str(e),
                )

    def _remove_from_docker_compose(self, subscription_id: str):
        """Remove volume mapping from docker-compose.yml"""
        with open(self.docker_compose_sftp, "r") as f:
            config = yaml.safe_load(f)

        if (
            "services" in config
            and "sftp" in config["services"]
            and "volumes" in config["services"]["sftp"]
        ):
            # Filter out volumes containing the subscription_id
            original_volumes = config["services"]["sftp"]["volumes"]
            filtered_volumes = [
                vol for vol in original_volumes if subscription_id not in vol
            ]
            config["services"]["sftp"]["volumes"] = filtered_volumes

            # Write atomically
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, dir=self.sftp_path, suffix=".tmp"
            ) as tmp_file:
                yaml.dump(config, tmp_file, default_flow_style=False, indent=2)
                tmp_path = tmp_file.name

            shutil.move(tmp_path, self.docker_compose_sftp)

    def _remove_from_users_conf(self, subscription_id: str):
        """Remove user from users.conf"""
        with open(self.users_conf, "r") as f:
            lines = f.readlines()

        # Filter out lines containing the subscription_id
        filtered_lines = [
            line for line in lines if not line.startswith(f"{subscription_id}:")
        ]

        # Write atomically
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=self.sftp_path, suffix=".tmp"
        ) as tmp_file:
            tmp_file.writelines(filtered_lines)
            tmp_path = tmp_file.name

        shutil.move(tmp_path, self.users_conf)
