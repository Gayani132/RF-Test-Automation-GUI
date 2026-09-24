
import os
from datetime import datetime

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")  # headless: safe to call from a worker thread
    import matplotlib.pyplot as plt
    _HAVE_MPL = True
except ImportError:
    _HAVE_MPL = False

from tests.constants import LOG_DIR

# results/tdl sits next to results/ber, results/dynamic, ... which sit next
# to logs/ at the project root (logs/ and results/ are siblings in your tree).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(LOG_DIR.rstrip("/\\"))))
RESULTS_DIR = os.path.join(_PROJECT_ROOT, "results", "tdl")


# --------------------------------------------------------------------------
# 3GPP TR 38.901 Table 7.7.2-1 (TDL-A) and Table 7.7.2-4 (TDL-D)
# Each row: (normalized delay, power in dB)
# --------------------------------------------------------------------------
TDL_A_TABLE = [
    (0.0000, -13.4), (0.3819, 0.0), (0.4025, -2.2), (0.5868, -4.0),
    (0.4610, -6.0), (0.5375, -8.2), (0.6708, -9.9), (0.5750, -10.5),
    (0.7618, -7.5), (1.5375, -15.9), (1.8978, -6.6), (2.2242, -16.7),
    (2.1718, -12.4), (2.4942, -15.2), (2.5119, -10.8), (3.0582, -11.3),
    (4.0810, -12.7), (4.4579, -16.2), (4.5695, -18.3), (4.7966, -18.9),
    (5.0066, -16.6), (5.3043, -19.9), (9.6586, -29.7),
]

# TDL-D: first tap is Rician (LOS). Its total power (-0.2 dB) is split into
# a specular (LOS) part and a diffuse Rayleigh part so that the ratio gives
# K1 = 13.3 dB. The remaining 12 taps are ordinary Rayleigh.
TDL_D_TABLE = [
    (0.000, -0.2), (0.035, -18.8), (0.612, -21.0), (1.363, -22.8),
    (1.405, -17.9), (1.804, -20.1), (2.596, -21.9), (1.775, -22.9),
    (4.042, -27.8), (7.937, -23.6), (9.424, -24.8), (9.708, -30.0),
    (12.525, -27.7),
]
TDL_D_K1_DB = 13.3

PROFILES = {
    "TDL-A": {"table": TDL_A_TABLE, "k1_db": None},
    "TDL-D": {"table": TDL_D_TABLE, "k1_db": TDL_D_K1_DB},
}


# --------------------------------------------------------------------------
# Doppler fading
# --------------------------------------------------------------------------
def _jakes_fading(num_samples, sample_rate, max_doppler, rng):
    """Unit-average-power complex Rayleigh process with a classical (Jakes)
    Doppler PSD, generated via the filtered-white-Gaussian-noise method."""
    if max_doppler <= 0:
        # No Doppler spread requested -> static (but still random) tap gain.
        g = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2)
        return np.full(num_samples, g, dtype=complex)

    freqs = np.fft.fftfreq(num_samples, d=1.0 / sample_rate)
    psd = np.zeros(num_samples)
    mask = np.abs(freqs) < max_doppler * 0.999
    psd[mask] = 1.0 / (np.pi * max_doppler * np.sqrt(1.0 - (freqs[mask] / max_doppler) ** 2))

    white = (rng.standard_normal(num_samples) + 1j * rng.standard_normal(num_samples)) / np.sqrt(2)
    shaped = np.fft.fft(white) * np.sqrt(psd)
    fading = np.fft.ifft(shaped) * num_samples

    power = np.mean(np.abs(fading) ** 2)
    if power > 0:
        fading /= np.sqrt(power)
    return fading


def _generate_taps(profile_name, delay_spread, max_doppler, sample_rate, num_samples, rng):
    """Returns a list of (delay_seconds, complex_gain[num_samples]) per tap,
    with tap powers normalized so the model's total average power is 1."""
    cfg = PROFILES[profile_name]
    table = cfg["table"]
    k1_db = cfg["k1_db"]

    norm_delays = np.array([d for d, _ in table])
    powers_db = np.array([p for _, p in table])
    powers_lin = 10.0 ** (powers_db / 10.0)
    powers_lin /= np.sum(powers_lin)  # normalize total average power to 1

    delays_sec = norm_delays * delay_spread  # TR 38.901 Section 7.7.3 scaling

    taps = []
    for idx, (tau, p_lin) in enumerate(zip(delays_sec, powers_lin)):
        if k1_db is not None and idx == 0:
            # Split tap-0 power between a specular LOS ray and a diffuse
            # Rayleigh ray so that P_LOS / P_diffuse = 10^(K1/10).
            k_lin = 10.0 ** (k1_db / 10.0)
            p_los = p_lin * k_lin / (k_lin + 1.0)
            p_diff = p_lin / (k_lin + 1.0)

            fs = 0.7 * max_doppler  # specular Doppler per TR 38.901 7.7.2
            n = np.arange(num_samples)
            phase0 = rng.uniform(0, 2 * np.pi)
            los = np.exp(1j * (2 * np.pi * fs * n / sample_rate + phase0))

            diffuse = _jakes_fading(num_samples, sample_rate, max_doppler, rng)
            gain = np.sqrt(p_los) * los + np.sqrt(p_diff) * diffuse
        else:
            gain = np.sqrt(p_lin) * _jakes_fading(num_samples, sample_rate, max_doppler, rng)

        taps.append((tau, gain))
    return taps


