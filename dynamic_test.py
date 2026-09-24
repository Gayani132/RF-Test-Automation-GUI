import csv
import os
import time
from datetime import datetime
from tests.constants import (DYNAMIC_START_POWER_DBM,DYNAMIC_STOP_POWER_DBM,DYNAMIC_POWER_STEP_DB,DYNAMIC_BER_LIMIT_PERCENT,DYNAMIC_RESULTS_DIR,)
from tests.ber_test import calculate_theoretical_ber

def sanitize_filename(value):
    value = str(value)
    invalid_characters = '<>:"/\\|?*'
    for char in invalid_characters:
        value = value.replace(char, "_")
    return value.strip()

def run_dynamic_tests(selected_waveforms,selected_fec,selected_bands,
        waveform_config,log_callback=None,stop_callback=None):
    def emit(message):
        if log_callback:
            log_callback(message)
    if stop_callback is None:
        stop_callback = lambda: False
    os.makedirs(DYNAMIC_RESULTS_DIR,exist_ok=True)
    total_tests = (len(selected_waveforms) * len(selected_fec) * len(selected_bands))
    test_number = 0
    emit("")
    emit("==========================================")
    emit("       DYNAMIC RANGE TEST")
    emit("==========================================")
    emit(f"Total Dynamic tests to run: {total_tests}")
    emit(f"RF Power Range: "f"{DYNAMIC_START_POWER_DBM} dBm "f"to "f"{DYNAMIC_STOP_POWER_DBM} dBm")
    emit(f"RF Power Step: "f"{DYNAMIC_POWER_STEP_DB} dB")
    emit(f"BER Limit: "f"{DYNAMIC_BER_LIMIT_PERCENT}%")
    emit("==========================================")
    all_results = []
    for waveform_name in selected_waveforms:
        if stop_callback():
            emit("Dynamic test stopped.")
            break

        config = waveform_config.get(waveform_name)
        if config is None:
            emit(f"[{waveform_name}] "
                f"Configuration not found.")
            continue

        for fec in selected_fec:
            if stop_callback():
                emit("Dynamic test stopped.")
                break

            for frequency_band in selected_bands:
                if stop_callback():
                    emit("Dynamic test stopped.")
                    break

                test_number += 1
                emit("")
                emit("==========================================")
                emit(f"Dynamic Test "f"{test_number}/{total_tests}")
                emit(f"Waveform       : "f"{waveform_name}")
                emit(f"FEC            : "f"{fec}")
                emit(f"Frequency Band : "f"{frequency_band}")
                emit("==========================================")

                results = run_single_dynamic_test(waveform_name=waveform_name,config=config,fec=fec,frequency_band=frequency_band,log_callback=emit,stop_callback=stop_callback,)
                all_results.extend(results)

    emit("")
    emit("==========================================")
    emit("Dynamic Range Test Run Complete")
    emit("==========================================")
    return all_results

