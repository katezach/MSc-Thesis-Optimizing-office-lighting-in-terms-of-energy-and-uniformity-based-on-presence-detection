import pandas as pd
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk, messagebox, PhotoImage
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import math
import datetime
import threading
import time
import random
import queue
import os, sys
from matplotlib.dates import DateFormatter
cwd = os.getcwd()
sys.path.append(cwd)
# from Optimization.random_search import random_search, LightingOptimizationProblem

# 0. SETUP VALUES
# Global variables
GRID_SIZE = 45 # Grid cell size in pixels (representing 50x50 cm)
GRID_WIDTH = 20  # Number of cells horizontally
GRID_HEIGHT = 16  # Number of cells vertically
CELL_FUNCTIONS = {}  # Dictionary to store functions assigned to grid cells
FUNCTIONS = ['empty', 'wall', 'window', 'sensor', 'light']
COLORS = {'empty': 'white', 'wall': 'gray', 'window': 'yellow', 'sensor': 'blue', 'light': 'orange'}
SENSOR_POSITIONS = []  # List to store positions of sensors
WINDOW_POSITIONS = []  # List to store positions of windows
WALL_POSITIONS = []    # List to store positions of walls
LIGHT_POSITIONS = []   # List to store positions of lights
FIXTURE_GROUPS = {}    # Dictionary mapping sensors to their controlled fixtures

# Sensor IDs
SENSOR_IDS = {}  # Map sensor positions to IDs
SENSOR_ID_COUNTER = 1  # Counter for assigning sensor IDs

# Simulation parameters
DESIRED_LIGHT_LEVEL = 500  # Desired office lux level
SIMULATION_DURATION = 1440  # Total simulation time in minutes (24 hours)
TIME_STEP = 1  # Time step in minutes; set to 1 for per-minute simulation
LATITUDE = 52  # Latitude for solar calculations (default value)
SUN_AZIMUTH_NOON = 260  # Default sun azimuth at noon (degrees)
NORTH_DIRECTION = 0  # North direction in the floor plan (0 degrees is up)
OCCUPANCY_STATE = False  # Global occupancy state
WEATHER_CONDITIONS = {}  # Dictionary to hold weather conditions per hour
TARGET_LIGHT_LEVELS = {} # Dictionary to hold target light levels per hour
OFFICE_HOURS_START = 7   # Office hours start time (hour, 24-hour format)
OFFICE_HOURS_END = 19    # Office hours end time (hour, 24-hour format)
user_start_time = 0
user_end_time = SIMULATION_DURATION 

# Weather effects adjusted for real-world measurements
WEATHER_EFFECTS = {'Clear': 5.0, 'Cloudy': 2.0, 'Rainy': 0.2}  # Adjusted factors

# LIGHT CONFIGURATIONS
BEAM_ANGLE = 40
MAX_LUMENS = 400
HEIGHT_ABOVE_DESK = 2
LIGHT_LUX_OUTPUTS = {} # Dictionary to store light LUX outputs per light block
LIGHT_LUMEN_OUTPUTS = {} # Dictionary to store light LUMEN outputs per light block
LIGHT_CONSUMPTION_W = 12.5  # Power consumption in watts per light block
LIGHT_LUM_PER_WATT = 115.7

# Initialize simulation conditions
for hour in range(24):
    random_weather = random.choice(['Clear', 'Cloudy', 'Rainy'])
    WEATHER_CONDITIONS[hour] = random_weather
    TARGET_LIGHT_LEVELS[hour] = DESIRED_LIGHT_LEVEL

# Playback control variables
is_playing = False
playback_speed = 1  # Normal speed
current_playback_time = 0

# Motion detection probabilities
BASE_MOTION_PROBABILITY = 0.01  # Increased base probability per minute
MOTION_TRIGGER_MULTIPLIER = 50  # Adjusted multiplier for realistic triggers

# GUI Elements
root = tk.Tk()
canvas = None
progress_bar = None
data_label = None
canvas_width = GRID_WIDTH * GRID_SIZE
canvas_height = GRID_HEIGHT * GRID_SIZE
sensor_status_labels = {}  # Labels to show sensor status
light_status_labels = {}  # Labels to show light status
north_arrow = None  # Canvas item for the north arrow
arrow_angle = 0  # Current angle of the north arrow
rotation_start_x = 0
rotation_start_y = 0
control_frame = None  # Make control_frame global

# Error Handling
error_queue = queue.Queue()

def environment_setup():
    print("Environment setup complete.")

# 1. CSV Generation at Start
def create_empty_csv():
    if not os.path.exists("Input"):
        os.makedirs("Input")
    columns = ["device", "sensor_pos", "timestamp", "time", "motiondetection", "presencedetection",
               "daylightdetection", "daylightcompensation", "human_obs_daylight", "infrared_daylight", "total_lux", "diff_from_ideal","nearby_light_1_name","nearby_light_1_pos", "nearby_light_1_lux", "nearby_light_1_lumen", "nearby_light_1_intensity(%)", "nearby_light_2_name", "nearby_light_2_pos", "nearby_light_2_lux", "nearby_light_2_lumen",  "nearby_light_2_intensity(%)","nearby_light_3_name","nearby_light_3_pos", "nearby_light_3_lux", "nearby_light_3_lumen", "nearby_light_3_intensity(%)","nearby_light_4_name","nearby_light_4_pos", "nearby_light_4_lux", "nearby_light_4_lumen", "nearby_light_4_intensity(%)"]

    df = pd.DataFrame(columns=columns)
    df.to_csv("Input/simulation_data.csv", index=False) 
    print("Empty CSV file created.")

# 2. User Interface
# def load_floorplan():
#     file_path = filedialog.askopenfilename()
#     if file_path:
#         try:
#             floorplan_image = tk.PhotoImage(file=file_path)
#             canvas.create_image(0, 0, anchor='nw', image=floorplan_image)
#             canvas.image = floorplan_image  # Keep a reference to prevent garbage collection
#             print("Floorplan loaded from:", file_path)
#         except Exception as e:
#             log_error(f"Failed to load floorplan: {e}")

def save_simulation():
    file_path = filedialog.asksaveasfilename(defaultextension=".sim", filetypes=[("Simulation Files", "*.sim")])
    if file_path:
        try:
            simulation_data = {
                "CELL_FUNCTIONS": CELL_FUNCTIONS,
                "SENSOR_POSITIONS": SENSOR_POSITIONS,
                "WINDOW_POSITIONS": WINDOW_POSITIONS,
                "WALL_POSITIONS": WALL_POSITIONS,
                "LIGHT_POSITIONS": LIGHT_POSITIONS,
                "FIXTURE_GROUPS": FIXTURE_GROUPS,
                "NORTH_DIRECTION": NORTH_DIRECTION,
                "LATITUDE": LATITUDE,
                "SUN_AZIMUTH_NOON": SUN_AZIMUTH_NOON,
                "WEATHER_CONDITIONS": WEATHER_CONDITIONS,
                "DESIRED_LIGHT_LEVEL": DESIRED_LIGHT_LEVEL,
                "TARGET_LIGHT_LEVELS": TARGET_LIGHT_LEVELS,
                "OFFICE_HOURS_START": OFFICE_HOURS_START,
                "OFFICE_HOURS_END": OFFICE_HOURS_END,
                "MOTION_TRIGGER_MULTIPLIER": MOTION_TRIGGER_MULTIPLIER,
                "SENSOR_IDS": SENSOR_IDS,
                "SENSOR_ID_COUNTER": SENSOR_ID_COUNTER
            }
            print(simulation_data)
            pd.to_pickle(simulation_data, file_path)
            print(f"Simulation saved to {file_path}")
        except Exception as e:
            log_error(f"Failed to save simulation: {e}")

