# Python 2.7
from __future__ import print_function

import random
from ConfigParser import SafeConfigParser
from lib import Leap
from math import pi
import visual as vs


def save_settings(settings_file, width, height):
    parser = SafeConfigParser()
    parser.add_section("Display")
    parser.set("Display", "width", str(width))
    parser.set("Display", "height", str(height))

    with open(settings_file, "w") as f:
        parser.write(f)


def load_settings(settings_file):
    # Use these defaults if the settings file is missing or doesn't contain the options
    width = 1024
    height = 720

    parser = SafeConfigParser()
    found = parser.read(settings_file)
    if found and parser.has_section("Display"):
        if parser.has_option("Display", "width"):
            width = parser.getint("Display", "width")
        if parser.has_option("Display", "height"):
            height = parser.getint("Display", "height")
    else:
        save_settings(settings_file, width, height)

    return width, height


def setup():
    settings_file = "settings.ini"
    width, height = load_settings(settings_file)

    # VPython Setup
    win = vs.window(width=width, height=height, menus=False, title="Leap Motion")
    scene = vs.display(window=win, width=width, height=height)

    # Camera
    scene.center = (3, 5, 5)
    scene.forward = (0, -0.18, -1)
    scene.range = 8
    scene.fov = pi/5
    # scene.userspin = False
    # scene.userzoom = False

    scene.ambient = vs.color.gray(0.25)
    scene.lights = [vs.distant_light(direction=(0.8, 0.2, 1), color=vs.color.gray(0.4)),
                    vs.distant_light(direction=(-0.8, 0.2, 1), color=vs.color.gray(0.4))]


def to_norm_vpython(lm_vector, i_box):
    # Uses the interaction box in a frame to normalise a point
    # returns a VPython vector in the range of [0-10)
    normalized = i_box.normalize_point(lm_vector)
    return vs.vector(normalized.x, normalized.y, normalized.z)*10


def create_open_box(dimensions, pos=(0, 0, 0), color=vs.color.gray(0.8),
                    material=vs.materials.rough, frame=None, middle=True):
    x, y, z = pos  # Position of the centre of the box
    width, height, depth = dimensions

    floor = vs.box(pos=(x, y-height/2.0+0.025, z), length=width, height=0.05,
                   width=depth, color=color, material=material, frame=frame)
    back = vs.box(pos=(x, y, z-depth/2.0+0.025), length=width, height=height,
                  width=0.05, color=color, material=material, frame=frame)
    roof = vs.box(pos=(x, y+height/2.0-0.025, z), length=width, height=0.05,
                  width=depth, color=color, material=material, frame=frame)
    left = vs.box(pos=(x-width/2.0+0.025, y, z), length=0.05, height=height,
                  width=depth, color=color, material=material, frame=frame)
    right = vs.box(pos=(x+width/2.0-0.025, y, z), length=0.05, height=height,
                   width=depth, color=color, material=material, frame=frame)
    if middle:
        middle = vs.box(pos=(x, y, z), length=width, height=0.05,
                        width=depth, color=color, material=material, frame=frame)

        return [floor, back, roof, left, right, middle]
    return [floor, back, roof, left, right]


class Button(vs.frame):
    def __init__(self, pos, label, on_press):
        super(Button, self).__init__(pos=pos)

        self.on_press = on_press
        self.box = vs.box(length=2, height=0.5, width=0.3, color=vs.color.white, frame=self)
        self.label = vs.text(pos=(0, -0.15, 0), text=str(label), height=0.3, align="center",
                             color=vs.color.green, font="monospace", frame=self)

        # Extended bounding box
        self.max_x = self.box.length/2.0 + 0.5
        self.max_y = self.box.height/2.0 + 0.7
        self.max_z = self.box.width/2.0 + 1

    def collision(self, pos):
        local_pos = self.world_to_frame(pos)

        if -self.max_x < local_pos.x < self.max_x and \
           -self.max_y < local_pos.y < self.max_y and \
           -self.max_z < local_pos.z < self.max_z:
            return True
        else:
            return False


