import csv
import math
import os
import platform
import re
import subprocess
from datetime import datetime

from .constants import (BER_RESULTS_DIR,BER_CSV_FIELDNAMES,BER_GMSK_ALPHA,MODULATION_ORDER,)

def db_to_linear(db_value):
    return 10 ** (db_value / 10)

def q_function(x):
    return 0.5 * math.erfc(x / math.sqrt(2))

def coding_rate_to_float(rate_str):
    rate_str = str(rate_str).strip()
    if "/" in rate_str:
        num, den = rate_str.split("/")
        return float(num) / float(den)

    return float(rate_str)

def infer_modulation(waveform_name):
    name = str(waveform_name).upper()

    for modulation, order in MODULATION_ORDER.items():
        if modulation in name:
            return modulation, order

    return "QPSK", MODULATION_ORDER["QPSK"]

def calculate_theoretical_ber(snr_db,coding_rate_str,waveform_name,awgn=True):

    modulation, m_order = infer_modulation( waveform_name)
    snr_linear = db_to_linear(snr_db)
    coding_rate = coding_rate_to_float( coding_rate_str)

    if modulation == "GMSK":
        uncoded_ber = q_function(math.sqrt(2 * BER_GMSK_ALPHA * snr_linear))

    elif modulation == "8PSK":
        k = math.log2(m_order)
        uncoded_ber = (2 / k) * q_function(math.sqrt( 2 * k * snr_linear)* math.sin( math.pi / m_order))

    else:
        uncoded_ber = q_function(math.sqrt(2 * snr_linear))
    coded_ber = (uncoded_ber * coding_rate)
    if not awgn:coded_ber *= 1.5
    coded_ber = min(max(coded_ber, 0.0),1.0)
    return coded_ber, modulation

def ping_host( host="127.0.0.1",count=4,timeout_ms=1000):
    system = platform.system().lower()
    if "windows" in system:
        cmd = ["ping","-n",str(count),"-w",str(timeout_ms),host]
    else:
        timeout_s = max(1,timeout_ms // 1000)
        cmd = ["ping","-c",str(count),"-W",str(timeout_s),host]
    try:
        proc = subprocess.run(cmd,capture_output=True,text=True,timeout=(count * timeout_ms / 1000) + 5,)
        output_text = proc.stdout
    except Exception as exc:
        return {"success": False,
            "packet_loss_percent": 100.0,
            "avg_latency_ms": None,
            "raw": str(exc), }

    return {"success": True,
        "packet_loss_percent":_parse_packet_loss(output_text),
        "avg_latency_ms": _parse_avg_latency(output_text,system),
        "raw": output_text, }


def _parse_packet_loss(text):
    windows_match = re.search(
        r"\((\d+(?:\.\d+)?)%\s*loss\)",
        text,
        re.IGNORECASE)
    if windows_match:
        return float(windows_match.group(1))

    linux_match = re.search(
        r"(\d+(?:\.\d+)?)\s*%\s*(?:packet)?\s*loss",
        text,
        re.IGNORECASE)

    if linux_match:
        return float(linux_match.group(1))
    return None

def _parse_avg_latency(text, system):
    if "windows" in system:
        match = re.search(
            r"Average\s*=\s*(\d+)\s*ms",
            text,
            re.IGNORECASE)
    else:
        match = re.search(
            r"=\s*[\d.]+/"
            r"([\d.]+)/"
            r"[\d.]+/",
            text)
    if match:
        return float(match.group(1))
    return None

def run_ber_test(waveform_name,config,fec,frequency_band, log_callback=None,ping_host_addr="127.0.0.1",ping_count=4):
    def emit(message):
        if log_callback:
            log_callback(message)

    snr_db = config.get("snr_db")
    coding_rate = fec
    awgn = config.get("awgn",True)
    bandwidth_mhz = config.get( "bandwidth_mhz")

    emit(f"[{waveform_name}] "
        f"FEC={fec}, "
        f"Band={frequency_band}")

    ping_result = ping_host(ping_host_addr, count=ping_count)

    if ping_result["success"]:
        emit(f"[{waveform_name}] Ping OK -> "
            f"{ping_result['packet_loss_percent']}% loss, "
            f"avg latency "
            f"{ping_result['avg_latency_ms']} ms")

    else:
        emit(f"[{waveform_name}] "
            f"Ping failed: "
            f"{ping_result.get('raw')}")

    theoretical_ber, modulation = (calculate_theoretical_ber(snr_db, coding_rate,waveform_name, awgn))
    emit(f"[{waveform_name}] "
        f"Modulation={modulation}, "
        f"SNR={snr_db} dB, "
        f"CodingRate={coding_rate}, "
        f"Band={frequency_band}, "
        f"BW={bandwidth_mhz} MHz, "
        f"AWGN={awgn}")

    emit( f"[{waveform_name}] "
        f"Theoretical BER = "
        f"{theoretical_ber:.3e}")


    return { "waveform":waveform_name,
        "fec": fec,
        "frequency_band": frequency_band,
        "snr_db":snr_db,
        "bandwidth_mhz":bandwidth_mhz,
        "modulation":modulation,
        "theoretical_ber":f"{theoretical_ber:.6e}",}

def run_ber_tests(selected_waveforms,selected_fec,selected_bands,waveform_config,log_callback=None,stop_callback=None):
    results = []
    total_tests = (len(selected_waveforms)* len(selected_fec)* len(selected_bands))
    test_number = 0
    if log_callback:
        log_callback("==========================================")
        log_callback( f"Total BER tests to run: {total_tests}")
        log_callback("==========================================")
    for waveform_name in selected_waveforms:
        for fec in selected_fec:
            for frequency_band in selected_bands:
                test_number += 1
                if log_callback:
                    log_callback("==========================================")
                    log_callback(f"BER Test {test_number}/{total_tests}")
                    log_callback(f"Waveform       : {waveform_name}")
                    log_callback(f"FEC            : {fec}")
                    log_callback(f"Frequency Band : {frequency_band}")
                    log_callback("==========================================")

                    config = waveform_config.get(waveform_name)
                    if config is None:
                        continue
                    try:
                        result = run_ber_test(waveform_name=waveform_name, config=config, fec=fec,
                                              frequency_band=frequency_band, log_callback=log_callback)

                        if result: results.append(result)

                    except Exception as exc:
                        if log_callback:
                            log_callback(f"[{waveform_name}] "
                                         f"FEC={fec}, "
                                         f"Band={frequency_band} "
                                         f"BER test failed: "
                                         f"{type(exc).__name__}: "f"{exc}")

                if (stop_callback and stop_callback()):
                    if log_callback:
                        log_callback(f"Stopped before running "f"{waveform_name}.")
                    break

    if results:
        csv_path = save_ber_results_csv(results)
        if log_callback:
            log_callback( f"Saved {len(results)} "f"BER result(s) to "f"{csv_path}")

    if log_callback:
        log_callback("=== BER test run complete ===")
    return results


def save_ber_results_csv(results):
    if not results:
        return None
    date_stamp = datetime.now().strftime("%Y%m%d")
    csv_path = os.path.join(BER_RESULTS_DIR,f"ber_results_{date_stamp}.csv")
    file_exists = os.path.exists(csv_path)

    with open(csv_path,"a",newline="",encoding="utf-8") as file:

        writer = csv.DictWriter(file,fieldnames=BER_CSV_FIELDNAMES )

        if ( not file_exists
                or os.path.getsize(csv_path) == 0):
            writer.writeheader()

        for row in results:
            writer.writerow({field: row.get(field)
                for field in BER_CSV_FIELDNAMES})
    return csv_path