first_call = True
def load_simulation():
    global first_call  

    if first_call:
        file_path = 'Simulation/my_sim.sim'  
        first_call = False 
        print("Loading default simulation file...")
    else:
        file_path = filedialog.askopenfilename(filetypes=[("Simulation Files", "*.sim")])
        if not file_path:  
            return
        print("Loading the simulation file...")

    if file_path:
        try:
            simulation_data = pd.read_pickle(file_path)
            global CELL_FUNCTIONS, SENSOR_POSITIONS, WINDOW_POSITIONS, WALL_POSITIONS, LIGHT_POSITIONS, FIXTURE_GROUPS
            global NORTH_DIRECTION, LATITUDE, SUN_AZIMUTH_NOON, WEATHER_CONDITIONS, DESIRED_LIGHT_LEVEL
            global TARGET_LIGHT_LEVELS, OFFICE_HOURS_START, OFFICE_HOURS_END, MOTION_TRIGGER_MULTIPLIER
            global SENSOR_IDS, SENSOR_ID_COUNTER
            CELL_FUNCTIONS = simulation_data["CELL_FUNCTIONS"]
            SENSOR_POSITIONS = simulation_data["SENSOR_POSITIONS"]
            WINDOW_POSITIONS = simulation_data["WINDOW_POSITIONS"]
            WALL_POSITIONS = simulation_data["WALL_POSITIONS"]
            # LIGHT_POSITIONS = simulation_data.get("LIGHT_POSITIONS", [])
            LIGHT_POSITIONS = simulation_data["LIGHT_POSITIONS"]
            FIXTURE_GROUPS = simulation_data.get("FIXTURE_GROUPS", {})
            NORTH_DIRECTION = simulation_data.get("NORTH_DIRECTION", 0)
            LATITUDE = simulation_data.get("LATITUDE", 52)
            SUN_AZIMUTH_NOON = simulation_data.get("SUN_AZIMUTH_NOON", 180)
            WEATHER_CONDITIONS = simulation_data.get("WEATHER_CONDITIONS", WEATHER_CONDITIONS)
            DESIRED_LIGHT_LEVEL = simulation_data.get("DESIRED_LIGHT_LEVEL", 500)
            TARGET_LIGHT_LEVELS = simulation_data.get("TARGET_LIGHT_LEVELS", TARGET_LIGHT_LEVELS)
            OFFICE_HOURS_START = simulation_data.get("OFFICE_HOURS_START", 9)
            OFFICE_HOURS_END = simulation_data.get("OFFICE_HOURS_END", 17)
            MOTION_TRIGGER_MULTIPLIER = simulation_data.get("MOTION_TRIGGER_MULTIPLIER", 50)
            SENSOR_IDS = simulation_data.get("SENSOR_IDS", {})
            SENSOR_ID_COUNTER = simulation_data.get("SENSOR_ID_COUNTER", 1)
            redraw_floorplan()
            populate_conditions_table()
            populate_simulation_settings_table()
            print(f"Simulation loaded from {file_path}")

            # Serialize and save data to CSV
            config_items = []
            for key, value in simulation_data.items():
                if isinstance(value, (dict, list, set, tuple)): 
                    value = str(value)
                config_items.append((key, value))
            df = pd.DataFrame(config_items, columns=['Configuration', 'Value'])
            df.to_csv('Simulation/simulation_configs.csv', index=False)
            print("Configuration data saved to CSV.")
        except Exception as e:
            log_error(f"Failed to load simulation: {e}")

def redraw_floorplan():
    canvas.delete("all")
    draw_grid()
    for (col, row), function in CELL_FUNCTIONS.items():
        update_cell_function(col, row, function)
    draw_legend()

# The command that inputs a new block (wall, window, sensor, light) into the grid - Locations are stored in x_POSITIONS
def place_marker(event):
    global SENSOR_ID_COUNTER
    # Determine the grid cell clicked
    col = event.x // GRID_SIZE
    row = event.y // GRID_SIZE
    if col >= GRID_WIDTH or row >= GRID_HEIGHT:
        return  # Clicked outside the grid area
    cell_key = (col, row)

    # Cycle through functions on each click
    current_function = CELL_FUNCTIONS.get(cell_key, 'empty')
    next_function = FUNCTIONS[(FUNCTIONS.index(current_function) + 1) % len(FUNCTIONS)]
    CELL_FUNCTIONS[cell_key] = next_function
    update_cell_function(col, row, next_function)

    # Update positions lists
    if next_function == 'sensor':
        if cell_key not in SENSOR_POSITIONS:
            SENSOR_POSITIONS.append(cell_key)
            # assign_fixtures_to_sensor(cell_key)
            # Assign a new sensor ID
            SENSOR_IDS[cell_key] = SENSOR_ID_COUNTER
            SENSOR_ID_COUNTER += 1
    else:
        if cell_key in SENSOR_POSITIONS:
            SENSOR_POSITIONS.remove(cell_key)
            FIXTURE_GROUPS.pop(cell_key, None)
            # Remove sensor status label
            if cell_key in sensor_status_labels:
                canvas.delete(sensor_status_labels[cell_key])
                del sensor_status_labels[cell_key]
        if cell_key in SENSOR_IDS:
            del SENSOR_IDS[cell_key]

    if next_function == 'window':
        if cell_key not in WINDOW_POSITIONS:
            WINDOW_POSITIONS.append(cell_key)
    else:
        if cell_key in WINDOW_POSITIONS:
            WINDOW_POSITIONS.remove(cell_key)

    if next_function == 'wall':
        if cell_key not in WALL_POSITIONS:
            WALL_POSITIONS.append(cell_key)
    else:
        if cell_key in WALL_POSITIONS:
            WALL_POSITIONS.remove(cell_key)

    if next_function == 'light':
        if cell_key not in LIGHT_POSITIONS:
            LIGHT_POSITIONS.append(cell_key)
    else:
        if cell_key in LIGHT_POSITIONS:
            LIGHT_POSITIONS.remove(cell_key)

# NEEDS TO BE UPDATED TO INCLUDE LIGHTS - currently not used
def assign_fixtures_to_sensor(sensor_pos):
    # Assign adjacent light cells as fixtures controlled by the sensor
    fixtures = []
    directions = [(-1,0), (1,0), (0,-1), (0,1)]  # Up, down, left, right
    for dx, dy in directions:
        adjacent_pos = (sensor_pos[0] + dx, sensor_pos[1] + dy)
        if 0 <= adjacent_pos[0] < GRID_WIDTH and 0 <= adjacent_pos[1] < GRID_HEIGHT:
            if CELL_FUNCTIONS.get(adjacent_pos) == 'light':
                fixtures.append(adjacent_pos)
    FIXTURE_GROUPS[sensor_pos] = fixtures

def update_cell_function(col, row, function):
    x1 = col * GRID_SIZE
    y1 = row * GRID_SIZE
    x2 = x1 + GRID_SIZE
    y2 = y1 + GRID_SIZE
    color = COLORS.get(function, 'white')
    canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='black')
    if function != 'empty':
        canvas.create_text(x1 + GRID_SIZE/2, y1 + GRID_SIZE/2, text=function[0].upper(), font=('Arial', 12, 'bold'))
    else:
        # Clear text if function is 'empty'
        canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='black')

def draw_legend():
    # Clear previous legend
    for widget in legend_frame.winfo_children():
        widget.destroy()
    # Create new legend
    legend_label = tk.Label(legend_frame, text="Legend", font=('Arial', 14, 'bold'))
    legend_label.pack(pady=5)
    legend_items = [('Sensor', 'blue'), ('Window', 'yellow'), ('Wall', 'gray'), ('Light', 'orange'), ('Empty', 'white')]
    for idx, (name, color) in enumerate(legend_items):
        frame = tk.Frame(legend_frame)
        frame.pack(anchor='w', padx=5)
        canvas_legend = tk.Canvas(frame, width=20, height=20)
        canvas_legend.create_rectangle(0, 0, 20, 20, fill=color, outline='black')
        canvas_legend.pack(side='left')
        label = tk.Label(frame, text=name, font=('Arial', 12))
        label.pack(side='left')

def set_sun_azimuth():
    global SUN_AZIMUTH_NOON
    info_text = "Enter the sun's azimuth at noon (degrees).\nYou can find the solar azimuth for your location at suncalc.org."
    sun_azimuth_input = simpledialog.askfloat("Sun Azimuth at Noon", info_text, minvalue=0, maxvalue=360)
    if sun_azimuth_input is not None:
        SUN_AZIMUTH_NOON = sun_azimuth_input
        print(f"Sun azimuth at noon set to {SUN_AZIMUTH_NOON} degrees.")

def set_latitude():
    global LATITUDE
    latitude_input = simpledialog.askfloat("Set Latitude", "Enter the latitude of the location (degrees):", minvalue=-90, maxvalue=90)
    if latitude_input is not None:
        LATITUDE = latitude_input
        print(f"Latitude set to {LATITUDE} degrees.")

