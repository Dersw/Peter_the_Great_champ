import logging
import os
import sys
from logging.handlers import RotatingFileHandler

class DualLogger:
    def __init__(self):
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        os.makedirs(self.log_dir, exist_ok=True)

        self.sys_logger = self._setup_file_logger(
            name="System", 
            filename="system.log",
            max_bytes=10*1024*1024,
            backup_count=5
        )

        self.cmd_logger = self._setup_file_logger(
            name="Command", 
            filename="commands.log",
            max_bytes=10*1024*1024,
            backup_count=5
        )

    def _setup_file_logger(self, name, filename, max_bytes, backup_count):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        handler = RotatingFileHandler(
            os.path.join(self.log_dir, filename),
            mode='a',
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def info(self, msg):
        self.sys_logger.info(msg)
        print(f"[INFO] {msg}")

    def error(self, msg):
        self.sys_logger.error(msg)
        print(f"[ERROR] {msg}")

    def warning(self, msg):
        self.sys_logger.warning(msg)
        print(f"[WARNING] {msg}")

    def cmd(self, msg):
        self.cmd_logger.info(msg)
        print(f"[COMMAND] {msg}")

log = DualLogger()