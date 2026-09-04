import pygame
import math
import random

HEIGHT= 800
WIDTH= 1200

FPS= 60

LANE_WIDTH= 100
ROAD_WIDTH= LANE_WIDTH * 2

CENTER_X= WIDTH // 2
CENTER_Y= HEIGHT // 2

INTERSECTION_HALF = ROAD_WIDTH // 2

BLACK= (0,0,0)
WHITE= (255,255,255)
RED= (250,10,10)
GREEN= (10,250,10)
YELLOW= (255,255,0)
ROAD_LINE= (211,211,211)
BACKGROUND_COLOR= (169,169,169)
LANE_LINE_COLOR= (192,192,192)
STOP_LINE_COLOR= (255,0,127)

CAR_LENGTH= 30
CAR_WIDTH= 20
CAR_SPEED= 120.0
CAR_ACCELERATION= 180.0
CAR_DECELERATION= 250.0
MIN_CAR_GAP= 40
CAR_COLORS = [
    (50, 120, 220),
    (220, 80, 70),
    (230, 170, 50),
    (120, 80, 200),
    (50, 180, 170),
    (220, 120, 50),
]

SPAWN_INTERVAL= 0.5

NS_LEFT_TIME = 8.8
NS_THROUGH_TIME = 8.0
EW_LEFT_TIME = 4.0
EW_THROUGH_TIME = 4.0
YELLOW_TIME = 3.0
STOP_DISTANCE = 35

NORTH= "north"
SOUTH= "south"
EAST= "east"
WEST= "west"

RIGHT = "right"
LEFT = "left"
THROUGH = "through"

APPROACHING= "approaching"
WAITING= "waiting"
CROSSING= "crossing"
TURNING= "turning"
LEAVING= "leaving"


def clamp(value,maximum, minimun):
    return max(min(maximum,value),minimun)

def distance(X1,X2,Y1,Y2):
    return math.sqrt(((X1-X2)**2 ) + ((Y1-Y2)**2))

class Phase :
    def __init__(self,name,duration,allowed_movements):
        self.name= name
        self.duration= duration
        self.allowed_movements= allowed_movements

    def allows(self, approach,movement) :
        return (approach, movement) in self.allowed_movements

class traffic_controller:
    def __init__(self):
        self.Phases=[
            Phase(
                "NS_THROUGH",
                NS_THROUGH_TIME,
                [
                (NORTH,THROUGH),
                (SOUTH,THROUGH),
                (NORTH,RIGHT),
                (SOUTH,RIGHT),
                ]
            ),
            Phase(
                "NS_LEFT",
                NS_LEFT_TIME,
                [
                (NORTH,LEFT),
                (SOUTH,LEFT)
                ]
            ),
            Phase(
                "EW_THROUGH",
                EW_THROUGH_TIME,
                [
                    (WEST,THROUGH),
                    (EAST,THROUGH),
                    (WEST,RIGHT),
                    (EAST,RIGHT),
                ]
            ),
            Phase(
                "EW_LEFT",
                EW_LEFT_TIME,
                [
                    (WEST,LEFT),
                    (EAST,LEFT)
                ]
            )       
        ]
        self.current_phase_index=0
        self.phase_timer=0.0
        self.yellow= False
        self.yellow_timer=0.0

    @property
    def current_phase(self):
        return self.Phases[self.current_phase_index]

    def update(self,dt):
        if  self.yellow:
            self.yellow_timer += dt
            if self.yellow_timer >= YELLOW_TIME:
                self.yellow= False
                self.yellow_timer= 0.0
                self.current_phase_index= (self.current_phase_index + 1) % len(self.Phases)
                self.phase_timer=0.0
            return
        self.phase_timer+= dt
        if self.phase_timer >= self.current_phase.duration:
            self.yellow= True
            self.yellow_timer= 0.0

    def get_light_state(self, approach, movement):
        current_phase = self.Phases[self.current_phase_index]

        if (approach, movement) in current_phase.allowed_movements:
            if self.yellow:
                return "YELLOW"
            return "GREEN"
        return "RED"        
    def is_movement_allowed(self,approach,movement):
        if self.yellow:
            return False
        return self.current_phase.allows(approach,movement)

    def get_signal(self,approach,movement):
        if self.yellow:
            if self.current_phase.allows(approach,movement):
                return YELLOW
            return RED
        if self.current_phase.allows(approach,movement):
            return GREEN
        return RED
    def get_remaining_time(self):
        if self.yellow:
            return max(0,YELLOW_TIME - self.yellow_timer)
        return max(0,self.current_phase.duration - self.phase_timer)

