from io import BytesIO
import hashlib
import pandas as pd
import re


def _generate_note_hash(node_id: str, note_content: str, column_name: str) -> str:
    """Generate a deterministic hash for a note entry to prevent duplicates."""
    combined = f"{node_id}|{note_content.strip()}|{column_name}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:32]


def _read_excel_bytes(excel_file):
    """Return Excel content as bytes, resetting the original stream when possible."""
    if isinstance(excel_file, (bytes, bytearray)):
        return bytes(excel_file)

    if isinstance(excel_file, str):
        raise ValueError(
            "Excel data must come from an uploaded file. File path inputs are no longer supported."
        )

    if not hasattr(excel_file, "read"):
        raise TypeError(
            "Excel data must be provided as an uploaded file object, bytes, or bytearray."
        )

    try:
        if hasattr(excel_file, "seek"):
            excel_file.seek(0)
            data = excel_file.read()
            excel_file.seek(0)
        else:
            data = excel_file.read()
    except Exception as exc:
        raise ValueError(f"Failed to read Excel upload: {exc}") from exc

    if isinstance(data, str):
        raise ValueError("Excel upload must be binary data, not text.")

    return data
def split_path_preserving_brackets(path_string):
    """
    Split a path by '/' while treating content within brackets/parentheses as a single node.
    Example: "A/B/(C/D)/E" -> ["A", "B", "(C/D)", "E"]
    Supports: (), [], {}
    """
    if not path_string:
        return []
    
    parts = []
    current = ""
    bracket_depth = 0
    bracket_chars = {'(': ')', '[': ']', '{': '}'}
    closing_brackets = set(bracket_chars.values())
    bracket_stack = []
    
    for char in path_string:
        if char in bracket_chars:
            bracket_stack.append(bracket_chars[char])
            bracket_depth += 1
            current += char
        elif char in closing_brackets:
            current += char
            if bracket_stack and char == bracket_stack[-1]:
                bracket_stack.pop()
                bracket_depth -= 1
        elif char == '/' and bracket_depth == 0:
            if current:
                parts.append(current)
                current = ""
        else:
            current += char
    
    if current:
        parts.append(current)
    
    return parts


def insert_char_at_positions(s, char, positions):
    """
    Inserts 'char' into string 's' at each index in 'positions'.
    Used for converting compact tag format to hierarchical path.
    """
    for offset, pos in enumerate(positions):
        if pos + offset < len(s):
            s = s[:pos + offset] + char + s[pos + offset:]
    return s


def detect_note_columns(df):
    """
    Dynamically detect note columns in the DataFrame.
    Returns all columns containing 'note' (case-insensitive).
    The hierarchy level is determined by column position, not column name,
    enabling support for different company naming conventions.
    """
    return [col for col in df.columns if 'note' in col.lower()]


def extract_notes_from_row(row, note_columns, path_parts, df):
    """
    Extract notes from a row using column position to determine hierarchy level.

    Args:
        row: DataFrame row
        note_columns: List of note column names
        path_parts: Split path components
        df: DataFrame (for column index lookup)

    Returns:
        Dictionary mapping node_id to list of notes (deduplicated)

    Excel layout (with Unnamed:0 at index 0):
    - Column 0 = Unnamed/empty
    - Column 1 = Hierarchy1, Column 2 = Hierarchy1Note
    - Column 3 = Hierarchy2, Column 4 = Hierarchy2Note
    - etc.
    Formula: depth = col_index // 2
    """
    notes_dict = {}

    for col in note_columns:
        if col not in df.columns:
            continue

        note_text = row.get(col)
        if pd.isna(note_text) or not str(note_text).strip():
            continue

        col_index = df.columns.get_loc(col)
        depth_index = col_index // 2
        depth_index = min(depth_index, len(path_parts))

        if depth_index > 0 and depth_index <= len(path_parts):
            node_id = '/'.join(path_parts[:depth_index])
        else:
            node_id = '/'.join(path_parts)

        note_str = str(note_text).strip()
        if node_id not in notes_dict:
            notes_dict[node_id] = []
        if note_str not in notes_dict[node_id]:
            notes_dict[node_id].append(note_str)

    return notes_dict


