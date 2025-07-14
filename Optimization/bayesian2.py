import numpy as np
import os
import sys
from ax.service.ax_client import AxClient, ObjectiveProperties
import logging
import time
cwd = os.getcwd()
sys.path.append(cwd)
import Simulation.control_DLX as control_DLX
import data_processing as dp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

efficacy = 124.1
lamp_names, _, _ = dp.get_initial_lamp_configs(540)
param_names = [f"Lamp{i}" for i in range(1, len(lamp_names) + 1)]
max_lumens = 3600
total_max_energy = (max_lumens / efficacy) * len(lamp_names)
desk_mapping = [
    {"Desk1": ["Sensor1"]}, {"Desk2": ["Sensor2"]}, {"Desk3": ["Sensor7"]},
    {"Desk4": ["Sensor8"]}, {"Desk5": ["Sensor9"]}, {"Desk6": ["Sensor10"]}
]



def identify_scenario(scenario):
    global initial_configs, cnt, sensor_activity
    motion, presence, daylight, daylight_compensation = dp.get_sensor_readings(scenario)
    presence = presence.tolist()
    motion = motion.tolist()
    sensor_activity = { f"Sensor{i+1}": (presence[i] or motion[i]) for i in range(len(presence)) }

    cnt = 0
    for sensor, activity in sensor_activity.items():
        if not activity:
            cnt += 1
    if cnt == len(sensor_activity):
        # initial_lumens = [0] * len(lamp_names)
        initial_configs = [{f"Lamp{i}": 0.0 for i in range(1, len(lamp_names) + 1)}] 

    else:
        initial_configs = [{f"Lamp{i}": 3400.0 for i in range(1, len(lamp_names) + 1)}] 




def lighting_evaluation_function(iteration, parameterization, threshold, algorithm_name, scenario):
    start_time = time.time()
    global lux_per_desk
    if iteration == 1:
        lux_per_desk = [500] * len(desk_mapping)

    motion, presence, daylight, daylight_compensation = dp.get_sensor_readings(scenario)
    presence = presence.tolist()
    motion = motion.tolist()
    # sensor_activity = { f"Sensor{i+1}": (presence[i] or motion[i]) for i in range(len(presence)) }
    lamps_mapping = dp.map_lamps_to_sensors(540)
    
    lumens = np.array([parameterization[p] for p in param_names])
    output_file = f"configs_iter_{iteration}.xlsx"
    control_DLX.run_iteration(lamp_names, lumens, len(lamp_names), output_file)
    uniformity, energy, lpd = control_DLX.extract_results(output_file)
    lux_per_desk = lpd

    avg_desk_lux = sum(lpd) / len(lpd)
    norm_energy = energy / total_max_energy
    uniformity_violation = 0

    desks_to_check = [0, 1, 6, 7, 8, 9]
    # for sensor_idx, _ in enumerate(lamps_mapping):
    #     if sensor_idx in desks_to_check:
    #         desk_index = desks_to_check.index(sensor_idx)
    #         if not (presence[sensor_idx] or motion[sensor_idx]):
    #             if lux_per_desk[desk_index] > 500:
    #                 desk_lux_violation += avg_desk_lux - 500
    #         else:
    #             if lux_per_desk[desk_index] < 500:
    #                 desk_lux_violation += 500 - avg_desk_lux
    #             if uniformity < 0.6:
    #                 uniformity_violation += 100* (0.6 - uniformity)


    active_desks = 0
    desk_lux_violation = 0
    uniformity_penalty = 0

    for sensor_idx in desks_to_check:
        desk_index = desks_to_check.index(sensor_idx)
        is_active = presence[sensor_idx] or motion[sensor_idx]
        
        if is_active:
            active_desks += 1
            if lux_per_desk[desk_index] < 500: 
                desk_lux_violation += (500 - lux_per_desk[desk_index]) 
        else:
            if lux_per_desk[desk_index] > 500:  
                desk_lux_violation += (lux_per_desk[desk_index] - 500) 

    if active_desks > 0 and uniformity < 0.6:  
        uniformity_violation = (0.6 - uniformity) * 100

    objective_uniformity = -uniformity
    objective_energy = norm_energy 

    # total_penalty = uniformity_penalty + desk_penalty
    # constraints = np.array([total_penalty])

    logging.info(f"Iteration {iteration}: Uniformity={uniformity:.4f}, Energy={energy:.4f}, Desk Penalty={desk_lux_violation:.4f}, Objective={objective_uniformity:.4f}")
    logging.info("-----------------------------------------------------------------------------------------------")
    elapsed_time = time.time() - start_time
    if elapsed_time > threshold:
        control_DLX.replace_dialux_file()

    dp.create_table_from_iterations(scenario,algorithm_name, iteration, lumens, [lumen / efficacy for lumen in lumens], energy, uniformity, lux_per_desk)

    return {
        "uniformity": (objective_uniformity, 1.0),  
        "energy": (objective_energy, 1.0), 
        "desk_lux_violation": (desk_lux_violation, 0.0), 
        "uniformity_violation": (uniformity_violation, 0.0), 
    }