def set_target_light_level():
    global DESIRED_LIGHT_LEVEL
    light_level_input = simpledialog.askfloat("Set Default Target Light Level", "Enter the desired light level (lux):", minvalue=0)
    if light_level_input is not None:
        DESIRED_LIGHT_LEVEL = light_level_input
        # Update TARGET_LIGHT_LEVELS
        for hour in range(24):
            TARGET_LIGHT_LEVELS[hour] = DESIRED_LIGHT_LEVEL
        populate_conditions_table()
        populate_simulation_settings_table()
        print(f"Desired light level set to {DESIRED_LIGHT_LEVEL} lux.")

# Might be unnecessary for now
# NORTH ARROW -----------------
def draw_north_arrow():
    global north_arrow
    # Remove previous arrow
    north_canvas.delete("all")
    x_center = 50
    y_center = 50
    length = 40
    angle_rad = math.radians(NORTH_DIRECTION)
    x_end = x_center + length * math.sin(angle_rad)
    y_end = y_center - length * math.cos(angle_rad)
    # Draw new arrow
    north_arrow = north_canvas.create_line(
        x_center, y_center, x_end, y_end, arrow=tk.LAST, fill='red', width=3, tags="north_arrow"
    )
    # Draw 'N' label
    north_canvas.create_text(x_center, y_center + 10, text='N', font=('Arial', 12, 'bold'), fill='red')
    # Bind events
    north_canvas.tag_bind("north_arrow", "<ButtonPress-1>", start_rotating_arrow)
    north_canvas.tag_bind("north_arrow", "<B1-Motion>", rotate_arrow)
    north_canvas.tag_bind("north_arrow", "<ButtonRelease-1>", stop_rotating_arrow)

def start_rotating_arrow(event):
    north_canvas.bind("<Motion>", rotate_arrow)
    north_canvas.bind("<ButtonRelease-1>", stop_rotating_arrow)

def rotate_arrow(event):
    global NORTH_DIRECTION
    try:
        x_center = 50
        y_center = 50
        dx = event.x - x_center
        dy = event.y - y_center
        angle = (math.degrees(math.atan2(dy, dx)) + 360) % 360  # Corrected angle calculation
        NORTH_DIRECTION = angle
        draw_north_arrow()
    except Exception as e:
        log_error(f"Error rotating north arrow: {e}")

def stop_rotating_arrow(event):
    north_canvas.unbind("<Motion>")
    north_canvas.unbind("<ButtonRelease-1>")
    print(f"North direction set to {NORTH_DIRECTION:.2f} degrees.")
# ----------------- NORTH ARROW

# Conditions Table Functions (Weather Conditions, Target Light Levels)
def create_conditions_table():
    global conditions_table
    conditions_frame = tk.Frame(side_frame)
    conditions_frame.pack(fill='both', expand=True)

    cols = ('Hour', 'Weather Condition', 'Target Light Level (lux)')
    conditions_table = ttk.Treeview(conditions_frame, columns=cols, show='headings', height=24)
    for col in cols:
        conditions_table.heading(col, text=col)
        conditions_table.column(col, anchor='center', width=120)
    conditions_table.pack(fill='both', expand=True)
    conditions_table.bind("<Double-1>", initiate_edit)
    populate_conditions_table()

def populate_conditions_table():
    for item in conditions_table.get_children():
        conditions_table.delete(item)
    for hour in range(24):
        weather = WEATHER_CONDITIONS.get(hour, 'Clear')
        target_light = TARGET_LIGHT_LEVELS.get(hour, DESIRED_LIGHT_LEVEL)
        conditions_table.insert('', 'end', values=(
            hour,
            weather,
            target_light
        ))

# Edit conditions table in the simulation settings
def initiate_edit(event):
    selected_item = conditions_table.focus()
    if not selected_item:
        return
    column = conditions_table.identify_column(event.x)
    row = conditions_table.identify_row(event.y)
    if not column or not row:
        return
    col_num = int(column.replace('#', '')) - 1
    if col_num == 0:
        return  # Hour column is not editable
    x, y, width, height = conditions_table.bbox(selected_item, column)
    value = conditions_table.set(selected_item, column)
    
    edit_popup = tk.Entry(conditions_table)
    edit_popup.insert(0, value)
    edit_popup.place(x=x, y=y, width=width, height=height)
    edit_popup.focus_set()
    
    def save_edit(event):
        new_value = edit_popup.get()
        edit_popup.destroy()
        column_name = conditions_table['columns'][col_num]
        hour = int(conditions_table.set(selected_item, '#1'))
        
        if column_name == 'Weather Condition':
            if new_value not in ['Clear', 'Cloudy', 'Rainy']:
                messagebox.showerror("Invalid Input", "Weather Condition must be one of: Clear, Cloudy, Rainy.")
                return
            WEATHER_CONDITIONS[hour] = new_value
        elif column_name == 'Target Light Level (lux)':
            try:
                new_light = float(new_value)
                TARGET_LIGHT_LEVELS[hour] = new_light
            except ValueError:
                messagebox.showerror("Invalid Input", "Target Light Level must be a number.")
                return
        # Update table
        populate_conditions_table()
        populate_simulation_settings_table()
        print(f"Conditions updated for hour {hour}.")
    
    edit_popup.bind("<Return>", save_edit)
    edit_popup.bind("<FocusOut>", lambda e: edit_popup.destroy())

# Simulation Settings Table Functions
def create_simulation_settings_table(parent_frame):
    global simulation_settings_table
    settings_frame = tk.Frame(parent_frame)
    settings_frame.pack(fill='both', expand=True, pady=10)

    cols = ('Setting', 'Value')
    simulation_settings_table = ttk.Treeview(settings_frame, columns=cols, show='headings', height=5)
    for col in cols:
        simulation_settings_table.heading(col, text=col)
        simulation_settings_table.column(col, anchor='center', width=130)
    simulation_settings_table.pack(fill='both', expand=True)
    simulation_settings_table.bind("<Double-1>", initiate_settings_edit)
    populate_simulation_settings_table()

def populate_simulation_settings_table():
    for item in simulation_settings_table.get_children():
        simulation_settings_table.delete(item)
    settings = {
        'Motion Trigger Multiplier': MOTION_TRIGGER_MULTIPLIER,
        'Office Hours Start (hour)': OFFICE_HOURS_START,
        'Office Hours End (hour)': OFFICE_HOURS_END
    }
    for setting, value in settings.items():
        simulation_settings_table.insert('', 'end', values=(setting, value))

# Edit simulation settings in the settings table
def initiate_settings_edit(event):
    selected_item = simulation_settings_table.focus()
    if not selected_item:
        return
    column = simulation_settings_table.identify_column(event.x)
    row = simulation_settings_table.identify_row(event.y)
    if not column or not row:
        return
    col_num = int(column.replace('#', '')) - 1
    if col_num == 0:
        return  # Setting name column is not editable
    x, y, width, height = simulation_settings_table.bbox(selected_item, column)
    value = simulation_settings_table.set(selected_item, column)
    
    edit_popup = tk.Entry(simulation_settings_table)
    edit_popup.insert(0, value)
    edit_popup.place(x=x, y=y, width=width, height=height)
    edit_popup.focus_set()
    
    def save_settings_edit(event):
        new_value = edit_popup.get()
        edit_popup.destroy()
        setting_name = simulation_settings_table.set(selected_item, '#1')
        
        if setting_name == 'Motion Trigger Multiplier':
            try:
                new_multiplier = int(new_value)
                if new_multiplier < 1 or new_multiplier > 1000:
                    raise ValueError
                global MOTION_TRIGGER_MULTIPLIER
                MOTION_TRIGGER_MULTIPLIER = new_multiplier
                print(f"MOTION_TRIGGER_MULTIPLIER set to {MOTION_TRIGGER_MULTIPLIER}x.")
            except ValueError:
                messagebox.showerror("Invalid Input", "Motion Trigger Multiplier must be an integer between 1 and 1000.")
                return
        elif setting_name == 'Office Hours Start (hour)':
            try:
                new_start_hour = int(new_value)
                if new_start_hour < 0 or new_start_hour > 23:
                    raise ValueError
                global OFFICE_HOURS_START
                OFFICE_HOURS_START = new_start_hour
                print(f"OFFICE_HOURS_START set to {OFFICE_HOURS_START}:00.")
            except ValueError:
                messagebox.showerror("Invalid Input", "Office Hours Start must be an integer between 0 and 23.")
                return
        elif setting_name == 'Office Hours End (hour)':
            try:
                new_end_hour = int(new_value)
                if new_end_hour < 0 or new_end_hour > 23:
                    raise ValueError
                global OFFICE_HOURS_END
                OFFICE_HOURS_END = new_end_hour
                print(f"OFFICE_HOURS_END set to {OFFICE_HOURS_END}:00.")
            except ValueError:
                messagebox.showerror("Invalid Input", "Office Hours End must be an integer between 0 and 23.")
                return
        # Update the settings table
        populate_simulation_settings_table()
    
    edit_popup.bind("<Return>", save_settings_edit)
    edit_popup.bind("<FocusOut>", lambda e: edit_popup.destroy())

