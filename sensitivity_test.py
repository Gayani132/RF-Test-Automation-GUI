import csv
import math
import os
from datetime import datetime

from tests.ber_test import (db_to_linear, q_function, coding_rate_to_float, infer_modulation, ping_host, )

from .constants import (THERMAL_NOISE_FLOOR_DBM_PER_HZ,DEFAULT_TARGET_BER,DEFAULT_NOISE_FIGURE_DB,DEFAULT_IMPLEMENTATION_MARGIN_DB,MODULATION_ORDER,SENSITIVITY_RESULTS_DIR,
    SENSITIVITY_CSV_FIELDNAMES,)

def _uncoded_ber_from_snr(snr_linear,modulation):
    modulation = modulation.upper()
    if modulation not in MODULATION_ORDER:
        raise ValueError(f"Unsupported modulation: {modulation}")
    m_order = MODULATION_ORDER[modulation]

    if modulation == "GMSK":
        alpha = 0.68
        return q_function(math.sqrt(2 * alpha * snr_linear))

    elif modulation == "8PSK":
        k = math.log2(m_order)
        return (2 / k) * q_function(math.sqrt(2 * k * snr_linear)* math.sin(math.pi / m_order))

    else:
        return q_function(math.sqrt(2 * snr_linear))

def _snr_linear_for_target_uncoded_ber(target_uncoded_ber,modulation,lo_db=-30.0,hi_db=40.0,max_iter=200,tol=1e-15,):
    lo = db_to_linear(lo_db)
    hi = db_to_linear(hi_db)
    f_lo = (_uncoded_ber_from_snr(lo,modulation) - target_uncoded_ber)
    f_hi = (_uncoded_ber_from_snr(hi,modulation) - target_uncoded_ber)

    if f_lo < 0 or f_hi > 0:
        raise ValueError(f"Target BER "
            f"{target_uncoded_ber:.3e} "
            f"is outside the solvable range "
            f"for {modulation} "
            f"within "
            f"[{lo_db}, {hi_db}] dB SNR.")

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = (_uncoded_ber_from_snr(mid,modulation) - target_uncoded_ber)
        if abs(f_mid) < tol:
            return mid
        if f_mid > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

def calculate_required_snr_db(target_coded_ber, modulation, fec, awgn=True):
    coding_rate = coding_rate_to_float(fec)
    target_uncoded_ber = target_coded_ber / coding_rate
    if not awgn:
        target_uncoded_ber /= 1.5
    target_uncoded_ber = min( max(target_uncoded_ber, 1e-300),0.5)
    snr_linear = _snr_linear_for_target_uncoded_ber(target_uncoded_ber,modulation)
    required_snr_db = 10 * math.log10(snr_linear)
    return required_snr_db

def calculate_sensitivity_dbm(bandwidth_mhz,required_snr_db,noise_figure_db=DEFAULT_NOISE_FIGURE_DB,implementation_margin_db=DEFAULT_IMPLEMENTATION_MARGIN_DB,):
    if (bandwidth_mhz is None
        or bandwidth_mhz <= 0):
        raise ValueError(f"Invalid bandwidth: "
            f"{bandwidth_mhz}")

    bandwidth_hz = (bandwidth_mhz * 1e6)
    noise_power_dbm = (THERMAL_NOISE_FLOOR_DBM_PER_HZ + 10 * math.log10(bandwidth_hz))
    sensitivity_dbm = (noise_power_dbm + noise_figure_db + required_snr_db + implementation_margin_db)
    return sensitivity_dbm

