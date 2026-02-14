# %%

import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# token = os.environ['tokeny']

current_time = datetime.now().strftime("%H:%M:%S")

# %%


def rand_delay(num):
  import random 
  import time 
  rando = random.random() * num
#   print(rando)
  time.sleep(rando)


# %%


import bom_scraper


rand_delay(5)

# import combiner