def start_opt(threshold,scenario, **params):
    ax_client = AxClient(verbose_logging=False)

    identify_scenario(scenario)
    parameters = [
        {"name": p, "type": "range", "bounds": [0.0, float(max_lumens)]} 
        for p in param_names
    ]

    objectives = {
        "uniformity": ObjectiveProperties(minimize=False),  
        "energy": ObjectiveProperties(minimize=True)  
    }

    outcome_constraints = [
        "desk_lux_violation <= 1000", 
        "uniformity_violation <= 50", 
    ]

    ax_client.create_experiment(
        name="lighting_optimization",
        parameters=parameters,
        objectives=objectives,
        outcome_constraints=outcome_constraints,
    )

    algorithm_name = "BO2_"+ str(params.get("num_trials"))

    # initial_configs = [{f"Lamp{i}": 3400.0 for i in range(1, len(lamp_names) + 1)}] 
    for config in initial_configs:
        ax_client.attach_trial(parameters=config)
        evaluation = lighting_evaluation_function(iteration=1, parameterization=config, threshold=threshold, algorithm_name=algorithm_name, scenario=scenario)
        ax_client.complete_trial(trial_index=ax_client.experiment.num_trials - 1, raw_data=evaluation)

    for iteration in range(2, params.get("num_trials", 20)+1):
        parameters, trial_index = ax_client.get_next_trial()
        evaluation = lighting_evaluation_function(iteration, parameters, threshold, algorithm_name, scenario)
        ax_client.complete_trial(trial_index=trial_index, raw_data=evaluation)

    results_df = ax_client.get_trials_data_frame()
    path = f"OptimizationResults/Best_per_algorithm/Scenario{scenario}"
    os.makedirs(path, exist_ok=True)

    results_df.to_csv(f"{path}/overall_BO2_{params.get("num_trials")}.csv", index=False)

    optimal_lumens = [3400.0] * len(lamp_names)
    optimal_watts = [lumen / efficacy for lumen in optimal_lumens]
    pareto_solution = None

    try: 
        pareto_solution = ax_client.get_pareto_optimal_parameters()
        logging.info(f"Pareto-optimal solution: {pareto_solution}")

        first_solution_key = next(iter(pareto_solution))
        best_parameters = pareto_solution[first_solution_key][0]
        
        optimal_lumens = [
            best_parameters.get(f"Lamp{i}", 3400.0) for i in range(1, len(lamp_names) + 1)
        ]
        optimal_watts = [lumen / efficacy for lumen in optimal_lumens]

        logging.info(f"Best Parameters: {best_parameters}")
        logging.info(f"Optimal Lumens: {optimal_lumens}")
        logging.info(f"Optimal Watts: {optimal_watts}")

    except Exception as e:
        logging.error(f"Error retrieving optimal solution details: {e}")
        logging.info("Returning fallback/default configuration.")

    control_DLX.replace_dialux_file()
    return pareto_solution, optimal_lumens, optimal_watts










# from ax.service.ax_client import AxClient, ObjectiveProperties
# import sys
# import os
# import time
# import logging
# cwd = os.getcwd()
# sys.path.append(cwd)
# import Simulation.control_DLX as control_DLX
# import data_processing as dp
# import numpy as np

# logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# efficacy = 124.1
# lamp_names, _, _ = dp.get_initial_lamp_configs(540)
# param_names = [f"Lamp{i}" for i in range(1, len(lamp_names) + 1)]

# max_lumens = 3600
# total_max_energy = (max_lumens / efficacy) * len(lamp_names)


# desk_mapping = [
#     {"Desk1": ["Sensor1"]}, {"Desk2": ["Sensor2"]}, {"Desk3": ["Sensor7"]},
#     {"Desk4": ["Sensor8"]}, {"Desk5": ["Sensor9"]}, {"Desk6": ["Sensor10"]}
# ]

# iteration_counter = 0
# lux_per_desk = [500] * len(desk_mapping)

