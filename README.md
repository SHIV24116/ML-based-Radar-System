# ML-Based Doppler Radar System

This project collects Doppler radar ADC samples from an ESP32, processes the signal with DSP, extracts micro-Doppler features, and trains a classical ML classifier for broad motion/object classes.

## Current Scope

- Detect motion in front of the CDM324 radar module.
- Classify recordings into broad classes such as `human`, `fan`, `background`, and optionally `pet`.
- Estimate speed magnitude from dominant Doppler frequency.
- Keep true distance/range and approach/recede direction as future extensions.

## Hardware Signal Chain

`CDM324 radar OUT -> high-pass + midpoint bias -> MCP6002 non-inverting amplifier -> low-pass filter -> ESP32 GPIO34 ADC`

The analog circuit conditions the weak radar signal so the ESP32 can safely sample it in the `0-3.3 V` range.

## Folder Structure

```text
PR project/
  Data Collection/
    serial_logger.py

  dataset/
    README.md
    background/.gitkeep
    fan/.gitkeep
    human/.gitkeep
    pet/.gitkeep

  dataset_simulated/
    background/background_sim_001.csv ... background_sim_008.csv
    fan/fan_sim_001.csv ... fan_sim_008.csv
    human/human_sim_001.csv ... human_sim_008.csv
    pet/pet_sim_001.csv ... pet_sim_008.csv

  docs/
    model_strategy.md
    project_notes.md

  DSP/
    preprocess.py
    radar_dsp.py

  ESP32 codes/
    adc_logger.ino

  ML/
    README.md
    compare_models.py
    feature_extraction.py
    live_predict.py
    train_svm.py

  models/
    .gitkeep
    best_supervised_model.pkl

  outputs/
    features/.gitkeep
    model_comparison/
      feature_table.csv
      summary.json
      supervised_reports.json
      supervised_results.csv
      unsupervised_results.csv
      plots/
        best_confusion_matrix.png
        supervised_accuracy.png
        supervised_macro_f1.png
        unsupervised_ari.png
    plots/.gitkeep
    recordings/.gitkeep

  Simulation/
    README.md
    generate_synthetic_dataset.py

  tools/
    check_environment.py

  circuit_diagram.py
  README.md
  requirements.txt

  zz_web_dashboard/
    README.md
    index.html
    run_dashboard.bat
    server.py
    static/
      app.js
      styles.css
```

`zz_web_dashboard/` is intentionally named with `zz_` so the complete web
dashboard stays visually separated at the bottom of the project tree.

## Setup

```powershell
python -m pip install -r requirements.txt
python "tools/check_environment.py"
```

## Data Collection

Upload `ESP32 codes/adc_logger.ino` to the ESP32. Then record each class:

```powershell
python "Data Collection/serial_logger.py" --port COM5 --label human --seconds 10
python "Data Collection/serial_logger.py" --port COM5 --label fan --seconds 10
python "Data Collection/serial_logger.py" --port COM5 --label background --seconds 10
```

Aim for `20-30` recordings per class, each `5-10` seconds long.

## Inspect A Recording

```powershell
python "DSP/preprocess.py" "dataset/human/human_YYYYMMDD_HHMMSS.csv" --show-stft
```

## Train

```powershell
python "ML/train_svm.py"
```

The trained model is saved to `models/radar_svm.pkl`.

## Software-Only Testing Before Hardware Is Ready

```powershell
python "Simulation/generate_synthetic_dataset.py" --recordings-per-class 30
python "ML/compare_models.py" --dataset dataset_simulated
```

This compares SVM, Random Forest, Extra Trees, Gradient Boosting, KNN,
Logistic Regression, Naive Bayes, K-Means, Gaussian Mixture, Agglomerative
Clustering, and DBSCAN. The best supervised model is saved to
`models/best_supervised_model.pkl`.

It also creates report-ready plots in `outputs/model_comparison/plots/`,
including supervised accuracy, supervised macro F1, unsupervised clustering
quality, and the best model confusion matrix.

## Web Interface

### Launch Locally From VS Code

1. Open this folder in VS Code:

```text
C:\Users\RUPENDRA SINGH\Desktop\PR project
```

2. Open the VS Code terminal:

```text
Terminal -> New Terminal
```

3. Start the local dashboard server:

```powershell
python "zz_web_dashboard\server.py"
```

4. Keep that terminal running and open this URL in a browser:

```text
http://127.0.0.1:8000
```

To stop the dashboard server, click the VS Code terminal and press:

```text
Ctrl + C
```

You can also double-click this launcher file instead of typing the command:

```text
zz_web_dashboard\run_dashboard.bat
```

### What The Dashboard Does

The dashboard connects simulation, dataset status, model comparison, one-file
DSP analysis, live detection, and ESP32 serial recording into one interface.

Main sections:

- `Simulation` creates temporary software-only data.
- `Models` compares supervised and unsupervised ML models.
- `Live Detection` shows the final demo output.
- `Signal` analyzes one saved recording.
- `Collect` records real ADC samples from ESP32 serial.

### Use Simulated Data Before Hardware Is Ready

Use this mode while the radar circuit is not ready.

1. Start the dashboard with `python "zz_web_dashboard\server.py"`.
2. Open `http://127.0.0.1:8000`.
3. Go to `Simulation`.
4. Click `Generate` if `dataset_simulated` is empty or you want fresh data.
5. Go to `Models`.
6. Set dataset to `dataset_simulated`.
7. Click `Run Comparison`.
8. Go to `Live Detection`.
9. Set mode to `Simulated playback`.
10. Set playback dataset to `dataset_simulated`.
11. Click `Start Live`.

The page will show class, confidence, speed magnitude, and recent prediction
history using simulated recordings.

### Switch From Simulated Data To Live ESP32 Data

Use this mode after the radar circuit and ESP32 are ready.

1. Upload `ESP32 codes/adc_logger.ino` to the ESP32.
2. Connect the circuit output to ESP32 `GPIO34`.
3. Confirm the ESP32 serial port in Arduino IDE or Device Manager, for example `COM5`.
4. Start the dashboard with `python "zz_web_dashboard\server.py"`.
5. Open `http://127.0.0.1:8000`.
6. Go to `Collect`.
7. Enter the ESP32 serial port and class label, for example `human`.
8. Record multiple files for each class: `human`, `fan`, `background`, and optional `pet`.
9. Go to `Models`.
10. Change dataset from `dataset_simulated` to `dataset`.
11. Click `Run Comparison` to train on real circuit data.
12. Go to `Live Detection`.
13. Change mode from `Simulated playback` to `ESP32 serial`.
14. Enter the same ESP32 COM port.
15. Click `Start Live`.

At that point the web page becomes the real-time demo screen. It reads ESP32 ADC
samples, runs DSP and ML in the backend, and displays the live detected class,
confidence, and speed magnitude.

Important: after collecting real radar data, always rerun model comparison using
`dataset`, because the model trained on `dataset_simulated` is only for software
testing.

## Live Demo

```powershell
python "ML/live_predict.py" --port COM5
```

The live demo prints class, confidence, and speed magnitude. Direction and distance are intentionally reported as future extensions.
