import csv
import os
import re
import shutil
import subprocess
import time
import paramiko
from datetime import datetime

from tests.constants import (IPERF_RESULTS_DIR,TEST_DURATION,INTERVAL,TARGET_BANDWIDTH,TARGET_BANDWIDTH_MBPS,PROTOCOL,IPERF_PORT,
                             IPERF_SUMMARY_CSV_FIELDNAMES,UBUNTU_IP,SSH_PORT,UBUNTU_USERNAME,UBUNTU_PASSWORD,SERVER_START_WAIT,SERVER_STOP_WAIT)

def find_iperf():
    iperf_path = shutil.which("iperf")
    if iperf_path:
        return iperf_path
    raise FileNotFoundError("iperf.exe was not found in Windows PATH.")

def convert_transfer_to_mbytes(value, unit):
    unit = unit.lower()
    if unit.startswith("k"):
        return value / 1024.0
    if unit.startswith("g"):
        return value * 1024.0
    return value

def convert_bandwidth_to_mbps(value, unit):
    unit = unit.lower()
    if unit.startswith("k"):
        return value / 1000.0
    if unit.startswith("g"):
        return value * 1000.0
    return value

def create_ssh_connection():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=UBUNTU_IP,port=SSH_PORT,username=UBUNTU_USERNAME,password=UBUNTU_PASSWORD,timeout=10,look_for_keys=False,allow_agent=False,)
    return ssh

def start_remote_iperf_server(ssh, log_callback=None):
    command = (f"rm -f /tmp/iperf_server.txt && "
        f"export DISPLAY=:0 && "
        f"export XAUTHORITY=$HOME/.Xauthority && "
        f"gnome-terminal -- bash -c "
        f"\"iperf -s -u -p {IPERF_PORT} -i {INTERVAL} "
        f"2>&1 | tee /tmp/iperf_server.txt; "
        f"echo 'iperf server stopped'; "
        f"read\"")
    if log_callback:
        log_callback("Starting iperf2 server on Ubuntu...")
        log_callback(f"SSH command: {command}")
    stdin, stdout, stderr = ssh.exec_command(command)
    stdout.channel.recv_exit_status()
    time.sleep(SERVER_START_WAIT)
    stdin, stdout, stderr = ssh.exec_command(f"pgrep -af 'iperf -s -u -p {IPERF_PORT}'")
    process_check = stdout.read().decode("utf-8",errors="replace")
    if not process_check.strip():
        error = stderr.read().decode("utf-8",errors="replace")
        raise RuntimeError("Ubuntu iperf2 server did not start.\n"
            f"{error}")
    if log_callback:
        log_callback( "Ubuntu iperf2 UDP server started successfully.")

def get_remote_server_output(ssh):
    stdin, stdout, stderr = ssh.exec_command("cat /tmp/iperf_server.txt")
    output = stdout.read().decode("utf-8", errors="replace")
    return output

def parse_iperf_udp_server_report(output):
    pattern = re.compile(
        r"""
        \[\s*\d+\]\s+
        (?P<start>\d+(?:\.\d+)?)
        \s*-\s*
        (?P<end>\d+(?:\.\d+)?)
        \s+sec\s+
        (?P<transfer>[\d.]+)
        \s+
        (?P<transfer_unit>[KMG]Bytes?)
        \s+
        (?P<bandwidth>[\d.]+)
        \s+
        (?P<bandwidth_unit>[KMG]bits/sec)
        \s+
        (?P<jitter>[\d.]+)
        \s+ms
        \s+
        (?P<lost>\d+)
        \s*/\s*
        (?P<total>\d+)
        \s*
        \(
        \s*
        (?P<loss>[\d.]+)
        \s*%
        \s*
        \)""",
        re.VERBOSE | re.IGNORECASE,)

    matches = list(pattern.finditer(output))
    if not matches:
        return None
    match = matches[-1]
    start = float(match.group("start"))
    end = float(match.group("end"))
    transfer = float(match.group("transfer"))
    transfer_unit = match.group("transfer_unit")
    bandwidth = float(match.group("bandwidth"))
    bandwidth_unit = match.group("bandwidth_unit")
    jitter = float(match.group("jitter"))
    lost_packets = int(match.group("lost"))
    total_packets = int(match.group("total"))
    if total_packets > 0:
        packet_loss = (lost_packets / total_packets) * 100.0
    else:
        packet_loss = 0.0
    transfer_mb = convert_transfer_to_mbytes(transfer,transfer_unit)
    throughput_mbps = convert_bandwidth_to_mbps(bandwidth,bandwidth_unit)

    return {"interval_start_s": start,
        "interval_end_s": end,
        "duration_s": round(end - start, 3),
        "total_transfer_mbytes": round(transfer_mb, 3),
        "average_throughput_mbps": round(throughput_mbps, 3),
        "jitter_ms": round(jitter, 3),
        "lost_packets": lost_packets,
        "total_packets": total_packets,
        "packet_loss_percent": round(packet_loss, 3)}

