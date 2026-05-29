# Dataset

Store labeled radar recordings here. Each class gets its own folder:

- `human/`
- `fan/`
- `background/`
- `pet/` optional

Use the serial logger to create CSV files:

```powershell
python "Data Collection/serial_logger.py" --port COM5 --label human --seconds 10
```

Each CSV should contain `time_s`, `adc`, and `voltage` columns.
