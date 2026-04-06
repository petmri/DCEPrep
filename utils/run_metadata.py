import json
import os


def get_nested_value(data, *keys):
    value = data
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def load_report_json(report_dir, source_dir, filename):
    candidates = []
    if report_dir:
        candidates.append(os.path.join(report_dir, 'reports', filename))
    if source_dir:
        candidates.append(os.path.join(source_dir, 'reports', filename))

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            with open(candidate, 'r') as file:
                return candidate, json.load(file)
        except Exception:
            continue

    return None, {}


def find_first_key_value(data, key_names):
    if isinstance(data, dict):
        for key in key_names:
            if key in data:
                return data[key]
        for value in data.values():
            found = find_first_key_value(value, key_names)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = find_first_key_value(item, key_names)
            if found is not None:
                return found
    return None


def coerce_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def coerce_float_list(values):
    if not isinstance(values, list):
        return None

    converted = []
    for value in values:
        try:
            converted.append(float(value))
        except (TypeError, ValueError):
            return None
    return converted


def coerce_indexed_float_list(values):
    if isinstance(values, list):
        return coerce_float_list(values)

    if not isinstance(values, dict):
        return None

    indexed_items = []
    for key, value in values.items():
        if str(key) == 'n_flips':
            continue
        try:
            index = int(key)
            indexed_items.append((index, float(value)))
        except (TypeError, ValueError):
            return None

    if not indexed_items:
        return None

    indexed_items.sort(key=lambda item: item[0])
    return [value for _, value in indexed_items]


def format_backend_usage(backend_used):
    if backend_used is None:
        return None

    backend_text = str(backend_used).strip().lower()
    if 'gpu' in backend_text:
        return 'GPU was used'
    if 'cpu' in backend_text:
        return 'CPU was used'
    return str(backend_used)


def convert_minutes_to_seconds(value):
    if value is None:
        return None

    try:
        seconds = float(value) * 60
    except (TypeError, ValueError):
        return value

    if seconds.is_integer():
        return int(seconds)
    return seconds