def save_server_output(server_output, waveform_name):
    output_dir = os.path.join(IPERF_RESULTS_DIR, waveform_name)
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_path = os.path.join(output_dir, f"iperf_server_output_{timestamp}.txt")
    with open(txt_path, "w", encoding="utf-8") as file:
        file.write(server_output)
    return txt_path

def save_summary(server_ip, summary, waveform_name,fec,frequency_band):
    os.makedirs(IPERF_RESULTS_DIR,exist_ok=True)
    date_string = datetime.now().strftime("%Y%m%d")
    csv_path = os.path.join(IPERF_RESULTS_DIR, f"iperf_udp_summary_{date_string}.csv")
    file_exists = os.path.exists(csv_path)
    now = datetime.now()

    with open(csv_path,"a",newline="",encoding="utf-8") as file:
        writer = csv.DictWriter(file,fieldnames=IPERF_SUMMARY_CSV_FIELDNAMES)
        if (not file_exists
            or os.path.getsize(csv_path) == 0):
            writer.writeheader()

        writer.writerow({
            "waveform": waveform_name,
            "fec": fec,
            "frequency_band": frequency_band,
            "target_bandwidth_mbps": TARGET_BANDWIDTH_MBPS,
            "duration_s": summary.get("duration_s"),
            "total_transfer_mbytes": summary.get("total_transfer_mbytes"),
            "average_throughput_mbps": summary.get("average_throughput_mbps"),
            "jitter_ms": summary.get("jitter_ms"),
            "lost_packets": summary.get("lost_packets"),
            "total_packets": summary.get("total_packets"),
            "packet_loss_percent": summary.get("packet_loss_percent"),})
    return csv_path

def stop_remote_iperf_server(ssh,log_callback=None):
    command = (f"pkill -f "
        f"'iperf -s -u -p {IPERF_PORT}'")
    try:
        ssh.exec_command(command)
        time.sleep(SERVER_STOP_WAIT)
        if log_callback:
            log_callback("Ubuntu iperf2 server stopped.")
    except Exception as e:
        if log_callback:
            log_callback(f"Warning: could not stop "
                f"Ubuntu iperf2 server: {e}")