class VariableBox(vs.frame):
    def __init__(self, pos, label):
        super(VariableBox, self).__init__(pos=pos)

        self.size = 1.6
        self.half_size = self.size/2.0
        text_height = 0.3

        self.label = label
        self.value = random.randint(10, 20)

        # Container box
        self.box = create_open_box((self.size, self.size, 0.6), color=vs.color.red, frame=self)

        self.code = vs.text(height=0.4, align="left", color=vs.color.green, font="monospace")

        # Labels containing the label and value text
        self.label_text = vs.text(text=str(self.label), height=text_height, align="center",
                                  color=vs.color.green, font="monospace", frame=self)
        self.label_text.pos = (0, -self.half_size/2.0 - text_height/2.0, 0)

        self.value_text = vs.text(height=text_height, align="center",
                                  color=vs.color.green, font="monospace", frame=self)
        self.value_text.pos = (0, self.half_size/2.0 - text_height/2.0, 0)

        self.set_value(self.value, None, 0)

        # Arrow that defines what the value of the label is
        self.arrow = vs.arrow(shaftwidth=0.1, frame=self)
        self.set_arrow_pos()
        self.connected_to = None
        self.connected_to_this = []

    def set_value(self, value, label, to_type):
        self.value = value

        if to_type is 0:
            # Value assignment
            if label is not None:
                self.value_text.text = str(self.value)
                self.code.text = "int " + str(self.label) + " = " + str(label)
            else:
                self.value_text.text = str(self.value)
                self.code.text = "int " + str(self.label) + " = " + str(self.value)
        elif to_type is 1:
            # Address assignment
            self.value_text.text = hex(self.value)
            self.code.text = "int* " + str(self.label) + " = &" + str(label)
        elif to_type is 2:
            # Dereference assignment
            self.value_text.text = str(self.value)
            self.code.text = "int " + str(self.label) + " = *" + str(label)

    def intersect_pos(self, pos, limit=False):
        # Finds the intersection point on the box of a line from the center of the box to the given pos
        rel_pos = self.world_to_frame(pos)

        if limit:
            rel_pos.y = min(rel_pos.y, 0)
        factor = self.half_size / max(abs(rel_pos.x), abs(rel_pos.y))
        intersect_pos = vs.vector(rel_pos * factor)
        intersect_pos.z = 0

        return self.frame_to_world(intersect_pos)

    def get_arrow_pos(self):
        # Returns the position of the tip of the arrow in world coords
        return self.frame_to_world(self.arrow.pos + self.arrow.axis)

    def set_arrow_pos(self, pos=None):
        # Sets the position of the tip of the arrow from world coords
        if pos:
            intersect_pos = self.world_to_frame(self.intersect_pos(pos))

            rel_pos = self.world_to_frame(pos)
            self.arrow.pos = intersect_pos
            self.arrow.axis = rel_pos - self.arrow.pos
        else:
            # Default pos
            self.arrow.pos = (0, self.half_size, 0)
            self.arrow.axis = (0, 0.6, 0)

    def update_box(self, new_pos):
        # arrow_pos = self.get_arrow_pos()
        self.pos = new_pos
        # Update arrow pos after moving the box
        if self.connected_to:
            self.set_arrow_pos(self.connected_to.intersect_pos(self.pos, limit=True))
        for box in self.connected_to_this:
            box.set_arrow_pos(self.intersect_pos(box.pos, limit=True))

    def drop_arrow(self, other_object=None):
        # If dropped onto value or empty space snap back to default pos
        if other_object:
            # TODO: add action to trigger dereference
            if self.get_arrow_pos().y > other_object.pos.y:
                # Value assignment
                if self.connected_to:
                    if self in self.connected_to.connected_to_this:
                        self.connected_to.connected_to_this.remove(self)
                    self.connected_to = None
                self.set_value(other_object.value, other_object.label, to_type=0)
                self.set_arrow_pos()
            else:
                # Address assignment
                self.connected_to = other_object
                other_object.connected_to_this.append(self)
                self.set_value(0x01000 + 4 * (ord(other_object.label) - ord("i")),
                               other_object.label, to_type=1)
                self.set_arrow_pos(self.connected_to.intersect_pos(self.pos, limit=True))
        else:
            if self.connected_to:
                if self in self.connected_to.connected_to_this:
                    self.connected_to.connected_to_this.remove(self)
                self.connected_to = None
            self.set_value(random.randint(10, 20), None, to_type=0)
            self.set_arrow_pos()

    def delete(self):
        self.visible = False
        self.code.visible = False
        if self.connected_to:
            self.drop_arrow()
        for item in self.connected_to_this:
            item.drop_arrow()


