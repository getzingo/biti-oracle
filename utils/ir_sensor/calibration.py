"""
Calibration data and conversion functions for the
Seeed Studio Grove Infrared Temperature Sensor v1.2.

Based on manufacturer's reference implementation.
"""
import os
import yaml

# ── Load config ──────────────────────────────────────────────────
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(_CONFIG_PATH) as f:
    _cfg = yaml.safe_load(f)

VREF: float = float(_cfg["vref"])
ADC_MAX: float = float(_cfg["adc_max"])
REFERENCE_VOL: float = float(_cfg["reference_vol"])
OFFSET_VOL: float = float(_cfg["offset_vol"])
TEMPERATURE_RANGE: float = float(_cfg["temp_range"])

# ── NTC thermistor resistance lookup (0°C to 99°C) ───────────────
# Used with binary search to find ambient temperature.
NTC_RESISTANCE_TABLE = [
    318300, 302903, 288329, 274533, 261471, 249100, 237381, 226276, 215750, 205768,
    196300, 187316, 178788, 170691, 163002, 155700, 148766, 142183, 135936, 130012,
    124400, 119038, 113928, 109059, 104420, 100000,  95788,  91775,  87950,  84305,
     80830,  77517,  74357,  71342,  68466,  65720,  63098,  60595,  58202,  55916,
     53730,  51645,  49652,  47746,  45924,  44180,  42511,  40912,  39380,  37910,
     36500,  35155,  33866,  32631,  31446,  30311,  29222,  28177,  27175,  26213,
     25290,  24403,  23554,  22738,  21955,  21202,  20479,  19783,  19115,  18472,
     17260,  16688,  16138,  15608,  15098,  14608,  14135,  13680,  13242,  12819,
     12412,  12020,  11642,  11278,  10926,  10587,  10260,   9945,   9641,   9347,
      9063,   8789,   8525,   8270,   8023,   7785,   7555,   7333,   7118,   6911,
]

# ── Object temperature lookup table ──────────────────────────────
# 13 rows = ambient temp -10°C to 110°C in 10°C steps
# 12 cols = object temp -10°C to 100°C in 10°C steps
# Values are thermopile output voltages (V).
OBJECT_TEMP_TABLE = [
    # ambient: -10°C
    [ 0, -0.274, -0.58,  -0.922, -1.301, -1.721, -2.183, -2.691, -3.247, -3.854, -4.516, -5.236],
    # ambient:   0°C
    [ 0.271, 0, -0.303, -0.642, -1.018, -1.434, -1.894, -2.398, -2.951, -3.556, -4.215, -4.931],
    # ambient:  10°C
    [ 0.567, 0.3, 0, -0.335, -0.708, -1.121, -1.577, -2.078, -2.628, -3.229, -3.884, -4.597],
    # ambient:  20°C
    [ 0.891, 0.628, 0.331, 0, -0.369, -0.778, -1.23, -1.728, -2.274, -2.871, -3.523, -4.232],
    # ambient:  30°C
    [ 1.244, 0.985, 0.692, 0.365, 0, -0.405, -0.853, -1.347, -1.889, -2.482, -3.13, -3.835],
    # ambient:  40°C
    [ 1.628, 1.372, 1.084, 0.761, 0.401, 0, -0.444, -0.933, -1.47, -2.059, -2.702, -3.403],
    # ambient:  50°C
    [ 2.043, 1.792, 1.509, 1.191, 0.835, 0.439, 0, -0.484, -1.017, -1.601, -2.24, -2.936],
    # ambient:  60°C
    [ 2.491, 2.246, 1.968, 1.655, 1.304, 0.913, 0.479, 0, -0.528, -1.107, -1.74, -2.431],
    # ambient:  70°C
    [ 2.975, 2.735, 2.462, 2.155, 1.809, 1.424, 0.996, 0.522, 0, -0.573, -1.201, -1.887],
    # ambient:  80°C
    [ 3.495, 3.261, 2.994, 2.692, 2.353, 1.974, 1.552, 1.084, 0.568, 0, -0.622, -1.301],
    # ambient:  90°C
    [ 4.053, 3.825, 3.565, 3.27,  2.937, 2.564, 2.148, 1.687, 1.177, 0.616, 0, -0.673],
    # ambient: 100°C
    [ 4.651, 4.43,  4.177, 3.888, 3.562, 3.196, 2.787, 2.332, 1.829, 1.275, 0.666, 0],
    # ambient: 110°C
    [ 5.29,  5.076, 4.83,  4.549, 4.231, 3.872, 3.47,  3.023, 2.527, 1.98,  1.379, 0.72],
]