# Simulation Logic

# Probably needs more data to be sent
def get_simulation_config_for_optimization():
    """
    Extracts the relevant configuration from the simulation without running the entire simulation.
    Returns a dictionary containing the configurations like light positions, occupancy, etc.
    """
    config = {
        "SENSOR_POSITIONS": SENSOR_POSITIONS,  # Positions of sensors in the grid
        "OCCUPANCY_STATE": [random.choice([0, 1]) for _ in range(len(SENSOR_POSITIONS))],  # Random occupancy data
        "Lmax": 1000,  # Maximum light level in lux
        "N": len(SENSOR_POSITIONS),  # Number of sensors
    }
    return config

def update_simulation_config(config):
    """
    Updates the simulation configuration based on the optimization results.
    """
    # Update light lux, lumens and intensities
    # for i, sensor_pos in enumerate(SENSOR_POSITIONS):
    #     artificial_light_levels[sensor_pos] = config["L"][i]
    #     light_lux_outputs[sensor_pos] = config["L"][i]
    #     light_lumen_outputs[sensor_pos] = config["L"][i] * (BEAM_ANGLE / 360) * (2 * math.pi * HEIGHT_ABOVE_DESK)
    

def simulate_sensor_data(timestamp):
    global OCCUPANCY_STATE
    try:
        # Set occupancy state directly based on office hours
        OCCUPANCY_STATE = is_within_office_hours(timestamp)

        # Determine motion detection per sensor
        motion_detections = {sensor_pos: simulate_motion(sensor_pos, timestamp) for sensor_pos in SENSOR_POSITIONS}

        # Calculate daylight levels per sensor
        daylight_levels = calculate_daylight_levels(timestamp)

        # Adjust artificial light levels to meet target lux levels
        artificial_light_levels, light_lux_outputs, light_lumen_outputs, nearby_lights, total_lux, diff_from_ideal = control_lighting(daylight_levels, timestamp)

        # Log data
        log_data(timestamp, motion_detections, OCCUPANCY_STATE, daylight_levels, artificial_light_levels, nearby_lights, total_lux, diff_from_ideal)

        # Update progress bar and data label
        progress = (timestamp / user_end_time) * 100
        progress_bar['value'] = progress
        data_label.config(text=f"Simulating... Time: {format_timestamp(timestamp)}")
        root.update_idletasks()

        # Update sensor status labels
        update_sensor_status_labels(motion_detections, daylight_levels, artificial_light_levels)
        update_light_status_labels(light_lux_outputs)

    except Exception as e:
        log_error(f"Error during simulation at timestamp {timestamp}: {e}")
        stop_simulation_thread()

# def is_within_office_hours(timestamp):
#     # Convert timestamp to hour
#     hour = (timestamp % 1440) // 60
#     if OFFICE_HOURS_START <= OFFICE_HOURS_END:
#         within_hours= OFFICE_HOURS_START <= hour < OFFICE_HOURS_END
#     else:
#         # Handles overnight office hours (e.g., 22 to 6)
#         within_hours=  hour >= OFFICE_HOURS_START or hour < OFFICE_HOURS_END
    
#     if within_hours:
#         # Higher probability of occupancy during office hours
#         return random.random() < 0.8  # 80% chance of occupancy
#     else:
#         # Lower probability of occupancy outside office hours
#         return random.random() < 0.2  # 20% chance of occupancy


import numpy as np
occupancy_schedule = {}

def generate_daily_occupancy_schedule():
    global occupancy_schedule
    occupancy_schedule.clear()
    
    current_minute = OFFICE_HOURS_START * 60
    end_minute = OFFICE_HOURS_END * 60

    while current_minute < end_minute:
        occupied_duration = np.random.randint(30, 120)  # occupancy session 30-120 min
        empty_duration = np.random.randint(15, 60)     # break duration 15-60 min

        # Set occupied period
        for minute in range(current_minute, min(current_minute + occupied_duration, end_minute)):
            occupancy_schedule[minute] = True

        current_minute += occupied_duration

        # Set unoccupied period
        for minute in range(current_minute, min(current_minute + empty_duration, end_minute)):
            occupancy_schedule[minute] = False

        current_minute += empty_duration

    # Outside office hours, occupancy probability is much lower
    for minute in range(0, OFFICE_HOURS_START * 60):
        occupancy_schedule[minute] = random.random() < 0.05  # 5% chance outside office hours
    for minute in range(OFFICE_HOURS_END * 60, 1440):
        occupancy_schedule[minute] = random.random() < 0.05  # 5% chance outside office hours



def is_within_office_hours(timestamp):
    minute_of_day = timestamp % 1440
    return occupancy_schedule.get(minute_of_day, False)


def update_sensor_status_labels(motion_detections, daylight_levels, artificial_light_levels):
    for sensor_pos in SENSOR_POSITIONS:
        sensor_id = SENSOR_IDS.get(sensor_pos)
        if sensor_id is None:
            continue
        sensor_name = f"Sensor_{sensor_id}"
        motion = 'Yes' if motion_detections[sensor_pos] else 'No'
        daylight_lux = round(daylight_levels[sensor_pos], 1)
        artificial_lux = round(artificial_light_levels[sensor_pos], 1)
        status_text = f"{sensor_name}\nMotion: {motion}\nDaylight Lux: {daylight_lux}\nArtificial Lux: {artificial_lux}"
        x = sensor_pos[0] * GRID_SIZE + GRID_SIZE / 2
        y = sensor_pos[1] * GRID_SIZE - 10  # Position above the sensor
        if sensor_pos not in sensor_status_labels:
            label = canvas.create_text(x, y, text=status_text, fill="red", font=('Arial', 8, 'bold'), anchor='s')
            sensor_status_labels[sensor_pos] = label
        else:
            label_id = sensor_status_labels[sensor_pos]
            canvas.itemconfig(label_id, text=status_text)

def update_light_status_labels(artificial_light_levels):
    for light_pos in LIGHT_POSITIONS:
        light_name = f"Light_{light_pos}"
        light_lux = round(artificial_light_levels.get(light_pos, 0), 1)
        status_text = f"{light_name}\nArtificial Lux: {light_lux}"
        x = light_pos[0] * GRID_SIZE + GRID_SIZE / 2
        y = light_pos[1] * GRID_SIZE - 10  # Position above the light
        if light_pos not in light_status_labels:
            label = canvas.create_text(x, y, text=status_text, fill="blue", font=('Arial', 8, 'bold'), anchor='s')
            light_status_labels[light_pos] = label
        else:
            label_id = light_status_labels[light_pos]
            canvas.itemconfig(label_id, text=status_text)

def simulate_motion(sensor_pos, timestamp):
    # Simulate motion detection for each sensor based on occupancy and multiplier
    # if OCCUPANCY_STATE:
    #     motion_prob = min(BASE_MOTION_PROBABILITY * MOTION_TRIGGER_MULTIPLIER, 0.99)
    # else:
    #     motion_prob = BASE_MOTION_PROBABILITY / MOTION_TRIGGER_MULTIPLIER
    # return random.random() < motion_prob
    if OCCUPANCY_STATE:
        # Higher motion probability during occupancy, but with randomness
        motion_prob = min(BASE_MOTION_PROBABILITY * MOTION_TRIGGER_MULTIPLIER * random.uniform(0.5, 1.5), 0.99)
    else:
        # Lower motion probability outside occupancy, but with randomness
        motion_prob = BASE_MOTION_PROBABILITY / MOTION_TRIGGER_MULTIPLIER 
    return random.random() < motion_prob