def extract_notes_with_hashes(row, note_columns, path_parts, df):
    """
    Extract notes from a row with hash info for deduplication on re-upload.

    Returns:
        Dictionary mapping node_id to list of tuples: (note_text, column_name, hash)
    """
    notes_dict = {}

    for col in note_columns:
        if col not in df.columns:
            continue

        note_text = row.get(col)
        if pd.isna(note_text) or not str(note_text).strip():
            continue

        col_index = df.columns.get_loc(col)
        depth_index = col_index // 2
        depth_index = min(depth_index, len(path_parts))

        if depth_index > 0 and depth_index <= len(path_parts):
            node_id = '/'.join(path_parts[:depth_index])
        else:
            node_id = '/'.join(path_parts)

        note_str = str(note_text).strip()
        note_hash = _generate_note_hash(node_id, note_str, col)

        if node_id not in notes_dict:
            notes_dict[node_id] = []

        if not any(e[2] == note_hash for e in notes_dict[node_id]):
            notes_dict[node_id].append((note_str, col, note_hash))

    return notes_dict


def _fix_node_types(node, depth=0):
    """
    Post-process tree to fix node types based on actual children.
    Nodes with children should NOT be 'sensor' type.
    """
    type_map = ["manufacturer", "segment", "site", "plant", "function", "system", "machine", "stage"]
    if 'children' in node and node['children']:
        if node.get('type') == 'sensor':
            node['type'] = type_map[min(depth, len(type_map) - 1)]
            if 'status' in node:
                del node['status']
        for child in node['children']:
            _fix_node_types(child, depth + 1)
    else:
        if node.get('type') != 'manufacturer':
            node['type'] = 'sensor'
            node['status'] = 'online'


def build_tree_from_excel(excel_file):
    """
    Reads Excel upload, converts flat or '/'-separated TAGs into paths,
    and builds a hierarchical tree structure.
    Defaults to "Sheet2" or first sheet if Sheet2 not found.

    Returns: List of manufacturer nodes (direct roots).
    """
    excel_bytes = _read_excel_bytes(excel_file)

    try:
        xl = pd.ExcelFile(BytesIO(excel_bytes))
    except Exception as exc:
        raise ValueError(f"Failed to read Excel upload: {exc}") from exc

    sheet_to_use = "Sheet2" if "Sheet2" in xl.sheet_names else xl.sheet_names[0]

    try:
        df = pd.read_excel(BytesIO(excel_bytes), sheet_name=sheet_to_use, header=2)
        tag_column = "TAG" if "TAG" in df.columns else "TagName" if "TagName" in df.columns else None
    except Exception:
        df = pd.read_excel(BytesIO(excel_bytes), sheet_name=sheet_to_use)
        tag_column = "TAG" if "TAG" in df.columns else "TagName" if "TagName" in df.columns else None
    
    if not tag_column:
        raise ValueError("Missing required column: TagName or TAG")

    # Dynamically detect note columns
    note_columns = detect_note_columns(df)

    tag_to_path = {}
    for tag in df[tag_column].dropna().unique():
        if "/" in tag:
            tag_to_path[tag] = tag
        else:
            tag_to_path[tag] = insert_char_at_positions(tag, "/", [4, 7, 10, 13, 16, 19, 22, 25])

    df["IOTPATH"] = df[tag_column].map(tag_to_path)

    manufacturers = {}
    notes_from_excel = {}

    def insert_path(path_parts, row_meta):
        if not path_parts:
            return

        manufacturer_name = path_parts[0]

        if manufacturer_name not in manufacturers:
            manufacturers[manufacturer_name] = {
                "id": manufacturer_name,
                "name": manufacturer_name,
                "type": "manufacturer",
                "children": []
            }

        current_node = manufacturers[manufacturer_name]
        current_path = manufacturer_name

        for idx in range(1, len(path_parts)):
            part = path_parts[idx]
            current_path = f"{current_path}/{part}"

            if "children" not in current_node:
                current_node["children"] = []

            child = next((c for c in current_node["children"] if c["name"] == part), None)
            if not child:
                child = {
                    "id": current_path,
                    "name": part,
                    "children": [],
                    "type": "sensor" if idx == len(path_parts) - 1 else [
                        "segment", "site", "plant", "function",
                        "system", "machine", "stage"
                    ][min(idx - 1, 6)]
                }
                current_node["children"].append(child)

            current_node = child

        if len(path_parts) > 1:
            current_node.update({
                **row_meta,
                "status": "online",
                "type": "sensor"
            })

    for _, row in df.iterrows():
        path_parts = split_path_preserving_brackets(row["IOTPATH"])
        meta = {tag_column: row[tag_column]}
        insert_path(path_parts, meta)

        row_notes = extract_notes_from_row(row, note_columns, path_parts, df)

        for node_id, note_list in row_notes.items():
            notes_from_excel.setdefault(node_id, []).extend(note_list)

    def attach_notes_to_tree(node):
        node_id = node.get('id', '')
        node['note'] = '\n\n'.join(notes_from_excel.get(node_id, []))
        
        if 'children' in node:
            for child in node['children']:
                attach_notes_to_tree(child)

    for manufacturer in manufacturers.values():
        attach_notes_to_tree(manufacturer)

    # Fix node types based on actual children (post-processing)
    for manufacturer in manufacturers.values():
        _fix_node_types(manufacturer, depth=0)

    return list(manufacturers.values())


