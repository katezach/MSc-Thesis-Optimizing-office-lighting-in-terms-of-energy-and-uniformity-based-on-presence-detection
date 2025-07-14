from skopt import gp_minimize
from skopt.space import Real
import sys
import os
import time
import logging
cwd = os.getcwd()
sys.path.append(cwd)
import Simulation.control_DLX as control_DLX
import data_processing as dp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.StreamHandler()])

lamp_names, _, _ = dp.get_initial_lamp_configs(540)
efficacy = 124.1
max_lumens = 3600
max_energy_per_lamp = (max_lumens / efficacy) 
total_max_energy = (max_lumens / efficacy) * len(lamp_names)
desk_mapping= [{"Desk1": ["Sensor1"]}, {"Desk2": ["Sensor2"]}, {"Desk3": ["Sensor7"]},
               {"Desk4": ["Sensor8"]}, {"Desk5": ["Sensor9"]}, {"Desk6": ["Sensor10"]}]


def identify_scenario(scenario):
    global initial_lumens, cnt, sensor_activity
    motion, presence, daylight, daylight_compensation = dp.get_sensor_readings(scenario)
    presence = presence.tolist()
    motion = motion.tolist()
    sensor_activity = { f"Sensor{i+1}": (presence[i] or motion[i]) for i in range(len(presence)) }

    cnt = 0
    for sensor, activity in sensor_activity.items():
        if not activity:
            cnt += 1
    if cnt == len(sensor_activity):
        initial_lumens = [0] * len(lamp_names)
    else:
        initial_lumens = [3400] * len(lamp_names)


def objective_function(lumens, iteration, threshold, algorithm_name, scenario):
    global cnt, sensor_activity
    if cnt == len(sensor_activity):
        return 0
    start_time = time.time()

    global lux_per_desk
    if iteration == 1:
        lux_per_desk = [500] * len(desk_mapping)

    motion, presence, daylight, daylight_compensation = dp.get_sensor_readings(scenario)
    presence = presence.tolist()
    motion = motion.tolist()
    sensor_activity = { f"Sensor{i+1}": (presence[i] or motion[i]) for i in range(len(presence)) }
    lamps_mapping = dp.map_lamps_to_sensors(540)
    
    output_file = f"configs_iter_{iteration}.xlsx"
    control_DLX.run_iteration(lamp_names, lumens, len(lamp_names), output_file)
    uniformity, energy, lpd = control_DLX.extract_results(output_file)
    lux_per_desk = lpd
    norm_energy = energy / total_max_energy

    desks_to_check = [0, 1, 6, 7, 8, 9]
    active_desks = 0
    desk_penalty = 0
    uniformity_penalty = 0
    for sensor_idx in desks_to_check:
        desk_index = desks_to_check.index(sensor_idx)
        is_active = presence[sensor_idx] or motion[sensor_idx]
        if is_active:
            active_desks += 1
            if lux_per_desk[desk_index] < 500: 
                desk_penalty += 500 - lux_per_desk[desk_index]
        else:
            if lux_per_desk[desk_index] > 500:  
                desk_penalty += lux_per_desk[desk_index] - 500
    if active_desks > 0 and uniformity < 0.6:  
        uniformity_penalty = (0.6 - uniformity) *100

    total_penalty = uniformity_penalty + desk_penalty
    objective_value = -uniformity + norm_energy + 0.1* total_penalty 

    logging.info(f"Uniformity: {uniformity}, Energy: {energy}, Desk lux: {lpd}")
    logging.info(f"Iteration {iteration}: Objective = {objective_value}")
    logging.info("-----------------------------------------------------------------------------------------------")
    elapsed_time = time.time() - start_time
    if elapsed_time > threshold:
        control_DLX.replace_dialux_file()
    
    dp.create_table_from_iterations(scenario, algorithm_name, iteration, lumens, [lumen / efficacy for lumen in lumens], energy, uniformity, lpd)
    return objective_value


def start_opt(threshold, ws, scenario, **params):
    search_space = [Real(0, 3600, name=f"lumen_{i}") for i in range(len(lamp_names))]

    identify_scenario(scenario)

    algorithm_name = "BO1_"+ str(params.get("n_calls")) +"_"+ str(params.get("n_initial_points"))+"_" + str(params.get("acq_func"))
    iteration_counter = [0]
    def objective(config):
        iteration_counter[0] += 1
        return objective_function(config, iteration_counter[0], threshold, algorithm_name, scenario)

    logging.info("Starting Bayesian Optimization...")
    logging.info("-----------------------------------------------------------------------------------------------")

    result = gp_minimize(
        func=objective,                
        dimensions=search_space,
        # x0=initial_lumens,   
        n_calls=params.get("n_calls", 20),
        n_random_starts=params.get("n_initial_points", 10),  
        acq_func=params.get("acq_func", "EI"),
        random_state=42            
    )

    logging.info("-----------------------------------------------------------------------------------------------")
    logging.info("RESULTS OF BAYESIAN OPTIMIZATION")
    logging.info("-----------------------------------------------------------------------------------------------")

    optimal_lumens = result.x
    optimal_watts = [lumen / efficacy for lumen in optimal_lumens]
    logging.info(f"Optimal Lumens: {optimal_lumens}")
    logging.info(f"Optimal Watts: {optimal_watts}")
    logging.info(f"Optimal Value: {result.fun}")
    if ws :
        path = f"Results/OptimizationResults/Best_per_algorithm/Scenario{scenario}"
    else:
        path = f"Results/OptimizationResults/NoWarmStart/bScenario{scenario}"
    os.makedirs(path, exist_ok=True)

    with open(f"{path}/overall_BO1_{params.get("n_calls")}_{params.get("n_initial_points")}_{params.get("acq_func")}.csv", "w") as f:
        f.write("Lamp,Lumen,Watts\n")
        for lamp, lumen, watt in zip(lamp_names, optimal_lumens, optimal_watts):
            f.write(f"{lamp},{lumen},{watt}\n")
        f.write(f"\nOptimal Value: {result.fun}\n")
    control_DLX.replace_dialux_file()
    return result.fun, optimal_lumens, optimal_watts