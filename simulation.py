import pygame
import math
import random

HEIGHT= 800
WIDTH= 1200

FPS= 60

LANE_WIDTH= 55
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
MIN_CAR_GAP= 12
CAR_COLORS = [
    (50, 120, 220),
    (220, 80, 70),
    (230, 170, 50),
    (120, 80, 200),
    (50, 180, 170),
    (220, 120, 50),
]

SPAWN_INTERVAL= 0.65

NS_LEFT_TIME = 4.0
NS_THROUGH_TIME = 4.0
EW_LEFT_TIME = 4.0
EW_THROUGH_TIME = 4.0
YELLOW_TIME = 3.0
STOP_DISTANCE = 35

NORTH= "north"
SOUTH= "south"
EAST= "east"
WEST= "west"

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
                (SOUTH,THROUGH)
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
                    (EAST,THROUGH)
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
class Car:
    def __init__(self,approach,movement):
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
    
            offset = LANE_WIDTH * 0.5
    
            if self.approach == NORTH:
    
                self.x = CENTER_X - offset
                self.y = -CAR_LENGTH
    
                self.direction_x = 0
                self.direction_y = 1
    
            elif self.approach == SOUTH:
    
                self.x = CENTER_X + offset
                self.y = HEIGHT + CAR_LENGTH
    
                self.direction_x = 0
                self.direction_y = -1
    
            elif self.approach == EAST:
    
                self.x = WIDTH + CAR_LENGTH
                self.y = CENTER_Y + offset
    
                self.direction_x = -1
                self.direction_y = 0
    
            elif self.approach == WEST:
    
                self.x = -CAR_LENGTH
                self.y = CENTER_Y - offset
    
                self.direction_x = 1
                self.direction_y = 0
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
    def should_stop(self, controller, cars):
    
            # Once inside the intersection, do not stop.
            if self.inside_intersection():
                return False
    
            allowed = controller.is_movement_allowed(
                self.approach,
                self.movement
            )
    
            if not allowed:
    
                if self.distance_to_stop_line() <= 80:
                    return True
    
            # Check car in front.
            for other in cars:
    
                if other is self:
                    continue
    
                if other.approach != self.approach:
                    continue
    
                if other.movement != self.movement:
                    continue
    
                # Same lane and ahead
                if self.approach == NORTH:
    
                    if other.y > self.y:
                        gap = other.y - self.y
    
                        if gap < CAR_LENGTH + MIN_CAR_GAP:
                            return True
    
                elif self.approach == SOUTH:
    
                    if other.y < self.y:
                        gap = self.y - other.y
    
                        if gap < CAR_LENGTH + MIN_CAR_GAP:
                            return True
    
                elif self.approach == EAST:
    
                    if other.x < self.x:
                        gap = self.x - other.x
    
                        if gap < CAR_LENGTH + MIN_CAR_GAP:
                            return True
    
                elif self.approach == WEST:
    
                    if other.x > self.x:
                        gap = other.x - self.x
    
                        if gap < CAR_LENGTH + MIN_CAR_GAP:
                            return True
    
            return False
    def update(self, dt, controller, cars):
    
            self.total_time += dt
    
            stopping = self.should_stop(controller, cars)
    
            if stopping:
    
                self.target_speed = 0
    
                self.state = WAITING
                self.waiting_time += dt
    
            else:
    
                self.target_speed = CAR_SPEED
    
                if self.inside_intersection():
                    self.state = CROSSING
                else:
                    self.state = APPROACHING
    
            # Acceleration/deceleration
    
            if self.speed < self.target_speed:
    
                self.speed += CAR_ACCELERATION * dt
                self.speed = min(self.speed, self.target_speed)
    
            elif self.speed > self.target_speed:
    
                self.speed -= CAR_DECELERATION * dt
                self.speed = max(self.speed, self.target_speed)
    
            # Move car
    
            self.x += self.direction_x * self.speed * dt
            self.y += self.direction_y * self.speed * dt
    
            # Handle turning
    
            if self.movement == LEFT:
    
                self.handle_left_turn()
    
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
    def handle_left_turn(self):
    
            if self.has_entered_intersection:
                return
    
            if self.inside_intersection():
    
                self.has_entered_intersection = True
                self.state = TURNING
    
                if self.approach == NORTH:
    
                    # North -> West
                    self.direction_x = -1
                    self.direction_y = 0
    
                    self.x = CENTER_X
                    self.y = CENTER_Y
    
                elif self.approach == SOUTH:
    
                    # South -> East
                    self.direction_x = 1
                    self.direction_y = 0
    
                    self.x = CENTER_X
                    self.y = CENTER_Y
    
                elif self.approach == EAST:
    
                    # East -> North
                    self.direction_x = 0
                    self.direction_y = -1
    
                    self.x = CENTER_X
                    self.y = CENTER_Y
    
                elif self.approach == WEST:
    
                    # West -> South
                    self.direction_x = 0
                    self.direction_y = 1
    
                    self.x = CENTER_X
                    self.y = CENTER_Y
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
            CENTER_X - 100,
            CENTER_Y - 130,
            NORTH,
            controller,
        )
    )

    lights.append(
        traffic_light(
            CENTER_X + 100,
            CENTER_Y + 130,
            SOUTH,
            controller,
        )
    )

    lights.append(
        traffic_light(
            CENTER_X + 130,
            CENTER_Y - 100,
            EAST,
            controller,
        )
    )

    lights.append(
        traffic_light(
            CENTER_X - 130,
            CENTER_Y + 100,
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

        



         