def populate_nodes_from_excel(excel_file, modified_by=None):
    """
    Populates the Node and Note models from Excel upload.
    Defaults to "Sheet2" or first sheet if Sheet2 not found.
    modified_by: User who is performing the upload (for tracking purposes).
    
    MULTI-UPLOAD SUPPORT:
    - Uses get_or_create for nodes (reuses existing)
    - Appends notes instead of overwriting
    - Uses hash-based deduplication to prevent duplicate notes on re-upload
    """
    from .models import Node, Note

    excel_bytes = _read_excel_bytes(excel_file)

    try:
        xl = pd.ExcelFile(BytesIO(excel_bytes))
    except Exception as exc:
        raise ValueError(f"Failed to read Excel upload: {exc}") from exc

    sheet_to_use = "Sheet2" if "Sheet2" in xl.sheet_names else xl.sheet_names[0]

    try:
        df = pd.read_excel(BytesIO(excel_bytes), sheet_name=sheet_to_use, header=2)
        tag_column = "TAG" if "TAG" in df.columns else "TagName" if "TagName" in df.columns else None
    except Exception:
        df = pd.read_excel(BytesIO(excel_bytes), sheet_name=sheet_to_use)
        tag_column = "TAG" if "TAG" in df.columns else "TagName" if "TagName" in df.columns else None
    
    if not tag_column:
        raise ValueError("Missing required column: TagName or TAG")

    # Dynamically detect note columns
    note_columns = detect_note_columns(df)

    notes_collector = {}
    IOTUnique = df[tag_column].dropna().unique()

    for _, row in df.iterrows():
        tag = row[tag_column]
        if pd.isna(tag):
            continue

        node_id = tag if "/" in tag else insert_char_at_positions(tag, "/", [4, 7, 10, 13, 16, 19, 22, 25])
        parts = split_path_preserving_brackets(node_id)

        row_notes = extract_notes_with_hashes(row, note_columns, parts, df)

        for n_id, note_entries in row_notes.items():
            if n_id not in notes_collector:
                notes_collector[n_id] = []
            existing_hashes = {e[2] for e in notes_collector[n_id]}
            for entry in note_entries:
                if entry[2] not in existing_hashes:
                    notes_collector[n_id].append(entry)
                    existing_hashes.add(entry[2])

    created_count = updated_count = 0
    notes_added_count = 0

    for tag in IOTUnique:
        node_id = tag if "/" in tag else insert_char_at_positions(tag, "/", [4, 7, 10, 13, 16, 19, 22, 25])
        node, created = Node.objects.get_or_create(node_id=node_id)
        created_count += created
        if not created:
            updated_count += 1

    for node_id, note_entries in notes_collector.items():
        target_node, _ = Node.objects.get_or_create(node_id=node_id)
        note_obj, note_created = Note.objects.get_or_create(node=target_node)

        existing_hashes = set(note_obj.imported_hashes or [])

        new_notes = []
        new_hashes = []
        for note_text, col_name, note_hash in note_entries:
            if note_hash not in existing_hashes:
                new_notes.append(note_text)
                new_hashes.append(note_hash)
                existing_hashes.add(note_hash)

        if new_notes:
            existing_content = note_obj.content_without_metadata().strip()
            if existing_content:
                combined_content = existing_content + '\n\n' + '\n\n'.join(new_notes)
            else:
                combined_content = '\n\n'.join(new_notes)

            note_obj.content = combined_content
            note_obj.imported_hashes = list(existing_hashes)

            if modified_by:
                note_obj.save(modified_by=modified_by)
            else:
                note_obj.save()

            notes_added_count += len(new_notes)

    return {
        'created': created_count,
        'updated': updated_count,
        'total': created_count + updated_count,
        'notes_added': notes_added_count
    }


