import os

PROCESSED_DIR = os.path.join(os.path.split(__file__)[0],"processed")

SOURCE_DIR = os.path.join(os.path.expanduser("~"),"SDRTrunk", "recordings")
LOCATION = "x County"
MODEL = "jacktol/whisper-medium.en-fine-tuned-for-ATC-faster-whisper"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE = "int8"
REBROADCAST_DELAY_SECONDS = 60*15 # THERE MIGHT BE A LEGALLY REQUIRED DELAY WHERE YOU LIVE! CONSULT A LAWYER!
