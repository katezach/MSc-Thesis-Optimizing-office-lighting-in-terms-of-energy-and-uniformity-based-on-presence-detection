# MSc Thesis: Optimizing office lighting in terms of energy and uniformity based on presence detection

## Description
This project simulates a smart lighting system using sensor data to optimize lighting conditions in an office environment. The simulation considers both energy efficiency and user comfort by adjusting lighting based on sensor inputs.

## Dataset Details
The initial dataset contains the following fields:
- `device`: Identifier for the device collecting the data.
- `sensor_x`: X-coordinate of the sensor's position.
- `sensor_y`: Y-coordinate of the sensor's position.
- `timestamp`: The date and time when the data was recorded. It is only an integer from 0 to 1439.
- `time`: The specific time of day when the data was recorded. It is in human-reading format, e.g. 14:05.
- `motiondetection`: Indicates whether motion was detected (true/false).
- `presencedetection`: Indicates whether presence was detected (true/false).

While the new adjusted input dataset for the optimization have the fields:
- `Lamp name`: The name of lamp, e.g. Lamp1.
- `Lumens`: The lumens exported from the lamp with name `Lamp name`.
- `Watts`: The wattages of the corresponding lamp.

## Output
The simulation outputs the following data for each sensor reading:
- `energy`: Total energy consumption in watts for a specific timestamp.
- `uniformity`: Illuminance Uniformity Distribution Index, measuring the uniformity of the lighting.
- `illuminance`: A list of lux levels per desk surface for the specific run.

## Run the Project
To run this project, follow these steps:
1. Ensure you have Python installed on your machine. The project is tested with Python 3.8.
2. Clone this repository or download the project files.
3. Install required Python packages:
`pip install -r requirements.txt`
4. Run the main simulation script:
`python experiments.py`: to run a grid search over the three algorithms (BO, SAMO-COBRA, PSO)
`python nows_experiments.py`: to run a grid search over the algorithms without a warm start / can also be used for the enhancement of PSO

**Note:** make sure you have a DIALux project created and that the corresponding path and name are indicated.

For more details, read the corresponding paper.
 
