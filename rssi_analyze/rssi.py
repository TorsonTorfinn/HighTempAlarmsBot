import pandas as pd
import numpy as np



list = ['eNodeB Function Name=SR1008LTE, Local Cell ID=72, Cell Name=SR1008L12, Cell FDD TDD indication=CELL_FDD']
splitted = [item.split(',') for item in list if item.strip()]
print(splitted)
# for item in list:
#     splitted.append(item.split('='))
# print(splitted[2])

exit()

df = pd.read_excel('L_CellSectorEQUIP_UL_RSSI_Avg_Ant_20250820150935-20250820161351.xlsx')

print(df)

def analyze_rssi(row):
    rssi_columns = [
        'L.CellSectorEQUIP.UL.RSSI.Avg.Ant0(dBm)',
        'L.CellSectorEQUIP.UL.RSSI.Avg.Ant1(dBm)',
        'L.CellSectorEQUIP.UL.RSSI.Avg.Ant2(dBm)',
        'L.CellSectorEQUIP.UL.RSSI.Avg.Ant3(dBm)'
    ]
    rssi_values = row[rssi_columns].values
    mean_rssi = np.mean(rssi_values)
    std_rssi = np.std(rssi_values)
    
    # Пороги
    strong_threshold = 2 * std_rssi  # Сильно отличается (> 2 std)
    simple_threshold = 1  # Просто отличается (> 1 dB)
    
    differences = []
    for col, value in zip(rssi_columns, rssi_values):
        ant_name = col.split('.')[-1].split('(')[0]  # Ant0, Ant1 и т.д.
        diff = abs(value - mean_rssi)
        if diff > strong_threshold:
            differences.append(f"{ant_name} сильно отличается ({value:.2f} от среднего {mean_rssi:.2f})")
        elif diff > simple_threshold:
            differences.append(f"{ant_name} отличается ({value:.2f} от среднего {mean_rssi:.2f})")
    
    if differences:
        return f"В eNodeB {row['eNodeB Name']}, Local cell ID {row['Local cell ID']}: " + '; '.join(differences)
    return None


results = df.apply(analyze_rssi, axis=1).dropna()

if not results.empty:
    for result in results:
        print(result)
else:
    print("Нет отличий в данных.")