import time
from pywinauto import Application, keyboard, findwindows
import os, shutil
from openpyxl import load_workbook
import logging

logging.basicConfig(level=logging.INFO)

efficacy = 124.1

DIALUX_PATH = r"C:\Program Files\DIAL GmbH\DIALux\DIALux.exe"
PROJECT_FILE = r"C:\Users\kate_\Desktop\Project1.evo"
def connect_to_dialux():
    global dlg, app
    time.sleep(5)
    app = Application(backend="uia").connect(title_re=".*DIALux evo.*")
    dlg = app.window(title_re=".*DIALux evo.*")
    dlg.set_focus()

connect_to_dialux()

def run_iteration(lamp_names, lumens, counter, output_file):
    """
    Run a single iteration in DIALux with the specified lamp configurations.
    """
    start_time = time.time()
    watts = [lumen / efficacy for lumen in lumens]

    for index in range(counter):
        retry_count = 3
        attempt = 0
        for attempt in range(retry_count+1):
            try:
                dlg.child_window(title="Dial.Dialux.InteractionTools.Project.ProjectTreeTool").select()
                break
            except Exception as e:
                if attempt < retry_count:
                    time.sleep(4) 
                    keyboard.send_keys("^s")
                    keyboard.send_keys("%+L")
                    logging.error(f"Attempt {attempt + 1}: Failed to locate or select Project Tree Tool: {e}")
                    # dlg.child_window(title="Dial.Dialux.InteractionTools.Project.ProjectTreeTool").select()

        dlg.child_window(title=lamp_names[index]).click_input()
        dlg.child_window(title="Dial.Dialux.InteractionTools.Lighting.LampTool", auto_id="LampTool", control_type="TabItem").select()

        flux_edit = dlg.child_window(auto_id="SelectedFlux", control_type="Edit")
        flux_edit.set_text(lumens[index]) 
        power_edit = dlg.child_window(auto_id="SelectedPower", control_type="Edit")
        power_edit.set_text(watts[index]) 
        if dlg.child_window(auto_id="MaintenanceLampTypeApplyButton", control_type="Button").is_enabled():
            dlg.child_window(auto_id="MaintenanceLampTypeApplyButton", control_type="Button").click()
       
    # Calculation
    dlg.child_window(auto_id="CalculationButtonStart", control_type="Button").click()
    time.sleep(14)

    # Export results
    view_menu = dlg.child_window(title="View", auto_id="View", control_type="MenuItem")
    view_menu.click_input()
    time.sleep(1)
    menu_items = view_menu.children(control_type="MenuItem")
    menu_items[len(menu_items)-1].click_input()
    retry_count = 3
    for attempt in range(retry_count):
        try:
            dlg.child_window(auto_id="aid_RenderProjectDocument", control_type="Button").click()
            break 
        except:
            if attempt < retry_count - 1:
                logging.info(f"Attempt {attempt + 1} failed. Retrying...")
                time.sleep(1) 
    # keyboard.send_keys("^p")

    time.sleep(0.5)
    saveas = dlg.child_window(auto_id="MenuSaveAs", control_type="Menu")
    retry_count = 3
    for attempt in range(retry_count):
        try:
            saveas.click_input()
            break 
        except:
            if attempt < retry_count - 1:
                logging.info(f"Attempt {attempt + 1} failed. Retrying...")
                time.sleep(1) 

    # dlg.print_control_identifiers(filename='out.txt')
    keyboard.send_keys("{DOWN}{DOWN}{DOWN}{DOWN}{ENTER}{ENTER}")
    time.sleep(1)
    keyboard.send_keys(output_file)
    keyboard.send_keys("{ENTER}")
    time.sleep(5)

    # Stop calculation
    dlg.child_window(auto_id="DiscardResultsButton", control_type="Button").click()
    elapsed = time.time() - start_time
    retry_count = 3
    for attempt in range(retry_count):
        try:
            keyboard.send_keys("^s")
            keyboard.send_keys("%+L")
            time.sleep(4) 
            attempt = attempt+1
            break
        except:
            if attempt < retry_count - 1:
                time.sleep(4) 
                keyboard.send_keys("^s")
                keyboard.send_keys("%+L")
    logging.info(f"Iteration completed in {elapsed:.2f} seconds. Project is saved.")

    return output_file
   

def extract_results(output_file):
    """
    Extract uniformity and energy results from the output XLSX file.
    """
    attempt = 0
    time.sleep(2)
    while attempt < 3:
        try:
            workbook = load_workbook(output_file)
            sheet = workbook.active
            uniformity = float(sheet["W29"].value)
            energy = float("".join(filter(lambda x: x.isdigit() or x == ".", sheet["I99"].value)))
            # lux_str = sheet["W26"].value
            # lux = float(lux_str.replace(' lx', ''))
            lux_per_desk = []
            for i in range(0, 6):
                tocheck = sheet[f"T{170+5*i}"].value
                if tocheck is None or ' lx' not in tocheck:
                    lux_str = sheet[f"T{171+5*i}"].value
                else:
                    lux_str = sheet[f"T{170+5*i}"].value
                lux_per_desk.append(float(lux_str.replace(' lx', '')))
            return uniformity, energy, lux_per_desk
        except Exception as e:
            attempt += 1
            logging.error(f"Attempt {attempt}: Invalid file exception: {e}")
            time.sleep(1)
    return None, None, None

def replace_dialux_file():
    def close_dialux():
        try:
            app = Application(backend="uia").connect(title_re=".*DIALux evo.*")
            window = app.window(title_re=".*DIALux evo.*")
            keyboard.send_keys("^s")
            window.close()
            time.sleep(2)
            print("DIALux window closed successfully.")
        except Exception as e:
            print(f"Error while closing DIALux: {e}")

    def copy_file():
        source = r"C:\Users\kate_\Desktop\DONT CHANGE\version19_02\Project1.evo"
        destination = r"C:\Users\kate_\Desktop\Project1.evo"
        try:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copy(source, destination)
            print(f"Copied old file to '{destination}'.")
        except Exception as e:
            print(f"Error copying file: {e}")
        return destination

    def open_file(file_path):
        os.startfile(file_path)
        print(f"Opened '{file_path}'.")

    time.sleep(5)
    close_dialux()
    time.sleep(1)
    new_file_path = copy_file()
    time.sleep(1)
    open_file(new_file_path)
    time.sleep(5)

    connect_to_dialux()
    luminaires_node = dlg.child_window(
        auto_id="Project_OFFICE_ROOM_OFFICE_Luminaires", 
        control_type="ListItem"
    )
    expand_checkbox = luminaires_node.child_window(auto_id="ExpandCheckBox", control_type="CheckBox")
    expand_checkbox.click_input()