class traffic_light:
    def __init__(self,x,y,approach,controller):
        self.x=x
        self.y=y
        self.approach=approach
        self.controller=controller

    def draw(self, screen):
    
            left_signal = self.controller.get_signal(
                self.approach,
                LEFT
            )
    
            through_signal = self.controller.get_signal(
                self.approach,
                THROUGH
            )
            housing = pygame.Rect(
                self.x - 20,
                self.y - 45,
                40,
                90,
            )
    
            pygame.draw.rect(
                screen,
                BLACK,
                housing,
                border_radius=8,
            )
            self.draw_light(
                screen,
                self.x,
                self.y - 20,
                left_signal,
            )
            self.draw_light(
                screen,
                self.x,
                self.y + 20,
                through_signal,
            )
    
    def draw_light(self, screen, x, y, signal):
    
        pygame.draw.circle(
            screen,
            signal,
            (int(x), int(y)),
            10,
        )
def get_bezier_point(p0, p1, p2, t):
    """Calculates (x, y) along a quadratic Bezier curve for t in [0.0, 1.0]."""
    u = 1 - t
    x = u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]
    y = u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]
    return x, y
class Car:
    def __init__(self,approach,movement):
        self.turn_progress = 0.0
        self.p0 = None
        self.p1 = None
        self.p2 = None
        self.approach=approach
        self.movement=movement
        self.speed = CAR_SPEED
        self.target_speed = CAR_SPEED
        
        self.waiting_time = 0.0
        self.total_time = 0.0
    
        self.state = APPROACHING
        
        self.color = random.choice(CAR_COLORS)
        
        self.has_entered_intersection = False

        self.finished = False
        
        self.turn_progress = 0.0
        self.direction_x = 0
        self.direction_y = 1
        self.x=0.0
        self.y=0.0
        self.initialize_position()

    def initialize_position(self):
        # Dedicated offsets: RIGHT turns use right side, LEFT/THROUGH use left/center side
        offset = LANE_WIDTH * 0.5  # 50px

        if self.approach == NORTH:
            self.x = CENTER_X - offset if self.movement != RIGHT else CENTER_X - (ROAD_WIDTH // 2) + 25
            self.y = -CAR_LENGTH
            self.direction_x, self.direction_y = 0, 1

        elif self.approach == SOUTH:
            self.x = CENTER_X + offset if self.movement != RIGHT else CENTER_X + (ROAD_WIDTH // 2) - 25
            self.y = HEIGHT + CAR_LENGTH
            self.direction_x, self.direction_y = 0, -1

        elif self.approach == EAST:
            self.x = WIDTH + CAR_LENGTH
            self.y = CENTER_Y - offset if self.movement != RIGHT else CENTER_Y - (ROAD_WIDTH // 2) + 25
            self.direction_x, self.direction_y = -1, 0

        elif self.approach == WEST:
            self.x = -CAR_LENGTH
            self.y = CENTER_Y + offset if self.movement != RIGHT else CENTER_Y + (ROAD_WIDTH // 2) - 25
            self.direction_x, self.direction_y = 1, 0
    def stop_line_position(self):
    
        if self.approach == NORTH:
            return CENTER_Y - INTERSECTION_HALF - STOP_DISTANCE
    
        if self.approach == SOUTH:
            return CENTER_Y + INTERSECTION_HALF + STOP_DISTANCE
    
        if self.approach == EAST:
            return CENTER_X + INTERSECTION_HALF + STOP_DISTANCE
    
        if self.approach == WEST:
            return CENTER_X - INTERSECTION_HALF - STOP_DISTANCE
    def distance_to_stop_line(self):
    
        if self.approach == NORTH:
            return self.stop_line_position() - self.y
    
        if self.approach == SOUTH:
            return self.y - self.stop_line_position()
    
        if self.approach == EAST:
            return self.x - self.stop_line_position()
    
        if self.approach == WEST:
            return self.stop_line_position() - self.x
    def inside_intersection(self):
        
        return (
            CENTER_X - INTERSECTION_HALF <= self.x <=
            CENTER_X + INTERSECTION_HALF
            and
            CENTER_Y - INTERSECTION_HALF <= self.y <=
            CENTER_Y + INTERSECTION_HALF
        )
    def has_passed_stop_line(self):
        # Checks if the car's front edge has crossed the stop line for its direction
        stop_pos = self.stop_line_position()
        if self.approach == NORTH:
            return self.y >= stop_pos
        elif self.approach == SOUTH:
            return self.y <= stop_pos
        elif self.approach == EAST:
            return self.x <= stop_pos
        elif self.approach == WEST:
            return self.x >= stop_pos
        return False

    def should_stop(self, controller, cars):
        # 1. Never stop if actively executing a curve or past the stop line
        if self.state == TURNING or self.has_entered_intersection or self.has_passed_stop_line():
            return self.check_car_in_front(cars)

        # 2. Query traffic light state
        light_state = controller.get_light_state(self.approach, self.movement)
        dist = self.distance_to_stop_line()

        if light_state == "RED":
            # Always brake if approaching a red light
            if dist <= 120:
                return True

        elif light_state == "YELLOW":
            # Calculate minimum required stopping distance: d = v^2 / (2 * a)
            safe_stopping_distance = (self.speed ** 2) / (2 * CAR_DECELERATION) + 20

            # DILEMMA ZONE DECISION:
            # If closer than safe stopping distance, commitment is made -> proceed through!
            # If farther than safe stopping distance -> apply smooth brakes.
            if dist <= safe_stopping_distance:
                return self.check_car_in_front(cars)  # Proceed safely
            else:
                return True  # Apply brakes smoothly

        # 3. Check for queuing behind other cars
        return self.check_car_in_front(cars)

    def check_car_in_front(self, cars):
        for other in cars:
            if other is self:
                continue
            if other.approach != self.approach or other.movement != self.movement:
                continue

            # Ignore cars that have already committed to turning
            if other.state == TURNING:
                continue

            # Linear distance check for cars in the same approach lane
            if self.approach == NORTH and other.y > self.y:
                if (other.y - self.y) < CAR_LENGTH + MIN_CAR_GAP:
                    return True
            elif self.approach == SOUTH and other.y < self.y:
                if (self.y - other.y) < CAR_LENGTH + MIN_CAR_GAP:
                    return True
            elif self.approach == EAST and other.x < self.x:
                if (self.x - other.x) < CAR_LENGTH + MIN_CAR_GAP:
                    return True
            elif self.approach == WEST and other.x > self.x:
                if (other.x - self.x) < CAR_LENGTH + MIN_CAR_GAP:
                    return True

        return False
    def update(self, dt, controller, cars):
        self.total_time += dt

        # Determine target state
        stopping = self.should_stop(controller, cars)

        if stopping:
            # Smooth deceleration down to 0
            self.speed = max(0.0, self.speed - CAR_DECELERATION * dt)
        else:
            # Smooth acceleration up to max speed
            self.speed = min(CAR_SPEED, self.speed + CAR_ACCELERATION * dt)

        # Handle turns vs linear movement
        if self.movement == LEFT:
            self.handle_left_turn(dt)
        elif self.movement == RIGHT:
            self.handle_right_turn(dt)

        # Move position based on updated continuous speed
        if self.state != TURNING:
            self.x += self.direction_x * self.speed * dt
            self.y += self.direction_y * self.speed * dt

        self.check_if_finished()
    def check_if_finished(self):
    
            margin = 100
    
            if (
                self.x < -margin
                or self.x > WIDTH + margin
                or self.y < -margin
                or self.y > HEIGHT + margin
            ):
                self.finished = True
                self.state = LEAVING
    def handle_right_turn(self, dt):
        # Trigger right turn immediately upon passing the stop line!
        if not self.has_entered_intersection and self.has_passed_stop_line():
            self.has_entered_intersection = True
            self.state = TURNING
            self.setup_right_turn_points()

        if self.state == TURNING:
            self.turn_progress += (self.speed * dt) / 80.0

            if self.turn_progress >= 1.0:
                self.turn_progress = 1.0
                self.state = LEAVING
                self.x, self.y = self.p2
                self.update_right_exit_direction()
            else:
                self.x, self.y = get_bezier_point(
                    self.p0, self.p1, self.p2, self.turn_progress
                )

    def setup_right_turn_points(self):
        # Lane offset for the rightmost lane center (e.g., 75px from road center)
        r_offset = (ROAD_WIDTH // 2) - 25

        if self.approach == NORTH:
            # North -> West (Exiting Westbound: Westbound lanes are UPPER side, so Y = CENTER_Y - r_offset)
            self.p0 = (CENTER_X - r_offset, CENTER_Y - INTERSECTION_HALF)
            self.p1 = (CENTER_X - INTERSECTION_HALF, CENTER_Y - INTERSECTION_HALF)
            self.p2 = (CENTER_X - INTERSECTION_HALF, CENTER_Y - r_offset)

        elif self.approach == SOUTH:
            # South -> East (Exiting Eastbound: Eastbound lanes are LOWER side, so Y = CENTER_Y + r_offset)
            self.p0 = (CENTER_X + r_offset, CENTER_Y + INTERSECTION_HALF)
            self.p1 = (CENTER_X + INTERSECTION_HALF, CENTER_Y + INTERSECTION_HALF)
            self.p2 = (CENTER_X + INTERSECTION_HALF, CENTER_Y + r_offset)

        elif self.approach == EAST:
            # East -> North (Exiting Northbound: Northbound lanes are RIGHT side, so X = CENTER_X + r_offset)
            self.p0 = (CENTER_X + INTERSECTION_HALF, CENTER_Y - r_offset)
            self.p1 = (CENTER_X + INTERSECTION_HALF, CENTER_Y - INTERSECTION_HALF)
            self.p2 = (CENTER_X + r_offset, CENTER_Y - INTERSECTION_HALF)

        elif self.approach == WEST:
            # West -> South (Exiting Southbound: Southbound lanes are LEFT side, so X = CENTER_X - r_offset)
            self.p0 = (CENTER_X - INTERSECTION_HALF, CENTER_Y + r_offset)
            self.p1 = (CENTER_X - INTERSECTION_HALF, CENTER_Y + INTERSECTION_HALF)
            self.p2 = (CENTER_X - r_offset, CENTER_Y + INTERSECTION_HALF)
    def update_right_exit_direction(self):
        if self.approach == NORTH:   # Turning West
            self.direction_x, self.direction_y = -1, 0
        elif self.approach == SOUTH: # Turning East
            self.direction_x, self.direction_y = 1, 0
        elif self.approach == EAST:  # Turning North
            self.direction_x, self.direction_y = 0, -1
        elif self.approach == WEST:  # Turning South
            self.direction_x, self.direction_y = 0, 1
    def handle_left_turn(self, dt):
            if not self.has_entered_intersection and self.inside_intersection():
                self.has_entered_intersection = True
                self.state = TURNING
                self.setup_bezier_points()

            if self.state == TURNING:
                # Advance interpolation based on car speed
                # (Turn path length is approximately 150px)
                self.turn_progress += (self.speed * dt) / 150.0

                if self.turn_progress >= 1.0:
                    # Turn finished - snap to exit line direction
                    self.turn_progress = 1.0
                    self.state = LEAVING
                    self.x, self.y = self.p2
                    self.update_exit_direction()
                else:
                    # Interpolate smooth position along curve
                    self.x, self.y = get_bezier_point(self.p0, self.p1, self.p2, self.turn_progress)

    def setup_bezier_points(self):
        offset = LANE_WIDTH * 0.5  # 50px offset to center in-lane

        if self.approach == NORTH:
            # North -> East (Turning towards positive X)
            self.p0 = (CENTER_X - offset, CENTER_Y - INTERSECTION_HALF)
            self.p1 = (CENTER_X - offset, CENTER_Y + offset)
            self.p2 = (CENTER_X + INTERSECTION_HALF, CENTER_Y + offset)

        elif self.approach == SOUTH:
            # South -> West (Turning towards negative X)
            self.p0 = (CENTER_X + offset, CENTER_Y + INTERSECTION_HALF)
            self.p1 = (CENTER_X + offset, CENTER_Y - offset)
            self.p2 = (CENTER_X - INTERSECTION_HALF, CENTER_Y - offset)

        elif self.approach == EAST:
            # East -> South (Turning towards positive Y)
            self.p0 = (CENTER_X + INTERSECTION_HALF, CENTER_Y - offset)
            self.p1 = (CENTER_X - offset, CENTER_Y - offset)
            self.p2 = (CENTER_X - offset, CENTER_Y + INTERSECTION_HALF)

        elif self.approach == WEST:
            # West -> North (Turning towards negative Y)
            self.p0 = (CENTER_X - INTERSECTION_HALF, CENTER_Y + offset)
            self.p1 = (CENTER_X + offset, CENTER_Y + offset)
            self.p2 = (CENTER_X + offset, CENTER_Y - INTERSECTION_HALF)
    def update_exit_direction(self):
        if self.approach == NORTH:   # North -> East
            self.direction_x, self.direction_y = 1, 0
        elif self.approach == SOUTH: # South -> West
            self.direction_x, self.direction_y = -1, 0
        elif self.approach == EAST:  # East -> South
            self.direction_x, self.direction_y = 0, 1
        elif self.approach == WEST:  # West -> North
            self.direction_x, self.direction_y = 0, -1
    def draw(self, screen):
    
            if self.direction_x != 0:
    
                rect_width = CAR_LENGTH
                rect_height = CAR_WIDTH
    
            else:
    
                rect_width = CAR_WIDTH
                rect_height = CAR_LENGTH
    
            rect = pygame.Rect(
                int(self.x - rect_width / 2),
                int(self.y - rect_height / 2),
                rect_width,
                rect_height,
            )
    
            pygame.draw.rect(
                screen,
                self.color,
                rect,
                border_radius=4,
            )
    
            # Small windshield
            pygame.draw.rect(
                screen,
                (180, 220, 230),
                (
                    rect.x + rect.width * 0.25,
                    rect.y + rect.height * 0.15,
                    rect.width * 0.5,
                    rect.height * 0.2,
                ),
            )
class Statistics:
    def __init__(self):
        self.total_cars= 0
        self.completed_cars=0
        self.total_waiting_time=0.0
        self.maximum_queue=0
        self.current_waiting_cars=0
    def register_car(self):
        self.total_cars+= 1
        
    def register_completed_car(self, car):
        self.completed_cars += 1
        self.total_waiting_time += car.waiting_time
            
    def update(self,cars):
        waiting=0
        for car in cars:
            if car.state == WAITING:
                waiting +=1
        self.current_waiting_cars = waiting
        self.maximum_queue = max(waiting, self.maximum_queue)
    def average_waiting_time(self):
        if self.completed_cars == 0:
            return 0
        return self.total_waiting_time / self.completed_cars

def draw_roads(screen):

    # --------------------------------------------------------
    # Horizontal road
    # --------------------------------------------------------

    horizontal_rect = pygame.Rect(
        0,
        CENTER_Y - ROAD_WIDTH // 2,
        WIDTH,
        ROAD_WIDTH,
    )

    pygame.draw.rect(
        screen,
        ROAD_LINE,
        horizontal_rect,
    )

    # --------------------------------------------------------
    # Vertical road
    # --------------------------------------------------------

    vertical_rect = pygame.Rect(
        CENTER_X - ROAD_WIDTH // 2,
        0,
        ROAD_WIDTH,
        HEIGHT,
    )

    pygame.draw.rect(
        screen,
        ROAD_LINE,
        vertical_rect,
    )

    # --------------------------------------------------------
    # Horizontal lane divider
    # --------------------------------------------------------

    pygame.draw.line(
        screen,
        LANE_LINE_COLOR,
        (0, CENTER_Y),
        (CENTER_X - INTERSECTION_HALF, CENTER_Y),
        2,
    )

    pygame.draw.line(
        screen,
        LANE_LINE_COLOR,
        (CENTER_X + INTERSECTION_HALF, CENTER_Y),
        (WIDTH, CENTER_Y),
        2,
    )

    # --------------------------------------------------------
    # Vertical lane divider
    # --------------------------------------------------------

    pygame.draw.line(
        screen,
        LANE_LINE_COLOR,
        (CENTER_X, 0),
        (CENTER_X, CENTER_Y - INTERSECTION_HALF),
        2,
    )

    pygame.draw.line(
        screen,
        LANE_LINE_COLOR,
        (CENTER_X, CENTER_Y + INTERSECTION_HALF),
        (CENTER_X, HEIGHT),
        2,
    )

    # --------------------------------------------------------
    # Stop lines
    # --------------------------------------------------------

    # North
    pygame.draw.line(
        screen,
        STOP_LINE_COLOR,
        (
            CENTER_X - ROAD_WIDTH // 2,
            CENTER_Y - INTERSECTION_HALF - STOP_DISTANCE,
        ),
        (
            CENTER_X + ROAD_WIDTH // 2,
            CENTER_Y - INTERSECTION_HALF - STOP_DISTANCE,
        ),
        4,
    )

    # South
    pygame.draw.line(
        screen,
        STOP_LINE_COLOR,
        (
            CENTER_X - ROAD_WIDTH // 2,
            CENTER_Y + INTERSECTION_HALF + STOP_DISTANCE,
        ),
        (
            CENTER_X + ROAD_WIDTH // 2,
            CENTER_Y + INTERSECTION_HALF + STOP_DISTANCE,
        ),
        4,
    )

    # East
    pygame.draw.line(
        screen,
        STOP_LINE_COLOR,
        (
            CENTER_X + INTERSECTION_HALF + STOP_DISTANCE,
            CENTER_Y - ROAD_WIDTH // 2,
        ),
        (
            CENTER_X + INTERSECTION_HALF + STOP_DISTANCE,
            CENTER_Y + ROAD_WIDTH // 2,
        ),
        4,
    )

    # West
    pygame.draw.line(
        screen,
        STOP_LINE_COLOR,
        (
            CENTER_X - INTERSECTION_HALF - STOP_DISTANCE,
            CENTER_Y - ROAD_WIDTH // 2,
        ),
        (
            CENTER_X - INTERSECTION_HALF - STOP_DISTANCE,
            CENTER_Y + ROAD_WIDTH // 2,
        ),
        4,
    )
def create_traffic_lights(controller):

    lights = []

    lights.append(
        traffic_light(
            CENTER_X ,
            CENTER_Y - 130,
            NORTH,
            controller,
        )
    )

    lights.append(
        traffic_light(
            CENTER_X ,
            CENTER_Y + 130,
            SOUTH,
            controller,
        )
    )

    lights.append(
        traffic_light(
            CENTER_X + 130,
            CENTER_Y ,
            EAST,
            controller,
        )
    )

    lights.append(
        traffic_light(
            CENTER_X - 130,
            CENTER_Y ,
            WEST,
            controller,
        )
    )

    return lights
def spawn_car(cars):

    approach = random.choice([
        NORTH,
        SOUTH,
        EAST,
        WEST,
    ])

    movement = random.choice([
        LEFT,
        THROUGH,
        RIGHT,
    ])

    new_car = Car(
        approach,
        movement,
    )

    # Avoid spawning directly on top of another car.
    for car in cars:

        if distance(
            new_car.x,
            new_car.y,
            car.x,
            car.y,
        ) < CAR_LENGTH * 2:

            return None

    cars.append(new_car)

    return new_car
def draw_information(
    screen,
    font,
    controller,
    statistics,
):

    lines = [

        f"Phase: {controller.current_phase.name}",

        f"Phase time remaining: "
        f"{controller.get_remaining_time():.1f}s",

        f"Cars generated: "
        f"{statistics.total_cars}",

        f"Cars completed: "
        f"{statistics.completed_cars}",

        f"Waiting cars: "
        f"{statistics.current_waiting_cars}",

        f"Maximum queue: "
        f"{statistics.maximum_queue}",

        f"Average waiting time: "
        f"{statistics.average_waiting_time():.2f}s",
    ]

    y = 15

    for text in lines:

        surface = font.render(
            text,
            True,
            WHITE,
        )

        screen.blit(
            surface,
            (15, y),
        )

        y += 25
def main():

    pygame.init()

    screen = pygame.display.set_mode(
        (WIDTH, HEIGHT)
    )

    pygame.display.set_caption(
        "AI Traffic Light Simulation - Version 1"
    )

    clock = pygame.time.Clock()

    font = pygame.font.SysFont(
        "Arial",
        18,
    )

    controller = traffic_controller()

    statistics = Statistics()

    traffic_lights = create_traffic_lights(
        controller
    )

    cars = []

    running = True

    spawn_timer = 0.0

    # --------------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------------

    while running:

        # ----------------------------------------------------
        # DELTA TIME
        # ----------------------------------------------------

        dt = clock.tick(FPS) / 1000.0

        # Prevent very large dt values if the program freezes.
        dt = min(dt, 0.1)

        # ----------------------------------------------------
        # EVENTS
        # ----------------------------------------------------

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                running = False

        # ----------------------------------------------------
        # UPDATE TRAFFIC CONTROLLER
        # ----------------------------------------------------

        controller.update(dt)

        # ----------------------------------------------------
        # SPAWN CARS
        # ----------------------------------------------------

        spawn_timer += dt

        if spawn_timer >= SPAWN_INTERVAL:

            spawn_timer = 0

            new_car = spawn_car(cars)

            if new_car is not None:

                statistics.register_car()

        # ----------------------------------------------------
        # UPDATE CARS
        # ----------------------------------------------------

        for car in cars:

            car.update(
                dt,
                controller,
                cars,
            )

        # ----------------------------------------------------
        # REMOVE FINISHED CARS
        # ----------------------------------------------------

        remaining_cars = []

        for car in cars:

            if car.finished:

                statistics.register_completed_car(
                    car
                )

            else:

                remaining_cars.append(car)

        cars = remaining_cars

        # ----------------------------------------------------
        # UPDATE STATISTICS
        # ----------------------------------------------------

        statistics.update(cars)

        # ----------------------------------------------------
        # DRAW
        # ----------------------------------------------------

        screen.fill(
            BACKGROUND_COLOR
        )

        draw_roads(screen)

        # Traffic lights
        for light in traffic_lights:

            light.draw(screen)

        # Cars
        for car in cars:

            car.draw(screen)

        # Information panel
        draw_information(
            screen,
            font,
            controller,
            statistics,
        )

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

        



         