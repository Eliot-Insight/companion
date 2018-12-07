#!/usr/bin/env python

'''
Print a json with information about screens that are running for a given user.
Most of the services offered by Blue Robotics companion are run as background
command line processes. These commands/services are running under detached 
screens. This program will return a json describing the screen ids and names
for a given user.

See also (or similar):
`udevadm info /dev/serial/by-id/usb-3D_Robotics_PX4_FMU_v2.x_0-if00 | sed -n 's/E: //p'`

The json format is:
{
    "devices":[
            {
                "path":</dev path>
                "serial-id":</by-id name>
                "usb-desc":<usb vid/pid>
                "companion-device": <known/expected devices in companion>
                "udev-info":{
                    <udev-attr>:<udev-value>,
                    ...
                }
            },
            ... 
        ]
    }
}
'''

# TODO we should move os to subprocess in companion
import sys
import subprocess
import glob
import argparse
import json

PARSER = argparse.ArgumentParser(description=__doc__)
PARSER.add_argument('--pattern',
                    action="store",
                    type=str,
                    default="/dev/serial/by-id/*",
                    help="Path to search for usb devices."
                    )
PARSER.add_argument('--indent',
                    action="store",
                    type=int,
                    default=None,
                    help="Indent level for json output formatting."
                    )
ARGS = PARSER.parse_args()

companionFamiliarDevices = {
    "Pixhawk Autopilot":
    {
        "ID_SERIAL":"3D_Robotics_PX4_FMU_v2.x_0"
    },
    "Pixhawk Autopilot (Bootloader)":
    {
        "ID_MODEL": 'PX4_BL_FMU_v2.x',
        "ID_SERIAL":"3D_Robotics_PX4_BL_FMU_v2.x_0"
    },
    "Blue Robotics HD Low Light USB Camera":
    {
        "ID_VENDOR_ID":"05a3",
        "ID_MODEL_ID":"9422"
    },
    "Raspberry Pi Camera Module":
    {
        "ID_VENDOR_ID":"05a3",
        "ID_MODEL_ID":"9422"
    }
}

ret = {
    "devices":[]
}

def getUdevInfo(devicePath):
    try:
        output = subprocess.check_output(
            ["udevadm", "info", devicePath],
            stderr = subprocess.DEVNULL,
            universal_newlines=True)

        fields = output.split('\n')
    except subprocess.CalledProcessError as e:
        if e.returncode is 4:
            print("no udevadm info for %s" % devicePath, file=sys.stderr)
            return {}
        else:
            raise e

    ret = {}

    # for each line "E: KEY=VALUE"
    for field in fields:
        # remove the first three characters
        field = field[3:]

        kvPair = field.split('=')

        if len(kvPair) > 1:
            ret[kvPair[0]] = kvPair[1]

    return ret

# get list of filesystem paths matching pattern
# ie /dev/ttyACM* -> [ '/dev/ttyACM0', '/dev/ttyACM1' ]
devices = glob.glob(ARGS.pattern)

# ie for each "filename" in list of filenames
# ex for each device in /dev/serial/by-id/
for device in devices:
    # no match for input search pattern
    if not len(device):
        continue

    deviceInfo = {}
    udevInfo = getUdevInfo(device)

    # nothing of interest
    if not len(udevInfo):
        continue

    # udev attributes
    deviceInfo["udev-info"] = udevInfo
    
    # search for known device attributes from list of known devices
    for familiarDevice in companionFamiliarDevices:
        match = True
        # list of identifying udev attributes for this device
        for identifier in companionFamiliarDevices[familiarDevice]:
            try:
                # see if this device has the attribute/value we are looking for
                if udevInfo[identifier] != companionFamiliarDevices[familiarDevice][identifier]:
                    match = False
                    break # all identifiers must match
            except KeyError as e:
                match = False
                break # all identifiers must match
        if match:
            deviceInfo["companion-device"] = familiarDevice
            break # we know what device this is

    ret["devices"].append(deviceInfo)

print(json.dumps(ret, indent = ARGS.indent))
