import pymem
from pynput import keyboard

from src import ui, exceptions
from src.logger import Logger


class Listener(keyboard.Listener):
    """ Listener for key events
    """

    def __init__(self, references):
        """ references
        :param references: the references
        """
        super().__init__(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.references = references

        # References
        self.gateway = references["Gateway"]
        self.storage = references["Storage"]
        self.features = self.storage.features

        self.keys = {}
        self.pressed = {}

        self.references.update({"Listener": self})

    @staticmethod
    def unctrl(c: int) -> str:
        """ Convert hex c to ascii characters / control characters
        :param int c: the character value
        """
        # Control character
        if c <= 0x1f:
            return chr(c + 0x40)

        else:
            return chr(c)

    def register_keys(self):
        """ Register keys
        """
        done = set()
        self.keys = {}

        for feature_id, feature_value in self.features.data.items():

            # Duplicates
            # For listener?
            if feature_id not in done and self.storage.features.presets[feature_id]["g"].listener and feature_value["key"]:
                feature_id_list = (list(feature_id) if feature_value["available"] else []) + \
                                  [x for x in feature_value["children"] if self.features[x]["available"]]

                done.update(feature_id_list)

                # Already exists?
                if feature_value["key"] in self.keys:
                    self.keys[feature_value["key"].lower()].extend(feature_id_list)

                else:
                    self.keys.update({feature_value["key"].lower(): feature_id_list})

    def inner(self, key, index: str, on_press: bool):
        """ To shorten up code, for register_keys
        :param key: key from pynput
        :param index: new setting index
        :param on_press: (bool) if from on press
        """
        try:
            # Normalize the key code
            if isinstance(key, keyboard.KeyCode):
                code = self.unctrl(key.vk).lower()

                # Key exists?
                if code in self.keys:

                    # First press?
                    if (code in self.pressed) is not on_press or self.pressed[code] is not on_press:
                        self.pressed.update({code: on_press})

                        # Do memory stuff
                        for feature_id in self.keys[code]:
                            feature_value = self.features[feature_id]

                            # Enabled?
                            if not feature_value["enabled"]:
                                continue

                            try:
                                self.gateway.write_address(feature_id, feature_value["settings"][index])

                            # Minecraft was closed
                            except (pymem.exception.MemoryWriteError, pymem.exception.ProcessError):
                                self.gateway.close_process()
                                self.gateway.status_check()

                                # Alert user
                                Logger.log("Minecraft was closed!")
                                ui.queue_alert_message(self.references, "Minecraft was closed!", warning=True)
                                self.references["Root"].bell()
                                self.references["Root"].start_button_var.set("Start")

                                return self.stop()

        except Exception:
            exceptions.handle_error(self.references)

    def on_press(self, key: keyboard.KeyCode):
        """ On press event
        :param key: the key code
        """
        self.inner(key, "after", True)

    def on_release(self, key: keyboard.KeyCode):
        """ On release event
        :param key: the key code
        """
        self.inner(key, "before", False)
