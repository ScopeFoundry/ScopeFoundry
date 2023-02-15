import logging
import subprocess
from enum import Enum

logger = logging.getLogger()


class InfoTypes(Enum):
    INFO = "INFO"
    FAILED = "FAILED"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    TASK = "TASK"


def decorate_info_text(text, info_type: InfoTypes):
    logger.debug(f"{info_type.value} {text}")
    if info_type == InfoTypes.INFO:
        text = f"<p style='color:black;'>INFO: {text}</p>"
    if info_type == InfoTypes.FAILED:
        text = f"<p style='color:red;'>FAILED: {text}</p>"
    if info_type == InfoTypes.ERROR:
        text = f"<p style='color:#7719aa;'>ERROR: {text}</p>"
    if info_type == InfoTypes.SUCCESS:
        text = f"<p style='color:green;'>SUCCESS: {text}</p>"
    if info_type == InfoTypes.TASK:
        text = f"<p style='color:#ac4c2c;'>TASK: {text}</p>"
    return text


def run_subprocess(cmd: str, shell=True, capture_output=True):
    # logger.debug(f'run_subprocess: {cmd} {shell=}, {capture_output=}')
    logger.debug(f'run_subprocess: {cmd}')
    cp = subprocess.run(cmd.split(), shell=shell,
                        capture_output=capture_output)
    return cp.stdout.decode(), cp.stderr.decode()