def calculate_daylight_levels(timestamp):
    # Calculate daylight level for each sensor
    daylight_levels = {}
    day_of_year = 300  # Approximate day of the year 
    hour = (timestamp % 1440) / 60  # Convert timestamp to hour of the day
    solar_elevation, solar_azimuth = calculate_solar_position(day_of_year, hour)
    if solar_elevation <= 0:
        daylight_factor = 0
    else:
        # Apply weather effect
        current_hour = int(hour)
        weather_condition = WEATHER_CONDITIONS.get(current_hour, 'Clear')
        weather_factor = WEATHER_EFFECTS.get(weather_condition, 1.0)
        daylight_factor = (solar_elevation / 90) * weather_factor  # Normalize solar elevation
    for sensor_pos in SENSOR_POSITIONS:
        daylight_level = estimate_daylight_level(sensor_pos, daylight_factor, solar_azimuth)
        if solar_elevation > 0:
            # Ensure minimum daylight level at ceiling sensors during daytime
            daylight_level = max(daylight_level, 50)
        else:
            # At night, no daylight
            daylight_level = 0
        daylight_levels[sensor_pos] = daylight_level
    return daylight_levels

def calculate_solar_position(day_of_year, hour):
    # Simplified solar position calculation
    declination = 23.45 * math.sin(math.radians(360/365 * (284 + day_of_year)))
    solar_time = hour  # Assuming solar time equals clock time
    hour_angle = 15 * (solar_time - 12)
    solar_elevation_rad = math.asin(math.sin(math.radians(LATITUDE)) * math.sin(math.radians(declination)) +
                              math.cos(math.radians(LATITUDE)) * math.cos(math.radians(declination)) * math.cos(math.radians(hour_angle)))
    solar_elevation = math.degrees(solar_elevation_rad)

    # Prevent division by zero if solar_elevation is zero
    if math.cos(solar_elevation_rad) == 0:
        raise ValueError("Solar elevation is 90 degrees, leading to division by zero in solar azimuth calculation.")

    # Calculate solar azimuth
    try:
        numerator = math.sin(math.radians(declination)) * math.cos(math.radians(LATITUDE)) - \
                    math.cos(math.radians(declination)) * math.sin(math.radians(LATITUDE)) * math.cos(math.radians(hour_angle))
        denominator = math.cos(solar_elevation_rad)
        arg = numerator / denominator
        # Clamp the value to [-1, 1] to avoid math domain error
        arg = max(-1.0, min(1.0, arg))
        solar_azimuth_rad = math.acos(arg)
        solar_azimuth = math.degrees(solar_azimuth_rad)
        if hour_angle > 0:
            solar_azimuth = 360 - solar_azimuth
        # Adjust for NORTH_DIRECTION
        solar_azimuth = (solar_azimuth + NORTH_DIRECTION) % 360
    except Exception as e:
        raise ValueError(f"Error calculating solar azimuth: {e}")

    return solar_elevation, solar_azimuth

def estimate_daylight_level(sensor_pos, daylight_factor, solar_azimuth):
    # Estimate daylight level based on solar elevation and sensor proximity to windows, accounting for walls
    if not WINDOW_POSITIONS or not SENSOR_POSITIONS:
        return 0
    # For each window, check if the path to the sensor is blocked by a wall
    total_daylight = 0
    for window_pos in WINDOW_POSITIONS:
        path_clear = is_path_clear(sensor_pos, window_pos)
        if not path_clear:
            continue  # Skip this window if path is blocked
        distance = calculate_distance(sensor_pos, window_pos)
        # Adjust the scaling factor as needed to increase daylight levels
        # Real-world measurement: 150 lux near window on cloudy day
        # Therefore, adjust constants to match
        # Max daylight at distance = 0 (near window)
        max_daylight = 150  # Lux on cloudy day near window
        # On clear day, daylight_factor will be higher due to weather effects
        daylight_level = daylight_factor * max_daylight / (1 + distance)
        total_daylight += daylight_level
    return total_daylight

def is_path_clear(sensor_pos, window_pos):
    # Simple line-of-sight check between sensor and window
    x1, y1 = sensor_pos
    x2, y2 = window_pos
    dx = x2 - x1
    dy = y2 - y1
    steps = max(abs(dx), abs(dy))
    if steps == 0:
        return True
    x_increment = dx / steps
    y_increment = dy / steps
    x, y = x1, y1
    for i in range(int(steps)):
        x += x_increment
        y += y_increment
        cell_x = int(round(x))
        cell_y = int(round(y))
        if (cell_x, cell_y) in WALL_POSITIONS:
            return False
    return True

def calculate_distance(pos1, pos2):
    # Calculate Euclidean distance between two grid cells
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    return math.sqrt(dx*dx + dy*dy)


LAST_UPDATED_HOUR = -1
def assign_random_lumen_to_lights(timestamp):
    """
    Assign random lux values to each light block every hour during work hours.
    Keeps the lux output fixed for a single hour.
    """
    global LIGHT_LUX_OUTPUTS, LIGHT_LUMEN_OUTPUTS, LAST_UPDATED_HOUR

    # Calculate the current hour, wrapping around for multi-day timestamps
    current_hour = (timestamp % 1440) // 60  # Assuming timestamp is in minutes since midnight

    # Check if the current timestamp is within work hours
    if is_within_office_hours(timestamp):
        # Regenerate light outputs only if the hour has changed
        if current_hour != LAST_UPDATED_HOUR:
            print(f"Generating new light configurations for hour {current_hour}")
            LIGHT_LUX_OUTPUTS = {}
            LIGHT_LUMEN_OUTPUTS = {}
            for light_pos in LIGHT_POSITIONS:
                random_lumen = random.uniform(MAX_LUMENS * 0.7, MAX_LUMENS * 1.0)
                area = math.pi * pow((HEIGHT_ABOVE_DESK * math.tan(math.radians(BEAM_ANGLE / 2))), 2)
                current_lux = random_lumen / area
                LIGHT_LUX_OUTPUTS[light_pos] = round(current_lux, 2)
                LIGHT_LUMEN_OUTPUTS[light_pos] = round(random_lumen, 2)

            # Update the last processed hour
            LAST_UPDATED_HOUR = current_hour

        return LIGHT_LUX_OUTPUTS, LIGHT_LUMEN_OUTPUTS
    else:
        # Lights emit 0 lux outside work hours
        return {light_pos: 0 for light_pos in LIGHT_POSITIONS}, {light_pos: 0 for light_pos in LIGHT_POSITIONS}


def control_lighting(daylight_levels, timestamp, max_distance=2):
    """
    Calculate the total lux (daylight + artificial light) received by each sensor,
    based on random lux outputs from light blocks and occupancy state.

    Parameters:
        daylight_levels (dict): A dictionary mapping sensor positions to daylight lux levels.
        timestamp (datetime): The current timestamp for generating light outputs.
        max_distance (int): Maximum distance within which lights contribute to a sensor's lux.

    Returns:
        tuple: A tuple containing:
            - artificial_light_levels (dict): Total lux (daylight + artificial light) for each sensor.
            - light_outputs (dict): Lux outputs of all lights at the current timestamp.
            - nearby_lights (dict): List of nearby lights contributing to each sensor.
    """
   

    # Initialize dictionaries to store results
    artificial_light_levels = {}
    nearby_lights = {}
    total_lux = {}
    diff_from_ideal = {}

    current_hour = (timestamp % 1440) // 60  # Assuming timestamp is in minutes since midnight
    target_light_level = TARGET_LIGHT_LEVELS.get(current_hour, DESIRED_LIGHT_LEVEL)
    area = math.pi * pow((HEIGHT_ABOVE_DESK * math.tan(math.radians(BEAM_ANGLE / 2))), 2)
    max_lux = MAX_LUMENS / area

    # Generate random lumen (and hence lux) outputs for the lights
    light_lux_outputs, light_lumen_outputs = assign_random_lumen_to_lights(timestamp)

    for sensor_pos in SENSOR_POSITIONS:
        daylight_level = daylight_levels[sensor_pos]
        total_lux[sensor_pos] = daylight_level
        sensor_nearby_lights = []

        # Add contributions from nearby light blocks
        light_contribution = 0
        for light_pos in LIGHT_POSITIONS:
            if is_path_clear(sensor_pos, light_pos):
                distance = calculate_distance(sensor_pos, light_pos)
                if distance <= max_distance:
                    current_light_lux = light_lux_outputs.get(light_pos, 1)  # Default lux of 1 if not found
                    sensor_nearby_lights.append({
                        'position': light_pos,
                        'lux': current_light_lux,
                        'lumen': light_lumen_outputs.get(light_pos, 1),
                        'intensity': (current_light_lux/max_lux)*100
                    })
                    light_contribution += current_light_lux # not correct calculation -> there is an overlap

        # Add light contributions to the total lux
        total_lux[sensor_pos] += light_contribution # also not correct calculation -> there is an overlap

        # Calculate required artificial light based on target and daylight
        if OCCUPANCY_STATE:
            required_artificial_light = max(0, target_light_level - daylight_level)
            artificial_light_level = min(required_artificial_light, 500)  # Max fixture output is 500 lux
        else:
            artificial_light_level = 0  # Turn off lights when no occupancy

        diff_from_ideal[sensor_pos] = target_light_level - daylight_level - light_contribution
        nearby_lights[sensor_pos] = sensor_nearby_lights
        artificial_light_levels[sensor_pos] = artificial_light_level
    return artificial_light_levels, light_lux_outputs, light_lumen_outputs, nearby_lights, total_lux, diff_from_ideal

