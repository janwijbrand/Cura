# Copyright (c) 2016 Ultimaker B.V.
# Cura is released under the terms of the AGPLv3 or higher.

import configparser #To read config files.
import io #To write config files to strings as if they were files.

import UM.VersionUpgrade

##  Creates a new profile instance by parsing a serialised profile in version 1
#   of the file format.
#
#   \param serialised The serialised form of a profile in version 1.
#   \return A profile instance, or None if the file format is incorrect.
def importFrom(serialised):
    try:
        return Profile(serialised)
    except (configparser.Error, UM.VersionUpgrade.FormatException, UM.VersionUpgrade.InvalidVersionException):
        return None

##  A representation of a profile used as intermediary form for conversion from
#   one format to the other.
class Profile:
    ##  Reads version 1 of the file format, storing it in memory.
    #
    #   \param serialised A string with the contents of a machine instance file.
    def __init__(self, serialised):
        parser = configparser.ConfigParser(interpolation = None)
        parser.read_string(serialised)

        # Check correctness.
        if not parser.has_section("general"):
            raise UM.VersionUpgrade.FormatException("No \"general\" section.")
        if not parser.has_option("general", "version"):
            raise UM.VersionUpgrade.FormatException("No \"version\" in the \"general\" section.")
        if int(parser.get("general", "version")) != 1: # Hard-coded profile version here. If this number changes the entire function needs to change.
            raise UM.VersionUpgrade.InvalidVersionException("The version of this profile is wrong. It must be 1.")

        # Parse the general section.
        self._name = parser.get("general", "name")
        self._type = parser.get("general", "type", fallback = None)
        if "weight" in parser["general"]:
            self._weight = int(parser.get("general", "weight"))
        else:
            self._weight = None
        self._machine_type_id = parser.get("general", "machine_type", fallback = None)
        self._machine_variant_name = parser.get("general", "machine_variant", fallback = None)
        self._machine_instance_name = parser.get("general", "machine_instance", fallback = None)
        if "material" in parser["general"]:
            self._material_name = parser.get("general", "material")
        elif self._type == "material":
            self._material_name = parser.get("general", "name", fallback = None)
        else:
            self._material_name = None

        # Parse the settings.
        self._settings = {}
        if parser.has_section("settings"):
            for key, value in parser["settings"].items():
                self._settings[key] = value

        # Parse the defaults and the disabled defaults.
        self._changed_settings_defaults = {}
        if parser.has_section("defaults"):
            for key, value in parser["defaults"].items():
                self._changed_settings_defaults[key] = value
        self._disabled_settings_defaults = []
        if parser.has_section("disabled_defaults"):
            disabled_defaults_string = parser.get("disabled_defaults", "values")
            self._disabled_settings_defaults = [item for item in disabled_defaults_string.split(",") if item != ""] # Split by comma.

    ##  Serialises this profile as file format version 2.
    #
    #   \return A serialised form of this profile, serialised in version 2 of
    #   the file format.
    def export(self):
        import VersionUpgrade21to22 # Import here to prevent circular dependencies.

        config = configparser.ConfigParser(interpolation = None)

        config.add_section("general")
        config.set("general", "version", "2") # Hard-coded profile version 2
        config.set("general", "name", self._name)
        if self._type:
            config.set("general", "type", self._type)
        if self._weight:
            config.set("general", "weight", self._weight)
        if self._machine_type_id:
            translated_machine = VersionUpgrade21to22.VersionUpgrade21to22.VersionUpgrade21to22.translatePrinter(self._machine_type_id)
            config.set("general", "definition", translated_machine)
        else:
            config.set("general", "definition", "fdmprinter")
        if self._machine_variant_name:
            config.set("general", "variant", self._machine_variant_name)
        if self._material_name and self._type != "material":
            config.set("general", "material", self._material_name)

        if self._settings:
            VersionUpgrade21to22.VersionUpgrade21to22.VersionUpgrade21to22.translateSettings(self._settings)
            config.add_section("settings")
            for key, value in self._settings.items():
                config.set("settings", key, str(value))

        if self._changed_settings_defaults:
            VersionUpgrade21to22.VersionUpgrade21to22.VersionUpgrade21to22.translateSettings(self._changed_settings_defaults)
            config.add_section("defaults")
            for key, value in self._changed_settings_defaults.items():
                config.set("defaults", key, str(value))

        if self._disabled_settings_defaults:
            disabled_settings_defaults = [VersionUpgrade21to22.VersionUpgrade21to22.VersionUpgrade21to22.translateSettingName(setting)
                                          for setting in self._disabled_settings_defaults]
            config.add_section("disabled_defaults")
            disabled_defaults_string = str(disabled_settings_defaults[0]) # Must be at least 1 item, otherwise we wouldn't enter this if statement.
            for item in disabled_settings_defaults[1:]:
                disabled_defaults_string += "," + str(item)

        output = io.StringIO()
        config.write(output)
        return output.getvalue()