# ══════════════════════════════════════════════════════════════════
#  Conversion functions
# ══════════════════════════════════════════════════════════════════

def adc_to_voltage(raw: int) -> float:
    """Convert 10-bit ADC raw value to voltage (INTERNAL 1.1V ref)."""
    return raw * VREF / ADC_MAX


def voltage_to_ntc_resistance(voltage: float) -> float:
    """NTC resistance from voltage divider (2MΩ pull-up to 2.5V)."""
    if voltage <= 0:
        return NTC_RESISTANCE_TABLE[0]
    if voltage >= 2.5:
        return NTC_RESISTANCE_TABLE[-1]
    return 2000000.0 * voltage / (2.50 - voltage)


def _bin_search_ntc(resistance: float) -> int:
    """Binary search in descending NTC table. Returns index (0-99)."""
    low, high = 0, len(NTC_RESISTANCE_TABLE) - 1
    mid = 0
    while low <= high:
        mid = (low + high) // 2
        if resistance < NTC_RESISTANCE_TABLE[mid]:
            low = mid + 1
        else:
            high = mid - 1
    return mid


def calculate_ambient_temp(adc_raw: int, temp_calibration: float = 0.0) -> float:
    """Ambient temperature from NTC ADC reading.

    Algorithm (OEM):
      1. ADC → voltage (1.1V ref)
      2. Voltage → NTC resistance via 2MΩ divider
      3. Binary search + interpolate in NTC table

    Returns °C.
    """
    voltage = adc_to_voltage(adc_raw)
    resistance = voltage_to_ntc_resistance(voltage)
    idx = _bin_search_ntc(resistance)

    if idx <= 0:
        return 0.0
    if idx >= len(NTC_RESISTANCE_TABLE):
        return float(len(NTC_RESISTANCE_TABLE) - 1)

    return (idx - 1) + temp_calibration + (
        (NTC_RESISTANCE_TABLE[idx - 1] - resistance)
        / (NTC_RESISTANCE_TABLE[idx - 1] - NTC_RESISTANCE_TABLE[idx])
    )


def _interpolate_ambient_column(
    sur_temp_c: float,
    row: int,
) -> float:
    """Linearly interpolate the table voltage between ambient columns.

    The table has columns at -10, 0, 10, 20, ..., 100°C (index 0-11).
    Most ambient temps fall between two columns — interpolate instead of snapping.
    """
    temp = sur_temp_c + 10  # shift so -10°C → 0
    col_low = int(temp / 10)
    col_high = col_low + 1
    frac = (temp / 10.0) - col_low

    if col_low < 0:
        return OBJECT_TEMP_TABLE[row][0]
    if col_high > 11:
        return OBJECT_TEMP_TABLE[row][11]

    v_low = OBJECT_TEMP_TABLE[row][col_low]
    v_high = OBJECT_TEMP_TABLE[row][col_high]
    return v_low + frac * (v_high - v_low)


def _array_search(sur_temp_c: float, voltage_mv: float) -> int:
    """Find row index in OBJECT_TEMP_TABLE for given ambient + thermopile mV.

    Uses ambient interpolation so readings aren't quantized to 10°C steps.
    """
    voltage = voltage_mv / 1000.0
    for row in range(12):
        v_row = _interpolate_ambient_column(sur_temp_c, row)
        v_next = _interpolate_ambient_column(sur_temp_c, row + 1)
        if v_row <= voltage <= v_next or v_next <= voltage <= v_row:
            return row
    return 0


def calculate_object_temp(
    adc_raw: int,
    ambient_temp_c: float,
    reference_vol: float = REFERENCE_VOL,
    offset_vol: float = OFFSET_VOL,
) -> float:
    """Object temperature from thermopile ADC reading.

    Algorithm (OEM):
      1. ADC → voltage
      2. Differential V = V_adc - (reference_vol + offset_vol)
      3. 2D table lookup + interpolation

    Returns °C.
    """
    voltage = adc_to_voltage(adc_raw)
    sur_temp_v = voltage - (reference_vol + offset_vol)
    sur_temp_mv = sur_temp_v * 1000.0

    row = _array_search(ambient_temp_c, sur_temp_mv)

    # Use interpolated ambient column values (not snapped to 10°C)
    v_low = _interpolate_ambient_column(ambient_temp_c, row)
    v_high = _interpolate_ambient_column(ambient_temp_c, row + 1)
    if v_high == v_low:
        temp_offset = 0.0
    else:
        temp_offset = TEMPERATURE_RANGE * (sur_temp_v - v_low) / (v_high - v_low)

    base_temp = row * 10 - 10
    return base_temp + temp_offset