# Save to file
def log_data(timestamp, motion_detections, occupancy, daylight_levels, artificial_light_levels, nearby_lights, total_luxs, diff_from_ideals):
    # Log data per sensor
    try:
        combined_rows = []
        for sensor_pos in SENSOR_POSITIONS:
            sensor_id = SENSOR_IDS[sensor_pos]
            device = f"Sensor_{sensor_id}"
            motion = motion_detections[sensor_pos]
            presence = occupancy
            daylight_detection = daylight_levels[sensor_pos]
            daylight_compensation = artificial_light_levels[sensor_pos]
            total_lux = total_luxs[sensor_pos]
            diff_from_ideal = diff_from_ideals[sensor_pos]
            # Human-readable time
            time_str = format_timestamp(timestamp)
            row = {
                "device": device,
                "sensor_pos": {sensor_pos[0], sensor_pos[1]},
                "timestamp": timestamp,
                "time": time_str,
                "motiondetection": motion,
                "presencedetection": presence,
                "daylightdetection": daylight_detection,
                "daylightcompensation": daylight_compensation,
                "human_obs_daylight": daylight_detection * random.uniform(0.8, 1.0),  # Sensor with peak at 450nm
                "infrared_daylight": daylight_detection * random.uniform(0.6, 0.9),  # Sensor with peak at 750nm
                "total_lux": total_lux,
                "diff_from_ideal": diff_from_ideal
            }
            for i, light in enumerate(nearby_lights[sensor_pos], 1):
                row[f'nearby_light_{i}_name'] = f"Lamp{light['position']}"
                row[f'nearby_light_{i}_pos'] = light['position']
                row[f'nearby_light_{i}_lux'] = light['lux']
                row[f'nearby_light_{i}_lumen'] = light['lumen']
                row[f'nearby_light_{i}_intensity(%)'] = light['intensity']
            combined_rows.append(row)
            # Save to individual sensor CSV
            # sensor_df = pd.DataFrame([row])
            # sensor_filename = f"Input/sensor_data_{device}.csv"
            # # If the file exists, append, else write header
            # if os.path.exists(sensor_filename):
            #     sensor_df.to_csv(sensor_filename, mode='a', header=False, index=False)
            # else:
            #     sensor_df.to_csv(sensor_filename, mode='w', header=True, index=False)
        # Append to combined CSV
        pd.DataFrame(combined_rows).to_csv("Input/simulation_data.csv", mode='a', header=False, index=False)
        print(f"Data logged at timestamp {timestamp}.")
    except Exception as e:
        log_error(f"Failed to log data at timestamp {timestamp}: {e}")

# 4. Playback Mode
def start_playback():
    global is_playing, current_playback_time
    if is_playing:
        messagebox.showinfo("Playback", "Playback is already running.")
        return
    is_playing = True
    current_playback_time = 0
    playback_thread = threading.Thread(target=playback_simulation, daemon=True)
    playback_thread.start()

def playback_simulation():
    global is_playing, current_playback_time
    try:
        data = pd.read_csv("Input/simulation_data.csv")
        if data.empty:
            log_error("CSV file is empty. Run a simulation first.")
            return

        data_grouped = data.groupby('timestamp')
        timestamps = sorted(data_grouped.groups.keys())
        total_steps = len(timestamps)

        # Build mapping from device names to positions
        DEVICE_NAME_TO_POS = {}
        for device in data['device'].unique():
            device_data = data[data['device'] == device]
            sensor_pos = {device_data['sensor_x'].iloc[0], device_data['sensor_y'].iloc[0]} 
            DEVICE_NAME_TO_POS[device] = (int(sensor_pos[0]), int(sensor_pos[1]))

        while is_playing and current_playback_time < total_steps:
            timestamp = timestamps[current_playback_time]
            group = data_grouped.get_group(timestamp)
            occupancy = group['presencedetection'].iloc[0]
            # Update data label and progress bar
            progress = (current_playback_time / total_steps) * 100
            progress_bar['value'] = progress
            data_label.config(text=f"Playback... Time: {format_timestamp(timestamp)}, Occupancy: {'Yes' if occupancy else 'No'}")
            root.update_idletasks()
            current_playback_time += 1
            time.sleep(1 / playback_speed)  # Control playback speed

            # Prepare data for update_sensor_status_labels
            motion_detections = {}
            daylight_levels = {}
            artificial_light_levels = {}
            for index, row in group.iterrows():
                device_name = row['device']
                sensor_pos = DEVICE_NAME_TO_POS[device_name]
                motion_detections[sensor_pos] = row['motiondetection']
                daylight_levels[sensor_pos] = row['daylightdetection']
                artificial_light_levels[sensor_pos] = row['daylightcompensation']

            # Update sensor status labels
            update_sensor_status_labels(motion_detections, daylight_levels, artificial_light_levels)
            update_light_status_labels(artificial_light_levels)

        is_playing = False
    except Exception as e:
        log_error(f"Error during playback: {e}")
        stop_playback()

def pause_playback():
    global is_playing
    if not is_playing:
        messagebox.showinfo("Playback", "Playback is not running.")
        return
    is_playing = False
    print("Playback paused.")

def stop_playback():
    global is_playing, current_playback_time
    is_playing = False
    current_playback_time = 0
    progress_bar['value'] = 0
    data_label.config(text="Playback stopped.")
    root.update_idletasks()
    # Clear sensor status labels
    for label_id in sensor_status_labels.values():
        canvas.delete(label_id)
    sensor_status_labels.clear()
    print("Playback stopped.")

def increase_playback_speed():
    global playback_speed
    playback_speed *= 2
    print(f"Playback speed increased to {playback_speed}x.")

def decrease_playback_speed():
    global playback_speed
    playback_speed = max(0.5, playback_speed / 2)
    print(f"Playback speed decreased to {playback_speed}x.")

# Optimization
def start_optimization(timestamp):
    data = pd.read_csv("Input/simulation_data.csv")
    # problem_instance = LightingOptimizationProblem(data[data['timestamp'] == timestamp])
    # optimization_thread = threading.Thread(target=lambda:random_search(problem_instance,n_iterations=100))
    # optimization_thread.start()
    # # Update your simulation with the best configuration found
    # # update_simulation_config(best_configuration)
    # print("Optimization complete.")