class Hand:
    def __init__(self, controller, color):
        self.pinching = False
        self.grabbed_object = None
        self.grabbed_arrow = False

        self.pinch_trigger_strength = 0.9
        self.pinch_distance = 0.6

        self.controller = controller

        starting_pos = (0, 0, 20)  # Start behind the camera
        self.palm = vs.sphere(pos=starting_pos, radius=0.3, color=color)
        self.fingers = [[vs.sphere(pos=starting_pos, radius=0.2, color=color),
                         vs.sphere(pos=starting_pos, radius=0.15, color=color)] for _ in xrange(5)]
        self.bones = [[vs.cylinder(pos=starting_pos, radius=0.1, color=color),
                       vs.cylinder(pos=starting_pos, radius=0.1, color=color)] for _ in xrange(5)]

    def update_pos(self, hand_frame):
        # Hand position with smoothing
        frames = 4

        count = 0
        average = Leap.Vector()
        for j in xrange(frames):
            hand_from_frame = self.controller.frame(j).hand(hand_frame.id)
            if hand_from_frame.is_valid:
                average += hand_from_frame.palm_position
                count += 1
        if count > 0:
            self.palm.pos = to_norm_vpython(average/count, hand_frame.frame.interaction_box)

        # Finger position with smoothing
        for i in xrange(5):
            count = 0
            average_tip = Leap.Vector()
            average_pip = Leap.Vector()
            finger_to_average = hand_frame.fingers[i]
            for j in xrange(frames):
                finger_from_frame = self.controller.frame(j).finger(finger_to_average.id)
                if finger_from_frame.is_valid:
                    average_tip += finger_from_frame.tip_position
                    average_pip += finger_from_frame.bone(Leap.Bone.TYPE_PROXIMAL).center
                    count += 1
            if count > 0:
                average_tip = to_norm_vpython(average_tip/count, hand_frame.frame.interaction_box)
                average_pip = to_norm_vpython(average_pip/count, hand_frame.frame.interaction_box)

                self.fingers[i][0].pos = average_tip
                self.fingers[i][1].pos = average_pip
                self.bones[i][0].pos = average_pip
                self.bones[i][0].axis = average_tip - average_pip
                self.bones[i][1].pos = self.palm.pos
                self.bones[i][1].axis = average_pip - self.palm.pos

    def update_pinch(self, hand_frame, grabbable_objects):
        # Thumb tip is the pinch position.
        thumb_tip = self.fingers[0][0].pos

        if hand_frame.pinch_strength > self.pinch_trigger_strength:
            # Only trigger pinch if not already pinching
            if not self.pinching:
                # Pinched
                self.pinching = True
                # Check if we pinched a movable object and grab the closest one.
                distance = vs.vector(self.pinch_distance, 0.0, 0.0)

                for grabbable_object in grabbable_objects.itervalues():
                    # Check box
                    new_distance = thumb_tip - grabbable_object.pos
                    if new_distance.mag2 < distance.mag2:
                        self.grabbed_object = grabbable_object
                        self.grabbed_arrow = False
                        distance = new_distance
                    # Check the arrow tip
                    new_distance = thumb_tip - grabbable_object.get_arrow_pos()
                    if new_distance.mag2 < distance.mag2:
                        self.grabbed_object = grabbable_object
                        self.grabbed_arrow = True
                        distance = new_distance
        else:
            # Released
            self.pinching = False
            # If released arrow figure out if it was dropped onto another object
            if self.grabbed_object and self.grabbed_arrow:
                arrow_pos = self.grabbed_object.get_arrow_pos()
                for box in grabbable_objects.itervalues():
                    # Check arrow position against an approximate sphere around the other objects
                    if box is not self.grabbed_object and vs.mag(box.pos-arrow_pos) < box.half_size*1.1:
                        self.grabbed_object.drop_arrow(box)
                        break
                else:
                    self.grabbed_object.drop_arrow()
            self.grabbed_object = None

        # Move grabbed object
        if self.grabbed_object:
            # Still pinched
            if self.grabbed_arrow:
                self.grabbed_object.set_arrow_pos(thumb_tip)
            elif 0.1 < thumb_tip.x < 9.9 and 0.1 < thumb_tip.y < 9.9 and 0.1 < thumb_tip.z < 9.9:
                self.grabbed_object.update_box(thumb_tip)
            else:
                # remove the object if close to the border
                self.grabbed_object.delete()
                try:
                    del grabbable_objects[self.grabbed_object.label]
                except KeyError:
                    pass
                self.grabbed_object = None

                # Reorder code lines
                for i, key in enumerate(sorted(grabbable_objects.keys())):
                    grabbable_objects[key].code.pos = (-5, 8.4-i*0.7, 3)


