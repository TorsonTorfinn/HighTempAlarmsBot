import pandas as pd
import numpy as np

alarm_logs_df = pd.read_excel('AlarmLogs20250821104405991.xlsx', skiprows=5)
rssi_df = pd.read_excel('L_CellSectorEQUIP_UL_RSSI_Avg_Ant_20250820150935-20250820161351.xlsx', 
                   parse_dates=['Date'],
                   na_values=['NIL'],
                   dtype={'L.CellSectorEQUIP.UL.RSSI.Avg.Ant0(dBm)': float, 'L.CellSectorEQUIP.UL.RSSI.Avg.Ant1(dBm)': float,
                          'L.CellSectorEQUIP.UL.RSSI.Avg.Ant2(dBm)': float, 'L.CellSectorEQUIP.UL.RSSI.Avg.Ant3(dBm)': float})

rssi_df = rssi_df.rename(columns={'L.CellSectorEQUIP.UL.RSSI.Avg.Ant0(dBm)': 'Ant0', 'L.CellSectorEQUIP.UL.RSSI.Avg.Ant1(dBm)': 'Ant1',
                                  'L.CellSectorEQUIP.UL.RSSI.Avg.Ant2(dBm)': 'Ant2', 'L.CellSectorEQUIP.UL.RSSI.Avg.Ant3(dBm)': 'Ant3'})


def rssi_proccessing(rssi_df, alarm_logs_df):
    # rssi_df['MAX'] = rssi_df[[
    #     'L.CellSectorEQUIP.UL.RSSI.Avg.Ant0(dBm)',
    #     'L.CellSectorEQUIP.UL.RSSI.Avg.Ant1(dBm)',
    #     'L.CellSectorEQUIP.UL.RSSI.Avg.Ant2(dBm)',
    #     'L.CellSectorEQUIP.UL.RSSI.Avg.Ant3(dBm)']].max(axis=1)
    
    rssi_df['MAX'] = rssi_df[['Ant0', 'Ant1', 'Ant2', 'Ant3']].max(axis=1)
    rssi_df['MEDIAN'] = rssi_df[['Ant0', 'Ant1', 'Ant2', 'Ant3']].median(axis=1)
    rssi_df['MAX_ANT_ID'] = rssi_df[['Ant0', 'Ant1', 'Ant2', 'Ant3']].idxmax(axis=1)
    # rssi_df['MEDIAN'] = rssi_df[[
    #     'L.CellSectorEQUIP.UL.RSSI.Avg.Ant0(dBm)',
    #     'L.CellSectorEQUIP.UL.RSSI.Avg.Ant1(dBm)',
    #     'L.CellSectorEQUIP.UL.RSSI.Avg.Ant2(dBm)',
    #     'L.CellSectorEQUIP.UL.RSSI.Avg.Ant3(dBm)']].median(axis=1)

    # rssi_df['MAX_ANT_ID'] = rssi_df[[
    #     'L.CellSectorEQUIP.UL.RSSI.Avg.Ant0(dBm)',
    #     'L.CellSectorEQUIP.UL.RSSI.Avg.Ant1(dBm)',
    #     'L.CellSectorEQUIP.UL.RSSI.Avg.Ant2(dBm)',
    #     'L.CellSectorEQUIP.UL.RSSI.Avg.Ant3(dBm)']].idxmax(axis=1)

    # rssi_df['MAX_ANT_ID'] = rssi_df['MAX_ANT_ID'].str[-9:-5]
    rssi_df = rssi_df[(rssi_df['MAX'] - rssi_df['MEDIAN'] >= 4) & (~rssi_df['Local cell ID'].isin([21, 22, 23]))]

    # proccess mae Cell Noise Rx alarm logs file
    alarm_logs_df['Local cell ID'] = alarm_logs_df['MO Name'].str.split(',') # split by comma MO Name for cell ID
    alarm_logs_df['Local cell ID'] = [cell[1].split('=')[1] for cell in alarm_logs_df['Local cell ID']] # and comperhensive list for exact val 
    alarm_logs_df['Local cell ID'] = alarm_logs_df['Local cell ID'].astype(int)

    alarm_logs_df = (alarm_logs_df[['Alarm Source', 'CELL Name', 'Local cell ID']])
    alarm_logs_df = alarm_logs_df[~alarm_logs_df['Local cell ID'].isin([21, 22, 23])]
    alarm_logs_df = alarm_logs_df.groupby(['Alarm Source', 'CELL Name', 'Local cell ID']).size().reset_index(name='Count cell ID')
    alarm_logs_df = alarm_logs_df.rename(columns={'Alarm Source': 'eNodeB Name'})

    rssi_df = pd.merge(rssi_df, alarm_logs_df, on=['eNodeB Name', 'Local cell ID'], how='inner')
    return rssi_df



rssi_result = rssi_proccessing(rssi_df, alarm_logs_df)


rssi_result.to_excel('L_Sector_EQUIP.xlsx', index=False)