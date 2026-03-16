# eRovinieta - Home Assistant Integration

[![GitHub Release](https://img.shields.io/github/v/release/emanuelbesliu/homeassistant-erovinieta)](https://github.com/emanuelbesliu/homeassistant-erovinieta/releases/latest)
[![HACS Validation](https://github.com/emanuelbesliu/homeassistant-erovinieta/actions/workflows/validate.yml/badge.svg)](https://github.com/emanuelbesliu/homeassistant-erovinieta/actions/workflows/validate.yml)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-blue.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/emanuelbesliu/homeassistant-erovinieta)](LICENSE)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/emanuelbesliu)

Custom Home Assistant integration for checking **Romanian road tax (rovinieta)** validity and expiry via [erovinieta.ro](https://erovinieta.ro) (CNAIR Romania). **No erovinieta.ro account or login required** — just your plate number and VIN.

Monitors your vehicle's vignette status daily and fires warning events when it's about to expire, so you never get caught driving without a valid rovinieta.

> **No account needed** — This integration uses the same anonymous public lookup available on the erovinieta.ro website. You do not need to create an account, log in, or provide any credentials. Only your vehicle's plate number and VIN (chassis number) are needed.

## Features

- **Vignette validity check** — binary sensor showing if your rovinieta is currently valid
- **Days remaining** — countdown sensor to expiry date
- **Expiry date** — timestamp sensor with the exact expiry date
- **Price paid** — how much was paid for the current vignette (RON)
- **Owner info** — payer name with email in extra attributes
- **Expiry warning events** — fires `erovinieta_expiring_soon` event when days remaining drops below a configurable threshold
- **Multiple vehicles** — add multiple config entries for different vehicles
- **Configurable polling** — defaults to once daily (24h), adjustable from 1h to 7 days
- **Configurable warning threshold** — set how many days before expiry you want to be notified (default: 14 days), changeable anytime in options

## Sensors

After configuration, the following entities are created for each vehicle:

| Entity | Type | Description |
|--------|------|-------------|
| `binary_sensor.erovinieta_{plate}_valid` | Binary Sensor | On = valid rovinieta, Off = expired/none |
| `sensor.erovinieta_{plate}_days_remaining` | Sensor | Days until expiry (0 if expired) |
| `sensor.erovinieta_{plate}_expiry_date` | Sensor | Expiry date (ISO timestamp) |
| `sensor.erovinieta_{plate}_price` | Sensor | Price paid in RON |
| `sensor.erovinieta_{plate}_owner` | Sensor | Payer name (email in extra attributes) |

### Extra Attributes

Each sensor exposes additional attributes:

- **Binary sensor**: `start_date`, `status`, `series`, `vehicle_category`, `duration`, `country`
- **Owner sensor**: `email` attribute with the payer's email address
- **All sensors**: `attribution` (Data provided by erovinieta.ro)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu (top right) and select **Custom repositories**
3. Add `https://github.com/emanuelbesliu/homeassistant-erovinieta` as an **Integration**
4. Search for "eRovinieta" and install it
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/erovinieta` directory to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

No account or login on erovinieta.ro is needed. The setup only asks for your vehicle details.

### Setup

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for **eRovinieta**
3. Enter your vehicle details:
   - **Plate Number** — Romanian registration plate (e.g. `B123ABC`)
   - **VIN / Chassis Number** — Full 17-character VIN
   - **Update interval** (optional) — Polling interval in seconds (default: 86400 = 24h)
   - **Expiry warning threshold** (optional) — Days before expiry to trigger warning events (default: 14)
4. The integration will validate your vehicle by querying erovinieta.ro

### Options

You can change the update interval and warning threshold at any time:

1. Go to **Settings > Devices & Services**
2. Find the eRovinieta entry for your vehicle
3. Click **Configure**
4. Adjust the settings — changes take effect immediately without restart

## Expiry Warning Events

When the days remaining drops below the configured threshold, the integration fires an `erovinieta_expiring_soon` event with the following data:

```yaml
event_type: erovinieta_expiring_soon
data:
  plate_number: "B123ABC"
  days_remaining: 10
  expiry_date: "2025-03-15T23:59:59+00:00"
```

The event fires only once per expiry date to avoid spamming.

### Example Automation — Mobile Notification

```yaml
alias: "Rovinieta Expiring Notification"
description: >-
  Send a mobile notification when the rovinieta is about to expire.
mode: single

triggers:
  - trigger: event
    event_type: erovinieta_expiring_soon

actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "Rovinieta Expiring Soon"
      message: >-
        Rovinieta for {{ trigger.event.data.plate_number }} expires in
        {{ trigger.event.data.days_remaining }} days
        ({{ trigger.event.data.expiry_date[:10] }}).
```

### Example Automation — Persistent Notification

```yaml
alias: "Rovinieta Expiring Dashboard Alert"
description: >-
  Create a persistent notification in HA when rovinieta is expiring.
mode: single

triggers:
  - trigger: event
    event_type: erovinieta_expiring_soon

actions:
  - action: persistent_notification.create
    data:
      title: "Rovinieta Expiring"
      message: >-
        Vehicle {{ trigger.event.data.plate_number }}: rovinieta expires in
        {{ trigger.event.data.days_remaining }} days.
      notification_id: "erovinieta_{{ trigger.event.data.plate_number }}"
```

## Dashboard Examples

### Entities Card

```yaml
type: entities
title: Rovinieta B123ABC
entities:
  - entity: binary_sensor.erovinieta_b123abc_valid
    name: Valid
  - entity: sensor.erovinieta_b123abc_days_remaining
    name: Days Remaining
  - entity: sensor.erovinieta_b123abc_expiry_date
    name: Expires
  - entity: sensor.erovinieta_b123abc_price
    name: Price Paid
  - entity: sensor.erovinieta_b123abc_owner
    name: Owner
```

## How It Works

The integration queries the [erovinieta.ro](https://erovinieta.ro) public anonymous API — **no account or login required**:

1. Fetches a CAPTCHA image from the CNAIR server
2. Solves the CAPTCHA using a built-in Pillow-based template OCR engine (no external ML dependencies)
3. Queries the road tax status using your plate number and VIN
4. Parses the response and updates all sensors

Unlike other erovinieta integrations that require you to create an account and log in, this integration uses the same anonymous public lookup available on the erovinieta.ro website. No credentials are stored or transmitted — only your plate number and VIN.

## Troubleshooting

### CAPTCHA Failures

The integration retries CAPTCHA solving up to 3 times per update cycle. If you see persistent errors:

1. Check Home Assistant logs: **Settings > System > Logs**, filter for `erovinieta`
2. The erovinieta.ro server may be temporarily unavailable
3. Try triggering a manual refresh from the integration page

### Sensors Show "Unknown"

- The vehicle may not have an active rovinieta — the binary sensor will show "Off" and days remaining will be 0
- If you recently purchased a rovinieta, it may take time to appear in the CNAIR system

### "Cannot Connect" During Setup

- Verify the plate number and VIN are correct
- The erovinieta.ro server may be temporarily down
- Try again in a few minutes

## Technical Details

- **API**: erovinieta.ro anonymous REST API (CNAIR Romania) — no account or login needed
- **CAPTCHA**: Server-side image CAPTCHA, solved via built-in Pillow-based template OCR (no external ML dependencies)
- **Polling**: Configurable, defaults to every 24 hours
- **Dependencies**: None beyond Pillow (bundled with Home Assistant)
- **Platforms**: `sensor`, `binary_sensor`

## Security & Privacy

- **No account or login required** — uses the anonymous public API, no credentials to store or protect
- Only plate number and VIN are sent to erovinieta.ro (no passwords, no tokens, no cookies)
- All communication uses HTTPS
- No personal data is stored beyond what the API returns
- Sensitive fields are automatically redacted in Home Assistant diagnostics

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## ☕ Support the Developer

If you find this project useful, consider buying me a coffee!

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/emanuelbesliu)

---

*This integration is not affiliated with CNAIR or erovinieta.ro. Data is provided by the CNAIR public vignette verification system.*