def run_single_dynamic_test(waveform_name,config,fec,frequency_band,log_callback=None,stop_callback=lambda: False):
    def emit(message):
        if log_callback:
            log_callback(message)
    results = []

    safe_waveform = sanitize_filename(waveform_name)
    safe_fec = sanitize_filename(fec)
    safe_band = sanitize_filename(frequency_band)
    waveform_dir = os.path.join(DYNAMIC_RESULTS_DIR,safe_waveform)
    os.makedirs(waveform_dir,exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = (f"{safe_waveform}_"f"{safe_fec}_"f"{safe_band}_"f"{timestamp}.csv")
    txt_filename = (f"{safe_waveform}_"f"{safe_fec}_"f"{safe_band}_"f"{timestamp}.txt")
    csv_path = os.path.join(waveform_dir,csv_filename)
    txt_path = os.path.join(waveform_dir,txt_filename)

    power = DYNAMIC_START_POWER_DBM
    while power <= DYNAMIC_STOP_POWER_DBM:
        if stop_callback():
            emit("Stop requested. ""Ending current Dynamic test.")
            break

        emit("")
        emit("------------------------------------------")
        emit(f"Testing RF Power: {power} dBm")
        emit("------------------------------------------")

        configure_rf_power(config=config,power_dbm=power,log_callback=emit)
        time.sleep(1)
        ber_fraction, modulation = (calculate_theoretical_ber(snr_db=config.get("snr_db"),coding_rate_str=fec, waveform_name=waveform_name,awgn=config.get("awgn", True)))
        ber_percent = (ber_fraction * 100.0)
        if ber_percent <= DYNAMIC_BER_LIMIT_PERCENT:
            result = "PASS"
        else:
            result = "FAIL"

        emit(f"Waveform : {waveform_name}")
        emit(f"FEC      : {fec}")
        emit(f"Band     : {frequency_band}" )
        emit(f"Power    : {power} dBm")
        emit(f"SNR      : {config.get('snr_db')} dB")
        emit(f"Modulation : {modulation}")
        emit(f"BER      : {ber_percent:.6f}%")
        emit(f"Result   : {result}")

        results.append({"Timestamp":datetime.now().strftime( "%Y-%m-%d %H:%M:%S" ),
            "Waveform":waveform_name,
            "FEC":fec,
            "Frequency_Band":frequency_band,
            "RF_Power_dBm":power,
            "SNR_dB":config.get("snr_db"),
            "Modulation":modulation,
            "BER_Percent":ber_percent,
            "BER_Limit_Percent":DYNAMIC_BER_LIMIT_PERCENT,
            "Result":result,})

        power += DYNAMIC_POWER_STEP_DB
    save_dynamic_csv(csv_path,results)
    save_dynamic_txt(txt_path,waveform_name,fec,frequency_band,results)
    calculate_dynamic_range(results,emit)
    emit("")
    emit(f"CSV saved: {csv_path}")
    emit(f"TXT saved: {txt_path}")
    return results

def configure_rf_power(config,power_dbm,log_callback=None):
    def emit(message):
        if log_callback:
            log_callback(message)
    config["output_power"] = power_dbm
    emit(f"RF output power set to "f"{power_dbm} dBm")

def save_dynamic_csv(csv_path,results):
    if not results:
        return

    fieldnames = ["Timestamp",
        "Waveform",
        "FEC",
        "Frequency_Band",
        "RF_Power_dBm",
        "SNR_dB",
        "Modulation",
        "BER_Percent",
        "BER_Limit_Percent",
        "Result",]

    with open(csv_path, "w",newline="", encoding="utf-8" ) as file:
        writer = csv.DictWriter( file,fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

def save_dynamic_txt(txt_path,waveform,fec,frequency_band, results):
    with open(txt_path,"w",encoding="utf-8") as file:
        file.write("==========================================\n")
        file.write("RF DYNAMIC RANGE TEST RESULT\n")
        file.write("==========================================\n\n" )
        file.write(f"Waveform       : {waveform}\n")
        file.write(f"FEC            : {fec}\n")
        file.write(f"Frequency Band : {frequency_band}\n\n")
        file.write("RF Power (dBm) | ""BER (%) | ""Result\n")
        file.write("------------------------------------------\n")
        for row in results:
            file.write(f"{row['RF_Power_dBm']:>14} | "
                f"{row['BER_Percent']:>7.6f} | "
                f"{row['Result']}\n" )

def calculate_dynamic_range(results,log_callback=None):
    def emit(message):
        if log_callback:
            log_callback(message)

    pass_powers = []
    for row in results:
        if row["Result"] == "PASS":
            pass_powers.append(float(row["RF_Power_dBm"]))
    if not pass_powers:
        emit("No PASS points found.")
        emit("Dynamic range could not be calculated.")

        return None
    minimum_usable_power = min(pass_powers)
    maximum_usable_power = max( pass_powers)

    dynamic_range = ( maximum_usable_power - minimum_usable_power)
    emit("")
    emit("==========================================")
    emit("Dynamic Range Summary")
    emit("==========================================")
    emit(f"Minimum usable power : "f"{minimum_usable_power} dBm")
    emit(f"Maximum usable power : "f"{maximum_usable_power} dBm")
    emit(f"Dynamic Range       : "f"{dynamic_range:.2f} dB" )
    emit("==========================================")
    return dynamic_range