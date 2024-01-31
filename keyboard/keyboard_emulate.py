import dbus
import dbus.service
import dbus.mainloop.glib
import keymap
import time
import redis


class BtkStringClient():
    # constants
    KEY_DOWN_TIME = 0.01
    KEY_DELAY = 0.01
    output_stream = "tts_final_decoded_sentence"
    trial_info_stream = 'trial_info'
    r = redis.Redis('192.168.150.2')

    def __init__(self):
        # the structure for a bt keyboard input report (size is 10 bytes)
        self.state = [
            0xA1,  # this is an input report
            0x01,  # Usage report = Keyboard
            # Bit array for Modifier keys
            [0,  # Right GUI - Windows Key
                 0,  # Right ALT
                 0,  # Right Shift
                 0,  # Right Control
                 0,  # Left GUI
                 0,  # Left ALT
                 0,  # Left Shift
                 0],  # Left Control
            0x00,  # Vendor reserved
            0x00,  # rest is space for 6 keys
            0x00,
            0x00,
            0x00,
            0x00,
            0x00]
        self.scancodes = {
            "-": "KEY_MINUS",
            "=": "KEY_EQUAL",
            ";": "KEY_SEMICOLON",
            "'": "KEY_APOSTROPHE",
            "`": "KEY_GRAVE",
            "\\": "KEY_BACKSLASH",
            ",": "KEY_COMMA",
            ".": "KEY_DOT",
            "/": "KEY_SLASH",
            "_": "key_minus",
            "+": "key_equal",
            ":": "key_semicolon",
            "\"": "key_apostrophe",
            "~": "key_grave",
            "|": "key_backslash",
            "<": "key_comma",
            ">": "key_dot",
            "?": "key_slash",
            " ": "KEY_SPACE",
        }

        # connect with the Bluetooth keyboard server
        print("setting up DBus Client")
        self.bus = dbus.SystemBus()
        self.btkservice = self.bus.get_object(
            'org.thanhle.btkbservice', '/org/thanhle/btkbservice')
        self.iface = dbus.Interface(self.btkservice, 'org.thanhle.btkbservice')

    def send_key_state(self):
        """sends a single frame of the current key state to the emulator server"""
        bin_str = ""
        element = self.state[2]
        for bit in element:
            bin_str += str(bit)
        self.iface.send_keys(int(bin_str, 2), self.state[4:10])

    def send_key_down(self, scancode, modifiers):
        """sends a key down event to the server"""
        self.state[2] = modifiers
        self.state[4] = scancode
        self.send_key_state()

    def send_key_up(self):
        """sends a key up event to the server"""
        self.state[4] = 0
        self.send_key_state()

    def send_string(self, string_to_send):
        for c in string_to_send:
            cu = c.upper()
            modifiers = [ 0, 0, 0, 0, 0, 0, 0, 0 ]
            if cu in self.scancodes:
                scantablekey = self.scancodes[cu]
                if scantablekey.islower():
                    modifiers = [ 0, 0, 0, 0, 0, 0, 1, 0 ]
                    scantablekey = scantablekey.upper()
            else:
                if c.isupper():
                    modifiers = [ 0, 0, 0, 0, 0, 0, 1, 0 ]
                scantablekey = "KEY_" + cu

            scancode = keymap.keytable[scantablekey]
            self.send_key_down(scancode, modifiers)
            time.sleep(BtkStringClient.KEY_DOWN_TIME)
            self.send_key_up()
            time.sleep(BtkStringClient.KEY_DELAY)
    
    def run(self):
        while True:

            sentence = self.r.xread(
                {self.output_stream: last_entry_seen}, block=0, count=1
            )
            if len(sentence) > 0:
                last_entry_seen = sentence[0][1][0][0]
                output = sentence[0][1][0][1][b'final_decoded_sentence'].decode() + " "

                trial_info = self.r.xread(
                    {self.trial_info_stream: trial_info_last_entry_seen},
                    block=0,
                    count=1,
                )

                for entry_id, entry in trial_info[0][1]:
                    trial_info_last_entry_seen = entry_id
                    if b'decoded_correctly' in entry:
                        decoded_correctly = int(entry[b'decoded_correctly'].decode())
                    else:
                        decoded_correctly = int(-1)

                # only type correct or mostly correct sentences
                if decoded_correctly in [-1,1,2]:
                    # 0 is INCORRECT
                    # 1 is CORRECT
                    # 2 is MOSTLY CORRECT
                    # -1 is NOT SPECIFIED

                    self.send_string(output)


if __name__ == "__main__":
    node = BtkStringClient()
    node.run()