def run_iperf_test(waveform_name,fec,frequency_band,log_callback=None):
    def emit(message):
        if log_callback:
            log_callback(message)
    ssh = None
    try:
        emit("==========================================")
        emit("Connecting to Ubuntu through SSH...")
        emit(f"Ubuntu IP: {UBUNTU_IP}")
        emit(f"Waveform       : {waveform_name}")
        emit(f"FEC            : {fec}")
        emit(f"Frequency Band : {frequency_band}")
        ssh = create_ssh_connection()
        emit("SSH connection successful.")
        start_remote_iperf_server(ssh,log_callback)
        iperf_path = find_iperf()
        emit(f"Windows iperf2: {iperf_path}")
        emit("Starting Windows iperf2 UDP client...")
        client_command = [iperf_path,
                          "-c",
                          UBUNTU_IP,
                          "-u",
                          "-p", str(IPERF_PORT),
                          "-t", str(TEST_DURATION),
                          "-i", str(INTERVAL),
                          "-b", TARGET_BANDWIDTH, ]

        emit("Client command: "+ " ".join(client_command))
        client_process = subprocess.run(client_command,capture_output=True,text=True,encoding="utf-8",errors="replace",)
        if client_process.stdout:
            emit("========== WINDOWS CLIENT OUTPUT ==========")
            emit(client_process.stdout)
            emit("===========================================")
        if client_process.stderr:
            emit("Windows iperf stderr:")
            emit(client_process.stderr)
        if client_process.returncode != 0:
            emit("ERROR: Windows iperf2 client failed.")
            emit(f"Return code: "
                f"{client_process.returncode}")
            return None
        emit("iperf2 client completed successfully.")
        time.sleep(SERVER_STOP_WAIT)

        server_output = get_remote_server_output(ssh)
        emit("========== UBUNTU SERVER OUTPUT ==========")
        emit(server_output)
        emit("==========================================")

        server_report = parse_iperf_udp_server_report(server_output)
        if server_report is None:
            emit("ERROR: Could not parse "
                "Ubuntu iperf2 server report.")
            return None
        summary_csv = save_summary(UBUNTU_IP,server_report,waveform_name,fec,frequency_band)
        emit("Summary CSV saved to:")
        emit(summary_csv)

        emit("==========================================")
        emit("UDP TEST RESULTS")
        emit(f"Server IP: {UBUNTU_IP}")
        emit(f"Duration: "
            f"{server_report['duration_s']} s")
        emit(f"Total Transfer: "
            f"{server_report['total_transfer_mbytes']} MB")
        emit(f"Average Throughput: "
            f"{server_report['average_throughput_mbps']} Mbps")
        emit(f"Jitter: "
            f"{server_report['jitter_ms']} ms")
        emit(f"Lost Packets: "
            f"{server_report['lost_packets']}")
        emit(f"Total Packets: "
            f"{server_report['total_packets']}")
        emit(f"Packet Loss: "
            f"{server_report['packet_loss_percent']} %")
        emit("==========================================")
        txt_path = save_server_output(server_output, waveform_name)
        return {"summary":server_report,"server_output_txt":txt_path ,"summary_csv":summary_csv,}

    except Exception as e:
        emit(f"iperf2 test failed: {e}")
        return None

    finally:
        if ssh:
            try:
                stop_remote_iperf_server(ssh,log_callback)
            except Exception:
                pass
            try:
                ssh.close()
            except Exception:
                pass
def run_iperf_tests(selected_waveforms,selected_fec,selected_bands,log_callback=None,stop_callback=None):
    def emit(message):
        if log_callback:
            log_callback(message)
    results = []
    total_tests = (len(selected_waveforms)* len(selected_fec)* len(selected_bands))
    test_number = 0
    emit("==========================================")
    emit(f"Total Iperf tests to run: {total_tests}")
    emit("==========================================")
    for waveform_name in selected_waveforms:
        for fec in selected_fec:
            for frequency_band in selected_bands:
                if stop_callback and stop_callback():
                    emit( "Iperf test stopped by user.")
                    return results
                test_number += 1
                emit("==========================================")
                emit(f"Iperf Test "f"{test_number}/{total_tests}")
                emit(f"Waveform       : "f"{waveform_name}")
                emit(f"FEC            : "f"{fec}")
                emit(f"Frequency Band : "f"{frequency_band}")
                emit("==========================================")
                try:
                    result = run_iperf_test(waveform_name=waveform_name,fec=fec,frequency_band=frequency_band,log_callback=log_callback)
                    if result is not None:
                        results.append(result)
                        summary = result["summary"]
                        emit("iperf2 test completed successfully.")
                        emit(f"Average Throughput: "f"{summary['average_throughput_mbps']} Mbps")
                        emit(f"Jitter:"f"{summary['jitter_ms']} ms")
                        emit(f"Packet Loss: "f"{summary['packet_loss_percent']} %")
                        emit(f"Server Output TXT: "f"{result['server_output_txt']}")
                        emit( f"Summary CSV: "f"{result['summary_csv']}")
                    else:
                        emit(f"iperf2 test failed for "f"{waveform_name}, "f"{fec}, "f"{frequency_band}")
                except Exception as exc:

                    emit( f"iperf2 test exception: "f"{type(exc).__name__}: {exc}")
    emit("==========================================")
    emit("=== All iperf2 tests completed ===")
    emit("==========================================")
    return results