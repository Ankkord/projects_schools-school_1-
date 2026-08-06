import os
from datetime import datetime
from excel_exporter import export_table

import pandas as pd

eff_name = "Efficiency, g/Watt"

columns_order = {
    False: [
        "time",
        "valid",
        "Throttle 1",
        "Voltage 1",
        "Current 1",
        "Power",
        "Thrust",
        eff_name,
    ],
    True: [
        "time",
        "valid",
        "Throttle 1",
        "Throttle 2",
        "Voltage 1",
        "Current 1",
        "Voltage 2",
        "Current 2",
        "Power 1",
        "Power 2",
        "Power",
        "Thrust",
        eff_name,
        "Power balance",
    ]
}

format_rules = {
        "Throttle 1" : "0",
        "Throttle 2" : "0",
        "Voltage 1" : "0.00",
        "Current 1" : "0.00",
        "Voltage 2": "0.00",
        "Current 2" : "0.00",
        "Power 1" : "0.0",
        "Power 2" : "0.0",
        "Power" : "0.0",
        "Thrust" : "0.0",
        eff_name : "0.00",
        "Power balance" : "0.0%",
    }


def reorder_columns(df, column_list):
    """
    Упорядочивает колонки в DataFrame по заданному списку.

    Параметры:
    - df: pandas DataFrame
    - column_list: список строк с именами колонок

    Возвращает: новый DataFrame с выбранными и упорядоченными колонками
    """
    # Находим общие колонки (в порядке из column_list)
    common_cols = [col for col in column_list if col in df.columns]
    # Возвращаем новый df с этими колонками
    return df[common_cols].copy()  # .copy() чтобы не модифицировать оригинал


def save_result(telemetry_data, name='', dual_mode=False, meta = {}):
    # 1. Создаем уникальное имя папки на основе test_name и текущей даты/времени
    # timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    timestamp = meta.get("datetime", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    folder_name = "results/" + f"{name}_{timestamp}".strip("_")
    os.makedirs(folder_name, exist_ok=True)

    df = pd.DataFrame(telemetry_data)  # convert list to df
    n = len(df['Throttle'].iloc[0])  # split throttle to multiple columns
    new_cols = [f'Throttle {i + 1}' for i in range(n)]
    df[new_cols] = pd.DataFrame(df['Throttle'].tolist(), index=df.index)
    df[new_cols] = df[new_cols] / 10  # перевод из диапазона 1000 к диапазону 100
    df = df.drop("Throttle", axis=1)

    df["Power 1"] = df["Current 1"] * df["Voltage 1"]
    df["Power 2"] = df["Current 2"] * df["Voltage 2"]
    if dual_mode:
        df["Power"] = df["Power 1"] + df["Power 2"]
    else:
        df["Power"] = df["Power 1"]
    df[eff_name] = df.apply(lambda row: row['Thrust'] / row['Power'] if row['Power'] != 0 else 0, axis=1)

    if dual_mode:
        df["Power balance 1"] = df["Power 1"] / df["Power"]
        df["Power balance 2"] = df["Power 2"] / df["Power"]
        df["Power balance"] = (df["Power 1"] - df["Power 2"]) / df["Power"]

    df = reorder_columns(df, columns_order[dual_mode])
    raw_data_file = os.path.join(folder_name, f"test {name}_{timestamp}.xlsx")
    # df.to_excel(raw_data_file, index=False)
    export_table(df, meta, format_rules, raw_data_file)

    report_data = []
    grouped = df.groupby('Throttle 1')
    for throttle_value, group in grouped:
        valid_data = group[group['valid'] == True]

        if not valid_data.empty:
            avg_values = valid_data.mean(numeric_only=True)
            avg_values['Throttle 1'] = throttle_value
            avg_values['Throttle 2'] = throttle_value  # fix it maybe someday somehow...
            report_data.append(avg_values)

    # Создаем DataFrame из отчетных данных
    report_df = pd.DataFrame(report_data)
    report_df = report_df.drop("time", axis=1)
    report_df = report_df.drop("valid", axis=1)
    report_df = reorder_columns(report_df, columns_order[dual_mode])


    # 4. Сохраняем отчет в файл report.xlsx
    report_file = os.path.join(folder_name, f"report {name}_{timestamp}.xlsx")
    export_table(report_df, meta, format_rules, report_file)

    print(f"Результаты сохранены в {folder_name}")
