import os
import logging
import pathlib
import shutil
import sys
import argparse
import subprocess
import tempfile
from typing import List, Tuple, Optional, Dict
import requests
import datetime

import gregistry
from customdataclasses import ServerResult, GameConfig
from sftpmanager import SFTPManager

HOST_API = "http://127.0.0.1:8000/api/server_report"
base_path = os.path.expanduser("~/servermgmnt")
log_path = os.path.join(base_path, "logs")
docker_game_template_path = os.path.join(base_path, "docker-game-templates")
subscription_path = os.path.join(base_path, "subscription-docker-compose")
game_configs_path = os.path.join(base_path, "game-configs")


# Create directories
for path in [
    log_path,
    docker_game_template_path,
    subscription_path,
    game_configs_path,
]:
    os.makedirs(path, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_path, "setup.log")),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("game-server-setup")


class GameServerManager:
    """Main game server management class"""

    def __init__(self):
        self.registry = gregistry.GameRegistry()

    @staticmethod
    def run_command(cmd: str) -> Tuple[int, str, str]:
        """Execute shell command"""
        try:
            logger.debug(f"Executing: {cmd}")
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
                logger.warning(
                    f"Command {cmd} failed with code {return_code}: {stderr}"
                )
            return return_code, stdout, stderr
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return 1, "", str(e)

    def create_compose_file(
        self,
        subscription_id: str,
        ports: List[int],
        memory_limit: str,
        cpu_limit: float,
        game_type: str,
    ) -> str:
        # common seetings for all template compse files
        defaults = {
            "SUBSCRIPTION_ID": subscription_id,
            "MEMORY_LIMIT": memory_limit,
            "CPU_LIMIT": str(cpu_limit),
            "GAME_TYPE": game_type,
        }
        for i, port in enumerate(ports):
            defaults[f"SUBSCRIPTION_PORT_{i}"] = str(port)

        # Set up file paths
        src_template_path = os.path.join(
            docker_game_template_path, f"{game_type}-template.yml"
        )
        target_compose_file = os.path.join(
            subscription_path,
            f"docker-compose-{game_type}-{subscription_id}.yml",
        )
        # Verify template files exist
        if not os.path.exists(src_template_path):
            raise Exception(
                f"Template not found for game: {game_type} at {src_template_path}"
            )

        handler = self.registry.get_handler(game_type)
        # fills and creates compose target compose file as well as env file
        handler.fill_compose_file(defaults=defaults, src_template_path=src_template_path,target_compose_file=target_compose_file)
        handler.create_default_subscription_config_file(
            subscription_path=subscription_path,
            subscription_id=subscription_id,
            docker_game_template_path=docker_game_template_path,
        )

        return target_compose_file

    def start_server(
        self, compose_file: str, subscription_id: str, ports: Optional[List[int]]
    ) -> ServerResult:
        """Start game server using docker compose"""
        logger.info(f"Starting server for {subscription_id}")

        # Start containers
        start_cmd = f"docker compose -f {compose_file} -p {subscription_id} up -d"
        return_code, _, stderr = self.run_command(start_cmd)
        if return_code != 0:
            return ServerResult(
                action="start",
                subscription_id=subscription_id,
                status="failed",
                error=f"Failed to start server: {stderr}",
            )

        # Get container ID
        container_cmd = f"docker compose -f {compose_file} -p {subscription_id} ps -q"
        return_code, stdout, stderr = self.run_command(container_cmd)
        if return_code != 0:
            return ServerResult(
                action="start",
                subscription_id=subscription_id,
                status="failed",
                error=f"Failed to get container id: {stderr}",
            )

        container_id = stdout.strip()

        # Get container IP
        ip_cmd = f"docker inspect -f '{{{{range.NetworkSettings.Networks}}}}{{{{.IPAddress}}}}{{{{end}}}}' {container_id}"
        return_code, stdout, stderr = self.run_command(ip_cmd)
        if return_code != 0:
            return ServerResult(
                action="start",
                subscription_id=subscription_id,
                status="failed",
                error=f"Failed to get container ip: {stderr}",
            )

        container_ip = stdout.strip()

        return ServerResult(
            action="start",
            subscription_id=subscription_id,
            status="running",
            container_id=container_id,
            container_ip=container_ip,
            ports=ports,
        )

    def stop_server(self, subscription_id: str, game_type: str) -> ServerResult:
        """Stop game server"""
        compose_file = os.path.join(
            subscription_path,
            f"docker-compose-{game_type}-{subscription_id}.yml",
        )

        if not os.path.exists(compose_file):
            return ServerResult(
                action="stop",
                subscription_id=subscription_id,
                status="not_found",
                error="Server doesn't exist",
            )

        stop_cmd = f"docker compose -f {compose_file} -p {subscription_id} down"
        return_code, _, stderr = self.run_command(stop_cmd)
        if return_code != 0:
            return ServerResult(
                action="stop",
                subscription_id=subscription_id,
                status="failed",
                error=f"Failed to stop server: {stderr}",
            )

        return ServerResult(
            action="stop",
            subscription_id=subscription_id,
            status="stopped",
        )

    def restart_server(self, subscription_id: str, game_type: str) -> ServerResult:
        """Restart game server"""
        # Stop the server first
        stop_result = self.stop_server(subscription_id, game_type)
        if stop_result.status != "stopped":
            return stop_result

        # Check if compose file exists
        compose_file = os.path.join(
            subscription_path,
            f"docker-compose-{game_type}-{subscription_id}.yml",
        )
        if not os.path.exists(compose_file):
            return ServerResult(
                action="restart",
                subscription_id=subscription_id,
                status="not_found",
                error="Server configuration not found",
            )

        # Start the server again
        return self.start_server(compose_file, subscription_id, None)

    def server_status(self, subscription_id: str, game_type: str) -> ServerResult:
        """Get server status and metrics"""
        compose_file = os.path.join(
            subscription_path,
            f"docker-compose-{game_type}-{subscription_id}.yml",
        )

        if not os.path.exists(compose_file):
            return ServerResult(
                action="status",
                subscription_id=subscription_id,
                status="not_found",
                error="Server not found",
            )

        # Get container ID
        id_cmd = f"docker compose -f {compose_file} -p {subscription_id} ps -q"
        _, container_id, _ = self.run_command(id_cmd)
        container_id = container_id.strip()

        if not container_id:
            return ServerResult(
                action="status",
                subscription_id=subscription_id,
                status="stopped",
                metrics={},
            )

        # Get container status
        status_cmd = f"docker inspect -f '{{{{.State.Status}}}}' {container_id}"
        _, status, _ = self.run_command(status_cmd)
        status = status.strip()

        metrics = {}
        if status == "running":
            # Get CPU usage
            cpu_cmd = (
                f"docker stats {container_id} --no-stream --format '{{{{.CPUPerc}}}}'"
            )
            _, cpu, _ = self.run_command(cpu_cmd)

            # Get memory usage
            mem_cmd = (
                f"docker stats {container_id} --no-stream --format '{{{{.MemUsage}}}}'"
            )
            _, mem, _ = self.run_command(mem_cmd)

            # Get uptime
            uptime_cmd = (
                f"docker inspect --format='{{{{.State.StartedAt}}}}' {container_id}"
            )
            _, uptime, _ = self.run_command(uptime_cmd)

            metrics = {
                "cpu_usage": cpu.strip(),
                "memory_usage": mem.strip(),
                "started_at": uptime.strip(),
            }

        return ServerResult(
            action="status",
            subscription_id=subscription_id,
            status=status,
            container_id=container_id if container_id else None,
            metrics=metrics,
        )

    def update_config(
        self, subscription_id: str, game_type: str, cfg_json: str
    ) -> ServerResult:
        """Update server configuration"""
        try:
            handler = self.registry.get_handler(game_type)
            config: GameConfig = handler.parse_config(cfg_json)

            if not handler.validate_config(config):
                return ServerResult(
                    action="updateConfig",
                    subscription_id=subscription_id,
                    status="failed",
                    error="Invalid configuration",
                )

            # Generate dict variables
            env_vars: Dict[str, str] = handler.generate_env_vars(
                config, subscription_id
            )
            # update the env file or appropriate file
            handler.update_config_file(
                env_vars=env_vars,
                subscription_path=subscription_path,
                subscription_id=subscription_id,
            )

            return ServerResult(
                action="updateConfig",
                subscription_id=subscription_id,
                status="configured",
            )

        except Exception as e:
            return ServerResult(
                action="updateConfig",
                subscription_id=subscription_id,
                status="failed",
                error=str(e),
            )

    def backup(self, subscription_id: str) -> ServerResult:
        now = datetime.datetime.now(datetime.timezone.utc)
        backup_source = f"/srv/allservers/{subscription_id}"
        backup_target = f"/srv/allservers/{subscription_id}/backup-{now.strftime('%Y-%m-%d-%H:%M')}.tar.gz"
        tmp = pathlib.Path(__file__).resolve().parent / "temp"
        tmp.mkdir(exist_ok=True)
        with tempfile.NamedTemporaryFile(
            delete=False, dir=tmp, mode="w", suffix=".tar.gz"
        ) as tmp_file:
            pass

        cmd = f"tar -czf {tmp_file.name} {backup_source}"
        return_code, stdout, stderr = self.run_command(cmd)
        shutil.move(tmp_file.name, backup_target)
        try:
            if return_code == 0:
                return ServerResult(
                    action="backup",
                    subscription_id=subscription_id,
                    status="completed",
                    metrics={
                        "backup_file": backup_target,
                        "size": os.path.getsize(backup_target),
                    },
                )
            else:
                return ServerResult(
                    action="backup",
                    subscription_id=subscription_id,
                    status="failed",
                    error=stderr,
                )
        except Exception as e:
            return ServerResult(
                action="backup",
                subscription_id=subscription_id,
                status="failed",
                error=str(e),
            )

    def update_sftp_server(self, game_type: str, subscription_id: str) -> ServerResult:
        """
        Improved SFTP server update method with better error handling and thread safety

        Args:
            game_type: Type of game server
            subscription_id: Unique subscription identifier

        Returns:
            ServerResult: Result of the SFTP update operation
        """
        try:
            # Initialize SFTP manager if not already done
            if not hasattr(self, "_sftp_manager"):
                self._sftp_manager = SFTPManager()

            # Add user and volume mapping
            result = self._sftp_manager.add_user_volume(game_type, subscription_id)

            # Log the result
            if result.status == "completed":
                logger.info(f"SFTP server updated successfully for {subscription_id}")
                if result.metrics:
                    logger.info(
                        f"SFTP credentials - Username: {result.metrics.get('username')}, "
                        f"Password: {result.metrics.get('password')}"
                    )
            else:
                logger.error(
                    f"Failed to update SFTP server for {subscription_id}: {result.error}"
                )

            return result

        except Exception as e:
            logger.error(f"Unexpected error updating SFTP server: {e}")
            return ServerResult(
                action="sftp_update",
                subscription_id=subscription_id,
                status="failed",
                error=str(e),
            )