def run_sensitivity_test(waveform_name,config,fec,frequency_band,log_callback=None,target_ber=DEFAULT_TARGET_BER,noise_figure_db=DEFAULT_NOISE_FIGURE_DB,
                         implementation_margin_db=DEFAULT_IMPLEMENTATION_MARGIN_DB,ping_host_addr="127.0.0.1",ping_count=4,):

    def emit(message):
        if log_callback:
            log_callback(message)

    awgn = config.get("awgn",True)
    bandwidth_mhz = config.get("bandwidth_mhz")
    if bandwidth_mhz is None:
        raise ValueError(f"Bandwidth is missing for "
            f"waveform '{waveform_name}'")

    modulation, _ = infer_modulation(waveform_name)

    emit(f"[{waveform_name}] "
         f"FEC={fec}, "
        f"Band={frequency_band}"
        f"Pinging {ping_host_addr} "
        f"(bench liveness check) ...")
    ping_result = ping_host(ping_host_addr,count=ping_count)

    if ping_result["success"]:
        emit(f"[{waveform_name}] "
            f"Ping OK -> "
            f"{ping_result['packet_loss_percent']}% loss, "
            f"avg latency "
            f"{ping_result['avg_latency_ms']} ms")
    else:
        emit(f"[{waveform_name}] "
            f"Ping failed: "
            f"{ping_result.get('raw')}")

    required_snr_db = (calculate_required_snr_db(target_ber,modulation,fec,awgn))
    sensitivity_dbm = (calculate_sensitivity_dbm(bandwidth_mhz,required_snr_db,noise_figure_db,implementation_margin_db))

    emit(f"[{waveform_name}] "
        f"Modulation={modulation}, "
        f"CodingRate={fec}, "
        f"BW={bandwidth_mhz} MHz, "
        f"AWGN={awgn}, "
        f"TargetBER={target_ber:.1e}")

    emit(f"[{waveform_name}] "
        f"Required SNR = "
        f"{required_snr_db:.2f} dB")

    emit(f"[{waveform_name}] "
        f"Theoretical sensitivity = "
        f"{sensitivity_dbm:.2f} dBm "
        f"(NF={noise_figure_db} dB, "
        f"margin={implementation_margin_db} dB)")

    return {"waveform":waveform_name,
        "fec":fec,
        "frequency_band": frequency_band,
        "bandwidth_mhz":bandwidth_mhz,
        "modulation":modulation,
        "target_ber":f"{target_ber:.1e}",
        "required_snr_db":f"{required_snr_db:.3f}",
        "sensitivity_dbm":f"{sensitivity_dbm:.3f}",}

def run_sensitivity_tests(selected_waveforms,selected_fec,selected_bands,waveform_config,log_callback=None,stop_callback=None,):
    results = []
    total_tests = (len(selected_waveforms) * len(selected_fec) * len(selected_bands))
    test_number = 0
    if log_callback:
        log_callback("==========================================")
        log_callback(f"Total Sensitivity tests to run: {total_tests}")
        log_callback("==========================================")
    for waveform_name in selected_waveforms:
        for fec in selected_fec:
            for frequency_band in selected_bands:
                test_number += 1
                if log_callback:
                    log_callback("==========================================")
                    log_callback(f"Sensitivity Test {test_number}/{total_tests}")
                    log_callback(f"Waveform       : {waveform_name}")
                    log_callback(f"FEC            : {fec}")
                    log_callback(f"Frequency Band : {frequency_band}")
                    log_callback("==========================================")

                    config = waveform_config.get(waveform_name)
                    if config is None:
                        continue
                    try:
                        result = run_sensitivity_test(waveform_name=waveform_name, config=config, fec=fec,
                                              frequency_band=frequency_band, log_callback=log_callback)

                        if result: results.append(result)

                    except Exception as exc:
                        if log_callback:
                            log_callback(f"[{waveform_name}] "
                                         f"FEC={fec}, "
                                         f"Band={frequency_band} "
                                         f"Sensitivity test failed: "
                                         f"{type(exc).__name__}: "f"{exc}")

                if (stop_callback and stop_callback()):
                    if log_callback:
                        log_callback(f"Stopped before running "f"{waveform_name}.")
                    break

    if results:
        csv_path = save_sensitivity_results_csv(results)
        if log_callback:
            log_callback(f"Saved {len(results)} "f"Sensitivity result(s) to "f"{csv_path}")

    if log_callback:
        log_callback("=== Sensitivity test run complete ===")
    return results


def save_sensitivity_results_csv(results):
    if not results:
        return None

    date_stamp = datetime.now().strftime("%Y%m%d")
    csv_path = os.path.join(SENSITIVITY_RESULTS_DIR,f"sensitivity_results_{date_stamp}.csv")
    file_exists = os.path.exists(csv_path)

    with open(csv_path,"a",newline="",encoding="utf-8") as file:
        writer = csv.DictWriter(file,fieldnames=SENSITIVITY_CSV_FIELDNAMES)

        if (not file_exists
            or os.path.getsize(csv_path) == 0):

            writer.writeheader()
        for row in results:
            writer.writerow({field: row.get(field)
                for field in SENSITIVITY_CSV_FIELDNAMES })
    return csv_path