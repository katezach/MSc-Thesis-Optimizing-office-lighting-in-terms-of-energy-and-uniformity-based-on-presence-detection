from pyswarm import pso
import time
import numpy as np
import sys
import os
import logging
cwd = os.getcwd()
sys.path.append(cwd)
import Simulation.control_DLX as control_DLX
import data_processing as dp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

lamp_names, _, _ = dp.get_initial_lamp_configs(540)
efficacy = 124.1
max_lumens = 3600
max_energy_per_lamp = (max_lumens / efficacy) 
total_max_energy = (max_lumens / efficacy) * len(lamp_names)  
desk_mapping= [{"Desk1": ["Sensor1"]}, {"Desk2": ["Sensor2"]}, {"Desk3": ["Sensor7"]},
               {"Desk4": ["Sensor8"]}, {"Desk5": ["Sensor9"]}, {"Desk6": ["Sensor10"]}]


def objective_function(lumens, iteration, threshold, algorithm_name, scenario):
    global cnt, sensor_activity,lux_per_desk
    if cnt == len(sensor_activity):
        return 0
    start_time = time.time()
    if iteration == 1:
        lux_per_desk = [500] * len(desk_mapping)
        lumens = np.array([3400] * len(lamp_names))

    motion, presence, daylight, daylight_compensation = dp.get_sensor_readings(scenario)
    motion, presence = np.array(motion), np.array(presence) 
    sensor_activity = { f"Sensor{i+1}": (presence[i] or motion[i]) for i in range(len(presence)) }
    # lamps_mapping = dp.map_lamps_to_sensors(540)

    output_file = f"configs_iter_{iteration}.xlsx"
    control_DLX.run_iteration(lamp_names, lumens, len(lamp_names), output_file)
    uniformity, energy, lpd = control_DLX.extract_results(output_file)
    lux_per_desk = lpd 
    lpd = np.array(lpd) 

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

    if active_desks > 0 and uniformity < 0.4:  
        uniformity_penalty = (0.4 - uniformity) *100

    total_penalty = uniformity_penalty + desk_penalty
    objective_value = -uniformity + norm_energy + 0.1*total_penalty

    logging.info(f"Iteration {iteration}: Uniformity={uniformity}, Desk lux: {lpd}, Energy={energy}, Objective={objective_value}")
    logging.info("-----------------------------------------------------------------------------------------------")
    elapsed_time = time.time() - start_time
    if elapsed_time>threshold:
        time.sleep(5)
        control_DLX.replace_dialux_file()
    dp.create_table_from_iterations(scenario,algorithm_name, iteration, lumens, [lumen / efficacy for lumen in lumens],energy, uniformity, lpd)
    return objective_value

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

def start_opt(threshold,scenario, **params):
    num_lamps = 18
    L_min, L_max = 0, 3600  
    lower_bounds = [L_min] * num_lamps
    upper_bounds = [L_max] * num_lamps
    algorithm_name = "PSO_"+str(params.get("swarmsize",3))+"_"+str(params.get("maxiter",10))+"_"+str(params.get("omega",0.5))
    
    identify_scenario(scenario)

    iteration_counter = [0]
    def pso_objective(config):
        iteration_counter[0] += 1
        return objective_function(config, iteration_counter[0],threshold, algorithm_name, scenario)

    logging.info("Starting Particle Swarm Optimization...")
    logging.info("-----------------------------------------------------------------------------------------------")
    best_config, best_value = pso(pso_objective, lower_bounds, upper_bounds, swarmsize=params.get("swarmsize",3), maxiter=params.get("maxiter",10), omega=params.get("omega",0.5))

    logging.info("-----------------------------------------------------------------------------------------------")
    logging.info("RESULTS OF PARTICLE SWARM OPTIMIZATION")
    logging.info("-----------------------------------------------------------------------------------------------")

    logging.info(f"Optimal Configuration (Lumens): {best_config}")
    optimal_watts = [lumen / efficacy for lumen in best_config]
    logging.info(f"Optimal Watts: {optimal_watts}")
    logging.info(f"Optimal Value: {best_value}")

    path = f"OptimizationResults/Best_per_algorithm/Scenario{scenario}"
    os.makedirs(path, exist_ok=True)

    with open(f"{path}/overall_PSO_{params.get("swarmsize")}_{params.get("maxiter")}_{params.get("omega")}.csv", "w") as f:
        f.write("Lamp,Lumen,Watts\n")
        for lamp, lumen, watt in zip(lamp_names, best_config, optimal_watts):
            f.write(f"{lamp},{lumen},{watt}\n")
        f.write(f"\nOptimal Value: {best_value}\n")
    logging.info("Optimization results saved to optimization_results.csv")
    return best_value, best_config, optimal_watts