def resolve_dce_report_metadata(report_dir, source_dir=None):
    path, data = load_report_json(report_dir, source_dir, 'dce_pipeline_run.json')
    stage_overrides = get_nested_value(data, 'config', 'stage_overrides') or {}

    tr_ms = get_nested_value(data, 'stages', 'A', 'tr_ms')
    if tr_ms is None:
        tr_ms = get_nested_value(stage_overrides, 'tr_ms')
    if tr_ms is None:
        tr_ms = find_first_key_value(data, ['tr_ms', 'repetition_time_ms', 'TR_ms'])

    fa_deg = get_nested_value(data, 'stages', 'A', 'fa_deg')
    if fa_deg is None:
        fa_deg = get_nested_value(stage_overrides, 'fa_deg')
    if fa_deg is None:
        fa_deg = find_first_key_value(data, ['fa_deg', 'flip_angle_deg', 'flip_angle', 'fa'])

    hematocrit = get_nested_value(data, 'stages', 'A', 'hematocrit')
    if hematocrit is None:
        hematocrit = get_nested_value(stage_overrides, 'hematocrit')
    if hematocrit is None:
        hematocrit = find_first_key_value(data, ['hematocrit', 'hct'])

    snr_threshold = get_nested_value(stage_overrides, 'snr_filter')
    if snr_threshold is None:
        snr_threshold = find_first_key_value(data, ['snr_filter', 'snr_threshold', 'aif_snr_threshold'])

    relaxivity = get_nested_value(data, 'stages', 'A', 'relaxivity')
    if relaxivity is None:
        relaxivity = get_nested_value(stage_overrides, 'relaxivity')
    if relaxivity is None:
        relaxivity = find_first_key_value(data, ['relaxivity', 'contrast_agent_relaxivity'])

    steady_state_image = get_nested_value(data, 'stages', 'A', 'steady_state_auto', 'end_1b')
    if steady_state_image is None:
        steady_state_time = get_nested_value(data, 'stages', 'A', 'steady_state_time')
        if isinstance(steady_state_time, list) and steady_state_time:
            steady_state_image = steady_state_time[-1]
    if steady_state_image is None:
        steady_state_image = get_nested_value(stage_overrides, 'steady_state_end')
    if steady_state_image is None:
        steady_state_image = find_first_key_value(
            data,
            ['steady_state_image_number', 'end_of_steady_state_time_image_number', 'steady_state_image'],
        )

    blood_t1_sec = get_nested_value(data, 'stages', 'A', 'blood_t1_mean_sec')
    if blood_t1_sec is None:
        blood_t1_sec = find_first_key_value(data, ['blood_t1_mean_sec', 'blood_t1_sec'])

    n_timepoints_output = get_nested_value(data, 'stages', 'A', 'timepoint_window', 'n_timepoints_output')
    if n_timepoints_output is None:
        n_timepoints_output = find_first_key_value(data, ['n_timepoints_output'])

    time_resolution = get_nested_value(data, 'stages', 'B', 'time_resolution_min')
    if time_resolution is None:
        time_resolution = get_nested_value(data, 'stages', 'A', 'time_resolution_min')
    if time_resolution is None:
        time_resolution = get_nested_value(stage_overrides, 'time_resolution_min')
    time_resolution_sec = None
    if time_resolution is None:
        time_resolution = find_first_key_value(data, ['time_resolution_min'])
    if time_resolution is not None:
        time_resolution_sec = convert_minutes_to_seconds(time_resolution)
    if time_resolution_sec is None:
        time_resolution_sec = coerce_float(find_first_key_value(data, ['time_resolution_sec']))

    r2_fit = get_nested_value(data, 'stages', 'B', 'fit_rsquared_cp_adj')
    if r2_fit is None:
        r2_fit = find_first_key_value(data, ['fit_rsquared_cp_adj', 'fit_r_squared_cp_adj', 'r2_fit'])

    r2_raw = get_nested_value(data, 'stages', 'B', 'fit_rsquared_stlv_adj')
    if r2_raw is None:
        r2_raw = find_first_key_value(data, ['fit_rsquared_stlv_adj', 'fit_r_squared_stlv_adj', 'r2_raw'])

    backend_used = get_nested_value(data, 'stages', 'D', 'backend_used')
    if backend_used is None:
        backend_used = get_nested_value(data, 'stages', 'D', 'selected_backend')
    if backend_used is None:
        backend_used = find_first_key_value(data, ['backend_used'])

    models_run = get_nested_value(data, 'stages', 'D', 'models_run')
    model = models_run[0] if isinstance(models_run, list) and models_run else None
    if model is None:
        model_outputs = get_nested_value(data, 'stages', 'D', 'model_outputs')
        if isinstance(model_outputs, dict) and model_outputs:
            model = next(iter(model_outputs.keys()))
    if model is None:
        model = find_first_key_value(data, ['dce_model', 'model_name', 'model'])

    elapsed_time_sec = get_nested_value(data, 'meta', 'duration_sec')
    if elapsed_time_sec is None:
        elapsed_time_sec = get_nested_value(data, 'provenance', 'duration_sec')
    if elapsed_time_sec is None:
        elapsed_time_sec = find_first_key_value(
            data,
            ['elapsed_time_sec', 'elapsed_seconds', 'runtime_sec', 'duration_sec'],
        )

    return {
        'path': path,
        'data': data,
        'tr_ms': coerce_float(tr_ms),
        'fa_deg': coerce_float(fa_deg),
        'hematocrit': coerce_float(hematocrit),
        'snr_threshold': coerce_float(snr_threshold),
        'relaxivity': coerce_float(relaxivity),
        'steady_state_image': coerce_float(steady_state_image),
        'n_timepoints_output': coerce_float(n_timepoints_output),
        'blood_t1_sec': coerce_float(blood_t1_sec),
        'time_resolution_sec': coerce_float(time_resolution_sec),
        'r2_fit': coerce_float(r2_fit),
        'r2_raw': coerce_float(r2_raw),
        'backend_used': backend_used,
        'model': model,
        'elapsed_time_sec': coerce_float(elapsed_time_sec),
    }


def resolve_t1_report_metadata(report_dir, source_dir=None):
    path, data = load_report_json(report_dir, source_dir, 'parametric_t1_run.json')

    resolved_inputs = get_nested_value(data, 'resolved_inputs') or {}

    tr_ms = get_nested_value(resolved_inputs, 'tr_ms')
    if tr_ms is None:
        tr_ms = find_first_key_value(data, ['tr_ms', 'repetition_time_ms', 'TR_ms'])

    flip_angles_deg = get_nested_value(resolved_inputs, 'flip_angles_deg')
    normalized_flip_angles_deg = coerce_indexed_float_list(flip_angles_deg)
    if normalized_flip_angles_deg is None:
        flip_angles_deg = find_first_key_value(data, ['flip_angles_deg', 'flip_angles', 'fa_deg', 'flip_angle_deg'])
        if not isinstance(flip_angles_deg, list) and flip_angles_deg is not None:
            flip_angles_deg = [flip_angles_deg]
        normalized_flip_angles_deg = coerce_float_list(flip_angles_deg)

    backend_used = get_nested_value(resolved_inputs, 'backend', 'selected')
    if backend_used is None:
        backend_used = find_first_key_value(data, ['backend_used', 'selected'])

    return {
        'path': path,
        'data': data,
        'tr_ms': coerce_float(tr_ms),
        'flip_angles_deg': normalized_flip_angles_deg,
        'backend_used': backend_used,
    }