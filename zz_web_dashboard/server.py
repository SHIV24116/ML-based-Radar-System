"""Local web interface for the ML-based Doppler radar project.

Run from the project root:
    python "zz_web_dashboard\\server.py"

Then open:
    http://127.0.0.1:8000
"""

from __future__ import annotations

import csv
import importlib.util
import json
import pickle
import sys
import threading
import time
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "model_comparison"
MODEL_PATH = PROJECT_ROOT / "models" / "best_supervised_model.pkl"
LIVE_LOCK = threading.Lock()
LIVE_STOP_EVENT = threading.Event()
LIVE_THREAD: threading.Thread | None = None
LIVE_STATE: dict[str, object] = {
    "running": False,
    "mode": None,
    "status": "Idle",
    "error": None,
    "current": None,
    "history": [],
    "started_at": None,
    "samples_seen": 0,
    "last_ultrasonic": None,
}

for folder in ("DSP", "ML", "Simulation"):
    path = PROJECT_ROOT / folder
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from compare_models import compare_supervised, compare_unsupervised, save_comparison_plots  # noqa: E402
from feature_extraction import FEATURE_NAMES, estimate_motion_metrics, extract_features_from_filtered_signal  # noqa: E402
from generate_synthetic_dataset import PROFILES, make_signal, write_recording  # noqa: E402
from radar_dsp import (  # noqa: E402
    bandpass_filter,
    compute_fft,
    compute_stft,
    dominant_doppler_frequency,
    estimate_speed_mps,
    load_recording,
)
from train_svm import build_feature_table  # noqa: E402


REQUIRED_PACKAGES = {
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "pandas": "pandas",
    "pyserial": "serial",
    "scikit-learn": "sklearn",
    "scipy": "scipy",
}


def package_status() -> dict[str, bool]:
    return {
        package_name: importlib.util.find_spec(import_name) is not None
        for package_name, import_name in REQUIRED_PACKAGES.items()
    }


def safe_relative_path(path: str | Path) -> Path:
    candidate = (PROJECT_ROOT / path).resolve()
    if not str(candidate).startswith(str(PROJECT_ROOT.resolve())):
        raise ValueError("Path is outside the project folder.")
    return candidate


def dataset_counts(root_name: str) -> dict[str, int]:
    root = PROJECT_ROOT / root_name
    if not root.exists():
        return {}
    counts: dict[str, int] = {}
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        counts[folder.name] = len(list(folder.glob("*.csv")))
    return counts


