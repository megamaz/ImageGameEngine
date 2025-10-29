import logging
import sys

class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',   # blue
        'INFO': '', # regular
        'WARNING': '\033[93m', # yellow
        'ERROR': '\033[91m',   # red
        'CRITICAL': '\033[95m' # magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        msg = super().format(record)
        return f"{color}{msg}{self.RESET}"

def setup_logging(out_log_name="_latest.log"):
    print("Setting up Python logger")
    level = logging.DEBUG if "debug" in sys.argv else logging.INFO

    string_format = "[%(asctime)s.%(msecs)03d %(levelname)s | %(module)s.%(funcName)s]: %(message)s"
    string_datefmt = "%H:%M:%S"
    console = logging.StreamHandler()
    file = logging.FileHandler(out_log_name, "w")
    
    file.setFormatter(logging.Formatter(string_format, datefmt=string_datefmt))
    console.setFormatter(ColorFormatter(string_format, datefmt=string_datefmt))
    
    file.setLevel(logging.DEBUG)
    console.setLevel(level)

    logging.basicConfig(handlers=[console, file])
    logging.getLogger().setLevel(logging.DEBUG)

    return logging

def test_logger():
    logg = setup_logging("test.log")
    logg.debug("Debug")
    logg.info("Info")
    logg.warning("Warning")
    logg.error("Error")
    logg.critical("Critical")

if __name__ == "__main__":
    sys.argv.append("debug")
    test_logger()