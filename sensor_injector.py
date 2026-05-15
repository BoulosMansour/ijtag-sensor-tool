import json
import entity_parser
import glob
import os
import re
import logging

PRAGMA_DECLARATION = "-- SENSOR-DECLARATION: "
PRAGMA_INSTANCIATION = "-- SENSOR-INSTANTIATION: "

topLevelEntity = ""
workingDirectory = ""
sensorsDirectory = ""
customComponents = {}
sensors = {}
instances = {}


def getConfig():

    global topLevelEntity, workingDirectory, sensorsDirectory, customComponents, sensors, instances
    with open('config.json', 'r') as f:
        config = json.load(f)

    topLevelEntity = config.get("topLevelEntity", "")
    workingDirectory = config.get("workingDirectory", "")
    sensorsDirectory = config.get("sensorsDirectory", "")
    customComponents = config.get("customComponents", {})
    sensors = config.get("sensors", {})
    instances = config.get("instances", {})

def scanAndInjectSensors():
    """
    Scan all VHDL files in the working directory (excluding the generated
    modified/ and out/ subdirectories), parse them for sensor pragmas, and
    inject the component declarations and instance mappings.
    """
    modifiedDir = os.path.join(workingDirectory, "modified")
    outputDir   = os.path.join(workingDirectory, "out")

    # Glob all VHD files recursively, then exclude our own output directories
    # so that re-running the tool never picks up previously generated files.
    modifiedDirNorm = os.path.normpath(modifiedDir) + os.sep
    outputDirNorm   = os.path.normpath(outputDir)   + os.sep
    allVHDLFiles = [
        f for f in glob.glob(os.path.join(workingDirectory, "**/*.vhd"), recursive=True)
        if not os.path.normpath(f).startswith(modifiedDirNorm)
        and not os.path.normpath(f).startswith(outputDirNorm)
    ]

    # Create or clean the modified directory
    if not os.path.exists(modifiedDir):
        os.makedirs(modifiedDir)
    else:
        for file in os.listdir(modifiedDir):
            os.remove(os.path.join(modifiedDir, file))

    logging.info(f"Found {len(allVHDLFiles)} VHDL files to scan in '{workingDirectory}'")

    for vhdlFile in allVHDLFiles:
        with open(vhdlFile, 'r') as f:
            vhdlContent = f.read()

        if PRAGMA_DECLARATION in vhdlContent:
            logging.info(f"Processing file with sensor pragmas: '{vhdlFile}'")

            # find all pragma declarations in the file and extract the sensor entity name
            declarations = re.findall(rf"{PRAGMA_DECLARATION}\s*(\w+)", vhdlContent)

            # find all pragma instantiations in the file and extract the instance name
            instantiations = re.findall(rf"{PRAGMA_INSTANCIATION}\s*(\w+)", vhdlContent)

            logging.info(f"  Declarations found: {declarations}")
            logging.info(f"  Instantiations found: {instantiations}")

            for instanceName in instantiations:
                if instanceName not in instances:
                    logging.error(f"Instance '{instanceName}' in file '{vhdlFile}' does not match any sensor in config.json")
                    continue
                sensorInfo = instances[instanceName]

                sensorPath = sensors.get(sensorInfo.get("sensor_name", ""), {}).get("vhdl_file_path", "")
                if not sensorPath:
                    logging.error(f"Sensor '{sensorInfo.get('sensor_name', '')}' for instance '{instanceName}' in file '{vhdlFile}' does not have a 'vhdl_file_path' defined in config.json")
                    continue
                sensorEntity, _, _ = entity_parser.entityParser(os.path.join(sensorsDirectory, sensorPath))
                if not sensorEntity:
                    logging.error(f"Instance '{instanceName}' in file '{vhdlFile}' does not have a 'component_name' defined in config.json")
                    continue
                if sensorEntity not in declarations:
                    logging.error(f"Instance '{instanceName}' in file '{vhdlFile}' references entity '{sensorEntity}' which does not have a component declaration pragma in the same file")
                    continue

                # support both legacy and current keys in config
                configGenerics = sensorInfo.get("generic_maps", sensorInfo.get("generics", {}))
                configPorts = sensorInfo.get("port_maps", sensorInfo.get("ports", {}))

                # load sensor VHDL and parse ports/generics
                sensorVhdlPath = os.path.join(sensorsDirectory, sensorPath)
                sensorEntityName, sensorPortsList, sensorGenericsList = entity_parser.entityParser(sensorVhdlPath)
                if not sensorPortsList and not sensorGenericsList:
                    logging.error(f"Entity '{sensorEntity}' for instance '{instanceName}' does not have any ports or generics defined in its VHDL file")
                    continue

                if configGenerics and not sensorGenericsList:
                    logging.warning(f"Instance '{instanceName}' in file '{vhdlFile}' has generics defined in config.json but the entity '{sensorEntity}' does not have any generics defined in its VHDL file")

                if configPorts and not sensorPortsList:
                    logging.error(f"Instance '{instanceName}' in file '{vhdlFile}' has ports defined in config.json but the entity '{sensorEntity}' does not have any ports defined in its VHDL file")
                    continue

                # build set of declared port names from the parsed entity
                entityPortNames = {p['name'] for p in sensorPortsList}

                # validate config port names -- report missing names
                badPorts = []
                for cfgPort in configPorts.keys():
                    if cfgPort not in entityPortNames:
                        badPorts.append(cfgPort)
                if badPorts:
                    logging.error(f"Instance '{instanceName}' in file '{vhdlFile}' has ports in config.json that are not present on entity '{sensorEntity}': {badPorts}")
                    continue

                # default any missing entity ports to 'open' mapping
                for p in entityPortNames:
                    if p not in configPorts:
                        configPorts[p] = "open"
                        logging.warning(f"Port '{p}' of instance '{instanceName}' in file '{vhdlFile}' is not defined in config.json. Defaulting to 'open'")

                componentDeclarationContent = entity_parser.generateComponentVHDL(sensorGenericsList, sensorPortsList, sensorEntity)
                instanceMappingContent = entity_parser.generateInstanceMapVHDL(instanceName, sensorEntity, configGenerics, configPorts)

                # Replace the declaration pragma (keyed by entity name, not instance name).
                # Only replace on first encounter — subsequent instances of the same sensor type
                # find the pragma already replaced and skip silently.
                declarationPragma = f"{PRAGMA_DECLARATION}{sensorEntity}"
                if declarationPragma in vhdlContent:
                    vhdlContent = vhdlContent.replace(declarationPragma, componentDeclarationContent)
                    logging.info(f"  Replaced declaration pragma for entity '{sensorEntity}'")

                # Replace the instantiation pragma (keyed by instance name, unique per instance)
                instantiationPragma = f"{PRAGMA_INSTANCIATION}{instanceName}"
                if instantiationPragma in vhdlContent:
                    vhdlContent = vhdlContent.replace(instantiationPragma, instanceMappingContent)
                    logging.info(f"  Replaced instantiation pragma for instance '{instanceName}'")
                else:
                    logging.error(f"Could not find instantiation pragma '{instantiationPragma}' in '{vhdlFile}'")

        # Write the (possibly modified) file into the modified directory
        newFileName = os.path.join(modifiedDir, f"modified_{os.path.basename(vhdlFile)}")
        with open(newFileName, 'w') as f:
            f.write(vhdlContent)
        logging.info(f"Written modified file: '{newFileName}'")