def main(argv: List[str]):
    manager = GameServerManager()
    """Main entry point"""
    parser = argparse.ArgumentParser("Game server management")
    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "status", "updateConfig", "backup"],
        help="Action to perform",
    )
    parser.add_argument(
        "-u", "--subscription-id", required=True, help="Unique subscription identifier"
    )
    parser.add_argument(
        "-p", "--port", type=int, nargs="+", help="List of game server ports"
    )
    parser.add_argument("-g", "--game-type", help="Game type (minecraft, valheim, etc)")
    parser.add_argument("-m", "--memory", default="2g", help="Memory limit (e.g. 2g)")
    parser.add_argument(
        "-c", "--cpu", type=float, default=2.0, help="CPU limit (e.g. 2.0)"
    )
    parser.add_argument(
        "--cfg-json", type=str, help="base64 encoded json Configuration of server"
    )

    args = parser.parse_args(argv)

    # Validate game type
    if args.game_type not in manager.registry.get_supported_games():
        logger.error(f"Unsupported game type: {args.game_type}")
        logger.info(
            f"Supported games: {', '.join(manager.registry.get_supported_games())}"
        )
        sys.exit(1)

    # Execute requested action
    result = None
    args.port = []
    if args.action == "start":
        handler = manager.registry.get_handler(args.game_type)
        args.port = handler.default_ports
        logger.info(f"Using  ports for {args.game_type}: {args.port}")

        compose_file = manager.create_compose_file(
            args.subscription_id, args.port, args.memory, args.cpu, args.game_type
        )
        rstp = manager.update_sftp_server(
            args.game_type,
            args.subscription_id,
        )
        result = manager.start_server(compose_file, args.subscription_id, args.
            port)
        if rstp.metrics:
            result.metrics=rstp.metrics

    elif args.action == "stop":
        result = manager.stop_server(args.subscription_id, args.game_type)

    elif args.action == "restart":
        result = manager.restart_server(args.subscription_id, args.game_type)

    elif args.action == "status":
        result = manager.server_status(args.subscription_id, args.game_type)

    elif args.action == "backup":
        result = manager.backup(args.subscription_id)

    elif args.action == "updateConfig":
        if not args.cfg_json:
            logger.error("Configuration JSON is required for updateConfig action")
            sys.exit(1)
        result = manager.update_config(
            args.subscription_id, args.game_type, args.cfg_json
        )

    if result:
        compose_file = os.path.join(
            subscription_path,
            f"docker-compose-{args.game_type}-{args.subscription_id}.yml",
        )
        logger.info(f"Finished {args.action} on {compose_file}")

        # Send result to API
        try:
            logger.info(result.to_dict())
            requests.post(url=HOST_API, json=result.to_dict())
        except Exception as e:
            logger.error(f"Failed to send result to API: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
