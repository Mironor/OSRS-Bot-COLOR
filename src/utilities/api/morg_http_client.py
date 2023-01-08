"""
API utility for MorgHTTPClient socket plugin.

Item IDs: https://www.runelocus.com/tools/osrs-item-id-list/
"""
import time
from typing import List, Tuple, Union

import requests
from deprecated import deprecated
from requests.exceptions import ConnectionError


class SocketError(Exception):
    def __init__(self, error_message: str, endpoint: str):
        self.__error_message = error_message
        self.__endpoint = endpoint
        super().__init__(self.get_error())

    def get_error(self):
        return f"{self.__error_message} endpoint: '{self.__endpoint}'"


class MorgHTTPSocket:
    # TODO: ID/NPC ID/Object ID conversion function/dict to get the readable name of an object

    def __init__(self):
        self.base_endpoint = "http://localhost:8081/"

        self.inv_endpoint = "inv"
        self.stats_endpoint = "stats"
        self.equip_endpoint = "equip"
        self.events_endpoint = "events"

        self.timeout = 1

    def __do_get(self, endpoint: str) -> dict:
        """
        Args:
                endpoint: One of either "inv", "stats", "equip", "events"
        Returns:
                All JSON data from the endpoint as a dict.
        Raises:
                SocketError: If the endpoint is not valid or the server is not running.
        """
        try:
            response = requests.get(f"{self.base_endpoint}{endpoint}", timeout=self.timeout)
        except ConnectionError as e:
            raise SocketError("Unable to reach socket", endpoint) from e

        if response.status_code != 200:
            if response.status_code == 204:
                raise SocketError(
                    f"Endpoint not available, consider adding pauses between API calls. Status code: {response.status_code}",
                    endpoint,
                )
            else:
                raise SocketError(
                    f"Unable to reach socket. Status code: {response.status_code}",
                    endpoint,
                )

        return response.json()

    def test_endpoints(self) -> bool:
        """
        Ensures all endpoints are working correctly to avoid errors happening when any method is called.
        Returns:
                True if successful, False otherwise.
        """
        for i in list(self.__dict__.values())[1:-1]:  # Look away
            try:
                self.__do_get(endpoint=i)
            except SocketError as e:
                print(e)
                print(f"Endpoint '{i}' is not working.")
                return False
        return True

    def get_hitpoints(self) -> Tuple[int, int]:
        """
        Fetches the current and maximum hitpoints of the player.
        Returns:
                A Tuple(current_hitpoints, maximum_hitpoints).
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        hitpoints_data = data["health"]
        cur_hp, max_hp = hitpoints_data.split("/")  # hitpoints_data example = "21/21"
        return int(cur_hp), int(max_hp)

    def get_run_energy(self) -> int:
        """
        Fetches the current run energy of the player.
        Returns:
                An int representing the current run energy.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return int(data["run energy"])

    def get_animation(self) -> int:
        """
        Fetches the current animation the actor is performing.
        Returns:
                An int representing the current animation.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return int(data["animation"])

    def get_animation_id(self) -> int:
        """
        Fetches the current animation frame ID the actor is using. Useful for checking if the player is doing
        a particular action.
        Returns:
                An int representing the current animation ID.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return int(data["animation pose"])

    def get_is_player_idle(self, poll_seconds=1) -> bool:
        """
        Checks if the player is doing an idle animation.
        Args:
                poll_seconds: The number of seconds to poll for an idle animation.
        Returns:
                True if the player is idle, False otherwise..
        """
        start_time = time.time()
        while time.time() - start_time < poll_seconds:
            data = self.__do_get(endpoint=self.events_endpoint)
            if data["animation"] != -1 or data["animation pose"] not in [808, 813]:
                return False
        return True

    def get_skill_level(self, skill: str) -> Union[int, None]:
        # sourcery skip: class-extract-method
        """
        Gets level of inputted skill.
        Args:
                skill: the name of the skill (not case sensitive)
        Returns:
                The level of the skill as an int, or None if an error occurred.
        """
        data = self.__do_get(endpoint=self.stats_endpoint)
        try:
            level = next(int(i["level"]) for i in data[1:] if i["stat"] == skill)
        except StopIteration:
            print(f"Invalid stat name: {skill}. Consider using the `stat_names` utility.")
            return None
        return level

    def get_skill_xp(self, skill: str) -> Union[int, None]:
        """
        Gets the total xp of a skill.
        Args:
                skill: the name of the skill (not case sensitive)
        Returns:
                The total xp of the skill as an int, or None if an error occurred.
        """
        data = self.__do_get(endpoint=self.stats_endpoint)
        try:
            total_xp = next(int(i["xp"]) for i in data[1:] if i["stat"] == skill)
        except StopIteration:
            print(f"Invalid stat name: {skill}. Consider using the `stat_names` utility.")
            return None
        return total_xp

    def get_skill_xp_gained(self, skill: str) -> Union[int, None]:
        """
        Gets the xp gained of a skill. The tracker begins at 0 on client startup.
        Args:
                skill: the name of the skill (not case sensitive)
        Returns:
                The xp gained of the skill as an int, or None if an error occurred.
        """
        data = self.__do_get(endpoint=self.stats_endpoint)
        try:
            xp_gained = next(int(i["xp gained"]) for i in data[1:] if i["stat"] == skill)
        except StopIteration:
            print(f"Invalid stat name: {skill}. Consider using the `stat_names` utility.")
            return None
        return xp_gained

    def wait_til_gained_xp(self, skill: str, timeout: int = 10) -> Union[int, None]:
        """
        Waits until the player has gained xp in the inputted skill.
        Args:
                skill: the name of the skill (not case sensitive).
                timeout: the maximum amount of time to wait for xp gain (seconds).
        Returns:
                The xp gained of the skill as an int, or None if no XP was gained during the timeout.
        """
        starting_xp = self.get_skill_xp(skill)
        if starting_xp is None:
            print("Failed to get starting xp.")
            return None

        stop_time = time.time() + timeout
        while time.time() < stop_time:
            data = self.__do_get(endpoint=self.stats_endpoint)
            final_xp = next(int(i["xp"]) for i in data[1:] if i["stat"] == skill)
            if final_xp > starting_xp:
                return final_xp
            time.sleep(0.2)
        return None

    def get_game_tick(self) -> int:
        """
        Fetches game tick number.
        Returns:
                An int representing the current game tick.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return int(data["game tick"])

    def get_player_position(self) -> Tuple[int, int, int]:
        """
        Fetches the world point of a player.
        Returns:
                A tuple of ints representing the player's world point (x, y, z).
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return (
            int(data["worldPoint"]["x"]),
            int(data["worldPoint"]["y"]),
            int(data["worldPoint"]["plane"]),
        )

    def get_player_region_data(self) -> Tuple[int, int, int]:
        """
        Fetches region data of a player's position.
        Returns:
                A tuple of ints representing the player's region data (region_x, region_y, region_ID).
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return (
            int(data["worldPoint"]["regionX"]),
            int(data["worldPoint"]["regionY"]),
            int(data["worldPoint"]["regionID"]),
        )

    def get_camera_position(self) -> dict:
        """
        Fetches the position of a player's camera.
        Returns:
                A dict containing the player's camera position {yaw, pitch, x, y, z, x2, y2, z2},
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return data["camera"]

    def get_mouse_position(self) -> Tuple[int, int]:
        """
        Fetches the position of a player's mouse.
        Returns:
                A tuple of ints representing the player's mouse position (x, y).
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return int(data["mouse"]["x"]), int(data["mouse"]["y"])

    def get_interaction_code(self) -> str:
        """
        Fetches the interacting code of the current interaction. (Use case unknown)
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return data["interacting code"]

    def get_is_in_combat(self) -> bool:
        """
        Determines if the player is in combat.
        Returns:
                True if the player is in combat, False if not.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        res = data["npc name"]
        return res != "null"

    @deprecated(reason="This method seems to return unreliable values for the NPC's HP.")
    def get_npc_hitpoints(self) -> Union[int, None]:
        """
        Fetches the HP of the NPC currently targetted.
        TODO: Result seems to be multiplied by 6...?
        Returns:
                An int representing the NPC's HP, or None if an error occurred.
                If no NPC is in combat, returns 0.
        """
        data = self.__do_get(endpoint=self.events_endpoint)
        return int(data["npc health "])

    def get_if_item_in_inv(self, item_id: int) -> bool:
        """
        Checks if an item is in the inventory or not
        Args:
                item_id: the id of the item to check for
        Returns:
                True if the item is in the inventory, False if not.
        """
        data = self.__do_get(endpoint=self.inv_endpoint)
        return any(inventory_slot["id"] == item_id for inventory_slot in data)

    def get_inv_item_indices(self, item_id: Union[List[int], int]) -> list:
        """
        For the given item ID(s), returns a list of inventory slot indexes that the item exists in.
        Useful for locating items you do not want to drop.
        Args:
                item_id: The item ID to search for (an single ID, or list of IDs).
        Returns:
                A list of inventory slot indexes that the item(s) exists in.
        """
        data = self.__do_get(endpoint=self.inv_endpoint)
        if isinstance(item_id, int):
            return [i for i, inventory_slot in enumerate(data) if inventory_slot["id"] == item_id]
        elif isinstance(item_id, list):
            return [i for i, inventory_slot in enumerate(data) if inventory_slot["id"] in item_id]

    def get_inv_item_stack_amount(self, item_id: Union[int, List[int]]) -> int:
        """
        For the given item ID, returns the total amount of that item in your inventory.
        This is only useful for items that stack (e.g. coins, runes, etc).
        Args:
            id: The item ID to search for. If a list is passed, the first matching item will be used.
                This is useful for items that have multiple IDs (e.g. coins, coin pouches, etc.).
        Returns:
            The total amount of that item in your inventory.
        """
        data = self.__do_get(endpoint=self.inv_endpoint)
        if isinstance(item_id, int):
            item_id = [item_id]
        if result := next((item for item in data if item["id"] in item_id), None):
            return int(result["quantity"])
        return 0

    def get_player_equipment(self) -> Union[List[int], None]:
        """
        Currently just gets the ID of the equipment until there is an easier way to convert ID to readable name
        -1 = nothing
        Returns: [helmet, cape, neck, weapon, chest, shield, legs, gloves, boots, ring, arrow]

        NOTE: Socket may be bugged with -1's in the middle of the data even all equipment slots are filled
        """
        data = self.__do_get(endpoint=self.equip_endpoint)
        return [equipment_id["id"] for equipment_id in data]

    def convert_player_position_to_pixels(self):
        """
        Convert a world point into coordinate where to click with the mouse to make it possible to move via the socket.
        TODO: Implement.
        """
        pass


# sourcery skip: remove-redundant-if
if __name__ == "__main__":
    api = MorgHTTPSocket()

    id_logs = 1511
    id_bones = 526

    # Note: Making API calls in succession too quickly can result in issues
    while True:
        # Player Data
        if True:
            # Example of safely getting player data
            if hp := api.get_hitpoints():
                print(f"Current HP: {hp[0]}")
                print(f"Max HP: {hp[1]}")

            print(f"Run Energy: {api.get_run_energy()}")
            print(f"get_animation(): {api.get_animation()}")
            print(f"get_animation_id(): {api.get_animation_id()}")
            print(f"Is player idle: {api.get_is_player_idle()}")

        # World Data
        if True:
            print(f"Game tick: {api.get_game_tick()}")
            print(f"Player position: {api.get_player_position()}")
            print(f"Player region data: {api.get_player_region_data()}")
            print(f"Mouse position: {api.get_mouse_position()}")
            # print(f"get_interaction_code(): {api.get_interaction_code()}")
            print(f"Is in combat?: {api.get_is_in_combat()}")
            print(f"get_npc_health(): {api.get_npc_hitpoints()}")

        # Inventory Data
        if True:
            print(f"Are logs in inventory?: {api.get_if_item_in_inv(item_id=1511)}")
            print(f"Find amount of change in inv: {api.get_inv_item_stack_amount(item_id=995)}")
            print(f"Get position of all bones in inv: {api.get_inv_item_indices(item_id=[526])}")

        # Wait for XP to change
        if False:
            print(f"WC Level: {api.get_skill_level('Woodcutting')}")
            print(f"WC XP: {api.get_skill_xp('Woodcutting')}")
            print(f"WC XP Gained: {api.get_skill_xp_gained('Woodcutting')}")
            print("---waiting for wc xp to be gained---")
            if api.wait_til_gained_xp(skill="Woodcutting", timeout=10):
                print("Gained xp!")
            else:
                print("No xp gained.")

        time.sleep(2)

        print("\n--------------------------\n")
