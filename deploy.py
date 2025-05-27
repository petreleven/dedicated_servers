import datetime
from pathlib import Path
import subprocess
import shutil
import logging


def run_cmd(cmd: str):
    process = subprocess.Popen(
        args=cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    stdout, stderr = process.communicate()
    returncode = process.returncode
    if returncode != 0:
        raise RuntimeError(f"ERROR EXECUTING <{cmd}> e:", stderr)


def create_copy_backup(src: Path):
    if not src.exists():
        return
    if not src.is_file():
        raise RuntimeError(f"The src provided should be a file {str(src.resolve())}")
    t = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H%M")
    src.resolve
    dest = str(src.resolve()) + f".backup.{t}"
    shutil.copy2(src, dest)


def deploy_valheim(docker_game_templates_path: Path):
    # copy valheim compose and .env
    current_valheim_path = Path(__file__).resolve().parent / "valheim"
    current_valheim_docker_compose = current_valheim_path / "valheim-template.yml"
    current_valheim_env = current_valheim_path / ".valheim_env"

    if not current_valheim_docker_compose.exists() or not current_valheim_env.exists():
        raise RuntimeError(
            f"Check {str(current_valheim_docker_compose.resolve())} and {str(current_valheim_env.resolve())} exist"
        )

    dest_compose = docker_game_templates_path / "valheim-template.yml"
    dest_env = docker_game_templates_path / ".valheim_env"
    if dest_compose.exists():
        create_copy_backup(dest_compose)
    if dest_env.exists():
        create_copy_backup(dest_env)

    shutil.copy2(current_valheim_docker_compose, dest_compose)
    shutil.copy2(current_valheim_env, dest_env)


def deploy_sftp_server():
    # copy valheim compose and .env
    sftp_path = Path(__file__).resolve().parent / "sftp"
    sftp_docker_compose = sftp_path / "docker-sftp.yml"
    users_conf = sftp_path / "users.conf"

    if not sftp_docker_compose.exists() or not users_conf.exists():
        raise RuntimeError(
            f"Check {str(sftp_docker_compose.resolve())} and {str(users_conf.resolve())} exist"
        )

    create_copy_backup(sftp_docker_compose)
    create_copy_backup(users_conf)


if __name__ == "__main__":
    logging.basicConfig(handlers=[
        logging.StreamHandler()])
    logger = logging.getLogger("deploy logger")
    servermgmnt_path: Path = Path("~/servermgmnt").expanduser()
    servermgmnt_path.mkdir(parents=True, exist_ok=True)


    logs_path = servermgmnt_path / "logs"
    docker_game_templates_path = servermgmnt_path / "docker-game-templates"
    subscription_compose_template_path = (
        servermgmnt_path / "subscription-docker-compose"
    )
    servermangementpaths = [
        logs_path,
        docker_game_templates_path,
        subscription_compose_template_path,
    ]
    for p in servermangementpaths:
        if not p.exists():
            p.mkdir(exist_ok=True)

    run_cmd("docker --version")
    logger.info("Docker exists 👌🏿")
    run_cmd("pip install pyaml")
    logger.info("Installed pyaml 👌🏿")

    # deploy sftp server
    logger.info("Pulling atomz/sftp image")
    run_cmd("docker pull atmoz/sftp")
    deploy_sftp_server()
    # deploy here
    logger.info("Pulling atomz/sftp valheim_server:v0.0.1")
    run_cmd("docker pull petreleven11/valheim_server:v0.0.1")
    deploy_valheim(docker_game_templates_path)
