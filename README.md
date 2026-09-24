# RF Waveform Test Automation GUI

A Python-based **RF Waveform Test Automation GUI** developed to automate and manage multiple RF communication tests, including **Bit Error Rate (BER), receiver sensitivity, dynamic range, and iPerf throughput testing**.

The application provides a centralized graphical interface for selecting RF waveforms, configuring test parameters, executing automated tests, calculating theoretical performance values, and organizing test results.

## Project Overview

The system was designed with a modular architecture that separates:

* Waveform configuration
* RF test execution
* Theoretical calculations
* Remote Ubuntu communication
* Result processing
* Date-based result storage
* Test-session logging

Waveform characteristics and test parameters are maintained using **JSON configuration files**, allowing different waveform configurations to be managed without modifying the core application.

## Main Features

### 1. Waveform Configuration

The application uses JSON files to define waveform characteristics and test parameters, including:

* Waveform type
* SNR
* Subcarrier configuration
* FEC / coding rate
* RF output power
* Bandwidth
* AWGN configuration
* Frequency-band information

This configuration-based approach makes it easier to add and modify waveform profiles.

### 2. BER Test Automation

The BER module performs automated Bit Error Rate testing for selected waveform configurations.

The system:

1. Loads waveform parameters from the JSON configuration.
2. Configures the selected test parameters.
3. Executes the BER measurement.
4. Calculates the theoretical BER using implemented mathematical equations.
5. Compares measured and theoretical performance.
6. Generates and stores the test results.

The theoretical BER calculation supports analysis of RF communication performance based on modulation and coding parameters.

### 3. Sensitivity Test

The sensitivity module evaluates receiver performance by varying the RF input power and measuring the resulting communication performance.

The system also calculates theoretical sensitivity using parameters such as:

* Bandwidth
* SNR
* Noise power
* Coding rate

Measured results can then be compared with the theoretical values.

### 4. Dynamic Range Test

A dynamic range test module was implemented to evaluate RF performance over a range of input power levels.

The test automatically steps through predefined RF power levels and records the corresponding BER performance.

Example:

```text
RF Power (dBm) | BER (%) | Result
----------------------------------
       -90     | 0.0000  | PASS
       -85     | 0.0000  | PASS
       -80     | 0.0000  | PASS
       -75     | 0.0000  | PASS
```

### 5. iPerf Throughput Automation

The iPerf test integrates the Windows-based Python application with an **Ubuntu Virtual Machine**.

The application establishes an SSH connection to Ubuntu and remotely executes the required iPerf commands.

The communication workflow is:

```text
Python GUI
     │
     ▼
SSH Connection
     │
     ▼
Ubuntu VM
     │
     ▼
iPerf Execution
     │
     ▼
Result Retrieval
     │
     ▼
Result Processing
```

The test supports communication in both directions by automatically switching the iPerf client and server roles between Windows and Ubuntu.

### 6. Automated Result Management

Test results are stored separately according to the test type and waveform.

```text
results/
│
├── BER/
│   ├── HT/
│   ├── GMSK/
│   └── OFDM_4M/
│
├── Sensitivity/
│   ├── HT/
│   ├── GMSK/
│   └── OFDM_4M/
│
└── iPerf/
    ├── HT/
    ├── GMSK/
    └── OFDM_4M/
```

Results are organized using the test date, making it easier to track historical measurements and compare different test sessions.

### 7. Test Session Logging

A separate logging mechanism records the execution status of each test session.

Example:

```text
logs/
├── rf_test_log_20260923.txt
├── rf_test_log_20260924.txt
└── ...
```

The logs can contain:

* Test initialization
* Selected waveform
* Test parameters
* SSH connection status
* Remote command execution
* Test results
* Errors and exceptions
* Test completion status

## Software Architecture

```text
                 RF Test Automation GUI
                           │
                           ▼
                 Waveform Configuration
                        (JSON)
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
       BER Test       Sensitivity Test    iPerf Test
          │                │                │
          ▼                ▼                ▼
  BER Measurement     RF Power Sweep     SSH → Ubuntu
          │                │                │
          ▼                ▼                ▼
 Theoretical BER    Theoretical         iPerf Throughput
   Calculation       Sensitivity          Measurement
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                    Result Processing
                           │
                           ▼
                 Date-Based Result Files
                           │
                           ▼
                    Test Session Logs
```

## Technologies Used

| Technology                         | Purpose                                |
| ---------------------------------- | -------------------------------------- |
| **Python**                         | Core application and automation        |
| **PyQt6**                          | Graphical User Interface               |
| **JSON**                           | Waveform and test configuration        |
| **SSH / Paramiko**                 | Remote Ubuntu communication            |
| **iPerf**                          | Network throughput measurement         |
| **NumPy / Mathematical Functions** | Theoretical calculations               |
| **CSV / Excel**                    | Result processing and reporting        |
| **Ubuntu VM**                      | Remote test execution environment      |
| **Git / GitHub**                   | Version control and project management |

## Supported Test Areas

The project is designed to support multiple RF waveform configurations, including examples such as:

* HT
* GMSK
* HFH
* OFDM 2M
* OFDM 4M
* OFDM 8M
* OFDM 40M
* BLWF GMSK
* BLWF QPSK
* BLWF 8PSK
* OFDM HFH

The framework can be extended with additional waveform configurations through the JSON configuration system.

## Project Structure

```text
RF-Waveform-Test-Automation-GUI/
│
├── main.py
│
├── gui/
│   └── mainwindow.py
│
├── tests/
│   ├── ber.py
│   ├── sensitivity.py
│   ├── dynamic_test.py
│   └── iperf.py
│
├── config/
│   └── waveforms.json
│
├── results/
│   ├── BER/
│   ├── Sensitivity/
│   └── iPerf/
│
├── logs/
│
├── requirements.txt
│
└── README.md
```

## Engineering Objective

The main objective of this project is to reduce manual effort in RF test execution by providing an automated software framework for **test configuration, measurement, theoretical analysis, remote test execution, and result management**.

The modular architecture also provides a foundation for integrating additional RF test cases and measurement equipment in the future.

## Future Improvements

Potential future enhancements include:

* Integration with RF test instruments through SCPI/PyVISA
* Automated report generation
* Graphical BER and sensitivity plots
* Additional RF waveform models
* Automated Excel report generation
* Hardware-in-the-loop testing
* Expanded TDL channel testing
* Integration of TDL-A / TDL-D fading models
* Continuous test execution and regression testing

## Author

**Gayani Harindi**

Electrical & Electronic Engineering

University of Peradeniya
