from dotenv import load_dotenv
load_dotenv()

import utils.setup_logging
from utils.interface import create_interface


if __name__ == '__main__':
    interface = create_interface()
    interface.launch()
