# Dataset Guide

## Labels

Use one folder per class under `dataset/`, for example:

- `dataset/human/`
- `dataset/dog/`
- `dataset/fan/`
- `dataset/vehicle/`
- `dataset/background/`

The current tools also support the earlier labels `human`, `fan`, `background`, and `pet`.

## Collection

Upload `ESP32 codes/adc_logger.ino` for raw serial recording, then run:

```powershell
python "Data Collection/serial_logger.py" --port COM5 --label human --seconds 10
```

Record at least `20-30` files per class. Keep each recording around `5-10` seconds.

## Important Rule

Do not save ultrasonic distance, speed, or presence values in the training feature table. The ultrasonic sensor is used only during live inference to confirm object presence and display distance/motion.

## Quality Checks

- Record all classes with the same radar circuit and sampling rate.
- Keep the object within the intended detection area.
- Include multiple speeds, angles, and distances per class.
- Add background/no-object data so the model learns non-target conditions.
- Re-run training after adding real hardware data; simulated data is only for software testing.