def read_csv_rows(path: Path, limit: int | None = None) -> list[dict[str, object]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows[:limit] if limit else rows


def read_summary() -> dict[str, object] | None:
    summary_path = OUTPUT_DIR / "summary.json"
    if not summary_path.exists():
        return None
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    plots = summary.get("plots", {})
    normalized_plots = {}
    for name, path in plots.items():
        try:
            plot_path = Path(path)
            if plot_path.is_absolute():
                normalized_plots[name] = relative_output_path(plot_path)
            else:
                normalized_plots[name] = str(plot_path).replace("\\", "/")
        except Exception:
            normalized_plots[name] = str(path).replace("\\", "/")
    summary["plots"] = normalized_plots
    return summary


def relative_output_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    return str(resolved.relative_to(PROJECT_ROOT)).replace("\\", "/")


def model_info() -> dict[str, object] | None:
    if not MODEL_PATH.exists():
        return None
    try:
        with MODEL_PATH.open("rb") as f:
            bundle = pickle.load(f)
    except Exception as exc:  # pragma: no cover - defensive for corrupted model files
        return {"path": str(MODEL_PATH), "error": str(exc)}

    return {
        "path": str(MODEL_PATH),
        "model_name": bundle.get("model_name", "unknown"),
        "labels": bundle.get("labels", []),
        "trained_on": bundle.get("trained_on", "unknown"),
        "fs": bundle.get("fs"),
    }


def load_model_bundle() -> dict[str, object]:
    if not MODEL_PATH.exists():
        raise ValueError("No trained model found. Run model comparison first.")
    with MODEL_PATH.open("rb") as f:
        return pickle.load(f)


def set_live_state(**updates: object) -> None:
    with LIVE_LOCK:
        LIVE_STATE.update(updates)


def get_live_state() -> dict[str, object]:
    with LIVE_LOCK:
        state = dict(LIVE_STATE)
        state["history"] = list(LIVE_STATE.get("history", []))
        return state


def add_live_prediction(prediction: dict[str, object]) -> None:
    with LIVE_LOCK:
        history = list(LIVE_STATE.get("history", []))
        history.insert(0, prediction)
        LIVE_STATE["history"] = history[:20]
        LIVE_STATE["current"] = prediction
        if any(key in prediction for key in ("distance_m", "ultrasonic_speed_mps", "motion", "presence")):
            LIVE_STATE["last_ultrasonic"] = {
                "distance_m": prediction.get("distance_m"),
                "ultrasonic_speed_mps": prediction.get("ultrasonic_speed_mps"),
                "motion": prediction.get("motion"),
                "presence": prediction.get("presence"),
            }


def parse_serial_telemetry(line: str) -> dict[str, object] | None:
    if "=" not in line:
        return None
    parsed: dict[str, object] = {"time": datetime.now().isoformat(timespec="seconds"), "source": "ESP32 telemetry"}
    aliases = {
        "object": "class",
        "label": "class",
        "confidence": "confidence",
        "distance_m": "distance_m",
        "speed_mps": "ultrasonic_speed_mps",
        "ultrasonic_speed_mps": "ultrasonic_speed_mps",
        "motion": "motion",
        "presence": "presence",
    }
    for part in line.split(","):
        if "=" not in part:
            continue
        key, value = [piece.strip() for piece in part.split("=", 1)]
        target = aliases.get(key.lower())
        if not target:
            continue
        if target in {"confidence", "distance_m", "ultrasonic_speed_mps"}:
            try:
                parsed[target] = float(value)
            except ValueError:
                continue
        elif target == "presence":
            parsed[target] = value.lower() in {"1", "true", "yes", "present"}
        else:
            parsed[target] = value
    if "class" not in parsed and "distance_m" not in parsed:
        return None
    parsed.setdefault("presence", parsed.get("distance_m") is not None)
    parsed.setdefault("motion", "Unknown")
    return parsed


def simulated_ultrasonic_snapshot(index: int, label: str) -> dict[str, object]:
    phase = (index % 12) / 12.0
    distance_m = 2.1 + 0.75 * np.sin(phase * 2 * np.pi)
    next_distance_m = 2.1 + 0.75 * np.sin(((index + 1) % 12) / 12.0 * 2 * np.pi)
    speed = abs(next_distance_m - distance_m) / 1.5
    if abs(next_distance_m - distance_m) < 0.03:
        motion = "Stationary"
    elif next_distance_m < distance_m:
        motion = "Approaching"
    else:
        motion = "Receding"
    present = label.lower() != "background"
    return {
        "presence": present,
        "distance_m": round(float(distance_m if present else 0.0), 3),
        "ultrasonic_speed_mps": round(float(speed if present else 0.0), 3),
        "motion": motion if present else "No object",
    }


def predict_adc_window(samples: list[int], bundle: dict[str, object], fs: float) -> dict[str, object]:
    from feature_extraction import extract_features_from_filtered_signal
    from radar_dsp import adc_to_voltage

    voltage = adc_to_voltage(np.asarray(samples, dtype=float))
    filtered = bandpass_filter(voltage, fs=fs)
    features = extract_features_from_filtered_signal(filtered, fs=fs)
    frame = __import__("pandas").DataFrame([features], columns=bundle["feature_names"])
    model = bundle["model"]
    label = str(model.predict(frame)[0])
    confidence = float(np.max(model.predict_proba(frame))) if hasattr(model, "predict_proba") else 0.0
    motion = estimate_motion_metrics(filtered, fs=fs)

    return {
        "time": datetime.now().isoformat(timespec="seconds"),
        "class": label,
        "confidence": round(confidence, 3),
        "speed_mps": round(float(motion["radar_speed_mps"]), 3),
        "motion": "ultrasonic-runtime",
    }


def run_serial_live(payload: dict[str, object], bundle: dict[str, object]) -> None:
    import serial

    port = str(payload.get("port", "COM5"))
    baud = int(payload.get("baud", 115200))
    fs = float(payload.get("fs", 2000.0))
    window_seconds = float(payload.get("window_seconds", 3.0))
    window_size = max(256, int(fs * window_seconds))
    samples: list[int] = []

    set_live_state(status=f"Connecting to {port}", samples_seen=0)
    with serial.Serial(port, baud, timeout=1) as ser:
        time.sleep(2)
        ser.reset_input_buffer()
        set_live_state(status=f"Reading from {port}")
        while not LIVE_STOP_EVENT.is_set():
            line = ser.readline().decode(errors="ignore").strip()
            telemetry = parse_serial_telemetry(line)
            if telemetry:
                add_live_prediction(telemetry)
                continue
            if not line.isdigit():
                continue
            samples.append(int(line))
            set_live_state(samples_seen=int(get_live_state().get("samples_seen", 0)) + 1)

            if len(samples) >= window_size:
                prediction = predict_adc_window(samples[-window_size:], bundle, fs)
                add_live_prediction(prediction)
                samples = samples[-window_size // 2 :]


def run_simulated_live(payload: dict[str, object], bundle: dict[str, object]) -> None:
    dataset = str(payload.get("dataset", "dataset_simulated"))
    fs = float(payload.get("fs", 2000.0))
    window_seconds = float(payload.get("window_seconds", 3.0))
    interval_seconds = float(payload.get("interval_seconds", 1.5))
    window_size = max(256, int(fs * window_seconds))
    recordings = list_recordings(dataset)
    if not recordings:
        raise ValueError(f"No recordings found in {dataset}.")

    index = 0
    set_live_state(status=f"Playing back {dataset}", samples_seen=0)
    while not LIVE_STOP_EVENT.is_set():
        recording = recordings[index % len(recordings)]
        index += 1
        signal = load_recording(PROJECT_ROOT / recording["path"])
        adc_samples = np.rint(signal * 4095 / 3.3).astype(int).tolist()
        if len(adc_samples) < window_size:
            continue
        start = 0 if len(adc_samples) == window_size else int((index * 733) % (len(adc_samples) - window_size))
        window = adc_samples[start : start + window_size]
        prediction = predict_adc_window(window, bundle, fs)
        prediction.update(simulated_ultrasonic_snapshot(index, str(recording["label"])))
        prediction["source"] = recording["path"]
        add_live_prediction(prediction)
        set_live_state(samples_seen=int(get_live_state().get("samples_seen", 0)) + len(window))
        LIVE_STOP_EVENT.wait(interval_seconds)


def live_worker(payload: dict[str, object]) -> None:
    mode = str(payload.get("mode", "serial"))
    try:
        bundle = load_model_bundle()
        set_live_state(
            running=True,
            mode=mode,
            status="Starting",
            error=None,
            current=None,
            history=[],
            started_at=datetime.now().isoformat(timespec="seconds"),
            samples_seen=0,
            last_ultrasonic=None,
        )
        if mode == "simulated":
            run_simulated_live(payload, bundle)
        else:
            run_serial_live(payload, bundle)
        set_live_state(status="Stopped")
    except Exception as exc:
        set_live_state(error=str(exc), status="Error")
    finally:
        set_live_state(running=False)


def start_live_detection(payload: dict[str, object]) -> dict[str, object]:
    global LIVE_THREAD
    if get_live_state().get("running"):
        return get_live_state()

    LIVE_STOP_EVENT.clear()
    LIVE_THREAD = threading.Thread(target=live_worker, args=(payload,), daemon=True)
    LIVE_THREAD.start()
    time.sleep(0.2)
    return get_live_state()


def stop_live_detection(_: dict[str, object]) -> dict[str, object]:
    LIVE_STOP_EVENT.set()
    thread = LIVE_THREAD
    if thread and thread.is_alive():
        thread.join(timeout=2)
    set_live_state(running=False, status="Stopped")
    return get_live_state()


def list_recordings(dataset: str) -> list[dict[str, object]]:
    root = safe_relative_path(dataset)
    if not root.exists():
        return []
    rows = []
    for csv_path in sorted(root.glob("*/*.csv")):
        rows.append(
            {
                "path": str(csv_path.relative_to(PROJECT_ROOT)),
                "label": csv_path.parent.name,
                "name": csv_path.name,
                "size_kb": round(csv_path.stat().st_size / 1024, 1),
            }
        )
    return rows


def generate_simulated_dataset(payload: dict[str, object]) -> dict[str, object]:
    out_dir = safe_relative_path(str(payload.get("out_dir", "dataset_simulated")))
    recordings_per_class = int(payload.get("recordings_per_class", 12))
    seconds = float(payload.get("seconds", 4.0))
    fs = float(payload.get("fs", 2000.0))
    seed = int(payload.get("seed", 42))
    selected_labels = payload.get("classes") or [profile.label for profile in PROFILES]

    profiles = {profile.label: profile for profile in PROFILES}
    selected_profiles = [profiles[label] for label in selected_labels if label in profiles]
    if not selected_profiles:
        raise ValueError("No valid classes selected.")

    rng = np.random.default_rng(seed)
    sample_count = int(seconds * fs)
    t = np.arange(sample_count) / fs

    for profile in selected_profiles:
        for index in range(recordings_per_class):
            voltage = make_signal(profile, t, rng)
            path = out_dir / profile.label / f"{profile.label}_web_{index + 1:03d}.csv"
            write_recording(path, t, voltage)

    return {
        "message": f"Generated {len(selected_profiles) * recordings_per_class} recordings.",
        "dataset": str(out_dir.relative_to(PROJECT_ROOT)),
        "counts": dataset_counts(str(out_dir.relative_to(PROJECT_ROOT))),
    }


def run_model_comparison(payload: dict[str, object]) -> dict[str, object]:
    dataset = str(payload.get("dataset", "dataset_simulated"))
    fs = float(payload.get("fs", 2000.0))
    test_size = float(payload.get("test_size", 0.25))
    random_state = int(payload.get("random_state", 42))

    dataset_root = safe_relative_path(dataset)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    feature_table = build_feature_table(dataset_root, fs=fs)
    feature_table.to_csv(OUTPUT_DIR / "feature_table.csv", index=False)

    x = feature_table[FEATURE_NAMES]
    y = feature_table["label"]
    if y.nunique() < 2:
        raise ValueError("Need at least two classes for model comparison.")

    supervised_results, best, reports = compare_supervised(
        x,
        y,
        test_size=test_size,
        random_state=random_state,
    )
    unsupervised_results = compare_unsupervised(x, y, random_state=random_state)

    supervised_results.to_csv(OUTPUT_DIR / "supervised_results.csv", index=False)
    unsupervised_results.to_csv(OUTPUT_DIR / "unsupervised_results.csv", index=False)
    (OUTPUT_DIR / "supervised_reports.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    plot_paths = save_comparison_plots(
        supervised_results,
        unsupervised_results,
        reports,
        str(best["name"]),
        sorted(y.unique()),
        OUTPUT_DIR,
    )

    summary = {
        "dataset": str(dataset_root),
        "recordings": int(len(feature_table)),
        "classes": sorted(y.unique()),
        "best_supervised_model": best["name"],
        "best_unsupervised_model": str(unsupervised_results.iloc[0]["model"]),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "plots": {name: relative_output_path(path) for name, path in plot_paths.items()},
    }
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    bundle = {
        "model": best["model"],
        "model_name": best["name"],
        "feature_names": FEATURE_NAMES,
        "fs": fs,
        "labels": sorted(y.unique()),
        "trained_on": str(dataset_root),
    }
    with MODEL_PATH.open("wb") as f:
        pickle.dump(bundle, f)

    return {
        "summary": summary,
        "supervised": supervised_results.to_dict(orient="records"),
        "unsupervised": unsupervised_results.replace({np.nan: None}).to_dict(orient="records"),
        "model": model_info(),
        "plots": summary["plots"],
    }


def analyze_recording(payload: dict[str, object]) -> dict[str, object]:
    csv_path = safe_relative_path(str(payload["path"]))
    fs = float(payload.get("fs", 2000.0))

    signal = load_recording(csv_path)
    filtered = bandpass_filter(signal, fs=fs)
    freqs, magnitude = compute_fft(filtered, fs=fs)
    stft_freqs, times, spectrogram = compute_stft(filtered, fs=fs)
    dominant_hz = dominant_doppler_frequency(freqs, magnitude)

    return {
        "path": str(csv_path.relative_to(PROJECT_ROOT)),
        "samples": int(len(signal)),
        "dominant_hz": round(dominant_hz, 3),
        "speed_mps": round(estimate_speed_mps(dominant_hz), 3),
        "signal_mean_v": round(float(np.mean(signal)), 5),
        "signal_std_v": round(float(np.std(signal)), 5),
        "stft_bins": int(len(stft_freqs)),
        "stft_frames": int(len(times)),
        "spectrogram_mean": round(float(np.mean(spectrogram)), 8),
        "features": dict(zip(FEATURE_NAMES, [round(float(value), 6) for value in extract_features_from_filtered_signal(filtered, fs=fs)])),
    }


def record_from_serial(payload: dict[str, object]) -> dict[str, object]:
    import serial

    port = str(payload.get("port", "COM5"))
    baud = int(payload.get("baud", 115200))
    label = str(payload.get("label", "human")).lower().strip()
    seconds = float(payload.get("seconds", 10.0))
    out_dir = safe_relative_path(str(payload.get("out_dir", "dataset")))
    label_dir = out_dir / label
    label_dir.mkdir(parents=True, exist_ok=True)
    output_path = label_dir / f"{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    rows: list[tuple[float, int, float]] = []
    with serial.Serial(port, baud, timeout=1) as ser:
        time.sleep(2)
        ser.reset_input_buffer()
        start = time.perf_counter()
        while time.perf_counter() - start < seconds:
            line = ser.readline().decode(errors="ignore").strip()
            if not line.isdigit():
                continue
            timestamp_s = time.perf_counter() - start
            adc = int(line)
            voltage = adc * (3.3 / 4095)
            rows.append((timestamp_s, adc, voltage))

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "adc", "voltage"])
        writer.writerows(rows)

    return {
        "message": f"Saved {len(rows)} samples.",
        "path": str(output_path.relative_to(PROJECT_ROOT)),
        "samples": len(rows),
    }


class RadarDashboardHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        request_path = parsed.path
        if request_path == "/":
            return str(WEB_DIR / "index.html")
        if request_path.startswith("/static/"):
            return str(WEB_DIR / request_path.removeprefix("/"))
        if request_path.startswith("/outputs/"):
            return str(PROJECT_ROOT / request_path.removeprefix("/"))
        return str(WEB_DIR / "index.html")

    def log_message(self, format: str, *args: object) -> None:
        print(f"[web] {self.address_string()} - {format % args}")

    def send_json(self, data: object, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self.send_json(
                {
                    "environment": package_status(),
                    "datasets": {
                        "dataset": dataset_counts("dataset"),
                        "dataset_simulated": dataset_counts("dataset_simulated"),
                    },
                    "model": model_info(),
                    "summary": read_summary(),
                }
            )
            return

        if parsed.path == "/api/results":
            self.send_json(
                {
                    "summary": read_summary(),
                    "supervised": read_csv_rows(OUTPUT_DIR / "supervised_results.csv"),
                    "unsupervised": read_csv_rows(OUTPUT_DIR / "unsupervised_results.csv"),
                }
            )
            return

        if parsed.path == "/api/live/status":
            self.send_json(get_live_state())
            return

        if parsed.path == "/api/recordings":
            query = parse_qs(parsed.query)
            dataset = query.get("dataset", ["dataset_simulated"])[0]
            self.send_json({"recordings": list_recordings(dataset)})
            return

        super().do_GET()

    def do_POST(self) -> None:
        routes = {
            "/api/simulate": generate_simulated_dataset,
            "/api/compare": run_model_comparison,
            "/api/analyze": analyze_recording,
            "/api/record": record_from_serial,
            "/api/live/start": start_live_detection,
            "/api/live/stop": stop_live_detection,
        }
        parsed = urlparse(self.path)
        action = routes.get(parsed.path)
        if not action:
            self.send_json({"error": "Unknown endpoint."}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            result = action(self.read_json())
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self.send_json(result)


def main() -> None:
    host = "127.0.0.1"
    port = 8000
    server = ThreadingHTTPServer((host, port), RadarDashboardHandler)
    print(f"Radar dashboard running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()




