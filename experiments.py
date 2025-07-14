import time
import os, sys
cwd = os.getcwd()
sys.path.append(cwd)
import Optimization.bayesian1 as bo1
# import Optimization.bayesian2 as bo2
import Optimization.pso as pso
import Optimization.samocobra.samo_cobra as samo_cobra
import logging
from sklearn.model_selection import ParameterGrid
import data_processing as dp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

THRESHOLD = 220
algorithms = [ "BO with scikit", "PSO", "SAMO-COBRA", "BO with ax"]
print(f"Starting the experiments for algorithms: {algorithms}")

# dp.create_scenarios()
# print("Created the randomized scenarios.")

def cleanup_files(file_prefix="configs_iter_"):
    for filename in os.listdir():
        if filename.startswith(file_prefix) and filename.endswith(".xlsx"):
            os.remove(filename)
    logging.info("Temporary files cleaned up.")


def define_grids():
    grids = {
        "BO with scikit": {
            "n_calls": [30, 50],
            "n_initial_points": [5, 10],
            "acq_func": ["EI","PI"],
        },
        "PSO": {
            "maxiter": [9],
            "swarmsize": [3, 5], 
            "omega": [0.5, 0.7, 0.9]
        },
        "SAMO-COBRA": {
            "max_iterations": [30, 50],
            "initial_points": [5, 10],
        },
        # "BO with ax": {
        #     "num_trials": [30, 50],
        # }
    }
    return grids

filename = "output.csv"
def run_grid_search(algorithm_name, grid, scenario):
    logging.info(f"Starting Grid Search for {algorithm_name}...")
    logging.info("-----------------------------------------------------------------------------------------------")

    best_score = float('inf')
    best_params = None

    param_grid = ParameterGrid(grid)
    path = f"OptimizationResults/Backup/Scenario{scenario}/"
    os.makedirs(path, exist_ok=True)

    for params in param_grid:
        logging.info(f"Testing parameters: {params}")
        if algorithm_name == "BO with scikit":
            start_time = time.time()
            result, optimal_lumens, optimal_watts = bo1.start_opt(THRESHOLD, True, scenario, **params)
            elapsed = time.time() - start_time
            filename = f"{path}bo1_{params['n_calls']}_{params['n_initial_points']}_{params['acq_func']}.xlsx"
            with open(filename, "w") as f:
                f.write(f"Result: {result}")
                f.write(f"Optimal Lumens: {optimal_lumens}")
                f.write(f"Optimal Watts: {optimal_watts}")
                f.write(f"Elapsed Time: {elapsed}")
        elif algorithm_name == "PSO":
            start_time = time.time()
            result, optimal_lumens, optimal_watts  = pso.start_opt(300,scenario, **params)
            elapsed = time.time() - start_time
            filename = f"{path}pso_{params['maxiter']}_{params['swarmsize']}_{params['omega']}.xlsx"
            with open(filename, "w") as f:
                f.write(f"Result: {result}")
                f.write(f"Optimal Lumens: {optimal_lumens}")
                f.write(f"Optimal Watts: {optimal_watts}")
                f.write(f"Elapsed Time: {elapsed}")
        elif algorithm_name == "SAMO-COBRA":
            start_time = time.time()
            result, optimal_lumens, optimal_watts = samo_cobra.start_opt(THRESHOLD, True, scenario, **params)
            elapsed = time.time() - start_time
            filename = f"{path}samocobra_{params['max_iterations']}_{params['initial_points']}.xlsx"
            with open(filename, "w") as f:
                f.write(f"Result: {result}")
                f.write(f"Optimal Lumens: {optimal_lumens}")
                f.write(f"Optimal Watts: {optimal_watts}")
                f.write(f"Elapsed Time: {elapsed}")
        # elif algorithm_name == "BO with ax":
        #     start_time = time.time()
        #     result, optimal_lumens, optimal_watts = bo2.start_opt(THRESHOLD,scenario, **params)
        #     elapsed = time.time() - start_time
        #     filename = f"{path}bo2_{params['num_trials']}.xlsx"
        #     with open(filename, "w") as f:
        #         f.write(f"Result: {result}")
        #         f.write(f"Optimal Lumens: {optimal_lumens}")
        #         f.write(f"Optimal Watts: {optimal_watts}")
        #         f.write(f"Elapsed Time: {elapsed}")
        cleanup_files()
        if algorithm_name == "SAMO-COBRA" or algorithm_name == "BO with ax":
            pass
        elif result < best_score:
            best_score = result
            best_params = params

    logging.info("-----------------------------------------------------------------------------------------------")
    logging.info(f"Best parameters for {algorithm_name}: {best_params}")
    logging.info(f"Best score: {best_score}")
    logging.info("-----------------------------------------------------------------------------------------------")
    cleanup_files()
    return best_params, best_score


grids = define_grids()
for scenario_number in range(1, 12):  
    print(f"----- Scenario {scenario_number} -----")
    scenario_file = f'Input/scenario_{scenario_number}.csv'
    print(f"Loaded {scenario_file} for optimization.")
    results = {}
    for algorithm_name, grid in grids.items():
        best_params, best_score = run_grid_search(algorithm_name, grid, scenario_number)
        results[algorithm_name] = {
            "best_params": best_params,
            "best_score": best_score
        }
    print(f"----- Finished optimization for Scenario {scenario_number} -----\n")