# 5. Data Visualization
def visualize_csv_data():
    try:
        # Read combined data
        data = pd.read_csv("Input/simulation_data.csv")
        if data.empty:
            log_error("No data found. Run a simulation first.")
            return

        # Get list of sensors
        sensor_list = sorted(data['device'].unique())

        # Create a Tkinter Toplevel window
        viz_window = tk.Toplevel(root)
        viz_window.title("Data Visualization")

        # Create a dropdown menu
        selected_sensor = tk.StringVar(viz_window)
        selected_sensor.set(sensor_list[0])  # Default selection

        sensor_menu_label = tk.Label(viz_window, text="Select Sensor:")
        sensor_menu_label.pack(pady=5)

        sensor_menu = ttk.Combobox(viz_window, textvariable=selected_sensor, values=sensor_list, state='readonly')
        sensor_menu.pack(pady=5)

        # Create a Figure and Canvas
        fig = plt.Figure(figsize=(14, 12))
        canvas_fig = FigureCanvasTkAgg(fig, master=viz_window)
        canvas_fig.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # Function to update plots
        def update_plots(*args):
            sensor = selected_sensor.get()
            sensor_data = data[data['device'] == sensor]
            if sensor_data.empty:
                return

            # Convert timestamp to datetime
            sensor_data = sensor_data.copy()
            sensor_data.loc[:, 'time_dt'] = sensor_data['timestamp'].apply(lambda x: datetime.datetime.strptime(format_timestamp(x), '%H:%M'))

            fig.clear()
            axs = fig.subplots(3, 1, sharex=True)

            # Daylight and Artificial Light Levels
            axs[0].plot(sensor_data["time_dt"], sensor_data["daylightdetection"], label="Daylight Level (lux)", color='skyblue')
            axs[0].plot(sensor_data["time_dt"], sensor_data["daylightcompensation"], label="Artificial Light Level (lux)", linestyle='--', color='orange')
            axs[0].fill_between(sensor_data["time_dt"], 0, sensor_data["daylightcompensation"], color='orange', alpha=0.1)
            axs[0].set_ylabel("Light Levels (lux)")
            axs[0].legend(loc="upper right")
            axs[0].set_title(f"Light Levels Over Time for {sensor}")

            # Combined Lux
            axs[1].plot(sensor_data["time_dt"], sensor_data["total_lux"], label="Combined Lux", color='green')
            axs[1].set_ylabel("Combined Lux (lux)")
            axs[1].legend(loc="upper right")
            axs[1].set_title("Combined Lux Over Time")

            # Motion and Occupancy
            axs[2].plot(sensor_data["time_dt"], sensor_data["motiondetection"] * 100, label="Motion Detection (%)", color='purple', linestyle=':')
            axs[2].plot(sensor_data["time_dt"], sensor_data["presencedetection"] * 100, label="Occupancy (%)", color='red', linestyle='--')
            axs[2].set_ylabel("Percentage (%)")
            axs[2].legend(loc="upper right")
            axs[2].set_title("Motion and Occupancy Over Time")

            axs[2].set_xlabel("Time")

            # Format x-axis to show only time
            time_formatter = DateFormatter('%H:%M')
            for ax in axs:
                ax.xaxis.set_major_formatter(time_formatter)

            fig.autofmt_xdate()
            canvas_fig.draw()

        # Bind the update function to the dropdown menu
        selected_sensor.trace_add('w', update_plots)

        # Initial plot
        update_plots()

    except KeyError as ke:
        log_error(f"Error during data visualization: '{ke.args[0]}'")
    except Exception as e:
        log_error(f"Error during data visualization: {e}")

# 6. Grid Overlay
def draw_grid():
    for col in range(GRID_WIDTH):
        for row in range(GRID_HEIGHT):
            x1 = col * GRID_SIZE
            y1 = row * GRID_SIZE
            x2 = x1 + GRID_SIZE
            y2 = y1 + GRID_SIZE
            canvas.create_rectangle(x1, y1, x2, y2, outline="#d3d3d3")

# 7. Simulation Loop and Data Generation
def start_simulation():
    try:
        # Delete existing CSVs to avoid appending to old data
        if os.path.exists("Input/simulation_data.csv"):
            os.remove("Input/simulation_data.csv")
        for sensor_id in SENSOR_IDS.values():
            device = f"Sensor_{sensor_id}"
            sensor_filename = f"Input/sensor_data_{device}.csv"
            if os.path.exists(sensor_filename):
                os.remove(sensor_filename)
        create_empty_csv()
        if not SENSOR_POSITIONS:
            log_error("No sensors placed. Simulation aborted.")
            return
        if not WINDOW_POSITIONS:
            log_error("No windows placed. Simulation aborted.")
            return

        # Clear sensor status labels before starting simulation
        for label_id in sensor_status_labels.values():
            canvas.delete(label_id)
        sensor_status_labels.clear()

        simulation_thread = threading.Thread(target=run_simulation, args=(user_start_time, user_end_time), daemon=True)
        simulation_thread.start()
    except Exception as e:
        log_error(f"Failed to start simulation: {e}")

def run_simulation(start_timestamp, end_timestamp):
    # try:
    #     for timestamp in range(start_timestamp, end_timestamp, TIME_STEP):
    #         simulate_sensor_data(timestamp)
    #         # No need to sleep since we're not simulating in real-time
            
    #     progress_bar['value'] = 100
    #     data_label.config(text="Simulation completed.")
    #     print("Simulation completed.")
    # except Exception as e:
    #     log_error(f"Error during simulation: {e}")
    try:
        generate_daily_occupancy_schedule()  # <-- Add this line here
        for timestamp in range(start_timestamp, end_timestamp, TIME_STEP):
            simulate_sensor_data(timestamp)
        progress_bar['value'] = 100
        data_label.config(text="Simulation completed.")
        print("Simulation completed.")
    except Exception as e:
        log_error(f"Error during simulation: {e}")


def stop_simulation_thread():
    global is_playing
    is_playing = False
    stop_playback()

# 8. Main GUI Setup

def open_time_dialog():
    def submit(dialog, start_time, end_time):
        global user_start_time, user_end_time
        try:
            start_time = int(start_time)
            end_time = int(end_time)
            if start_time >= 0 and end_time > start_time:
                user_start_time, user_end_time = start_time, end_time
                print(f"Times set: Start at {user_start_time}s, end at {user_end_time}s.")
                dialog.destroy()
            else:
                raise ValueError("Start time must be less than end time and both should be positive.")
        except ValueError as e:
            print(f"Invalid input: {e}")

    dialog = tk.Toplevel(root)
    dialog.title("Set Simulation Interval")
    dialog_width = 300  # Define the width of the dialog
    dialog_height = 120  # Define the height of the dialog
    screen_width = root.winfo_screenwidth()  # Get screen width
    screen_height = root.winfo_screenheight()  # Get screen height
    x = (screen_width / 2) - (dialog_width / 2)
    y = (screen_height / 2) - (dialog_height / 2)
    dialog.geometry(f"{dialog_width}x{dialog_height}+{int(x)}+{int(y)}")

    start_label = tk.Label(dialog, text="Start Time (m):", padx=30, pady=5)
    start_label.grid(row=0, column=0)
    start_entry = tk.Entry(dialog)
    start_entry.grid(row=0, column=1)
    start_entry.insert(0, str(user_start_time))

    end_label = tk.Label(dialog, text="End Time (m):", padx=30, pady=5)
    end_label.grid(row=1, column=0)
    end_entry = tk.Entry(dialog)
    end_entry.grid(row=1, column=1)
    end_entry.insert(0, str(user_end_time))

    empty_label = tk.Label(dialog, text="")
    empty_label.grid(row=2, column=0)

    ok_button = tk.Button(dialog, text="OK", command=lambda: submit(dialog, start_entry.get(), end_entry.get()))
    ok_button.grid(row=3, column=0)

    cancel_button = tk.Button(dialog, text="Cancel",command=dialog.destroy)
    cancel_button.grid(row=3, column=1)