# def apply_constraints(lumens, presence, motion, lamps_mapping):
#     adjusted_lumens = lumens.copy()
#     for sensor_idx, sensor_map in enumerate(lamps_mapping):
#         if not (presence[sensor_idx] or motion[sensor_idx]):
#             _, lamps = list(sensor_map.items())[0]
#             lamp_indices = [lamp_names.index(lamp_name) for lamp_name in lamps]
#             for lamp_idx in lamp_indices:
#                 adjusted_lumens[lamp_idx] = 0.1 * lumens[lamp_idx]
#     return adjusted_lumens

# def check_desk_lux_constraints(lux_per_desk, desk_mapping, sensor_activity, min_lux=500):
#     """Calculate penalty if desks are under-illuminated when occupied."""
#     total_penalty = 0
#     for desk_entry, desk_lux in zip(desk_mapping, lux_per_desk):
#         desk, sensors = list(desk_entry.items())[0]
#         if any(sensor_activity.get(s, True) for s in sensors):
#             if desk_lux < min_lux:
#                 total_penalty += max(min_lux - desk_lux, 0)
#     return total_penalty / (min_lux * len(desk_mapping))


# def lighting_evaluation_function(parameterization):
#     global iteration_counter, lux_per_desk
#     iteration_counter += 1

#     lumens = np.array([parameterization[p] for p in param_names])

#     motion, presence, daylight, _ = dp.get_sensor_readings(540)
#     presence = presence.tolist()
#     motion = motion.tolist()
#     sensor_activity = {f"Sensor{i+1}": (presence[i] or motion[i]) for i in range(len(presence))}
#     lamps_mapping = dp.map_lamps_to_sensors(540)

#     lumens_adjusted = apply_constraints(lumens, presence, motion, lamps_mapping)

#     output_file = f"configs_iter_{iteration_counter}.xlsx"
#     control_DLX.run_iteration(lamp_names, lumens_adjusted, len(lamp_names), output_file)
#     uniformity, energy, lpd = control_DLX.extract_results(output_file)
#     lux_per_desk = lpd

#     uniformity_penalty = max(0.6 - uniformity, 0)
#     energy_penalty = min(energy / total_max_energy, 1)
#     desk_penalty = check_desk_lux_constraints(lpd, desk_mapping, sensor_activity, min_lux=500)
#     objective_value = (40 * uniformity_penalty + 50 * energy_penalty + 10 * desk_penalty)
#     logging.info(f"Iteration {iteration_counter}: Uniformity={uniformity:.4f}, Energy={energy:.4f}, Desk Penalty={desk_penalty:.4f}, Objective={objective_value:.4f}")
#     return {"lighting_objective": (objective_value, 0.1),"energy": (energy, 0.1)}

# ax_client = AxClient()
# ax_client.create_experiment(
#     name="lighting_optimization",
#     parameters=[
#         {
#             "name": p_name,
#             "type": "range",
#             "bounds": [0.0, 3600.0],
#         }
#         for p_name in param_names
#     ],
#     objectives={"lighting_objective": ObjectiveProperties(minimize=True),"energy": ObjectiveProperties(minimize=True),},
#     objective_thresholds=[{"metric_name": "energy", "bound": total_max_energy, "relative": False},]
# )

# logging.info("Starting Bayesian Optimization with AxClient...")

# start_time = time.time()

# for i in range(100):  
#     parameters, trial_index = ax_client.get_next_trial()
#     evaluation = lighting_evaluation_function(parameters)
#     ax_client.complete_trial(trial_index=trial_index, raw_data=evaluation)

# results_df = ax_client.get_trials_data_frame()
# results_df.to_csv("ax_lighting_optimization_results.csv", index=False)

# best_parameters, _ = ax_client.get_best_parameters()
# optimal_lumens = [best_parameters[f"Lamp{i}"] for i in range(1, len(lamp_names) + 1)]
# optimal_watts = [lumen / efficacy for lumen in optimal_lumens]

# logging.info(f"Best Parameters: {best_parameters}")
# logging.info(f"Optimal Lumens: {optimal_lumens}")
# logging.info(f"Optimal Watts: {optimal_watts}")

# with open("ax_optimization_results_summary.csv", "w") as f:
#     f.write("Lamp,Lumen,Watts\n")
#     for lamp, lumen, watt in zip(lamp_names, optimal_lumens, optimal_watts):
#         f.write(f"{lamp},{lumen},{watt}\n")

# elapsed = time.time() - start_time
# logging.info(f"Optimization completed in {elapsed:.2f} seconds.")