def apply_tdl_channel(tx, sample_rate, delay_spread, max_doppler, profile="TDL-A", rng=None):
    """Passes complex baseband signal `tx` through the requested TDL model.
    Equivalent to MATLAB's `rx = tdl(tx)` in the script you posted."""
    if profile not in PROFILES:
        raise ValueError(f"Unknown TDL profile: {profile}")
    if rng is None:
        rng = np.random.default_rng()

    num_samples = len(tx)
    taps = _generate_taps(profile, delay_spread, max_doppler, sample_rate, num_samples, rng)

    freqs = np.fft.fftfreq(num_samples, d=1.0 / sample_rate)
    tx_f = np.fft.fft(tx)

    rx = np.zeros(num_samples, dtype=complex)
    for tau, gain in taps:
        delayed = np.fft.ifft(tx_f * np.exp(-1j * 2 * np.pi * freqs * tau))
        rx += gain * delayed
    return rx


# --------------------------------------------------------------------------
# GUI-facing entry points (same calling convention as run_ber_tests etc.)
# --------------------------------------------------------------------------
def _run_tdl_profile(profile_name, selected_waveforms, selected_fec, selected_bands,
                      waveform_config, log_callback, stop_callback,
                      delay_spread=100e-9, max_doppler=70.0,
                      sample_rate=20e6, num_samples=200_000):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    rng = np.random.default_rng()

    log_callback(f"--- {profile_name} channel test ---")
    log_callback(f"Delay spread: {delay_spread*1e9:.1f} ns, "
                  f"Max Doppler: {max_doppler:.1f} Hz, "
                  f"Sample rate: {sample_rate/1e6:.1f} Msps")

    for waveform in selected_waveforms:
        if stop_callback():
            break
        for fec in selected_fec:
            if stop_callback():
                break
            for band in (selected_bands or [None]):
                if stop_callback():
                    break

                label = f"{waveform}_FEC{fec.replace('/', '-')}"
                if band:
                    label += f"_{band.replace(' ', '')}"

                log_callback(f"Running {profile_name} for {label} ...")

                tx = (rng.standard_normal(num_samples) +
                      1j * rng.standard_normal(num_samples))
                rx = apply_tdl_channel(tx, sample_rate, delay_spread, max_doppler,
                                        profile=profile_name, rng=rng)

                tx_rms = np.sqrt(np.mean(np.abs(tx) ** 2))
                rx_rms = np.sqrt(np.mean(np.abs(rx) ** 2))
                log_callback(f"  {label}: input RMS={tx_rms:.3f}, "
                              f"output RMS={rx_rms:.3f}")

                if _HAVE_MPL:
                    fig, axes = plt.subplots(2, 1, figsize=(9, 6))
                    axes[0].plot(np.abs(tx[:5000]))
                    axes[0].set_title("Transmitted Signal")
                    axes[0].set_xlabel("Sample")
                    axes[0].set_ylabel("Amplitude")

                    axes[1].plot(np.abs(rx[:5000]))
                    axes[1].set_title(f"{profile_name} Received Signal")
                    axes[1].set_xlabel("Sample")
                    axes[1].set_ylabel("Amplitude")

                    fig.tight_layout()
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    out_path = os.path.join(
                        RESULTS_DIR, f"{profile_name}_{label}_{ts}.png")
                    fig.savefig(out_path, dpi=120)
                    plt.close(fig)
                    log_callback(f"  Saved plot: {out_path}")

    if not stop_callback():
        log_callback(f"--- {profile_name} test complete ---")


def run_tdla_tests(selected_waveforms, selected_fec, selected_bands,
                    waveform_config, log_callback, stop_callback,
                    delay_spread=100e-9, max_doppler=70.0):
    _run_tdl_profile("TDL-A", selected_waveforms, selected_fec, selected_bands,
                      waveform_config, log_callback, stop_callback,
                      delay_spread=delay_spread, max_doppler=max_doppler)


def run_tdld_tests(selected_waveforms, selected_fec, selected_bands,
                    waveform_config, log_callback, stop_callback,
                    delay_spread=100e-9, max_doppler=70.0):
    _run_tdl_profile("TDL-D", selected_waveforms, selected_fec, selected_bands,
                      waveform_config, log_callback, stop_callback,
                      delay_spread=delay_spread, max_doppler=max_doppler)