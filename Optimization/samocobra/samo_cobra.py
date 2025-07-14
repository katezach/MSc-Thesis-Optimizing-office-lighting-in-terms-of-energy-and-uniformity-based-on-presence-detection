import numpy as np
import os
import sys

from .SAMO_COBRA_Init import SAMO_COBRA_Init
from .SAMO_COBRA_PhaseII import SAMO_COBRA_PhaseII
cwd = os.getcwd()
sys.path.append(cwd)
import Simulation.control_DLX as control_DLX
import data_processing as dp
import logging
import time

logging.basicConfig(level=logging.INFO)

lamp_names, _, _ = dp.get_initial_lamp_configs(540)
efficacy = 124.1
max_lumens = 3600
max_energy_per_lamp = max_lumens / efficacy
total_max_energy = max_energy_per_lamp * len(lamp_names)
desk_mapping = [{"Desk1": ["Sensor1"]}, {"Desk2": ["Sensor2"]}, {"Desk3": ["Sensor7"]},
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




def lighting_objective(lumens,iteration, threshold, algorithm_name, scenario):
    global cnt, sensor_activity
    if cnt == len(sensor_activity):
        return 0
    start_time = time.time()

    global lux_per_desk
    if iteration == 1:
        lux_per_desk = np.array([500] * len(desk_mapping))  

    motion, presence, daylight, daylight_compensation = dp.get_sensor_readings(scenario)
    presence = presence.tolist()
    motion = motion.tolist()
    # sensor_activity = {f"Sensor{i+1}": (presence[i] or motion[i]) for i in range(len(presence))}
    # lamps_mapping = dp.map_lamps_to_sensors(540)

    output_file = f"configs_iter_{iteration}.xlsx"
    control_DLX.run_iteration(lamp_names, lumens, len(lamp_names), output_file)
    uniformity, energy, lpd = control_DLX.extract_results(output_file)
    lux_per_desk = lpd

    norm_energy = energy / total_max_energy
    uniformity_penalty = 0
    avg_desk_lux = sum(lux_per_desk) / len(lux_per_desk)

    desks_to_check = [0, 1, 6, 7, 8, 9]
    active_desks = 0
    desk_penalty = 0
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


    objective_uniformity = -uniformity
    objective_energy = norm_energy 

    total_penalty = uniformity_penalty + desk_penalty
    constraints = np.array([total_penalty])
    # constraints = np.array([uniformity_penalty, avg_desk_penalty])

    logging.info(f"Iteration {iteration}: Objective E: {objective_energy}, Objective U: {objective_uniformity}, Constraints: {constraints}")
    logging.info("-----------------------------------------------------------------------------------------------")
    elapsed = time.time() - start_time
    if elapsed > threshold:
        control_DLX.replace_dialux_file()
    
    dp.create_table_from_iterations(scenario, algorithm_name, iteration, lumens, [lumen / efficacy for lumen in lumens], energy, uniformity, lpd)
    return np.array([objective_uniformity, objective_energy]), -1 * constraints 
 


def start_opt(threshold, ws, scenario, **params):
    np.random.seed(42)
    lower_bounds = np.array([0] * len(lamp_names))    
    upper_bounds = np.array([3600] * len(lamp_names)) 

    identify_scenario(scenario)   
    x_start = initial_lumens
    dummy = np.array([1800] * len(lamp_names))  

    algorithm_name = "SAMO-COBRA_" + str(params.get("max_iterations", 30)) +"_"+ str(params.get("initial_points", 5))


    iteration_counter = [0]
    def objective(config):
        iteration_counter[0] += 1
        return lighting_objective(config, iteration_counter[0], threshold, algorithm_name, scenario)

    logging.info("Starting SAMO-COBRA...")
    logging.info("-----------------------------------------------------------------------------------------------")

    cobra = SAMO_COBRA_Init(
        xStart= dummy,
        fn=objective,
        fName='SmartLightingOptimization',
        lower=lower_bounds,
        upper=upper_bounds,
        nConstraints=1,
        ref=np.array([1, 9]),
        feval= params.get("max_iterations", 30),
        initDesPoints= params.get("initial_points", 5),
        cobraSeed=0,
        iterPlot=False
    )

    cobra = SAMO_COBRA_PhaseII(cobra)

    logging.info("-----------------------------------------------------------------------------------------------")
    logging.info("RESULTS OF SAMO-COBRA")
    logging.info("-----------------------------------------------------------------------------------------------")

    pareto_frontier = cobra.get('paretoFrontier')
    feasibility = cobra.get('paretoFrontierFeasible')
    Fres = cobra.get('Fres')
    A = cobra.get('A')
    original_lumens_lower = cobra.get('originalL')  
    original_lumens_upper = cobra.get('originalU') 
    optimal_objectives = pareto_frontier[feasibility[:len(pareto_frontier)]]
    
    if Fres is None or A is None or pareto_frontier is None or feasibility is None:
        raise RuntimeError("COBRA output incomplete!")
    pareto_indices = []
    for pf_solution in pareto_frontier:
        for idx, candidate in enumerate(Fres):
            if np.allclose(candidate, pf_solution):
                pareto_indices.append(idx)
                break

    feasible_pareto_indices = [idx for idx, feas in zip(pareto_indices, feasibility) if feas]
    optimal_configs_normalized = A[feasible_pareto_indices]
    def denormalize(config, lower_bounds, upper_bounds):
        return lower_bounds + (config + 1) * 0.5 * (upper_bounds - lower_bounds)

    optimal_lumens = [
        denormalize(config, original_lumens_lower, original_lumens_upper)
        for config in optimal_configs_normalized
    ]

    for i, lumens in enumerate(optimal_lumens):
        print(f"Configuration {i+1}: {lumens}")

    optimal_watts = [lumen / efficacy for lumen in optimal_lumens]
    logging.info(f"Optimal Lumens: {optimal_lumens}")
    logging.info(f"Optimal Watts: {optimal_watts}")
    logging.info(f"Optimal Value: {optimal_objectives}")

    if ws :
        path = f"Results/OptimizationResults/Best_per_algorithm/Scenario{scenario}"
    else:
        path = f"Results/OptimizationResults/NoWarmStart/sScenario{scenario}"

    os.makedirs(path, exist_ok=True)
    with open(f"{path}/overall_samo_cobra_{params.get("max_iterations")}_{params.get("initial_points")}.csv", "w") as f:
            f.write("Lamp,Lumen,Watts\n")
            for lamp, lumen, watt in zip(lamp_names, optimal_lumens, optimal_watts):
                f.write(f"{lamp},{lumen},{watt}\n")
            f.write(f"\nOptimal Value: {optimal_objectives}\n")
    control_DLX.replace_dialux_file()
    return optimal_objectives, optimal_lumens, optimal_watts