def setup_gui():
    global root, canvas, progress_bar, data_label, canvas_width, canvas_height, legend_frame, conditions_table, side_frame
    global north_canvas, error_log_window, error_log_text, simulation_settings_table, control_frame
    root.title("Office Lighting Simulation")
    # Adjust window size appropriately
    window_width = 1500
    window_height = 1000
    root.geometry(f"{window_width}x{window_height}")
    root.resizable(True, True)

    # Create Canvas for floorplan display
    canvas_frame = tk.Frame(root)
    canvas_frame.pack(side=tk.LEFT)

    canvas = tk.Canvas(canvas_frame, width=canvas_width, height=canvas_height, bg='white', relief='sunken', bd=2)
    canvas.pack()

    # Draw grid
    draw_grid()

    # Bind events
    canvas.bind("<Button-1>", place_marker)  # Event binding for placing markers

    # Right-side panel for controls
    control_frame = tk.Frame(root)
    control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

    # Legend and Conditions Frame
    legend_frame = tk.Frame(control_frame)
    legend_frame.pack(fill='x')
    draw_legend()

    # Simulation Controls
    sim_control_label = tk.Label(control_frame, text="Simulation Controls", font=('Arial', 14, 'bold'))
    sim_control_label.pack(pady=5)

    # load_floorplan_btn = tk.Button(control_frame, text="Load Floorplan", width=25, command=load_floorplan)
    # load_floorplan_btn.pack(pady=2)

    button_frame = tk.Frame(control_frame)
    button_frame.pack(side=tk.TOP)  # Packs the button frame within the control frame

    # Load and configure the sun azimuth icon
    # sun_azimuth_icon = PhotoImage(file="Icons/sun_azimuth.png")
    # sun_azimuth_icon = sun_azimuth_icon.subsample(30, 30)
    set_sun_btn = tk.Button(button_frame,  command=set_sun_azimuth) #image=sun_azimuth_icon,)
    set_sun_btn.pack(side=tk.LEFT, pady=2)  # Pack the button horizontally
    # set_sun_btn.image = sun_azimuth_icon  # Keep a reference!

    # Load and configure the latitude icon
    # latitude_icon = PhotoImage(file="Icons/latitude.png")
    # latitude_icon = latitude_icon.subsample(22, 22)
    set_latitude_btn = tk.Button(button_frame, command=set_latitude)
    set_latitude_btn.pack(side=tk.LEFT, pady=2)  # Also pack this button horizontally next to the sun button
    # set_latitude_btn.image = latitude_icon  # Keep a reference!

    # light_level_icon = PhotoImage(file="Icons/target_level.png")
    # light_level_icon = light_level_icon.subsample(24, 24)
    set_light_level_btn = tk.Button(button_frame, command=set_target_light_level)
    set_light_level_btn.pack(pady=2)
    # set_light_level_btn.image = light_level_icon

    # Save and Load Simulation
    simulation_frame = tk.Frame(control_frame)
    simulation_frame.pack(side=tk.TOP, pady=5)

    simulate_label = tk.Label(simulation_frame, text="Simulation", font=('Arial', 14, 'bold'))
    simulate_label.pack()

    set_time_btn = tk.Button(simulation_frame, text="Set Simulation Time", width=25, command=open_time_dialog)
    set_time_btn.pack(padx=0)
    
    top_frame = tk.Frame(simulation_frame)
    bottom_frame = tk.Frame(simulation_frame)
    top_frame.pack(side=tk.TOP, fill=tk.X)
    bottom_frame.pack(side=tk.TOP, fill=tk.X)

    load_sim_btn = tk.Button(top_frame, text="Load", width=12, command=load_simulation)
    load_sim_btn.pack(side=tk.LEFT, pady=2)

    save_btn = tk.Button(top_frame, text="Save", width=12, command=save_simulation)
    save_btn.pack(side=tk.LEFT, pady=2)

    simulate_btn = tk.Button(bottom_frame, text="Start", width=12, command=start_simulation)
    simulate_btn.pack(side=tk.LEFT, pady=2)

    visualize_btn = tk.Button(bottom_frame, text="Visualize Data", width=12, command=visualize_csv_data)
    visualize_btn.pack(side=tk.LEFT, pady=2)

    # Playback Controls
    # create frame as simulation top and bottom
    playback_frame = tk.Frame(control_frame)
    playback_frame.pack(side=tk.TOP, pady=5)

    playback_label = tk.Label(playback_frame, text="Playback Controls", font=('Arial', 14, 'bold'))
    playback_label.pack(pady=5)

    # playback_icon = PhotoImage(file="Icons/play.png")
    # playback_icon = playback_icon.subsample(6, 6)
    playback_btn = tk.Button(playback_frame, command=start_playback)
    playback_btn.pack(side=tk.LEFT, pady=2)
    # playback_btn.image = playback_icon

    # pause_icon = PhotoImage(file="Icons/pause.png")
    # pause_icon = pause_icon.subsample(6, 6)
    pause_btn = tk.Button(playback_frame, command=pause_playback)
    pause_btn.pack(side=tk.LEFT, pady=2)
    # pause_btn.image = pause_icon

    # stop_icon = PhotoImage(file="Icons/stop.png")
    # stop_icon = stop_icon.subsample(6, 6)
    stop_btn = tk.Button(playback_frame, command=stop_playback)
    stop_btn.pack(side=tk.LEFT, pady=2)
    # stop_btn.image = stop_icon

    # speed_up_icon = PhotoImage(file="Icons/up.png")
    # speed_up_icon = speed_up_icon.subsample(24, 24)
    speed_up_btn = tk.Button(playback_frame, command=increase_playback_speed)
    speed_up_btn.pack(side=tk.LEFT, pady=2)
    # speed_up_btn.image = speed_up_icon

    # slow_down_icon = PhotoImage(file="Icons/down.png")
    # slow_down_icon = slow_down_icon.subsample(24, 24)
    slow_down_btn = tk.Button(playback_frame, command=decrease_playback_speed)
    slow_down_btn.pack(side=tk.LEFT, pady=2)
    # slow_down_btn.image = slow_down_icon

    # Adding a button to start optimization
    optimize_label = tk.Label(control_frame, text="Optimization", font=('Arial', 14, 'bold'))
    optimize_label.pack(pady=5)
    optimize_button = tk.Button(control_frame, text="Run Optimization", width=25, command=lambda: start_optimization(user_start_time))
    optimize_button.pack(pady=5)  

    # Progress bar and data label
    progress_frame = tk.Frame(control_frame)
    progress_frame.pack(fill='x', pady=5)

    progress_label = tk.Label(progress_frame, text="Progress", font=('Arial', 14, 'bold'))
    progress_label.pack()

    progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', length=185, mode='determinate')
    progress_bar.pack()

    data_label = tk.Label(progress_frame, text="Ready", font=('Arial', 10))
    data_label.pack()

    # North Arrow below progress bar
    north_canvas = tk.Canvas(control_frame, width=100, height=100)
    north_canvas.pack(pady=10)
    draw_north_arrow()

    # Simulation Settings Table
    side_frame = tk.Frame(root)
    side_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=10)
    sim_settings_label = tk.Label(side_frame, text="Simulation Settings", font=('Arial', 14, 'bold'))
    sim_settings_label.pack(pady=10)
    create_simulation_settings_table(side_frame)  # Pass control_frame as parent

    # Conditions Table (Weather Conditions, Target Light Levels)
    conditions_label = tk.Label(side_frame, text="Simulation Conditions", font=('Arial', 14, 'bold'))
    conditions_label.pack(pady=5)
    create_conditions_table()

    # Error Log Window (Hidden by default)
    error_log_window = None
    error_log_text = None

    # Run environment setup
    environment_setup()

    # Start a thread to process errors from the queue
    root.after(100, process_error_queue)

def format_timestamp(timestamp):
    # Convert timestamp in minutes to HH:MM format
    hours = (timestamp % 1440) // 60
    minutes = timestamp % 60
    return f"{int(hours):02d}:{int(minutes):02d}"

def log_error(message):
    error_queue.put(message)
    # Optionally, show a pop-up for critical errors
    messagebox.showerror("Error", message)

def process_error_queue():
    global error_log_window, error_log_text
    try:
        while True:
            message = error_queue.get_nowait()
            if not error_log_window or not tk.Toplevel.winfo_exists(error_log_window):
                create_error_log_window()
            error_log_text.config(state='normal')
            error_log_text.insert(tk.END, message + "\n")
            error_log_text.see(tk.END)
            error_log_text.config(state='disabled')
    except queue.Empty:
        pass
    finally:
        root.after(100, process_error_queue)

def create_error_log_window():
    global error_log_window, error_log_text
    error_log_window = tk.Toplevel(root)
    error_log_window.title("Error Log")
    error_log_window.geometry("400x300")
    error_log_window.resizable(False, False)
    tk.Label(error_log_window, text="Error Log", font=('Arial', 14, 'bold')).pack(pady=5)
    error_log_text = tk.Text(error_log_window, state='disabled', wrap='word')
    error_log_text.pack(expand=True, fill='both', padx=10, pady=5)
    tk.Button(error_log_window, text="Close", command=error_log_window.destroy).pack(pady=5)


setup_gui()
root.mainloop()