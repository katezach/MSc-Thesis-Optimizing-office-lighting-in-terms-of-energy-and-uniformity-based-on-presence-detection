import pandas as pd
import numpy as np
import os

# LOAD SIMULATAION DATA
simulated_data = pd.read_csv("Input/simulation_data.csv")

def get_unique_lamp_positions_for_timestamp(dataframe, timestamp):
    """
    For a specific timestamp, gather all unique lamp positions across all sensors
    and sort them numerically by (x, y).
    
    Parameters:
    dataframe (pd.DataFrame): The DataFrame containing lamp position columns for sensors.
    timestamp (int or str): The specific timestamp to filter the data.

    Returns:
    list: A sorted list of unique lamp positions as (x, y) tuples.
    """
    # Filter the DataFrame for the given timestamp
    filtered_df = dataframe[dataframe['timestamp'] == timestamp]
    
    # Gather all relevant lamp position columns
    lamp_position_cols = [col for col in dataframe.columns if col.startswith("nearby_light_") and col.endswith("_pos")]
    
    # Collect all positions into a set to ensure uniqueness
    unique_positions = set()
    for col in lamp_position_cols:
        unique_positions.update(filtered_df[col].dropna())

    # Convert positions to numeric tuples if they are not already
    numeric_positions = set()
    for pos in unique_positions:
        if isinstance(pos, str):
            numeric_positions.add(eval(pos))  # Convert string tuples like '(7, 6)' to (7, 6)
        else:
            numeric_positions.add(pos)
    
    sorted_positions = sorted(numeric_positions, key=lambda pos: (pos[1], pos[0]))

    position_to_name = {pos: f"Lamp{index+1}" for index, pos in enumerate(sorted_positions)}

    return sorted_positions, position_to_name

def update_existing_lamp_names(dataframe, position_to_name):
    lamp_name_cols = [col for col in dataframe.columns if col.startswith("nearby_light_") and col.endswith("_name")]
    for col in lamp_name_cols:
        def replace_lamp_name(existing_name):
            if isinstance(existing_name, str) and "Lamp" in existing_name:
                coords_str = existing_name[existing_name.find("(") + 1 : existing_name.find(")")]
                coords = tuple(map(int, coords_str.split(", ")))
                return position_to_name.get(coords, existing_name)
            return existing_name
        dataframe[col] = dataframe[col].apply(replace_lamp_name)
    return dataframe


# simulated_data = rename_all_nearby_lamps(simulated_data)
sorted, name = get_unique_lamp_positions_for_timestamp(simulated_data, 540)
simulated_data = update_existing_lamp_names(simulated_data, name)

print(simulated_data.head())
new_file = "Output/simulation_data_inoutput.csv"
simulated_data.to_csv(new_file, index=False)

# 1. Calculate energy consumption for each sensor
# LIGHT CONFIGURATION CONSTANT
LIGHT_CONSUMPTION_W = 12.5  # Power consumption in watts per light block

def calculate_energy_by_timestamp(simulated_data):
    """
    Calculate energy consumption per row, avoiding double-counting of lamps within the same timestamp.

    Parameters:
    simulated_data (DataFrame): Input DataFrame with sensor data.

    Returns:
    DataFrame: Updated DataFrame with per-row energy considering unique lamps within each timestamp.
    """
    energy = []
    for timestamp, group in simulated_data.groupby('timestamp'):
        seen_lamps = set() 
        for _, row in group.iterrows():
            row_energy = 0 

            lamps = [
                (row['nearby_light_1_pos'], row['nearby_light_1_lux'], row['nearby_light_1_intensity(%)']),
                (row['nearby_light_2_pos'], row['nearby_light_2_lux'], row['nearby_light_2_intensity(%)']),
            ]

            for lamp_pos,_, intensity in lamps:
                if lamp_pos not in seen_lamps:
                    row_energy += intensity / 100 * LIGHT_CONSUMPTION_W 
                    seen_lamps.add(lamp_pos)

            energy.append(row_energy)

    simulated_data['energy'] = energy
    return simulated_data


# 2. Calculate IUDI (Illumination Uniformity Deviation Index)
def calculate_iudi(simulated_data, u_h=0.6):
    """
    Calculate the Illuminance Uniformity Deviation Index (IUDI) for the dataset grouped by timestamp.

    Parameters:
    simulated_data (DataFrame): Input dataset containing lux values for lights.
    u_h (float): Higher uniformity set point (default: 0.6).

    Returns:
    DataFrame: Updated DataFrame with IUDI values for each timestamp.
    """
    iudi_results = []

    for timestamp, group in simulated_data.groupby('timestamp'):   
        lux_values = []
        for _, row in group.iterrows():
            lux_values.extend([row['nearby_light_1_lux'], row['nearby_light_2_lux']])
        
        lux_values = np.array(lux_values)

        if len(lux_values) == 0 or lux_values.max() == 0:
            iudi_results.append({'timestamp': timestamp, 'iudi': 0})
            continue

        E_av = lux_values.mean()
        E_max = lux_values.max()
        E_min = lux_values.min()
        # print(f"Avg: {E_av}, Max: {E_max}, Min: {E_min}")

        N_av = E_av / E_max
        N_jk = lux_values / E_max
        # print(f"Normalized Avg: {N_av}, Normalized Values: {N_jk}")

        W = len(lux_values)
        ID = np.sum(np.abs(N_av - N_jk)) / (N_av * W)
        # print(f"ID: {ID}")

        U_o = E_min / E_av
        UD = (u_h - U_o) / u_h
        # print(f"UD: {UD}")

        IUDI = ID * UD
        # print(f"IUDI: {IUDI}")
        iudi_results.append({'timestamp': timestamp, 'iudi': IUDI})

    iudi_simulated_data = pd.DataFrame(iudi_results)
    return simulated_data.merge(iudi_simulated_data, on='timestamp', how='left')


simulated_data = calculate_energy_by_timestamp(simulated_data)
simulated_data = calculate_iudi(simulated_data)

if not os.path.exists("Output"):
    os.makedirs("Output")
output_file = "Output/simulation_data_output.csv"
simulated_data.to_csv(output_file, index=False)
print(f"Output saved to {output_file}")