# Fault category schema: Category -> { SubCategory -> [keywords...] }
FAULT_CATEGORIES = {
    "Power-Related Faults": {
        "No Power / Device Dead": ["no power", "device dead", "not turning on", "won't start", "no led", "no lights"],
        "Power Supply Failure (AC/DC adapter, DC-DC converter, regulator)": [
            "power supply", "supply failure", "adapter", "regulator", "dc-dc", "buck", "boost", "psu", "smps"
        ],
        "Voltage Fluctuation / Brownout Issues": ["voltage drop", "brownout", "undervoltage", "overvoltage", "voltage fluctuation"],
        "High Current Consumption / Short Circuit": ["high current", "overcurrent", "short", "short circuit", "hot", "heating"],
        "Battery Fault / Battery Not Charging (if applicable)": ["battery", "not charging", "charge", "battery fault", "battery low"],
        "Reverse Polarity / Overvoltage Damage": ["reverse polarity", "polarity reversed", "burnt", "damaged by overvoltage", "over voltage"],
    },
    "Communication Faults": {
        "GSM Network Not Connecting": ["gsm", "no network", "network not connecting", "no service"],
        "SIM Detection Failure": ["sim", "sim not detected", "no sim", "sim error"],
        "GPRS Data Not Transmitting": ["gprs", "data not sending", "no data", "data failed"],
        "Wi-Fi Not Connecting / Weak Signal": ["wifi", "wi-fi", "weak signal", "not connecting", "disconnected"],
        "MQTT / Cloud Communication Failure": ["mqtt", "broker", "cloud", "publish failed", "subscribe failed"],
        "RS485 Communication Failure": ["rs485", "485", "comm fail", "communication error"],
        "Modbus Communication Failure": ["modbus", "crc", "time out", "timeout", "modbus error"],
        "CAN / UART / SPI / I²C Communication Error": ["can", "uart", "spi", "i2c", "i²c", "bus error", "nack", " framing"],
        "BLE / RF Link Failure": ["ble", "bluetooth", "rf", "radio", "link loss"],
    },
    "Controller / Firmware Related": {
        "Controller Not Booting": ["no boot", "not booting", "no start", "boot fail"],
        "Firmware Crash / Hang": ["hang", "freeze", "crash", "lockup", "stuck"],
        "Auto Restart / Watchdog Reset": ["auto restart", "reset", "watchdog", "wdt"],
        "Configuration Not Saving": ["config not saving", "lost settings", "defaults", "not persisted"],
        "Wrong Parameter Readings": ["wrong reading", "incorrect value", "offset", "calculation error"],
        "Bootloader Corrupted / Flash Issue": ["bootloader", "flash error", "flashing failed", "corrupt"],
        "Firmware Update Failure (OTA / Serial)": ["ota", "update failed", "firmware update", "serial flash failed"],
        "RTC Malfunction / Time Drift": ["rtc", "time drift", "wrong time", "clock"],
    },
    "Sensor / Input Faults": {
        "Sensor Not Responding": ["sensor not responding", "no response", "dead sensor"],
        "Wrong Sensor Readings": ["wrong reading", "incorrect reading", "drift", "offset"],
        "ADC Input Error / Noise in Analog Input": ["adc", "analog", "noise", "spike", "ripple"],
        "Digital Input Not Detecting": ["digital input", "not detecting", "no pulse", "edge"],
        "Sensor Calibration Issue": ["calibration", "calibrate", "needs calibration"],
        "Sensor Communication Timeout": ["sensor timeout", "timeout", "no ack"],
    },
    "Output / Actuation Faults": {
        "Relay Not Switching": ["relay", "not switching", "no click", "stuck"],
        "Relay Always ON / OFF": ["relay always on", "relay always off", "welded", "stuck relay"],
        "Output Overload / Burnt Driver": ["overload", "burnt driver", "driver burnt", "mosfet", "transistor"],
        "Output Not Responding to Command": ["output not responding", "no actuation", "no output"],
        "PWM / DAC Output Error": ["pwm", "dac", "d/a", "d to a", "d-a"],
    },
    "Mechanical / Assembly Faults": {
        "Loose Connection / Cold Solder": ["loose", "cold solder", "dry solder", "loose connection"],
        "Connector Misalignment / Damage": ["connector", "misaligned", "bent", "broken"],
        "Enclosure Damage / Crack": ["enclosure", "case crack", "housing", "cover broken"],
        "Button Not Working / Keypad Fault": ["button", "keypad", "not working", "stuck button"],
        "Improper Cable Crimping / Wire Cut": ["crimp", "wire cut", "open wire", "bad cable"],
        "Mounting / Fitment Issue": ["mounting", "fitment", "loose mount", "bracket"],
    },
    "Environmental / Field Issues": {
        "Overheating": ["overheat", "hot", "thermal", "temperature high"],
        "Moisture / Corrosion Damage": ["moisture", "corrosion", "rust", "wet", "condensation"],
        "Dust / Ingress Issue (IP protection failure)": ["dust", "ingress", "ip", "contamination"],
        "Static / ESD Damage": ["esd", "static", "zap", "electrostatic"],
        "Vibration-Induced Failure": ["vibration", "shock", "mechanical stress"],
    },
    "PCB / Component-Level Faults": {
        "Component Burnt / Damaged": ["component burnt", "burnt", "damaged", "charred"],
        "Track Cut / Pad Lifted": ["track cut", "pad lifted", "trace", "broken track"],
        "Solder Short / Dry Joint": ["solder short", "shorted", "dry joint", "solder bridge"],
        "Wrong Component Assembly": ["wrong component", "wrong part", "misplaced"],
        "Component Tolerance / Drift Issue": ["tolerance", "drift", "variation"],
        "EMI / EMC Related Malfunction": ["emi", "emc", "noise", "interference"],
    },
    "Software / Cloud Integration Issues": {
        "Device Not Visible on Cloud": ["not visible", "no device on cloud", "not showing", "cloud"],
        "Data Not Syncing": ["not syncing", "sync fail", "no sync", "out of sync"],
        "Wrong Timestamp / Location Data": ["wrong timestamp", "wrong time", "wrong location", "gps"],
        "Server Authentication Failure": ["auth fail", "authentication", "token", "401", "forbidden"],
        "API Communication Error": ["api error", "http", "request failed", "timeout"],
        "Firmware-Cloud Compatibility Issue": ["compatibility", "version mismatch", "incompatible"],
    },
    "User / Installation Related Issues": {
        "Wrong Power Supply Used": ["wrong power", "wrong adapter", "wrong supply", "incorrect voltage"],
        "Improper Wiring / Polarity Reversed": ["improper wiring", "wiring", "reverse polarity", "wrong connection"],
        "Configuration Error by User": ["user error", "misconfigured", "wrong setting"],
        "Antenna Not Connected Properly": ["antenna", "not connected", "loose antenna"],
        "SIM Not Inserted / Wrong APN": ["sim not inserted", "no sim", "apn", "wrong apn"],
        "Device Installed in Poor Network Zone": ["poor network", "low signal", "weak signal", "no coverage"],
    },
    "Production / Testing Faults": {
        "Functional Test Failed": ["functional test", "ft fail", "test failed"],
        "Firmware Not Flashed Properly": ["not flashed", "flash fail", "programming failed"],
        "Calibration Not Done / Incorrect": ["calibration not done", "incorrect calibration"],
        "Burn-In Test Failure": ["burn-in", "soak test", "aging fail"],
        "Serial Number Not Programmed": ["serial number", "sn not programmed", "no serial"],
    },
    "Miscellaneous / Others": {
        "Intermittent Fault (Random Reset / Hang)": ["intermittent", "random reset", "random hang", "sporadic"],
        "Field Replacement / RMA": ["rma", "replacement", "returned"],
        "Fault Not Reproducible": ["not reproducible", "cannot reproduce", "rare"],
        "Pending Root Cause Analysis": ["rca", "root cause", "analysis pending"],
    },
}


def get_fault_schema():
    return [
        {
            "name": cat,
            "subcategories": [
                {"name": sub, "keywords": FAULT_CATEGORIES[cat][sub]} for sub in FAULT_CATEGORIES[cat]
            ],
        }
        for cat in FAULT_CATEGORIES
    ]


def get_keywords_for(category: str, subcategory: str):
    if not category or not subcategory:
        return []
    cat = FAULT_CATEGORIES.get(category)
    if not cat:
        return []
    return cat.get(subcategory, [])