def generateIJTAGTessentScript():
    """
    Generate a Tessent script to integrate the sensors into the design.
    All outputs (this script, Tessent-written design files) are placed in
    the out/ directory inside the working directory.
    """
    outputDir = os.path.join(workingDirectory, "out")
    os.makedirs(outputDir, exist_ok=True)

    scriptContent = ""

    # 1. Initialize Tessent for IJTAG Insertion at the RTL level
    scriptContent += "set_context dft -ijtag\n"
    scriptContent += "set_system_mode setup\n\n"

    # 2. Define the Search Paths for standard libraries and ICL files
    modifiedDirForTcl = os.path.normpath(os.path.join(workingDirectory, "modified")).replace('\\', '/')
    scriptContent += f"set_design_sources -dir {modifiedDirForTcl}\n\n"

    # 3. Read the Leaf-Level ICL Files (The Blueprints)
    for sensorName, sensorInfo in sensors.items():
        iclPath = sensorInfo.get("icl_blueprint_path", "")
        if not iclPath:
            logging.error(f"Sensor '{sensorName}' does not have an 'icl_blueprint_path' defined in config.json")
            continue
        iclFullPath = os.path.normpath(os.path.join(workingDirectory, iclPath)).replace('\\', '/')
        scriptContent += f"read_icl {iclFullPath}\n\n"

    # 4. Read the Hardware Design (VHDL) — all modified files are in the flat modified/ directory
    for vhdlFile in glob.glob(os.path.join(workingDirectory, "modified", "*.vhd")):
        vhdlFileForTcl = os.path.normpath(vhdlFile).replace('\\', '/')
        scriptContent += f"read_vhdl {vhdlFileForTcl}\n"

    scriptContent += "\n"

    # 5. Set the Top-Level Entity
    scriptContent += f"set_current_design {topLevelEntity}\n\n"

    # 6. Transition from setup mode to analysis mode (runs design rule checks internally)
    scriptContent += "set_system_mode analysis\n\n"

    # 7. Define the Target Instances
    for instanceName in instances.keys():
        sensorInfo = instances[instanceName]
        tessentPath = sensorInfo.get("tessent_path", "")
        if not tessentPath:
            logging.warning(f"Instance '{instanceName}' does not have a 'tessent_path' defined in config.json; skipping set_instrument_instances")
            continue
        scriptContent += f"set_instrument_instances -instances {tessentPath}\n"

    # 8. Create the IJTAG Network
    scriptContent += "\ncreate_ijtag_network\n\n"

    # 9. Extract the New Chip-Level ICL
    scriptContent += "extract_icl\n\n"

    # 10. Write the Output Files (Tessent writes these into the same out/ directory)
    outputDirForTcl = os.path.normpath(outputDir).replace('\\', '/')
    scriptContent += f"write_design -output {outputDirForTcl}/injected_design.vhd\n"
    scriptContent += f"write_icl -output {outputDirForTcl}/injected_network.icl\n\n"

    # 11. Finalize the Script
    scriptContent += "puts \"Sensor injection completed successfully!\"\n"

    # Save the TCL script into out/ alongside the other outputs
    scriptFilePath = os.path.join(outputDir, "inject_sensors.tcl")
    with open(scriptFilePath, 'w') as f:
        f.write(scriptContent)
    logging.info(f"Tessent script generated at: '{scriptFilePath}'")
    print(f"Tessent script generated successfully at: {scriptFilePath}")
    return scriptFilePath

if __name__ == "__main__":
    getConfig()

    # Create the output directory first so the log file lands inside it
    outputDir = os.path.join(workingDirectory, "out")
    os.makedirs(outputDir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s',
        filename=os.path.join(outputDir, "sensor_injector.log"),
        filemode='w'
    )

    scanAndInjectSensors()
    generateIJTAGTessentScript()
