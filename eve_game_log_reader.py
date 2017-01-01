# Read the Eve Logs and change some LEDs based on events in the game log

import os
import time
import json
import SettingsError
import sys
import RPi.GPIO as GPIO

mining_led = 18
mining_issue_led = 22
combat_issue_led = 27
mining_button = 17




def find_log_file(log_directory, wanted_characters):
    date = time.strftime("%Y%m%d")
    files = os.listdir(log_directory)
    wanted_logs = []
    for wanted_character in wanted_characters:
        # print("Looking for", wanted_character)
        today_logs = []
        for file in files:
            # print("File:",file)
            if file[0:8] == date:
                file_pointer = open(os.path.join(log_directory, file),"r")
                file_contents = file_pointer.readlines()
                if wanted_character in file_contents[2]:
                    # print("Found a log for", wanted_character)
                    today_logs.append(file)
        wanted_logs.append(today_logs[-1])

    return(wanted_logs)


def get_settings():
    print("I cannot find any settings file, so I'm assuming this is your first run.\n")
    print("To make your log file accessible you could use a command that follows this format:")
    print("sudo mount -t cifs -o username=windows_username,password=windows_password //IP_of_windows_machine/Users ~/my_windows_home")
    print("Replace the windows username, password and ip sections from the above line with the correct details and create a directory in your home directory called my_windows_home.")

    log_dir = input("Please enter the path to your log directory:")
    files = os.listdir(log_dir)

    characters = []

    print("You will now be asked to enter the name(s) of the characters you wish to track.")
    print("Please enter them one at a time and enter a blank line when you have given all the names.\n")
    character = input("Please enter the name of a character you would like to check the logs for: ")
    while character != "":
        characters.append(character)
        character = input("Please enter the name of a character you would like to check the logs for: ")

    if len(characters) > 0 and len(files) > 0:
        saved_settings = {"log_directory": log_dir, "wanted_characters": characters}
    else:
        print("There was a problem with the settings you gave, please check them over and rerun this program")
        raise SettingsError("%i,%i" %(len(files), len(characters)))


def init():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(mining_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(mining_led, GPIO.OUT)
    GPIO.setup(mining_issue_led, GPIO.OUT)
    GPIO.setup(combat_issue_led, GPIO.OUT)
    if os.path.isfile("log_reader_settings.json"):
        return json.load(open("log_reader_settings.json"))
    else:

        saved_settings = get_settings()
        print("Thank you, I'm saving your settings as")
        json.dump(saved_settings, open("log_reader_settings.json","w"))
        return saved_settings


def set_leds(mining_issue, combat_issue):
    if mining_issue:
        GPIO.output(mining_issue_led,GPIO.HIGH)
        GPIO.output(mining_led,GPIO.LOW)
    if combat_issue:
        GPIO.output(combat_issue_led,GPIO.HIGH)
        GPIO.output(mining_led,GPIO.LOW)
    if not mining_issue and not combat_issue:
        GPIO.output(mining_led,GPIO.HIGH)
        GPIO.output(combat_issue_led,GPIO.LOW)
        GPIO.output(mining_issue_led,GPIO.LOW)


if __name__ == "__main__":
    try:
        read_settings = init()

        mining_issue = False
        combat_issue = False
        dismissed = False
        log_directory = read_settings["log_directory"]
        wanted_characters = read_settings["wanted_characters"]
        log_filenames = find_log_file(log_directory, wanted_characters)
        log_files = []
        for file in log_filenames:
            log_files.append(os.path.join(log_directory, file))

        log_file_pointers = []
        for log_file in log_files:
            log_file_pointers.append(open(log_file, "r"))
            log_file_pointers[-1].readlines()
        heading = "Reading events from: "+ str(log_files)[1:-1]
        print(heading)
        print("¯"*len(heading))
        try:
            while True:
                for log_file_pointer in log_file_pointers:
                    line = log_file_pointer.readline()
                    if line != "":
                        print(line)
                        if "pale shadow" in line:
                            mining_issue = True
                        elif "combat" in line:
                            combat_issue = True

                    if not GPIO.input(mining_button):
                        mining_issue = False
                        combat_issue = False
                set_leds(mining_issue, combat_issue)
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("Closing down now")
            GPIO.output(mining_led,GPIO.LOW)
            log_file_pointer.close()
    except SettingsError as se:
        parts = se.split(",")
        print("There was a problem with your setup information. We found %i log files and %i characters which caused some problems." %(int(se[0]),int(se[1])))
        sys.exit()