class Game:
    def __init__(self):
        self.exit = False

        # Code box
        create_open_box((5, 10, 0.6), pos=(-3, 5, 3), color=vs.color.gray(0.35), middle=False)
        vs.text(text="Code:", pos=(-5, 9.2, 3), height=0.45, align="left", color=vs.color.green, font="monospace")

        self.variables = {}
        self.add_var(pos=(2, 7, 3))
        self.add_var(pos=(8, 7, 3))

        self.buttons = [Button((1, 1, 3), "Add Var", self.add_var),
                        Button((9, 1, 3), "Exit", vs.exit)]

        # Leap setup
        self.controller = Leap.Controller()
        self.controller.enable_gesture(Leap.Gesture.TYPE_SCREEN_TAP)
        self.controller.config.set("Gesture.ScreenTap.MinForwardVelocity", 10.0)
        self.controller.config.set("Gesture.ScreenTap.HistorySeconds", 0.8)
        self.controller.config.set("Gesture.ScreenTap.MinDistance", 0.7)
        self.controller.config.save()

        self.last_frame_id = 0

        self.left_hand = Hand(self.controller, vs.color.green)
        self.right_hand = Hand(self.controller, vs.color.red)

    def update(self):
        lm_frame = self.controller.frame()
        for hand_frame in lm_frame.hands:
            if hand_frame.is_left:
                self.left_hand.update_pos(hand_frame)
                self.left_hand.update_pinch(hand_frame, self.variables)
            elif hand_frame.is_right:
                self.right_hand.update_pos(hand_frame)
                self.right_hand.update_pinch(hand_frame, self.variables)

        # Check for tap gestures on UI elements on any frames that haven't already been processed
        i = 0
        while i < 5:
            # If frame is not valid or has already been processed stop
            frame = self.controller.frame(i)
            if not frame.is_valid or frame.id == self.last_frame_id:
                break

            for gesture in frame.gestures():
                if gesture.type is Leap.Gesture.TYPE_SCREEN_TAP:
                    print("Tap")
                    screen_tap = Leap.ScreenTapGesture(gesture)
                    tap_pos = to_norm_vpython(screen_tap.position, frame.interaction_box)

                    for button in self.buttons:
                        if button.collision(tap_pos):
                            print("Button tap")
                            button.on_press()
                            break
            i += 1

        self.last_frame_id = lm_frame.id

    def add_var(self, pos=(5, 5, 3)):
        # Add the next free variable to the list
        # starts at 'i' and stops at 't' (11 characters from 'i')

        i = 0
        while i < 12 and chr(ord("i")+i) in self.variables:
            i += 1

        # Don't add a var if we have run out of space
        if i < 12:
            self.variables[chr(ord("i")+i)] = (VariableBox(pos, chr(ord("i")+i)))

            # Reorder code lines
            for i, key in enumerate(sorted(self.variables.keys())):
                self.variables[key].code.pos = (-5, 8.4-i*0.7, 3)


def main():
    setup()

    game = Game()

    # Wait for the Leap Motion controller to register as connected
    while not game.controller.is_connected:
        vs.sleep(0.1)

    print("Leap Motion Connected")

    # # Main game loop # #
    while not game.exit:
        # Limit the game loop to running 30 times per second
        vs.rate(30)

        game.update()


if __name__ == '__main__':
    main()
