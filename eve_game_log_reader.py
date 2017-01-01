""" Read the Eve Logs and change some LEDs based on events in the game log """

__appname__ = "Eve Mining Status"
__author__  = "Graeme Nimmo (Nimmo/NimmoG)"
__version__ = "0.1"
__license__ = "GNU GPL 3.0"

# Import required libraries
import os
import time
import json
import SettingsError
import sys
import RPi.GPIO as GPIO

# Create some variables to store relevant GPIO pins
mining_led = 18 # LED to show that all is clear (Green in my setup)
mining_issue_led = 22 # LED to show that there is a mining issue (Amber in my setup)
combat_issue_led = 27 # LED to show that there is a combat issue (Red in my setup)
mining_button = 17 # Button used to acknowledge the issue and reset back to green status (My button is push-to-make)


def find_log_file(log_directory, wanted_characters):
	"""Find the log file(s) for the character(s) that we're wanting to track."""
    date = time.strftime("%Y%m%d") # Decided to only check the logs for today when looking for the latest log.
	# When I get around to a round of code refactoring I'll just reverse the list of files
	# then stop when I get to a log file for a character I'm looking for. This should give me the latest log
	# for this char and allow us to roll over midnight.
    files = os.listdir(log_directory)
	# Create an empty list of log filenames
    wanted_logs = []
	
	# Find the log file for each character we're interested in:
    for wanted_character in wanted_characters:
        # Creates an empty list to store all of the log files from today for the character we're interested in		
        today_logs = []
		
		# This code will be refactored at some point to be more efficient
		# Look at every file in our log file directory
        for file in files:
            # If the date of the log file matches today's date check to see if it is for the character we're looking for
            if file[0:8] == date:
                file_pointer = open(os.path.join(log_directory, file),"r")
                file_contents = file_pointer.readlines()
                if wanted_character in file_contents[2]:
                    # If the log is for our character append it to the list of log files for our character
                    today_logs.append(file)
		# Once we've looked at every file in the directory we'll assume that the last one appended to the list is the current one for our character
        wanted_logs.append(today_logs[-1])
	
	# Return the log files for our character(s)
    return(wanted_logs)


def get_settings():
	"""If this is the first time we're running get the location of the log files and the character(s) we're looking to track."""
    print("I cannot find any settings file, so I'm assuming this is your first run.\n")
    print("To make your log file accessible you could use a command that follows this format:")
	# This is how I make my log directory available. It's used for other projects too
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
		# This is an attempt at some very basic input validation. I'll perhaps try to tidy this up if there's a demand for it
        print("There was a problem with the settings you gave, please check them over and rerun this program")
        raise SettingsError("%i,%i" %(len(files), len(characters)))


def init():
	""" Perform some initialisation operations."""
    GPIO.setmode(GPIO.BCM) # Set pin numbering to BCM mode.
    GPIO.setwarnings(False)
    GPIO.setup(mining_button, GPIO.IN, pull_up_down=GPIO.PUD_UP) # I'm using a push-to-make switch
    GPIO.setup(mining_led, GPIO.OUT)
    GPIO.setup(mining_issue_led, GPIO.OUT)
    GPIO.setup(combat_issue_led, GPIO.OUT)
	
	# Try to read the settings from the settings file.
    if os.path.isfile("log_reader_settings.json"):
        return json.load(open("log_reader_settings.json"))
    else:
		# If we can't find the settings file let's make one
        saved_settings = get_settings()
        print("Thank you, I'm saving your settings now.")
        json.dump(saved_settings, open("log_reader_settings.json","w"))
        return saved_settings


def set_leds(mining_issue, combat_issue):
	""" Set the LEDs to reflect the current mining status """
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
			# Open each of the log files that we are interested in and read to the end of the file
            log_file_pointers.append(open(log_file, "r"))
            log_file_pointers[-1].readlines()
		
		# Try to print a little heading so we know which files are being read. I am being very cheeky here and just stripping the [] from the list of log filenames and printing it as a string.
        heading = "Reading events from: "+ str(log_files)[1:-1]
        print(heading)
		# Put a nice little underline under the heading which is the same length as the heading itself
        print("¯"*len(heading))
        try:
            while True:
                for log_file_pointer in log_file_pointers:
					# Try to read the next line from a log file. 
					# We take advantage of the fact that when you read past the end of the file it returns an empty string
                    line = log_file_pointer.readline()
					# If we've actually got a new line in the log file print it out and see if we care about what it says
                    if line != "":
                        print(line)
						# Detects whether we've depleted an asteroid
                        if "pale shadow" in line:
                            mining_issue = True
						# Detects if there are come combat notifications
                        elif "combat" in line:
                            combat_issue = True

					# If the button is pressed (it's negated perhaps because I'm using a push-to-make button?)
                    if not GPIO.input(mining_button):
						# If the button is pushed reset the notification indicators back to false
                        mining_issue = False
                        combat_issue = False
						
				# Now that we've checked what the LED status should be we can actually set the status.
                set_leds(mining_issue, combat_issue)
				
				# Wait for a little while before checking again
                time.sleep(0.5)
				
        except KeyboardInterrupt:
			# If the user hits Ctrl+c to kill the program this exception handler will neatly tidy up what we're doing with GPIO and display a little exiting message
            print("Closing down now")
            GPIO.output(mining_led,GPIO.LOW)
            GPIO.cleanup()
			
			# Close each of our log files
			for log_file_pointer in log_file_pointers:
				log_file_pointer.close()
    except SettingsError as se:
		# Handle the user giving us unsuitable information in the setup stage. Very crude, for now.
        parts = se.split(",")
        print("There was a problem with your setup information. We found %i log files and %i characters which caused some problems." %(int(se[0]),int(se[1])))
        GPIO.cleanup()
        sys.exit()
