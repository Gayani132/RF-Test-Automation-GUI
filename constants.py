# constants.py

import os
# ============================================================
# Project Directories
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR,"config","waveform.json")

BER_RESULTS_DIR = os.path.join(BASE_DIR, "results", "ber")
SENSITIVITY_RESULTS_DIR = os.path.join(BASE_DIR, "results", "sensitivity")
IPERF_RESULTS_DIR = os.path.join(BASE_DIR, "results", "iperf")
DYNAMIC_RESULTS_DIR = "results/dynamic"
LOG_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(BER_RESULTS_DIR, exist_ok=True)
os.makedirs(SENSITIVITY_RESULTS_DIR, exist_ok=True)
os.makedirs(IPERF_RESULTS_DIR, exist_ok=True)
os.makedirs(DYNAMIC_RESULTS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ============================================================
# BER Constants
# ============================================================
BER_GMSK_ALPHA = 0.68
DEFAULT_SNR_DB = 10.0
DEFAULT_CODING_RATE = "1/1"
DEFAULT_AWGN = True


# ============================================================
# Sensitivity Constants
# ============================================================

THERMAL_NOISE_FLOOR_DBM_PER_HZ = -174.0
DEFAULT_TARGET_BER = 1e-5
DEFAULT_NOISE_FIGURE_DB = 5.0
DEFAULT_IMPLEMENTATION_MARGIN_DB = 2.0
SENSITIVITY_NON_AWGN_FACTOR = 1.5

# ============================================================
# Iperf Constants
# ============================================================

TEST_DURATION = 30
INTERVAL = 1
TARGET_BANDWIDTH = "10M"
TARGET_BANDWIDTH_MBPS = 10
PROTOCOL = "UDP"
SERVER_START_WAIT = 2
SERVER_STOP_WAIT = 2
UBUNTU_USERNAME = "gayani"
UBUNTU_IP = "192.168.56.105"
UBUNTU_PASSWORD= "e19132"
SSH_PORT = 22
IPERF_PORT = 5005

# ============================================================
# Dynamic Range Constants
# ============================================================

DYNAMIC_START_POWER_DBM = -90
DYNAMIC_STOP_POWER_DBM = -30
DYNAMIC_POWER_STEP_DB = 5

# BER acceptance limit
DYNAMIC_BER_LIMIT_PERCENT = 1.0

# ============================================================
# Modulation
# ============================================================

MODULATION_ORDER = {
    "QPSK": 4,
    "GMSK": 2,
    "8PSK": 8,}

# ============================================================
# BER CSV
# ============================================================

BER_CSV_FIELDNAMES = [
    "waveform",
    "fec",
    "frequency_band",
    "snr_db",
    "bandwidth_mhz",
    "modulation",
    "theoretical_ber",
]


# ============================================================
# Sensitivity CSV
# ============================================================

SENSITIVITY_CSV_FIELDNAMES = [
    "waveform",
    "fec",
    "frequency_band",
    "bandwidth_mhz",
    "modulation",
    "target_ber",
    "required_snr_db",
    "sensitivity_dbm",
]
# ============================================================
# IPERF2 CSV FIELD NAMES
# ============================================================
IPERF_SUMMARY_CSV_FIELDNAMES = [
    "waveform",
    "fec",
    "frequency_band",
    "target_bandwidth_mbps",
    "duration_s",
    "total_transfer_mbytes",
    "average_throughput_mbps",
    "jitter_ms",
    "lost_packets",
    "total_packets",
    "packet_loss_percent",]

# ============================================================
# IPERF2 CSV FIELD NAMES
# ============================================================
DYNAMIC_CSV_FIELDS = ["Timestamp",
    "Waveform",
    "FEC",
    "Band",
    "RF_Power_dBm",
    "BER_Percent",
    "Result",]
